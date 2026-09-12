#!/usr/bin/env python3
"""JSONL correction sidecar: load the pinned MLX correction model, polish transcripts.

Speaks the same line protocol the engine already used for the correction stage:
  stdin:  {"command":"warmup"} | {"command":"run","inputText":"…"}
          {"command":"status"} | {"command":"shutdown"}
  stdout: {"ok":true,"status":{"state":"ready","message":"…"}}
          {"ok":true,"outputText":"…","diagnostics":{…}}
          {"ok":false,"error":"…"}
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
import time
import traceback

# S1-mini by Superwhisper was trained on this exact prompt and control format.
SYSTEM_PROMPT = (
    "You are a text normalizer for speech-to-text transcripts. The input begins "
    "with a control line specifying the styling, structure, and context settings; "
    "clean the transcript to match those settings and output only the cleaned text."
)
CONTROL = "[Styling: semi-formal] [Structure: prose] [Context: general]"
# The model card recommends ~1,000 input tokens. Leave room for the template.
INPUT_CHUNK_TOKENS = 768
OUTPUT_TOKEN_CEILING = 2048
OUTPUT_TOKEN_FLOOR = 64
LEAKED_MARKER_PATTERN = re.compile(r"<think>.*?</think>|<\|[^>]+\|>", re.DOTALL)


def emit(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def clean_output(text: str) -> str:
    return LEAKED_MARKER_PATTERN.sub("", text).strip()


def split_transcript(text: str, tokenizer, limit: int = INPUT_CHUNK_TOKENS) -> list[str]:
    """Lossless whitespace boundaries; an oversized single word is passed through."""
    chunks = []
    current = ""
    units = []
    for sentence in re.split(r"(?<=[.!?])(?=\s)|(?<=\n)(?=\S)", text):
        if len(tokenizer.encode(sentence)) > limit:
            units.extend(re.findall(r"\s+|\S+", sentence))
        elif sentence:
            units.append(sentence)
    for piece in units:
        if current and len(tokenizer.encode(current + piece)) > limit:
            chunks.append(current)
            current = ""
        current += piece
    if current:
        chunks.append(current)
    return chunks


def build_prompt(tokenizer, transcript: str) -> str:
    return tokenizer.apply_chat_template(
        [{"role": "system", "content": SYSTEM_PROMPT},
         {"role": "user", "content": f"{CONTROL}\n{transcript}"}],
        add_generation_prompt=True, tokenize=False, enable_thinking=False,
    )


def output_budget(tokenizer, text: str) -> int:
    return max(OUTPUT_TOKEN_FLOOR, min(
        OUTPUT_TOKEN_CEILING, math.ceil(len(tokenizer.encode(text)) * 1.8) + 32
    ))


def preserve_chunk(source: str, candidate: str, truncated: bool) -> str:
    # A token cap is a failed cleanup, never permission to drop the rest of speech.
    if truncated or not candidate:
        return source
    leading = source[:len(source) - len(source.lstrip())]
    trailing = source[len(source.rstrip()):]
    return leading + candidate + trailing


def normalize(text: str, tokenizer, generate) -> dict:
    started_at = time.perf_counter()
    ttft_ms = None
    generated = 0
    budget_total = 0
    fallback_count = 0
    outputs = []
    chunks = split_transcript(text, tokenizer)
    for source in chunks:
        spoken = source.strip()
        if not spoken or len(tokenizer.encode(spoken)) > INPUT_CHUNK_TOKENS:
            outputs.append(source)
            continue
        budget = output_budget(tokenizer, spoken)
        budget_total += budget
        pieces = []
        count = 0
        finish_reason = None
        for response in generate(build_prompt(tokenizer, spoken), budget):
            if ttft_ms is None:
                ttft_ms = (time.perf_counter() - started_at) * 1000
            pieces.append(response.text)
            count = response.generation_tokens
            finish_reason = getattr(response, "finish_reason", None)
        generated += count
        candidate = clean_output("".join(pieces))
        truncated = finish_reason == "length" or count >= budget
        fallback_count += int(truncated or not candidate)
        outputs.append(preserve_chunk(source, candidate, truncated))
    latency_ms = (time.perf_counter() - started_at) * 1000
    output = "".join(outputs)
    return {
        "ok": True, "outputText": output,
        "diagnostics": {
            "latencyMilliseconds": latency_ms,
            "timeToFirstTokenMilliseconds": ttft_ms or 0.0,
            "tokensPerSecond": generated / (latency_ms / 1000) if latency_ms else 0.0,
            "generatedTokenCount": generated,
            "inputCharacterCount": len(text), "outputCharacterCount": len(output),
            "maxOutputTokenBudget": budget_total,
            "chunkCount": len(chunks), "fallbackChunkCount": fallback_count,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--model", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--system-prompt-file")
    return parser.parse_known_args()[0]


def main() -> None:
    args = parse_args()

    emit({"ok": True, "status": {"state": "loading", "message": "importing MLX"}})
    try:
        from huggingface_hub import snapshot_download
        from mlx_lm import load
        from mlx_lm.generate import stream_generate
        from mlx_lm.sample_utils import make_sampler
    except Exception as error:  # noqa: BLE001 - report to the engine, never crash silently
        emit({"ok": False, "error": f"correction runtime import failed: {error}"})
        return

    emit(
        {
            "ok": True,
            "status": {
                "state": "loading",
                "message": f"resolving {args.model}@{args.revision[:7]}",
            },
        }
    )
    try:
        local_dir = snapshot_download(args.model, revision=args.revision)
    except Exception as error:  # noqa: BLE001
        emit({"ok": False, "error": f"correction model download failed: {error}"})
        return

    emit(
        {
            "ok": True,
            "status": {"state": "loading", "message": "loading weights (MLX)"},
        }
    )
    started = time.perf_counter()
    try:
        model, tokenizer = load(local_dir)
    except Exception as error:  # noqa: BLE001
        emit({"ok": False, "error": f"correction model load failed: {error}"})
        traceback.print_exc(file=sys.stderr)
        return
    load_seconds = time.perf_counter() - started

    if args.system_prompt_file:
        try:
            prompt = open(args.system_prompt_file, encoding="utf-8").read().strip()
            if prompt != SYSTEM_PROMPT:
                raise ValueError("S1-mini requires the exact Superwhisper system prompt")
        except (OSError, ValueError) as error:
            emit({"ok": False, "error": str(error)})
            return

    sampler = make_sampler(temp=0.0)

    def generate(prompt, budget):
        return stream_generate(model, tokenizer, prompt, max_tokens=budget, sampler=sampler)

    def run(text: str) -> dict:
        return normalize(text, tokenizer, generate)

    ready_message = f"S1-mini by Superwhisper loaded in {load_seconds:.1f}s"

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError as error:
            emit({"ok": False, "error": f"bad json: {error}"})
            continue
        command = request.get("command")
        if command == "shutdown":
            break
        if command == "status":
            emit({"ok": True, "status": {"state": "ready", "message": ready_message}})
            continue
        if command == "warmup":
            try:
                run("warmup pass")
            except Exception as error:  # noqa: BLE001
                emit({"ok": False, "error": f"warmup failed: {error}"})
                traceback.print_exc(file=sys.stderr)
                continue
            emit({"ok": True, "status": {"state": "ready", "message": ready_message}})
            continue
        if command == "run":
            text = request.get("inputText") or ""
            if not text.strip():
                emit({"ok": False, "error": "empty inputText"})
                continue
            try:
                emit(run(text))
            except Exception as error:  # noqa: BLE001
                emit({"ok": False, "error": f"correction failed: {error}"})
                traceback.print_exc(file=sys.stderr)
            continue
        emit({"ok": False, "error": f"unknown command: {command}"})


if __name__ == "__main__":
    main()
