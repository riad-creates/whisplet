#!/usr/bin/env python3
"""Manual Mac/Metal integration check using synthetic speech, not recorded user audio.

Run with uv --with parakeet-mlx==0.5.2 --with sentencepiece==0.2.2.
Requires the pinned Parakeet model already cached. Output stays under target/.
"""
import json, sys, subprocess, time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'sidecar'))
from dictionary_bias import compile_bias
from asr_server import transcribe_file
from parakeet_mlx import from_pretrained
import sentencepiece as spm
folder=Path.home()/'.cache/huggingface/hub/models--mlx-community--parakeet-tdt-0.6b-v2/snapshots/8ae155301e23d820d82aa60d24817c900e69e487'
model=from_pretrained(str(folder))
tok=spm.SentencePieceProcessor(model_file=str(folder/'tokenizer.model'))
testdir=root/'target/dictionary-recognition-test';testdir.mkdir(parents=True,exist_ok=True)
cases=[
 ('name1','I use Phonon for dictation.'),
 ('name2','Please open Phonon.'),
 ('name3','Phonon is running on my Mac.'),
 ('name4','I installed phone on yesterday.'),
 ('name5','Phone on is a dictation application.'),
 ('ordinary1','Put my phone on the table.'),
 ('ordinary2','Please turn the phone on.'),
 ('ordinary3','I left my phone on the charger.'),
 ('ordinary4','Can you put your headphones on?'),
 ('ordinary5','Please send the report by Friday.'),
 ('ordinary6','Peter and Philip will join the meeting.'),
]
report=[]
for name,text in cases:
 source=testdir/(name+'.txt');source.write_text(text)
 audio=testdir/(name+'.wav')
 if not audio.exists():
  aiff=testdir/(name+'.aiff')
  subprocess.run(['/usr/bin/say','-v','Samantha','-r','185','-f',str(source),'-o',str(aiff)],check=True)
  subprocess.run(['/usr/bin/afconvert','-f','WAVE','-d','LEI16@16000','-c','1',str(aiff),str(audio)],check=True)
 row={'name':name,'synthesized_text':text,'outputs':{}}
 for strength in [0,1.5]:
  bias=compile_bias(['Phonon'],tok,model.vocabulary,strength)
  start=time.perf_counter();out=transcribe_file(model,str(audio),bias)
  row['outputs'][str(strength)]={'text':out.text,'ms':round((time.perf_counter()-start)*1000)}
 report.append(row);print(json.dumps(row),flush=True)
(testdir/'results.json').write_text(json.dumps(report,indent=2))
for row in report:
    if row['name'].startswith('ordinary'):
        assert row['outputs']['1.5']['text'] == row['outputs']['0']['text'], row
assert sum('phonon' in row['outputs']['1.5']['text'].lower() for row in report[:5]) >= 3
print('PASS: dictionary examples improve and ordinary-speech controls are unchanged')
