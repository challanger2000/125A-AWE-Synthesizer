#!/usr/bin/env python3
"""Reconstruct actual P45 Creative DMA writes, reuse P83 RIFF parser.
Private sample words never enter numeric output or Git.
"""
import csv,hashlib,io,json,pathlib,struct,sys
import numpy as np
sys.path.insert(0,'/workspace/awe-v25-independent/tools')
from p83_generic_sf2 import chunks
r=pathlib.Path('/tmp/awe-sf2-117-evidence');p=pathlib.Path('/tmp/awe-sf2-private-20261111')
names=['Synth 512 Bank(3).sf2','FM Dreams Sampler(1).sf2','Vintage Dreams Bank.sf2','Vintage Synth 2001.sf2']
for arg in sys.argv[1:]:
 b=int(arg);cases=json.load((r/f'original-bank-{b}/matched-results.json').open());stop=cases[0]['original_trace_byte_range'][0]
 folder='guest-bank-2-fixed-inventory' if b==2 else f'guest-bank-{b}'
 trace=r/folder/'win95-pnp/driver-potential-emu8000-io.csv'
 ram=np.zeros(0x1000000,dtype='<u2');seen=np.zeros(len(ram),dtype=np.bool_);addr=0;writes=0
 with trace.open('rb') as f:data=f.read(stop)
 assert len(data)==stop and data.endswith(b'\n')
 for a in csv.DictReader(io.StringIO(data.decode())):
  if a['kind']!='data' or a['reg']!='1':continue
  port=int(a['port'],16);voice=int(a['voice']);val=int(a['value'],16)
  if port not in (0xa20,0xa22):continue
  if voice==22:addr=((addr&0xffff)|(val<<16)) if port==0xa22 else ((addr&0xffff0000)|val)
  if voice==26:
   k=addr&0xffffff;ram[k]=val;seen[k]=True;addr=(addr+1)&0xffffff;writes+=1
 raw=(p/names[b]).read_bytes();sec={}
 for tag,body in chunks(raw,12,len(raw)):
  if tag==b'LIST':
   for k,v in chunks(body,4,len(body)):sec[(body[:4],k)]=v
 x=np.frombuffer(sec[(b'sdta',b'smpl')],dtype='<i2').astype(np.int64)
 sh=list(struct.iter_unpack('<20sIIIIIBbHH',sec[(b'pdta',b'shdr')]))[:-1]
 model=np.zeros_like(x);used=np.zeros(len(x),dtype=bool);interior=np.zeros(len(x),dtype=bool)
 for s in sh:
  if s[-1]&0x8000:continue
  st,en=s[1:3];idx=np.arange(st,en)
  prev=np.where(idx>st,x[np.maximum(idx-1,0)],0)
  nxt=np.where(idx+1<en,x[np.minimum(idx+1,len(x)-1)],0)
  model[idx]=np.clip((6*x[idx]-prev-nxt)//8,-32768,32767)
  used[idx]=True;interior[st+8:max(st+8,en-3)]=True
 y=ram[0x200010:0x200010+len(x)].view('<i2').astype(np.int64)
 coverage=seen[0x200010:0x200010+len(x)]
 assert coverage.all(),'Cannot substitute unobserved sample RAM'
 (r/f'original-bank-{b}-memory.u16le').write_bytes(ram.tobytes())
 a=dict(bank_index=b,file=names[b],source_sha256=hashlib.sha256(raw).hexdigest(),dram_upload_base='0x200010',smpl_words=len(x),observed_written_words=int(coverage.sum()),original_dma_writes=writes,
  raw_mismatch_words=int(np.count_nonzero(x!=y)),raw_rmse=float(np.sqrt(np.mean((x-y)**2))),
  full_sample_preemphasis_model_mismatch_words=int(np.count_nonzero(model!=y)),model_rmse=float(np.sqrt(np.mean((model-y)**2))),
  sample_words=int(used.sum()),interior_words=int(interior.sum()),interior_model_mismatch_words=int(np.count_nonzero(model[interior]!=y[interior])),
  boundary_or_padding_model_mismatch_words=int(np.count_nonzero(model[~interior]!=y[~interior])),
  model='clip16(floor((6*x-prev-next)/8)) on each whole non-ROM sample, outside neighbours/padding 0; boundary exceptions reported, never fitted',
  observed_smpl_ram_sha256=hashlib.sha256(y.astype('<i2').tobytes()).hexdigest(),trace_sha256_before_first_case=hashlib.sha256(data).hexdigest())
 (r/f'original-bank-{b}-upload-analysis.json').write_text(json.dumps(a,indent=2)+'\n');print(json.dumps(a),flush=True)
