#!/usr/bin/env python3
"""P235 controlled 2x2 filter/interpolator dry sound comparison.

One actual original Creative Win95 dry capture, same ROM/SBK/NoteOff frames
and all original PCM byte ranges for 4 temporary native 86Box chip builds.
Only numerical JSON evidence; raw source/stem files remain private on runner.
NO equal-state audio PASS claim from diagnostic statistics alone.
"""
from __future__ import annotations
import argparse, hashlib, json, math, sys
from pathlib import Path

import numpy as np

from p234_dry_compare import (
    PROGRAMS, RATE, SLICES, crop, decode_rows, edges, need, private_pcm,
    require_hold_timing, compare, stats,
)
from p89_compare_voice_registers import native_trace

LABELS={
    "A":{"filter":"Chamberlin","interpolation":"BSPLINE4"},
    "B":{"filter":"Chamberlin","interpolation":"CUBIC"},
    "C":{"filter":"MOOG","interpolation":"BSPLINE4"},
    "D":{"filter":"MOOG","interpolation":"CUBIC"},
}
ORIGINAL_ROM="4e143b94f758734f594ded78f4e5115635975c16fa37fabeae0baa4938ca710e"
ORIGINAL_SBK="fd2e35a260fef22fe809918dda3c921c6d48d53a29c3515af8a41019ce72d586"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def first_nonzero_frame(x):
    active=np.flatnonzero(np.any(x!=0,axis=1))
    return int(active[0]) if len(active) else None

def diff(a,b):
    return round(a-b,4)

def voice_metrics(o,n):
    if not np.any(o) or not np.any(n):
        return {"pair_valid":False,
                "original_nonzero_frames":int(np.count_nonzero(np.any(o!=0,axis=1))),
                "native_nonzero_frames":int(np.count_nonzero(np.any(n!=0,axis=1))),
                "reason":"physical voice absent from one side: need voice/layer mapping, not a fake matched stem"}
    result=compare(o,n)
    result["pair_valid"]=True
    result["original_first_nonzero_frame"]=first_nonzero_frame(o)
    result["native_first_nonzero_frame"]=first_nonzero_frame(n)
    result["voice_start_difference_samples"]=(
        result["original_first_nonzero_frame"]-result["native_first_nonzero_frame"])
    return result

