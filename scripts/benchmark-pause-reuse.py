#!/usr/bin/env python3
"""Experimental pause-based batch reuse; saved audio stays on this Mac.

Outputs word disagreement against the installed batch decoder, not an accuracy
score. This script does not modify the installed app or enable this strategy.
"""
import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('replay_helpers', ROOT/'scripts/benchmark-streaming-reuse.py')
helpers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'target/streaming-reuse-2026-09-11/results.json')
    p.add_argument('--output',type=Path,default=ROOT/'target/pause-reuse-2026-09-11')
    p.add_argument('--pause',type=float,default=0.4)
    args = p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    import mlx.core as mx
    import numpy as np
    import sentencepiece as spm
    from parakeet_mlx import from_pretrained
    from parakeet_mlx.audio import get_logmel
    from sidecar.asr_server import read_wav, transcribe_file
    from sidecar.dictionary_bias import compile_bias, generate_with_bias, recognition_terms, restore_case, support_directory

    snapshot=Path.home()/'.cache/huggingface/hub/models--mlx-community--parakeet-tdt-0.6b-v2/snapshots/8ae155301e23d820d82aa60d24817c900e69e487'
    model=from_pretrained(str(snapshot))
    mx.eval(model.parameters())
    terms=recognition_terms(support_directory())
    tokenizer=spm.SentencePieceProcessor(model_file=str(snapshot/'tokenizer.model'))
    bias=compile_bias(terms,tokenizer,model.vocabulary)
    rate=model.preprocessor_config.sample_rate
    frame=round(rate*.02)
    def decode(audio):
        mel=get_logmel(mx.array(audio,dtype=mx.float32),model.preprocessor_config)
        result=generate_with_bias(model,mel,bias)[0]
        return restore_case(result.text.strip(),terms)
    transcribe_file(model,str(ROOT/'assets/startup.wav'),bias)
    cases=json.loads(args.source.read_text())
    rows=[]
    for case in cases:
        wav=support_directory()/'Corpus'/case['id']/'audio.wav'
        digest=hashlib.sha256(wav.read_bytes()).hexdigest()
        audio=read_wav(str(wav),rate)
        segment_start=0
        quiet=0
        saw_voice=False
        frame_levels=[]
        chunks=[]
        virtual_done=0.0
        for start in range(0,len(audio),frame):
            end=min(start+frame,len(audio))
            rms=float(np.sqrt(np.mean(audio[start:end]**2)))*32768
            frame_levels.append(rms)
            # Causal floor estimate: only preceding two seconds are available.
            floor=float(np.quantile(frame_levels[-100:],.15))
            threshold=max(180,min(500,floor*2))
            if rms>=threshold:
                quiet=0
                saw_voice=True
            else:
                quiet+=end-start
            if saw_voice and quiet>=rate*args.pause and end-segment_start>=rate*2:
                t=time.perf_counter()
                text=decode(audio[segment_start:end])
                elapsed=time.perf_counter()-t
                virtual_done=max(virtual_done,end/rate)+elapsed
                chunks.append({'start':segment_start/rate,'end':end/rate,'text':text,'compute_ms':elapsed*1000})
                segment_start=end
                saw_voice=False
                quiet=0
        t=time.perf_counter()
        tail_text=decode(audio[segment_start:]) if saw_voice and len(audio)-segment_start>=rate*.08 else ''
        tail_ms=(time.perf_counter()-t)*1000
        text=' '.join([c['text'] for c in chunks]+([tail_text] if tail_text else [])).strip()
        assert digest==hashlib.sha256(wav.read_bytes()).hexdigest()
        row={'id':case['id'],'sha256':digest,'duration_seconds':len(audio)/rate,
            'batch_text':case['batch_text'],'text':text,'chunks':chunks,
            'tail_seconds':(len(audio)-segment_start)/rate,'tail_text':tail_text,
            'tail_compute_ms':tail_ms,'estimated_after_release_ms':max(0,virtual_done-len(audio)/rate)*1000+tail_ms,
            'word_edits_vs_batch':helpers.distance(helpers.words(case['batch_text']),helpers.words(text)),
            'batch_word_count':len(helpers.words(case['batch_text']))}
        rows.append(row)
        (args.output/'results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
        print(json.dumps({k:row[k] for k in ['id','duration_seconds','tail_seconds','word_edits_vs_batch','estimated_after_release_ms']}),flush=True)
    summary={'pause_seconds':args.pause,'recordings':len(rows),
        'same_words_count':sum(r['word_edits_vs_batch']==0 for r in rows),
        'word_edits_vs_batch':sum(r['word_edits_vs_batch'] for r in rows),
        'reference_words':sum(r['batch_word_count'] for r in rows),
        'median_estimated_after_release_ms':statistics.median(r['estimated_after_release_ms'] for r in rows)}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2))
    print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
