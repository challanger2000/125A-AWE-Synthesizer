#!/usr/bin/env python3
"""Metadata-only cross-check of P228 regions and measured original IFATN.
Existing P83 RIFF parser; actual voice I/O from existing P89/P234 paths.
No renderer, no audio fitting, no ROM/SF2 payload in output.
"""
import csv,json,math,pathlib,struct,sys,collections
import numpy as np
from scipy.optimize import linear_sum_assignment
sys.path.insert(0,'/workspace/awe-v25-independent/tools')
from p83_generic_sf2 import chunks
r=pathlib.Path('/tmp/awe-sf2-117-evidence');p=pathlib.Path('/tmp/awe-sf2-private-20261111')
names=['Synth 512 Bank(3).sf2','FM Dreams Sampler(1).sf2','Vintage Dreams Bank.sf2','Vintage Synth 2001.sf2']
def tables(raw):
 sections={}
 for tag,body in chunks(raw,12,len(raw)):
  if tag==b'LIST':
   for k,v in chunks(body,4,len(body)):sections[(body[:4],k)]=v
 return {k:list(struct.iter_unpack(fmt,sections[(b'pdta',k)])) for k,fmt in [(b'phdr','<20sHHHIII'),(b'pbag','<HH'),(b'pgen','<Hh'),(b'inst','<20sH'),(b'ibag','<HH'),(b'igen','<Hh'),(b'shdr','<20sIIIIIBbHH')]}
def zones(t,bags,gens,lo,hi):
 return [dict(t[gens][t[bags][i][0]:t[bags][i+1][0]]) for i in range(lo,hi)]
def inside(g,n,v):
 for op,value in ((43,n),(44,v)):
  bounds=g.get(op,0x7f00)&0xffff
  if not (bounds&255)<=value<=bounds>>8:return False
 return True
def regions(t,program,note,velocity):
 hdr=t[b'phdr'];ix=next(i for i,v in enumerate(hdr[:-1]) if v[1:3]==(program,0));out=[];pg={}
 for zone in zones(t,b'pbag',b'pgen',hdr[ix][3],hdr[ix+1][3]):
  if 41 not in zone:pg.update(zone);continue
  preset=pg|zone
  if not inside(preset,note,velocity):continue
  ins=zone[41];ig={}
  for z in zones(t,b'ibag',b'igen',t[b'inst'][ins][1],t[b'inst'][ins+1][1]):
   if 53 not in z:ig.update(z);continue
   inst=ig|z
   if not inside(inst,note,velocity):continue
   sid=inst[53];sample=t[b'shdr'][sid]
   get=lambda op:inst.get(op,0)+preset.get(op,0)
   base=0 if sample[-1]&0x8000 else 0x200010
   start=base+sample[1]+get(0)+32768*get(4)-4
   loop=base+sample[3]+get(2)+32768*get(45)-1
   out.append(dict(sample_id=sid,ccca=start&0xffffff,psst=loop&0xffffff,
       initial_attenuation_cb=get(48),instrument_attenuation_cb=inst.get(48,0),preset_attenuation_cb=preset.get(48,0)))
 return out
def word(o,name):return o.get(name+'_LO',0)|(o.get(name+'_HI',0)<<16)
records=[];summary=[]
for b in range(4):
 t=tables((p/names[b]).read_bytes());cases=json.load((r/f'original-bank-{b}/matched-results.json').open());counts=collections.Counter()
 for case in cases:
  nr=case['native_noteon_registers'];orig=list(case['original_noteon_registers'].items());meta=regions(t,case['program'],case['note'],case['velocity'])
  assert len(meta)==len(nr),(b,case['case'],'metadata count')
  for m,n in zip(meta,nr):assert m['ccca']==int(n['CCCA'])&0xffffff,(b,case['case'],'metadata sample start')
  cost=np.zeros((len(orig),len(nr)),dtype=np.int64)
  for i,(_,o) in enumerate(orig):
   for j,n in enumerate(nr):
    cost[i,j]=(1000000 if word(o,'CCCA')&0xffffff!=int(n['CCCA'])&0xffffff else 0)+(100000 if word(o,'PSST')&0xffffff!=int(n['PSST'])&0xffffff else 0)+100*abs((word(o,'PSST')>>24)-(int(n['PSST'])>>24))+abs(o.get('IP',0)-int(n['IP']))
  ii,jj=linear_sum_assignment(cost);matched=set()
  for i,j in zip(ii,jj):
   ov,o=orig[i];n=nr[j];m=meta[j];cb=m['initial_attenuation_cb'];assert cb>=0
   base=6 if case['velocity']==112 else 21
   u=math.floor(cb*.4/10/.375+.5);old=((base+(u*15//2+12)//24)*8)//3
   direct=((base+(cb+12)//24)*8)//3
   actual=o['IFATN']&255;native=int(n['IFATN'])&255
   assert old==native,(b,case['case'],'current formula/metadata mismatch',cb,old,native)
   address_ok=(word(o,'CCCA')&0xffffff)==(int(n['CCCA'])&0xffffff) and (word(o,'PSST')&0xffffff)==(int(n['PSST'])&0xffffff)
   counts['matched_layers']+=1;counts['sample_address_mismatches']+=not address_ok;counts['current_IFATN_mismatches']+=actual!=native;counts['direct_cb_IFATN_mismatches']+=actual!=direct
   counts['IP_mismatches']+=o.get('IP')!=int(n['IP']);counts['pan_mismatches']+=(word(o,'PSST')>>24)!=(int(n['PSST'])>>24)
   matched.add(j)
   records.append(dict(bank_index=b,case=case['case'],program=case['program'],note=case['note'],velocity=case['velocity'],original_physical_voice=int(ov),native_physical_voice=int(n['voice']),**m,original_ifatn_low=actual,native_ifatn_low=native,direct_raw_cb_prediction=direct,sample_addresses_equal=address_ok,original_ip=o.get('IP'),native_ip=int(n['IP']),original_pan=word(o,'PSST')>>24,native_pan=int(n['PSST'])>>24))
  if len(orig)!=len(nr):counts['cases_with_different_layer_count']+=1
  counts['unmatched_native_layers']+=len(nr)-len(matched)
 summary.append(dict(bank_index=b,**counts))
data=dict(method='Match actual CCCA/loop addresses, then pan/pitch; never physical-voice number or allocation order. Raw SF2 generators parsed independently. Candidate is original VXD integer domain: ((base_db + (raw_cb+12)/24)*8)/3, integer truncation.',banks=summary,records=records)
(r/'attenuation-layer-register-analysis.json').write_text(json.dumps(data,indent=2)+'\n');print(json.dumps(summary,indent=2))