def factor(native):
    def rms(k):return native[k]["before_noteoff"]["metrics"]["native"]["left_rms_dbfs"]
    return {"filter_Moog_minus_Chamberlin_bspline_db":diff(rms("C"),rms("A")),
            "filter_Moog_minus_Chamberlin_cubic_db":diff(rms("D"),rms("B")),
            "interpolator_Cubic_minus_BSpline_Chamberlin_db":diff(rms("B"),rms("A")),
            "interpolator_Cubic_minus_BSpline_Moog_db":diff(rms("D"),rms("C")),
            "filter_by_interpolator_interaction_db":
                round(diff(rms("D"),rms("B"))-diff(rms("C"),rms("A")),4)}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--original-stage",type=Path,required=True)
    p.add_argument("--original-dry",type=Path,required=True)
    p.add_argument("--guest-report",type=Path,required=True)
    p.add_argument("--p67",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--commit-sha",required=True)
    p.add_argument("--original-86box-sha",required=True)
    a=p.parse_args()
    need(not a.out.exists(),"refuse overwritten P235 evidence")
    guest=json.loads(a.guest_report.read_text());p67=json.loads(a.p67.read_text())
    need(guest.get("hardware")=="sbawe64_gold","no original 86Box Win95 AWE64 guest")
    need(p67.get("agent_launched_in_actual_win95")
        and p67.get("original_creative_winmm_endpoint_selected")
        and p67.get("audio_observed"),"original Creative WinMM provenance unverified")
    need(sha(a.root/"native-assets"/"awe32.raw")==ORIGINAL_ROM,"wrong Wave ROM")
    need(sha(a.root/"native-assets"/"SYNTHGM.SBK")==ORIGINAL_SBK,"wrong Creative SBK")
    cases={x["program"]:x for x in guest["p230_original_gm_8_capture"]["cases"]
           if x["bank"]==16383}
    need(set(PROGRAMS)<=set(cases),"missing actual original GM WAV evidence")
    original_raw=private_pcm(a.original_dry,None,None)
    original_stems={}
    for voice in (0,3):
        pth=a.root/f"original-voice{voice}-dry.i32le"
        original_stems[voice]=private_pcm(pth,None,None)
        need(len(original_stems[voice])==len(original_raw),
             f"GM39 original voice{voice} stem length / dry length inconsistent")

    native_root=a.root/"variants"
    preflight={}
    for program in PROGRAMS:
        c=cases[program]
        need(c["valid_original_pcm"],f"invalid original GM{program} capture")
        need(c["velocity"]==100 and c["note"]==60 and c["channel"]==0,
             "unexpected MIDI note conditions")
        original_segments,original_edges,_=decode_rows(
            a.original_stage,c["p233_stage_file_byte_range"])
        meta=c["p234_dry_pcm_byte_range"]
        eorig=edges(original_edges)
        gates={}
        reference_trace=None
        for variant in LABELS:
            directory=native_root/variant
            rows,reg_edges,stage=decode_rows(directory/f"native-gm{program}-stage.csv")
            ecand=edges(reg_edges)
            # Enforce the exact P234 timing contract, no reporting-only Boolean.
            gate=require_hold_timing(eorig,ecand,f"GM{program}-variant{variant}")
            trace=native_trace(directory/f"native-gm{program}"/"traces"/
                (f"gm_b16383_p{program:03d}_n060_v100.wav.trace"))
            need(len(trace)>=12,"missing chip-register sequence")
            if reference_trace is None:reference_trace=trace
            else:need(trace==reference_trace,
                      f"variant {variant} changed EMU8000 REGISTER WRITES GM{program}")
            stem_lens={}
            for voice in (0,3):
                vp=directory/f"native-gm{program}-voice{voice}-dry.i32le"
                stem_lens[voice]=vp.stat().st_size
                need(stem_lens[voice]==(directory/f"native-gm{program}-dry.i32le").stat().st_size,
                     f"variant {variant} voice {voice} stem misaligned to dry PCM")
            gates[variant]=(rows,ecand,gate,trace,stem_lens)
        preflight[program]=(c,original_segments,eorig,meta,gates)
    print("P235_2x2_MANDATORY_TIMING_PASS_12_OF_12 (3 GM x 4 variants)",
          flush=True)
    print("P235_2x2_REGISTER_IDENTITY_PASS_3_OF_3",flush=True)

    allrows=[]
    for program in PROGRAMS:
        c,original_segments,eorig,meta,gates=preflight[program]
        row={"gm_program":program,"midi_note":60,"velocity":100,
             "original_capture_wav_sha256":c["reference_sha256"],
             "original_duration_samples":eorig["duration_frames"],
             "variants":{}, "variant_effects":{},
             "original_layers":{}}
        o_stems_by_window={}
        for name,window in SLICES.items():
            start,end=window(eorig["noteon_chip_frame"],eorig["noteoff_chip_frame"])
            o_stems_by_window[name]={}
            if program==39:
                for voice in (0,3):
                    o_stems_by_window[name][voice]=crop(
                        original_segments,original_stems[voice],start,end,meta)
        for variant,conf in LABELS.items():
            folder=native_root/variant
            rows,ecand,gate,trace,stem_lens=gates[variant]
            audio=private_pcm(folder/f"native-gm{program}-dry.i32le",None,None)
            native_stems={voice:private_pcm(folder/f"native-gm{program}-voice{voice}-dry.i32le",None,None)
                          for voice in (0,3)}
            windows={}
            for name,window in SLICES.items():
                ostart,oend=window(eorig["noteon_chip_frame"],eorig["noteoff_chip_frame"])
                nstart,nend=window(ecand["noteon_chip_frame"],ecand["noteoff_chip_frame"])
                need(oend-ostart==nend-nstart,"unequal original/native window lengths")
                original=crop(original_segments,original_raw,ostart,oend,meta)
                candidate=crop(rows,audio,nstart,nend)
                numbers=compare(original,candidate)
                numbers["original_voice_start_offset_samples"]=first_nonzero_frame(original)
                numbers["native_voice_start_offset_samples"]=first_nonzero_frame(candidate)
                if numbers["original_voice_start_offset_samples"] is not None \
                    and numbers["native_voice_start_offset_samples"] is not None:
                    numbers["start_delta_samples"]=(numbers["original_voice_start_offset_samples"]
                                                    -numbers["native_voice_start_offset_samples"])
                windows[name]={"metrics":numbers}
                if program==39:
                    layer={}
                    for voice in (0,3):
                        cand=crop(rows,native_stems[voice],nstart,nend)
                        layer[str(voice)]=voice_metrics(o_stems_by_window[name][voice],cand)
                    windows[name]["physical_chip_voices"]=layer
            row["variants"][variant]={
                "filter":conf["filter"],"interpolation":conf["interpolation"],
                "pcm_sha256":sha(folder/f"native-gm{program}-dry.i32le"),
                "timing":gate,"windows":windows,
                "voice_stems_sha256":({str(v):sha(folder/f"native-gm{program}-voice{v}-dry.i32le")
                                       for v in (0,3)} if program==39 else {}),
            }
        # Compute factorial contrasts *only from native dry PCM*, with
        # the same unchanged original Creative reference for every variant.
        native={k:row["variants"][k]["windows"] for k in LABELS}
        row["variant_effects"]=factor(native)
        row["rms_differences_original_minus_native_db"]={
            k:row["variants"][k]["windows"]["before_noteoff"]["metrics"][
                "creative_minus_native_left_rms_db"] for k in LABELS}
        ranked=sorted(LABELS,key=lambda k:abs(row[
            "rms_differences_original_minus_native_db"][k]))
        row["ranked_by_rms_only_NOT_acoustic_fidelity"]=ranked
        allrows.append(row)
        print("P235_GM",program,"RMS(beforeNoteOff) original-minus-native",
              row["rms_differences_original_minus_native_db"],
              "factorial",row["variant_effects"],flush=True)
        if program==39:
            for k in LABELS:
                x=row["variants"][k]["windows"]["before_noteoff"]["physical_chip_voices"]
                print("P235_GM39_PHYSICAL_VOICES",k,
                      {v:{"valid":q["pair_valid"],
                          "rms_delta":q.get("creative_minus_native_left_rms_db")}
                       for v,q in x.items()},flush=True)
    report={
        "schema":"125A-P235-4way-filter-interpolation-dry-v1",
        "validity":"DIAGNOSIS_NOT_VST3_RELEASE_ACCEPTANCE",
        "reference":"New same-run original Creative Win95 SBAWE.VXD on unmodified 86Box",
        "original_86box_commit":a.original_86box_sha,
        "native_source_commit":a.commit_sha,
        "original_chip_stage_sha256":sha(a.original_stage),
        "original_private_dry_pcm_sha256":sha(a.original_dry),
        "original_wave_rom_sha256":ORIGINAL_ROM,"original_sbk_sha256":ORIGINAL_SBK,
        "registered_variants":LABELS,
        "mandatory_p234_timing_checked_before_all_audio":True,
        "all_variant_register_sequences_identical":True,
        "timing_pass_pairs":12,
        "new_actual_creative_vs_native_audio_diagnostic_pairs":12,
        "tolerance_passed_equal_state":0,
        "no_gain_normalization":True,
        "dry_tap":"86Box native voice mix before any reverb/chorus and pre fitted EQ",
        "real_original_86box_waveform_used_four_times_per_GM":True,
        "GM39_physical_voices":"Separate actual 86Box physical voice indices 0 and 3; missing voices do NOT count as comparable sample layers",
        "programs":allrows,
        "three_original_drums_blocked":True,
        "production_engine_unchanged":True,
        "release":"BLOCKED"
    }
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    print("P235_2x2_NATIVE_DRY_FACTORIAL_COMPLETE_12, original_wav_same_for_all_four",
          "not_presets_or_product_DSP",flush=True)

if __name__=="__main__":main()
