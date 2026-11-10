#!/usr/bin/env python3
"""P222 real Windows exported VST3 fixed-MIDI 2x2x4 FX audio analysis.

This analyzes ORIGINAL VST3 process() float samples, which may ALREADY be
int16-quantized/clipped upstream. No clipping restoration, no normalization,
no fake Creative original driver comparison, no hardware release claim.

All four FX conditions for each program/note/velocity group have exactly
the same MIDI CC1/7/11/91/93 schedule (verified by recorder stdout).
The result can localize FX-dependent DIGITAL-RAIL incidence, NOT infer
an original physical Creative AWE64 transfer function.
"""
from __future__ import annotations
import argparse,array,hashlib,json,math,re,struct,sys
from pathlib import Path
from zipfile import ZipFile

SCHEMA="125a-p222-controlled-vst3-fx-factorial-diagnostics-v1"
BANK_SHA="d5b99ec38fddf59f53f66b90921e170d207bf3bbd73960f6e4175c39ef68349b"
PROGRAMS=(0,21)
INPUTS=((48,64),(72,120))
FX=("DRY","REVERB","CHORUS","BOTH")
SAMPLE_RATE=44100
FRAMES=132300
WAV_SIZE=44+FRAMES*2*4
REPORT_LINE=re.compile(
 r"^P222_FX_CASE (P\d{3}-N\d+V\d+-(?:DRY|REVERB|CHORUS|BOTH)) "
 r"preset=(\d+) note=(\d+) velocity=(\d+) "
 r"CC1=96 CC7=100 CC11=127 CC91=48 CC93=32 "
 r"gui_rev=(\d+) gui_chor=(\d+) "
 r"peak=([0-9.eE+\-]+) rms=([0-9.eE+\-]+) "
 r"rail_negative=(\d+) rail_positive=(\d+) "
 r"exact_int16_grid=(\d+) audio_sample_count=(\d+) "
 r"first_overrange_frame=(-?\d+) first_overrange_channel=(-?\d+) "
 r"callbacks=(\d+) raw_float_wav=.+ "
 r"verdict=(?:AUDIO_NO_RAIL_DETECTED|AUDIO_CLIP_OR_SILENCE) "
 r"sonic_release=BLOCKED$")

class EvidenceError(ValueError):pass
def insist(ok,msg):
    if not ok:raise EvidenceError("P222 INVALID EVIDENCE: "+msg)
def labels(synthetic=False):
    for p in PROGRAMS:
        if synthetic and p!=0:continue
        for note,velocity in INPUTS:
            for stage in FX:
                yield (p,note,velocity,stage,f"P{p:03d}-N{note}V{velocity}-{stage}")
def data_from(path_dir,zip_path,name):
    if zip_path:
        with ZipFile(zip_path) as z:
            files=z.namelist()
            exact=[x for x in files if x==name or x.endswith("/"+name)]
            insist(len(exact)==1,"missing/multiple unique file "+name)
            info=z.getinfo(exact[0])
            insist(info.file_size==WAV_SIZE and info.compress_size<=WAV_SIZE+10000,
                   "wrong WAV size or decompression anomaly "+name)
            return z.read(info)
    path=path_dir/name
    insist(path.is_file() and path.stat().st_size==WAV_SIZE,"missing or wrong WAV size "+name)
    return path.read_bytes()
def parse_float_wav(raw,label):
    insist(len(raw)==WAV_SIZE,"wrong FLOAT WAV byte length "+label)
    insist(raw[0:4]==b"RIFF" and raw[8:16]==b"WAVEfmt " and raw[36:40]==b"data",
           "not original direct 44-byte RIFF WAV "+label)
    riff_size=struct.unpack_from("<I",raw,4)[0]
    fmt_size,code,channels,rate,byte_rate,block_align,bits=struct.unpack_from("<IHHIIHH",raw,16)
    data_len=struct.unpack_from("<I",raw,40)[0]
    insist((riff_size,fmt_size,code,channels,rate,byte_rate,block_align,bits,data_len)==
           (len(raw)-8,16,3,2,SAMPLE_RATE,SAMPLE_RATE*8,8,32,FRAMES*8),
           "not 3s 44.1k 32-bit IEEE float stereo "+label)
    vals=array.array('f')
    vals.frombytes(raw[44:])
    if sys.byteorder!='little':vals.byteswap()
    insist(len(vals)==FRAMES*2 and all(math.isfinite(v) for v in vals),
           "nonfinite, missing or extra host samples "+label)
    return vals
