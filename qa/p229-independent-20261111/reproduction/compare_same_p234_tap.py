#!/usr/bin/env python3
"""Final equal-tap 88200-frame dry comparison with existing P234 gates."""
import csv,hashlib,json,pathlib,sys,collections
import numpy as np
sys.path.insert(0,'/workspace/awe-v25-independent/tools')
from p234_dry_compare import decode_rows,edges,crop,stats,require_hold_timing
r=pathlib.Path('/tmp/awe-sf2-117-evidence')
class Cached:
 def __init__(self,path):self.raw=path.read_bytes()
 def read_bytes(self):return self.raw
allcases=[];bankstats=[]
for b in range(4):
 original=json.load((r/f'original-bank-{b}/matched-results.json').open())
 no=Cached(r/f'native-p234-v2-bank-{b}-stages.csv');oo=Cached(r/f'original-bank-{b}-stages.csv')
 npcm=np.memmap(r/f'native-p234-v2-bank-{b}-dry.i32le',dtype='<i4',mode='r').reshape(-1,2)
 opcm=np.memmap(r/f'original-bank-{b}-dry.i32le',dtype='<i4',mode='r').reshape(-1,2)
 counts=collections.Counter()
 for g in original:
  i=g['case'];span={k:int(v) for k,v in next(csv.DictReader((r/f'private-p234-v2-native-bank-{b}/case-{i}/native-p234-spans.csv').open())).items()}
  Pn,Qn,Mn=decode_rows(no,[span['stage_begin'],span['stage_end']]);en=edges(Qn)
  Po,Qo,Mo=decode_rows(oo,g['stage_byte_range']);eo=edges(Qo)
  timing=require_hold_timing(eo,en,f'bank{b}-case{i}')
  n=crop(Pn,npcm,en['noteon_chip_frame'],en['noteon_chip_frame']+88200,[span['pcm_begin'],span['pcm_end']])
  o=crop(Po,opcm,eo['noteon_chip_frame'],eo['noteon_chip_frame']+88200,g['dry_byte_range'])
  def over(a):return int(np.count_nonzero((a < -32768)|(a > 32767)))
  # P233 M rows give actual post-FX/EQ overrange FRAMES (not values).
  # The entire original span includes pre/post guard time. A zero count
  # proves zero clipping in the exact contained note window as well.
  lines=oo.raw[g['stage_byte_range'][0]:g['stage_byte_range'][1]].decode().splitlines()
  original_post_output_frames=sum(int(v[9]) for v in (line.split(',') for line in lines) if v[0]=='M' and len(v)==10 and v[3]=='output')
  a=dict(bank_index=b,case=i,file=g['file'],source_sha256=g['source_sha256'],program=g['program'],note=g['note'],velocity=g['velocity'],
   tap='actual_chip_voice_sum_before_reverb_chorus_EQ_at_both_endpoints',sample_rate=44100,frames=88200,timing_gate=timing,
   original=stats(o),native=stats(n),original_raw_overrange_values=over(o),native_raw_overrange_values=over(n),
   original_post_FX_EQ_overrange_frames_in_inclusive_capture_span=original_post_output_frames,
   original_audio_sha256=hashlib.sha256(o.astype('<i4').tobytes()).hexdigest(),native_audio_sha256=hashlib.sha256(n.astype('<i4').tobytes()).hexdigest(),
   no_gain_normalization=True,no_fitted_alignment=True,physical_hardware='NOT RUN')
  allcases.append(a);counts['cases']+=1;counts['original_pre_FX_overrange_values']+=over(o);counts['native_pre_FX_overrange_values']+=over(n);counts['native_pre_FX_clipping_cases']+=over(n)>0;counts['original_post_FX_EQ_overrange_frames']+=original_post_output_frames
 bankstats.append(dict(bank_index=b,**counts))
data=dict(schema='p229-original-native-equal-tap-actual-reg-edge-88200-v1',source_core_commit='8d2f41dfefd84d98a903ee8c3bdfe0350ae9de95',banks=bankstats,cases=allcases,
 limitations=['Original driver is Creative in 86Box, not physical EMU8000 silicon.','P67 logs attest aggregate WinMM delivery count, not per-message payload echoes.','Both captures use measured chip-note edges; up to 44 samples hold tolerance is explicit.','Original and native use different 86Box DSP revisions; register/DMA differences are independent of DSP.','Earlier delivered-native versus pre-FX-original RMS comparisons are exploratory and superseded here.'])
(r/'sample-accurate-same-tap-comparison.json').write_text(json.dumps(data,indent=2)+'\n');print('FINAL_BANK_TOTALS',json.dumps(bankstats))
