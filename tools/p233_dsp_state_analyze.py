#!/usr/bin/env python3
"""P233: evaluate real original Creative Win95 and 125A DSP-stage read-only taps.

State rows and DSP component energies come from temporary instrumentation
inside both EMU8000 chips; final 16-bit PCM from existing P65/P230. Never
claim full equal-state parity from matching final voice registers alone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

GM=(0,88)
STAGES=("dry","reverb","chorus","output")
WIN={"onset":(0,22050),"sustain":(22050,44100),"tail":(44100,88200)}

def must(ok,msg):
    if not ok:raise ValueError("P233_EVIDENCE_INVALID: "+msg)

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def parse_csv_lines(data):
    rows=[]
    for line in data.splitlines():
        p=line.strip().split(",")
        if p[0]=="M":
            must(len(p)==10,"malformed M row")
            _,fr,n,stage,*vals=p
            must(stage in STAGES and int(n)>0,"invalid stage row")
            rows.append({"kind":"M","frame":int(fr),"n":int(n),"stage":stage,
                "l2":float(vals[0]),"r2":float(vals[1]),
                "m2":float(vals[2]),"s2":float(vals[3]),
                "lr":float(vals[4]),"rails":int(vals[5])})
        elif p[0]=="S":
            must(len(p)>=4,"malformed state")
            key=p[2]
            if key.startswith("INIT"):
                must(len(p)==35,"invalid INIT snapshot "+key)
                values=[int(v,16) for v in p[3:]]
                must(len(values)==32,"incomplete INIT slot count")
            elif key=="FX":
                values={x.split("=",1)[0]:x.split("=",1)[1] for x in p[3:]}
            else:
                values=int(p[3],16)
            rows.append({"kind":"S","frame":int(p[1]),"key":key,"value":values})
        elif p[0]=="V":
            values={x.split("=",1)[0]:x.split("=",1)[1] for x in p[3:]}
            rows.append({"kind":"V","frame":int(p[1]),"voice":int(p[2]),"values":values})
    return rows

def parse_segment(file, span=None):
    raw=file.read_bytes()
    if span is not None:
        must(len(span)==2 and span[0] is not None and span[1]>span[0]
             and span[1]<=len(raw),"invalid original DSP stage offset")
        raw=raw[span[0]:span[1]]
    return parse_csv_lines(raw.decode("utf-8",errors="strict"))

def first_states(rows):
    seen={}
    for row in rows:
        if row["kind"]=="S" and row["key"] not in seen:
            seen[row["key"]]=row["value"]
    needed=("INIT1","INIT2","INIT3","INIT4","HWCF4","HWCF5","HWCF3","FX")
    must(all(k in seen for k in needed),"missing original or native initial FX/DSP state snapshot")
    return seen

def render_val(value,fmt):
    return f"0x{value:0{fmt}X}"

def compare_state(original,native):
    mismatches=[]; count=0
    for key in ("INIT1","INIT2","INIT3","INIT4"):
        for i,(o,n) in enumerate(zip(original[key],native[key])):
            if o!=n:
                count+=1
                if len(mismatches)<48:
                    mismatches.append({"state":key,"slot":i,"creative":render_val(o,4),
                                       "native":render_val(n,4)})
    for key in ("HWCF3","HWCF4","HWCF5"):
        if original[key]!=native[key]:
            count+=1
            mismatches.append({"state":key,"creative":render_val(original[key],8),
                               "native":render_val(native[key],8)})
    # Distinguish FX preset coefficients from runtime write cursors and LFO phase.
    dynamic=("rv_tail_pos","chorus_write","chorus_lfo")
    staticfx=[k for k in original["FX"] if k not in dynamic]
    for key in staticfx:
        o=original["FX"].get(key);n=native["FX"].get(key)
        if o!=n:
            count+=1
            if len(mismatches)<48:
                mismatches.append({"state":"FX."+key,"creative":o,"native":n})
    dynamic_diffs=[{"state":"FX."+k,"creative":original["FX"].get(k),
                    "native":native["FX"].get(k)}
                 for k in dynamic if original["FX"].get(k)!=native["FX"].get(k)]
    return {"static_parameter_difference_count":count,
            "mismatches":mismatches,
            "mismatches_omitted":max(0,count-len(mismatches)),
            "dynamic_delay_lfo_phase_differences":dynamic_diffs,
            "original_hwcf4":render_val(original["HWCF4"],8),
            "native_hwcf4":render_val(native["HWCF4"],8),
            "original_hwcf5":render_val(original["HWCF5"],8),
            "native_hwcf5":render_val(native["HWCF5"],8),
            "original_chorus_feedback":original["FX"].get("chorus_feedback"),
            "native_chorus_feedback":native["FX"].get("chorus_feedback"),
            "original_reverb_out_mix":original["FX"].get("reverb_out"),
            "native_reverb_out_mix":native["FX"].get("reverb_out")}

def summarize(rows):
    measured=[r for r in rows if r["kind"]=="M"]
    must(measured,"missing observer energy rows")
    active=[r for r in measured if r["stage"]=="dry" and r["l2"]+r["r2"]>1e6]
    onset=min([r["frame"] for r in active],default=None)
    must(onset is not None,"no audible dry component in selected note interval")
    result={}
    for window,(start,end) in WIN.items():
        result[window]={}
        for stage in STAGES:
            seq=[r for r in measured if r["stage"]==stage
                 and onset+start<=r["frame"]<onset+end]
            if not seq:
                result[window][stage]={"status":"NO_OBSERVATIONS"}
                continue
            samples=sum(r["n"] for r in seq)
            l2=sum(r["l2"] for r in seq);r2=sum(r["r2"] for r in seq)
            m2=sum(r["m2"] for r in seq);s2=sum(r["s2"] for r in seq)
            lr=sum(r["lr"] for r in seq);rails=sum(r["rails"] for r in seq)
            def dB(power):
                return round(10*math.log10(max(power/samples/(32768*32768),1e-24)),3)
            corr=lr/math.sqrt(l2*r2) if l2>0 and r2>0 else 0.0
            result[window][stage]={
                "n_frames":samples,"left_rms_dbfs":dB(l2),
                "right_rms_dbfs":dB(r2),
                "mid_rms_dbfs":dB(m2),"side_rms_dbfs":dB(s2),
                "side_over_mid_db":round(10*math.log10(max(s2,1e-24)/max(m2,1e-24)),3),
                "lr_correlation":round(corr,6),
                "pre_pcm16_out_of_range_frame_count":rails}
    return {"active_dry_first_chip_frame":onset,"windows":result,
            "total_stage_observation_blocks":len(measured)}

def capture_state(rows):
    # First complete parameter snapshot in the actual MIDI / P65 note range.
    state=first_states(rows)
    voices={}
    for row in rows:
        if row["kind"]=="V":
            v=row["voice"]
            if v not in voices:voices[v]=row["values"]
    return state,voices

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--original-stage",required=True,type=Path)
    p.add_argument("--p48",required=True,type=Path)
    p.add_argument("--p67",required=True,type=Path)
    p.add_argument("--native-root",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--creative-sha",required=True)
    p.add_argument("--native-sha",required=True)
    p.add_argument("--instrumentation-sha",required=True)
    a=p.parse_args()
    must(not a.out.exists(),"overwrite refused")
    guest=json.loads(a.p48.read_text());p67=json.loads(a.p67.read_text())
    must(guest.get("hardware")=="sbawe64_gold","not original Win95 AWE64 Gold")
    must(p67.get("original_creative_winmm_endpoint_selected") is True,"Win95 driver not proven")
    must(p67.get("agent_launched_in_actual_win95") is True,"Win95 guest agent not proven")
    cases={c["program"]:c for c in guest["p230_original_gm_8_capture"]["cases"]
           if c["bank"]==16383}
    out=[]
    for program in GM:
        c=cases[program]
        must(c["valid_original_pcm"] and len(c["p233_stage_file_byte_range"])==2,
             f"invalid original GM{program} source evidence")
        original=parse_segment(a.original_stage,c["p233_stage_file_byte_range"])
        nativefile=a.native_root/f"native-gm{program}-stage.csv"
        native=parse_segment(nativefile)
        orig_state,orig_voices=capture_state(original)
        nat_state,nat_voices=capture_state(native)
        diff=compare_state(orig_state,nat_state)
        om=summarize(original);nm=summarize(native)
        perwindow={}
        for win in WIN:
            perwindow[win]={}
            for stage in STAGES:
                oo=om["windows"][win][stage]
                nn=nm["windows"][win][stage]
                if "side_over_mid_db" in oo and "side_over_mid_db" in nn:
                    perwindow[win][stage]={
                        "creative_side_mid_db":oo["side_over_mid_db"],
                        "native_side_mid_db":nn["side_over_mid_db"],
                        "side_mid_difference_db":round(oo["side_over_mid_db"]-nn["side_over_mid_db"],3),
                        "creative_left_rms_dbfs":oo["left_rms_dbfs"],
                        "native_left_rms_dbfs":nn["left_rms_dbfs"],
                        "creative_right_rms_dbfs":oo["right_rms_dbfs"],
                        "native_right_rms_dbfs":nn["right_rms_dbfs"],
                        "creative_correlation":oo["lr_correlation"],
                        "native_correlation":nn["lr_correlation"],
                        "creative_clip_frames":oo["pre_pcm16_out_of_range_frame_count"],
                        "native_clip_frames":nn["pre_pcm16_out_of_range_frame_count"]}
                else:perwindow[win][stage]={"status":"MISSING_WINDOW"}
        out.append({"gm_program":program,"original_wav_sha256":c["reference_sha256"],
            "original_p233_trace_offsets":c["p233_stage_file_byte_range"],
            "native_stage_file_sha256":sha(nativefile),
            "chip_initial_and_fx_states":diff,
            "original_layer_pan_effects":orig_voices,
            "native_layer_pan_effects":nat_voices,
            "original_stage_stats":om,
            "native_stage_stats":nm,
            "direct_stage_side_mid_differences":perwindow,
            "unproven_equal_state_if_different":diff["static_parameter_difference_count"]>0
             or bool(diff["dynamic_delay_lfo_phase_differences"])})
    # Drum audit still remains separate and invalid.
    drum=[c for c in guest["p230_original_gm_8_capture"]["cases"] if c["bank"]==16382]
    must(len(drum)==3,"missing all three invalid original drums")
    drums=[{"note":c["note"],"original_valid_pcm":c["valid_original_pcm"],
            "original_ATKHLDV":sorted(set(f"0x{v:04X}" for _,r,v in c["register_write_sequence"]
                                     if r=="ATKHLDV")),
            "original_nonzero_frames":c["pcm_observed"]["nonzero_frames"]}
           for c in drum]
    result={"schema":"125A-P233-dsp-state-stage-v1",
      "provenance":{"original_86box_commit":a.creative_sha,"native_125a_commit":a.native_sha,
          "observer_source_commit":a.instrumentation_sha,
          "original_p48_sha256":sha(a.p48),"original_p67_sha256":sha(a.p67),
          "original_stage_sha256":sha(a.original_stage),
          "p233_stage_definition":"C internal EMU8000 preFX dry; reverb and chorus incremental component; final postEQ/gain; original wavetable and native chip separately",
          "p65_tap":"86Box wavetable_poll outbuffer_w post-chip",
          "native_tap":"Emu8000Box RenderFrame post-chip FIFO"},
      "gm":[*out],"drum_invalid":drums,"new_original_equal_state_AB_certified":0,
      "original_reference_was_muted_for_dry_trial":False,
      "source_stage_instrumentation_changes_signal_math":False,
      "release":"BLOCKED"}
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2)+"\n")
    for row in out:
        print("P233_PROGRAM",row["gm_program"],
              "DSP_STATIC_DIFFS",row["chip_initial_and_fx_states"]["static_parameter_difference_count"])
        print("P233_HWCF4_5",row["chip_initial_and_fx_states"]["original_hwcf4"],
              row["chip_initial_and_fx_states"]["native_hwcf4"],
              row["chip_initial_and_fx_states"]["original_hwcf5"],
              row["chip_initial_and_fx_states"]["native_hwcf5"])
        for win in ("onset","tail"):
            for stage in ("dry","reverb","chorus","output"):
                v=row["direct_stage_side_mid_differences"][win][stage]
                print("P233_STAGE",row["gm_program"],win,stage,
                    v.get("creative_side_mid_db"),v.get("native_side_mid_db"),
                    v.get("side_mid_difference_db"))
    print("P233_DSP_STEREO_STAGES_MEASURED 2 GM; drum originals remain invalid; no engine changes")
if __name__=="__main__":main()
