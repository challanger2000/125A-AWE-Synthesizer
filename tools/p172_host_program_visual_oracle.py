#!/usr/bin/env python3
"""P172 independent HWND pixel oracle: host MIDI program 63, absent from SF2.
Given captures from a source-built generic TestLab GUI host and TWO pinned
production VST3 builds (P168 original bug/P169 correction), this requires
the positive existing program 12 to change the same text rectangle in both
builds, and rejects a missing-program 'fix' that still shows program 0.

This script does not use OCR, test product source text, invent screenshot
content, nor call a mocked GUI. It compares actual Win32 editor BMP pixels.
"""
from __future__ import annotations
import hashlib
import json
import pathlib
import struct
import sys

# independent screen region from owner-approved P165/P169 geometry:
# live hardware menu x=261..552, y=179..218; keep border/arrow out.
TEXT_BOX=(279,186,511,212)
COLOR_THRESHOLD=24
MIN_CHANGED_PIXELS=100
MAX_STABLE_PIXELS=24

def read_bmp(path):
    p=pathlib.Path(path)
    data=p.read_bytes()
    if data[:2]!=b"BM" or len(data)<54:
        raise ValueError("not an actual BMP: "+str(p))
    offset=struct.unpack_from("<I",data,10)[0]
    head,w,h,planes,bits,compression=struct.unpack_from("<IiiHHI",data,14)
    if head!=40 or planes!=1 or bits!=32 or compression!=0 or h>=0:
        raise ValueError("not expected real top-down Win32 BGRA32: "+str(p))
    if w<850 or w>1500 or -h<600 or -h>950:
        raise ValueError("invalid actual native plugin editor geometry")
    if len(data)<offset+w*(-h)*4:
        raise ValueError("truncated editor pixel buffer")
    return w,-h,memoryview(data)[offset:offset+w*(-h)*4].tobytes(),hashlib.sha256(data).hexdigest()

def delta(before,after,box=TEXT_BOX):
    aw,ah,a,hs1=before
    bw,bh,b,hs2=after
    if aw!=bw or ah!=bh:
        raise ValueError("images have inconsistent dimensions")
    x0,y0,x1,y1=box
    # Interpret as 1000x708 independent hardware GUI logical coords.
    cx0=int(round(x0*aw/1000));cx1=int(round(x1*aw/1000))
    cy0=int(round(y0*ah/708));cy1=int(round(y1*ah/708))
    changed=0
    energy=0
    for y in range(cy0,cy1):
        for x in range(cx0,cx1):
            idx=(y*aw+x)*4
            d=max(abs(a[idx+ch]-b[idx+ch]) for ch in range(3))
            energy+=d
            if d>=COLOR_THRESHOLD:changed+=1
    return {"changed_pixels":changed,"pixel_difference_total":energy,"rect":[cx0,cy0,cx1,cy1]}

def collect(root):
    imgs=[read_bmp(pathlib.Path(root)/f"step-{i}.bmp") for i in range(4)]
    lines=(pathlib.Path(root)/"host-values.tsv").read_text(encoding="utf-8-sig").splitlines()
    if len(lines)!=5 or lines[0].strip()!="step\trequested\tobserved\tbitmap":
        raise ValueError("native TestLab host parameter evidence missing/incomplete")
    expected=[0.0,12.0/127.,63.0/127.,0.0]
    for i,row in enumerate(lines[1:]):
        cols=row.strip().split("\t")
        if len(cols)!=4 or int(cols[0])!=i or cols[3]!=f"step-{i}.bmp":
            raise ValueError("invalid native host ordering/provenance")
        if abs(float(cols[1])-expected[i])>1e-8 or abs(float(cols[2])-expected[i])>1e-8:
            raise ValueError("real controller did not accept exact MIDI program sequence")
    return {
        "valid_program12":delta(imgs[0],imgs[1]),
        "missing_program63":delta(imgs[0],imgs[2]),
        "return_program0":delta(imgs[0],imgs[3]),
        "shas":[i[3] for i in imgs],
        "geometry":[imgs[0][0],imgs[0][1]],
        "host_values":lines[1:]
    }

def main():
    if len(sys.argv)!=4:
        print("Usage: p172_host_program_visual_oracle.py OLD_DIR NEW_DIR OUT_JSON")
        return 2
    old=collect(sys.argv[1])
    new=collect(sys.argv[2])
    # Independently selected and audible patches 0 and 12 both present in
    # the synthetic SF2, while 63 is absent. It is important to affirm that
    # parameter changes actually reach BOTH real VSTGUI menu displays.
    predicates={
       "old_present_12_repainted": old["valid_program12"]["changed_pixels"]>=MIN_CHANGED_PIXELS,
       "new_present_12_repainted": new["valid_program12"]["changed_pixels"]>=MIN_CHANGED_PIXELS,
       "old_missing_63_reproduces_bug": old["missing_program63"]["changed_pixels"]<=MAX_STABLE_PIXELS,
       "new_missing_63_visible": new["missing_program63"]["changed_pixels"]>=MIN_CHANGED_PIXELS,
       "old_return_program0_stable": old["return_program0"]["changed_pixels"]<=MAX_STABLE_PIXELS,
       "new_return_program0_stable": new["return_program0"]["changed_pixels"]<=MAX_STABLE_PIXELS,
    }
    report={
        "schema":"125a-p172-independent-vst3-external-program-gui-v1",
        "product_baseline":"P168 at 8ad695055cdaa0dafc99e3b1d1d61b83d9f30f14",
        "product_fix":"P169 at 99fb90fc855c4c7643e24816fa644fdc738c290f",
        "test_surface":"native VST3 controller param1000, live editor HWND bitmap; synthetic bank0 {0,12} and absent 63",
        "not_covered":["physical ASIO","Fender Studio Pro","on-screen native popup menu highlight","ROM/EMU8000 audio"],
        "old":old,"new":new,"assertions":predicates,
        "conclusion":"PASS" if all(predicates.values()) else "FAIL"
    }
    dst=pathlib.Path(sys.argv[3]);dst.parent.mkdir(parents=True,exist_ok=True)
    dst.write_text(json.dumps(report,indent=2),encoding="utf-8")
    for label,ok in predicates.items():
        print(("PASS " if ok else "FAIL ")+label)
    print(json.dumps({"old":{k:old[k]["changed_pixels"] for k in ["valid_program12","missing_program63","return_program0"]},"new":{k:new[k]["changed_pixels"] for k in ["valid_program12","missing_program63","return_program0"]}},indent=2))
    return 0 if all(predicates.values()) else 1

if __name__=="__main__":
    sys.exit(main())
