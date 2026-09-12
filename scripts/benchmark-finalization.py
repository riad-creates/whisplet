#!/usr/bin/env python3
"""Paced local replay of current streaming+batch versus batch-only finalization.

The audio arrives at its original rate. The measured clock starts at its end
and includes pending streaming work and teardown, but excludes the native app,
microphone, WAV writing and text insertion. Never changes app settings or audio.
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',type=Path,default=ROOT/'target/paced-finalization-2026-09-11')
    p.add_argument('--id',action='append',default=[])
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    import mlx.core as mx
    import sentencepiece as spm
    from parakeet_mlx import from_pretrained
    from sidecar.asr_server import read_wav,transcribe_file
    from sidecar.dictionary_bias import compile_bias,recognition_terms,restore_case,support_directory
    snapshot=Path.home()/'.cache/huggingface/hub/models--mlx-community--parakeet-tdt-0.6b-v2/snapshots/8ae155301e23d820d82aa60d24817c900e69e487'
    model=from_pretrained(str(snapshot));mx.eval(model.parameters())
    terms=recognition_terms(support_directory())
    tok=spm.SentencePieceProcessor(model_file=str(snapshot/'tokenizer.model'))
    bias=compile_bias(terms,tok,model.vocabulary)
    rate=model.preprocessor_config.sample_rate
    ids=args.id or ['bar_1789159104373_55500','bar_1789159135440_55500','bar_1789159172844_55500','bar_1789159255256_55500','bar_1789159324461_55500']
    transcribe_file(model,str(ROOT/'assets/startup.wav'),bias)
    rows=[]
    for index,rid in enumerate(ids):
        wav=support_directory()/'Corpus'/rid/'audio.wav'
        digest=hashlib.sha256(wav.read_bytes()).hexdigest()
        audio=read_wav(str(wav),rate);duration=len(audio)/rate
        modes=['current_streaming','batch_only'] if index%2==0 else ['batch_only','current_streaming']
        case={'id':rid,'sha256':digest,'duration_seconds':duration,'modes':{}}
        for mode in modes:
            print(json.dumps({'starting':rid,'mode':mode,'seconds':duration}),flush=True)
            stream=None
            if mode=='current_streaming':
                stream=model.transcribe_stream(context_size=(128,64));stream.__enter__()
            started=time.perf_counter()
            if stream is not None:
                step=round(rate*.4)
                for end in range(step,len(audio)+1,step):
                    time.sleep(max(0,started+end/rate-time.perf_counter()))
                    stream.add_audio(mx.array(audio[end-step:end],dtype=mx.bfloat16))
                    _=stream.result.text
            time.sleep(max(0,started+duration-time.perf_counter()))
            backlog_ms=max(0,time.perf_counter()-(started+duration))*1000
            t=time.perf_counter()
            if stream is not None:stream.__exit__(None,None,None)
            teardown_ms=(time.perf_counter()-t)*1000
            t=time.perf_counter()
            text=restore_case(transcribe_file(model,str(wav),bias).text.strip(),terms)
            compute_ms=(time.perf_counter()-t)*1000
            after_release_ms=(time.perf_counter()-(started+duration))*1000
            case['modes'][mode]={'text':text,'after_audio_end_ms':after_release_ms,
                'stream_backlog_ms':backlog_ms,'stream_teardown_ms':teardown_ms,'batch_compute_ms':compute_ms}
            print(json.dumps({'completed':rid,'mode':mode,'after_audio_end_ms':round(after_release_ms),'backlog_ms':round(backlog_ms),'teardown_ms':round(teardown_ms)}),flush=True)
        case['identical_final_text']=case['modes']['current_streaming']['text']==case['modes']['batch_only']['text']
        assert digest==hashlib.sha256(wav.read_bytes()).hexdigest()
        rows.append(case)
        (args.output/'results.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
