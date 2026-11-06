#!/usr/bin/env python3
"""Deterministic *numeric* A/B characterization of original vs altered 86Box
Chorus integer feedback; NOT physical AWE32/AWE64 audio validation.
Both raw streams come from the actual production DSP compiled separately.
"""
from array import array
from hashlib import sha256
import csv
import math
from pathlib import Path
import sys

if len(sys.argv)!=4:
    raise SystemExit("usage: compare.py baseline-dir candidate-dir metrics.csv")
base, candidate, output=map(Path,sys.argv[1:])
output.parent.mkdir(parents=True,exist_ok=True)
rows=[]
SR=44100
for p in range(8):
    a_file=base/f"chorus-{p}.pcm"
    b_file=candidate/f"chorus-{p}.pcm"
    a_bytes=a_file.read_bytes()
    b_bytes=b_file.read_bytes()
    if len(a_bytes)!=len(b_bytes) or len(a_bytes)<SR*4*2*4:
        raise SystemExit(f"Mismatch or truncated PCM for preset {p}")
    a=array("i"); a.frombytes(a_bytes)
    b=array("i"); b.frombytes(b_bytes)
    # Excitation lasts 0.5s; early stimulus window includes modulated taps.
    excitation_end=SR*2
    # Last second of measured residual, after 3.0 s no sound input.
    tail_start=SR*3*2
    early_sum_ref=0
    early_sum_diff=0
    early_peak_diff=0
    diff_count=0
    for x,y in zip(a[:excitation_end],b[:excitation_end]):
        early_sum_ref+=int(x)*int(x)
        d=int(x)-int(y)
        early_sum_diff+=d*d
        early_peak_diff=max(early_peak_diff,abs(d))
        diff_count+=bool(d)
    denom=max(1,excitation_end)
    early_rms_ref=math.sqrt(early_sum_ref/denom)
    early_rms_diff=math.sqrt(early_sum_diff/denom)
    early_rel_db=20*math.log10(early_rms_diff/early_rms_ref) if early_rms_diff and early_rms_ref else float("-inf")
    tail_a=a[tail_start:];tail_b=b[tail_start:]
    tail_nonzero_a=sum(v!=0 for v in tail_a)
    tail_nonzero_b=sum(v!=0 for v in tail_b)
    tail_peak_a=max(map(abs,tail_a),default=0)
    tail_peak_b=max(map(abs,tail_b),default=0)
    row={
       "preset":p,"feedback":(0,8,16,32,128,224,0,192)[p],
       "source_pcm_sha256":sha256(a_bytes).hexdigest(),
       "candidate_pcm_sha256":sha256(b_bytes).hexdigest(),
       "first_half_second_rms_original":round(early_rms_ref,7),
       "first_half_second_rms_delta":round(early_rms_diff,7),
       "first_half_second_relative_error_db":round(early_rel_db,4),
       "first_half_second_max_abs_delta":early_peak_diff,
       "first_half_second_changed_values":diff_count,
       "last_second_nonzero_samples_original":tail_nonzero_a,
       "last_second_nonzero_samples_candidate":tail_nonzero_b,
       "last_second_max_abs_original":tail_peak_a,
       "last_second_max_abs_candidate":tail_peak_b,
    }
    rows.append(row)
    print(f"CHORUS_AB preset={p} feedback={row['feedback']}"
          f" early_difference_rel_dB={early_rel_db:.2f}"
          f" early_max_difference={early_peak_diff}"
          f" original_tail_nonzero={tail_nonzero_a}"
          f" candidate_tail_nonzero={tail_nonzero_b}"
          f" original_tail_peak={tail_peak_a}"
          f" candidate_tail_peak={tail_peak_b}")
with output.open("w",newline="") as f:
    writer=csv.DictWriter(f,fieldnames=rows[0].keys())
    writer.writeheader();writer.writerows(rows)
# The two no-feedback presets must be completely bit-for-bit identical.
if any(rows[p]["source_pcm_sha256"]!=rows[p]["candidate_pcm_sha256"] for p in (0,6)):
    raise SystemExit("No-feedback preset changed: candidate has unrelated DSP mutation")
# The six feedback presets must be affected: quantization was modified.
if not all(rows[p]["source_pcm_sha256"]!=rows[p]["candidate_pcm_sha256"] for p in (1,2,3,4,5,7)):
    raise SystemExit("Expected feedback differences absent")
print("CHORUS_AB_FULL_REPRODUCED: eight native production DSP impulse/sine streams; no hardware reference")
