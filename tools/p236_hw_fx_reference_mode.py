#!/usr/bin/env python3
"""P236 hardware-fixture *test-only* bypass of new GUI=0 wet mute.

The physical CT4390 SoundFont Spec v3.0 recording has Hall1+Chorus1 ON.
Since P190, Synth() defaults GUI FX 0 and therefore forcibly mutes chip
returns and zeroes all per-note sends even if the P97 renderer writes
the correct Hall1/Chorus1 INIT presets. Comparing that dry render against
the physical wet capture yields a FALSE hardware-reverb/chorus regression.

This diagnostic patch restores EXACT historical Creative SF2/CC sends
and their returns ONLY in a disposable CI source copy. It does not modify
the shipping Synth or any DSP/reverb/filter/interpolation coefficient.
"""
from __future__ import annotations
import argparse
from pathlib import Path

MARKERS={
    # Force the same effect return state as the historically HW-checked baseline.
    "    m_core.MuteEffectReturns(true,true);":
    "    m_core.MuteEffectReturns(false,false); /* P236: test-only CT4390 Hall1/Chorus1 fixture */",
    "    const int chorus=AWE125::FxSendLevel::Apply(originalChorus,m_guiControls[11]);":
    "    const int chorus=originalChorus; /* P236: historical Creative bank+CC send */",
    "    const int reverb=AWE125::FxSendLevel::Apply(originalReverb,m_guiControls[10]);":
    "    const int reverb=originalReverb; /* P236: historical Creative bank+CC send */",
}
def patch(code):
    for orig in MARKERS:
        if code.count(orig)!=1:
            raise ValueError(f"P236 cannot prove effective send/mute patch match: {orig}")
    for a,b in MARKERS.items():code=code.replace(a,b,1)
    if code.count("P236:")!=3:
        raise ValueError("unverified P236 test-only patch count")
    return code
def selftest():
    template="\n".join(MARKERS)
    changed=patch(template)
    assert changed!=template and changed.count("P236:")==3
    try:patch(template.replace(next(iter(MARKERS)),""))
    except ValueError:pass
    else:raise AssertionError("missing original mute marker did not block")
    try:patch(changed)
    except ValueError:pass
    else:raise AssertionError("double-application was accepted")
    print("P236_CT4390_HALL1_CHORUS1_TEST_ONLY_SEND_MUTE_PATCH_SELFTEST_PASS")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path)
    p.add_argument("--out",type=Path)
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:return selftest()
    if not a.source or not a.out or a.source.resolve()==a.out.resolve():
        p.error("source and different output required")
    a.out.write_text(patch(a.source.read_text()))
    print("P236_TEMPORARY_HW_REFERENCE_FX_MODE_ON; never a product engine change")
if __name__=="__main__": main()
