#!/usr/bin/env python3
"""Replay full-quality streaming checkpoints plus an overlapping final tail.

Experimental only. Benchmarks local computation, not live microphone-to-paste
latency. Parameters are fixed before replay; mismatched anchors fall back to
full batch recognition. All transcripts remain in the ignored output folder.
"""
import argparse
import hashlib
import importlib.util
import json
import statistics
import sys
import time
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('helpers',ROOT/'scripts/benchmark-streaming-reuse.py')
helpers=importlib.util.module_from_spec(spec)
spec.loader.exec_module(helpers)


def find_anchor(previous, tail, offset, checkpoint_end):
    """Join only on >=8 matching subword IDs with consistent audio timestamps.

    Both sides need two seconds of shared context before the anchor. Keep its
    end away from the unfinished checkpoint boundary. Relative timestamps
    disambiguate repeated phrases. Returning None requests full batch fallback.
    """
    best=None
    for i,a in enumerate(previous):
        if not offset+2 <= a.start <= checkpoint_end-1:
            continue
        for j,b in enumerate(tail):
            if a.id!=b.id or abs(a.start-(offset+b.start))>.4:
                continue
            length=0
            while i+length<len(previous) and j+length<len(tail):
                x,y=previous[i+length],tail[j+length]
                if x.id!=y.id or abs(x.start-(offset+y.start))>.4 or x.end>checkpoint_end-.4:
                    break
                length+=1
            if length>=8 and (best is None or length>best[0]):
                best=(length,i,j)
    if best is None:
        return None
    return best


def merge_anchor(previous, tail, offset, checkpoint_end):
    anchor=find_anchor(previous,tail,offset,checkpoint_end)
    if anchor is None:return None
    _,i,j=anchor
    return ''.join(t.text for t in previous[:i])+''.join(t.text for t in tail[j:])