def features(vals):
    N=len(vals);peak=0.;energy=0.;neg=pos=grid=0
    firstRail=None;longestRail=0;currentRail=0
    floor=-1.0;ceiling=32767/32768
    for i,v in enumerate(vals):
        a=abs(v);peak=max(peak,a);energy+=v*v
        below=(v==floor);above=(v==ceiling)
        neg+=below;pos+=above
        grid+=(v*32768)==round(v*32768)
        if below or above:
            if firstRail is None:firstRail=i//2
            currentRail+=1;longestRail=max(longestRail,currentRail)
        else: currentRail=0
    return {"rms":round(math.sqrt(energy/N),9),"float_peak":round(peak,9),
            "peak_dbfs":None if peak==0 else round(20*math.log10(peak),3),
            "negative_int16_rail_samples":neg,
            "positive_int16_rail_samples":pos,
            "total_int16_rail_samples":neg+pos,
            "first_int16_rail_frame":firstRail,
            "longest_contiguous_rail_samples":longestRail,
            "int16_grid_samples":grid,
            "int16_grid_fraction":round(grid/N,8),
            "audible_nonzero_pcm":energy/N>0.00015**2}
def rms_difference(a,b):
    insist(len(a)==len(b),"different lengths in controlled comparison")
    return round(math.sqrt(sum((x-y)*(x-y) for x,y in zip(a,b))/len(a)),8)
def check_log(path,rows,synthetic):
    if path is None:return "NOT PROVIDED: audio provenance pending"
    text=Path(path).read_text(encoding="utf8",errors="replace")
    messages=[l.strip() for l in text.splitlines() if l.startswith("P222_FX_CASE ")]
    insist(len(messages)==len(rows),"missing or duplicate actual export VST3 process logs")
    for line,(p,note,vel,fx,label) in zip(messages,rows):
        m=REPORT_LINE.fullmatch(line)
        insist(m is not None,"malformed raw VST3 recorder log "+label)
        fields=m.groups()
        expectedGuiRev=10000 if fx in ("REVERB","BOTH") else 0
        expectedGuiChor=10000 if fx in ("CHORUS","BOTH") else 0
        insist(fields[0]==label and int(fields[1])==p and
               int(fields[2])==note and int(fields[3])==vel and
               int(fields[4])==expectedGuiRev and int(fields[5])==expectedGuiChor and
               int(fields[-1])>=130,"MIDI input or GUI FX factorial not fixed/complete "+label)
    mode="SYNTHETIC" if synthetic else "PRIVATE_SF2"
    insist(re.search(rf"^P222_FX_SUMMARY MODE={mode} ATTEMPTED={len(rows)} "
                     r"FAIL=\d+ CREATIVE_DRIVER=NOT_RUN AWE64_PHYSICAL=NOT_TESTED RELEASE=BLOCKED$",
                     text,re.M),
           "recorder did not finish all expected actual VST3 A/B cases")
    return "P222 genuine exported Windows VST3 process() log structurally verified"
def evaluate(path_dir=None,zip_path=None,source_sf2=None,recorder_log=None,synthetic=False):
    expected=list(labels(synthetic))
    if not synthetic:
        insist(source_sf2 is not None and Path(source_sf2).is_file(),
               "exact private owner SF2 required to authenticate sound bank")
        insist(hashlib.sha256(Path(source_sf2).read_bytes()).hexdigest()==BANK_SHA,
               "wrong private owner's 77-preset source soundfont")
    else:
        insist(source_sf2 is None,"synthetic CI cannot pretend genuine owner SF2")
    insist((path_dir is None)!=(zip_path is None),"specify exactly one directory or ZIP")
    insist(recorder_log is not None,"actual exported VST3 recorder-log required")
    log_state=check_log(recorder_log,expected,synthetic)
    measurements=[];perGroup={}
    for p,note,vel,stage,label in expected:
        wav=label+"-ACTUAL-VST3-F32.wav"
        raw=data_from(Path(path_dir) if path_dir else None,zip_path,wav)
        vals=parse_float_wav(raw,label)
        feat=features(vals)
        feat.update({"id":label,"program":p,"note":note,"velocity":vel,
            "fx_stage":stage,"sha256":hashlib.sha256(raw).hexdigest(),
            "file_format":"WAV IEEE FLOAT32 44.1k stereo, 3 seconds",
            "actual_vst3_float_pre_file_conversion":True,
            "can_recover_prior_chip_clipping":False})
        measurements.append(feat)
        group=(p,note,vel)
        if group not in perGroup:perGroup[group]={}
        perGroup[group][stage]=(feat,vals)
    groups=[]
    for (p,note,vel),items in perGroup.items():
        insist(set(items)==set(FX),"incomplete effects matrix for controlled input")
        dry,pcm=items["DRY"]
        comparisons={}
        observed_rails={fx:items[fx][0]["total_int16_rail_samples"] for fx in FX}
        for fx in FX:
            feat,wet=items[fx]
            comparisons[fx]={
                "rms_delta_from_dry":rms_difference(pcm,wet),
                "level_change_from_dry_db":None if dry["rms"]==0 else round(
                    20*math.log10(max(feat["rms"],1e-20)/dry["rms"]),3),
                "digital_rail_samples":feat["total_int16_rail_samples"],
                "audio_changed_vs_dry":feat["sha256"]!=dry["sha256"]}
        if observed_rails["DRY"]:
            diagnosis="DRY_SIGNAL_AT_SIGNED16_RAIL_WITH_FIXED_NOTE_VELOCITY; effects not exclusive root cause"
        elif any(observed_rails[fx] for fx in FX[1:]):
            implicated=[fx for fx in FX[1:] if observed_rails[fx]]
            diagnosis="FX_CONDITIONAL_RAIL_WITH_FIXED_MIDI: "+",".join(implicated)
        else:
            diagnosis="NO_SIGNED16_RAIL_AT_THIS_FIXED_INPUT"
        groups.append({
           "program":p,"note":note,"velocity":vel,
           "fixed_controllers":{"CC1":96,"CC7":100,"CC11":127,"CC91":48,"CC93":32},
           "actual_fx_levels":"absolute VST3 GUI sends 0 or 10000; NOT Creative CC parity",
           "rails_by_stage":observed_rails,
           "comparisons_to_dry":comparisons,
           "interpretation":diagnosis})
    return {"schema":SCHEMA,"status":"COMPLETE_DIAGNOSTIC_NOT_SONIC_ACCEPTANCE",
        "original_creative_driver_capture":"NOT RUN",
        "exact_owner_77_preset_bank_sha256":BANK_SHA if not synthetic else "NOT USED",
        "owner_bank_confirmed":not synthetic,
        "windows_vst3_real_process_log":log_state,
        "reference_chip":"86Box-derived EMU8000 plugin only, no physical AWE64 asserted",
        "release":"BLOCKED","product_dsp_modified":False,
        "frames_per_case":FRAMES,"cases_expected":len(expected),
        "cases_observed":len(measurements),
        "factorial_4_way_groups":groups,
        "cases":measurements}
def main():
    p=argparse.ArgumentParser(description=__doc__)
    sources=p.add_mutually_exclusive_group(required=True)
    sources.add_argument("--wav-dir",type=Path)
    sources.add_argument("--wav-zip",type=Path)
    p.add_argument("--source-sf2",type=Path)
    p.add_argument("--log",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--synthetic-probe",action="store_true")
    a=p.parse_args()
    out=evaluate(path_dir=a.wav_dir,zip_path=a.wav_zip,source_sf2=a.source_sf2,
                 recorder_log=a.log,synthetic=a.synthetic_probe)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
    for row in out["factorial_4_way_groups"]:
        print(f'P222 P{row["program"]:03d} N{row["note"]}/V{row["velocity"]}: '
             +str(row["rails_by_stage"])+" "+row["interpretation"])
    print("P222",out["status"],"cases",out["cases_observed"],
          "original Creative capture NOT RUN, release BLOCKED")
if __name__=="__main__":
    main()