def merge_checkpoint(previous,tail,offset,checkpoint_end):
    anchor=find_anchor(previous.tokens,tail.tokens,offset,checkpoint_end)
    if anchor is None:return None
    _,i,j=anchor
    tokens=previous.tokens[:i]+[replace(t,start=t.start+offset) for t in tail.tokens[j:]]
    return SimpleNamespace(tokens=tokens,text=''.join(t.text for t in tokens))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,default=ROOT/'target/streaming-reuse-2026-09-11/results.json')
    p.add_argument('--output',type=Path,default=ROOT/'target/checkpoint-reuse-2026-09-11')
    p.add_argument('--context',type=float,default=8)
    p.add_argument('--interval',type=float,default=2)
    p.add_argument('--rolling',action='store_true')
    p.add_argument('--pause-checkpoints',action='store_true')
    p.add_argument('--id',action='append',default=[])
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    import mlx.core as mx
    import numpy as np
    import sentencepiece as spm
    from parakeet_mlx import from_pretrained
    from parakeet_mlx.audio import get_logmel
    from sidecar.asr_server import read_wav,transcribe_file
    from sidecar.dictionary_bias import compile_bias,generate_with_bias,recognition_terms,restore_case,support_directory
    snapshot=Path.home()/'.cache/huggingface/hub/models--mlx-community--parakeet-tdt-0.6b-v2/snapshots/8ae155301e23d820d82aa60d24817c900e69e487'
    model=from_pretrained(str(snapshot));mx.eval(model.parameters())
    terms=recognition_terms(support_directory())
    tok=spm.SentencePieceProcessor(model_file=str(snapshot/'tokenizer.model'))
    bias=compile_bias(terms,tok,model.vocabulary)
    rate=model.preprocessor_config.sample_rate
    def decode(audio):
        return generate_with_bias(model,get_logmel(mx.array(audio,dtype=mx.float32),model.preprocessor_config),bias)[0]
    transcribe_file(model,str(ROOT/'assets/startup.wav'),bias)
    cases=json.loads(args.source.read_text())
    if args.id:cases=[c for c in cases if c['id'] in args.id]
    rows=[]
    for case in cases:
        wav=support_directory()/'Corpus'/case['id']/'audio.wav'
        digest=hashlib.sha256(wav.read_bytes()).hexdigest()
        audio=read_wav(str(wav),rate);duration=len(audio)/rate
        checkpoint=None;checkpoint_end=0;virtual_done=0;costs=[];checkpoint_fallbacks=0
        # Each snapshot only sees samples available at its simulated arrival.
        # Actual live-worker scheduling/backpressure is a separate validation.
        ends=range(round(rate*args.interval),len(audio),round(rate*args.interval))
        if args.pause_checkpoints:
            ends=[];quiet=0;saw_voice=False;levels=[];last_end=0
            frame=round(rate*.02)
            for start in range(0,len(audio),frame):
                end=min(start+frame,len(audio))
                rms=float(np.sqrt(np.mean(audio[start:end]**2)))*32768
                levels.append(rms)
                threshold=max(180,min(500,float(np.quantile(levels[-100:],.15))*2))
                if rms>=threshold:quiet=0;saw_voice=True
                else:quiet+=end-start
                if saw_voice and quiet>=rate*.4 and end>=rate*4 and end-last_end>=rate*args.interval and end<len(audio):
                    ends.append(end);last_end=end;saw_voice=False;quiet=0
        for end in ends:
            t=time.perf_counter()
            candidate=None
            if args.rolling and checkpoint is not None and checkpoint_end-args.context>=2:
                start=checkpoint_end-args.context
                candidate=merge_checkpoint(checkpoint,decode(audio[round(start*rate):end]),start,checkpoint_end)
                if candidate is None:checkpoint_fallbacks+=1
            checkpoint=candidate if candidate is not None else decode(audio[:end])
            elapsed=time.perf_counter()-t
            checkpoint_end=end/rate;virtual_done=max(virtual_done,checkpoint_end)+elapsed
            costs.append(elapsed*1000)
        final_start=time.perf_counter()
        offset=max(0,checkpoint_end-args.context)
        mode='full_short';text=None
        if checkpoint is not None and offset>=2:
            result=decode(audio[round(offset*rate):])
            text=merge_anchor(checkpoint.tokens,result.tokens,offset,checkpoint_end)
            mode='reuse' if text is not None else 'full_anchor_fallback'
        if text is None:text=decode(audio).text
        text=restore_case(text.strip(),terms)
        final_ms=(time.perf_counter()-final_start)*1000
        assert digest==hashlib.sha256(wav.read_bytes()).hexdigest()
        row={'id':case['id'],'sha256':digest,'duration_seconds':duration,'mode':mode,
            'batch_text':case['batch_text'],'text':text,'checkpoint_end_seconds':checkpoint_end,
            'tail_start_seconds':offset,'checkpoint_compute_ms':costs,'final_compute_ms':final_ms,
            'rolling':args.rolling,'pause_checkpoints':args.pause_checkpoints,'checkpoint_fallbacks':checkpoint_fallbacks,
            'estimated_after_release_ms':max(0,virtual_done-duration)*1000+final_ms,
            'word_edits_vs_batch':helpers.distance(helpers.words(case['batch_text']),helpers.words(text)),
            'reference_words':case['batch_word_count']}
        rows.append(row)
        (args.output/'results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))
        print(json.dumps({k:row[k] for k in ['id','duration_seconds','mode','word_edits_vs_batch','estimated_after_release_ms']}),flush=True)
    summary={'recordings':len(rows),'context_seconds':args.context,'checkpoint_interval_seconds':args.interval,
        'rolling':args.rolling,'pause_checkpoints':args.pause_checkpoints,'mlx_peak_allocated_gb':mx.get_peak_memory()/1e9,
        'same_words_count':sum(r['word_edits_vs_batch']==0 for r in rows),
        'reuse_count':sum(r['mode']=='reuse' for r in rows),
        'word_edits_vs_batch':sum(r['word_edits_vs_batch'] for r in rows),
        'reference_words':sum(r['reference_words'] for r in rows),
        'median_estimated_after_release_ms':statistics.median(r['estimated_after_release_ms'] for r in rows)}
    (args.output/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)


if __name__=='__main__':main()
