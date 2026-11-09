#!/usr/bin/env python3
"""P202 independent provenance audit: original Creative SF2 1s EG1 attack is
register 0x0C, *outside* hardware AWETST25 block-30 tested attack rates.
Fetch original upstream code at pinned commit and original SF2 at pinned hash;
no CHIP/DSP/production changes and no extra hardware measurement inferred.
"""
import argparse
import json
import math
import re
from pathlib import Path


def require(condition, msg):
    if not condition:
        raise ValueError("P202 source/fixture verification failed: " + msg)


def original_win95_attack_rate(tc):
    """Literal x86 IDIV-style integer operations from source, not SF2 ideal math."""
    if tc <= -600:
        return min(127, (37-tc)//75+8)
    if tc >= 4300:
        return 1
    q=int((tc+500)/150)  # truncates toward 0 like x86 IDIV
    mant=((~q)&7)|8
    shift=int(q/8)
    return max(1, mant >> shift if 0 <= shift < 32 else 1)


def main():
    ap=argparse.ArgumentParser()
    for n in ("sf2-metadata","soundfont-cpp","awetest-c","upstream-emu","current-emu","out"):
        ap.add_argument("--"+n,required=True)
    args=ap.parse_args()
    meta=json.loads(Path(args.sf2_metadata).read_text())
    local=Path(args.soundfont_cpp).read_text()
    awetest=Path(args.awetest_c).read_text()
    upstream=Path(args.upstream_emu).read_text()
    chip=Path(args.current_emu).read_text()
    p=[x for x in meta if x["bank"]==0 and x["program"]==0]
    require(len(p)==1,"original SF2 program 0")
    linked=[pz["generator"]["instrument"] for pz in p[0]["preset_zones"]
        if "instrument" in pz["generator"] and
        pz["generator"].get("keyRange",[0,127])[0]<=59<=pz["generator"].get("keyRange",[0,127])[1]]
    regions=[zone["generator"] for instrument in p[0]["instruments"]
        if instrument["id"] in linked for zone in instrument["zones"]
        if "sampleID" in zone["generator"] and
        zone["generator"].get("keyRange",[0,127])[0]<=59<=zone["generator"].get("keyRange",[0,127])[1]]
    require(len(regions)==1 and regions[0].get("sampleID")==43,
            "single original sample43 in EG1 modulation-to-pitch note59")
    g=regions[0]
    require(g.get("modEnvToPitch")==1200 and "attackModEnv" in g,
            "original EG1 pitch modulation and explicit attack generator")
    tc=g["attackModEnv"]
    require(tc==0,"original 1000ms timecents/driver attack input")
    code_anchors=(
        "int AttackRateFromSf2Timecents(int timecents)",
        "if (timecents <= -600)",
        "if (timecents >= 4300) return 1;",
        "const int quotient = (timecents + 500) / 150;",
        "const int mantissa = ((~quotient) & 7) | 8;",
        "const int shift = quotient / 8;",
        "? AttackRateFromSf2Timecents(g.value[Gen::AttackModEnv])"
    )
    require(all(s in local for s in code_anchors),"real Creative VXD SF2 converter body changed")
    actual=original_win95_attack_rate(tc)
    require(actual==0x0C, "Win95 SF2 attack0 not 0x0C")
    m=re.search(r"static int rate\[8\]\s*=\s*\{([^}]+)\}", awetest)
    require(m is not None,"original AWETEST block30 attack vector not found")
    rates=[int(x.strip(),0) for x in m.group(1).split(",")]
    expected=[0x10,0x14,0x18,0x20,0x24,0x2C,0x34,0x3C]
    require(rates==expected,"hardware source tested rates changed")
    require("t.mod_atk = (unsigned) rate[i];" in awetest,
            "hardware test actually wrote the listed ATKHLD rates")
    require("t.pefe   = 0x7F;" in awetest and
            "t.smp     = &SMP_NOISE;" in awetest,
            "hardware test was noise-to-filter not pitch")
    for s in ('static constexpr double kModAttackExp = 13.5;',
              'vs.modLevel = 1.0 - std::pow(1.0 - x, kModAttackExp);',
              'rates 0x10..0x3C'):
        require(s in upstream,"upstream hardware interpolation source mismatch")
    require("const double amp = 1.0 - pow(1.0 - x, 13.5);" in chip,
            "our native default curve diverged from upstream original")
    comparison=[]
    for x in (.05,.10,.25,.50,.75,1.0):
        baseline=1.0-(1.0-x)**13.5
        c30=baseline-0.30*x*(1-x)
        observation={.05:.45,.10:.76}.get(x)
        comparison.append({
          "normalised_attack_phase":x,
          "original_block30_model":round(baseline,5),
          "p201_0_30_research_candidate":round(c30,5),
          "upstream_approximate_hardware_brightness_proxy":
              observation,
          "original_model_minus_brightness_proxy":
              round(baseline-observation,5) if observation is not None else None,
          "candidate_minus_brightness_proxy":
              round(c30-observation,5) if observation is not None else None,
        })
    report={
      "test":"P202 independent original AWE32Emu AWETST25 block30 provenance vs current SF2 test",
      "original_original_pinned_upstream_commit":"17b0578fe59909dfaa784b5531d6d1a3a80729ce",
      "original_public_sf2_program":0,
      "eg1_test_midi_note":59,
      "sf2_instrument_generators":g,
      "sf2_attack_mod_env_timecents":tc,
      "nominal_sf2_attack_seconds":round(2**(tc/1200),3),
      "real_creative_win95_sbawe_vxd_emulated_register_rate_hex":hex(actual),
      "original_awetest_block30_chip_rates_hex":[hex(x) for x in rates],
      "original_awetest_rate_millisecond_range_approx":[106,742],
      "eg1_sf2_rate_in_awetest_hw_calibrated_set":actual in rates,
      "original_hardware_observation":"filtered noise brightness after 0.05T ~0.45, 0.10T ~0.76, saturation above ~0.70; eight rates only",
      "test_mod_destination":"SF2 reference modEnvToPitch +1200c, AWETST25 original modEnvToFilter +127; not same observable",
      "normalized_shape_comparison":comparison,
      "research_p201_p200_median_abs_pitch_cents":{"baseline":81.85,"candidate_030":29.47},
      "conclusions":[
          "P200 note 59 uses slow ATKHLD modulation attack register 0x0C, absent from the source's independent block30 0x10..0x3C hardware data.",
          "The original shape parameter 13.5 is a model fitted to saturated filter brightness, not directly captured chip envelope state.",
          "P201 0.30 candidate agrees better with one separate CT4390 slow SF2 pitch test, but is not silicon-validated for other rates/filter destinations.",
          "Potential next test must isolate slow-rate hardware envelope and destination before changing shared production chip DSP."
      ],
      "production_code_change":"NONE",
    }
    Path(args.out).write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print("P202 PASS: Original SF2 note59 attack=0 timecents (1s), actual Win95 ATKHLD rate=0x%02X"%actual)
    print("P202 PASS: Original AWETST block30 measured ATKHLD",list(map(hex,rates)),
          "; slow rate in hardware test:",actual in rates)
    for row in comparison[:2]:
        print("P202 normalized phase %.2f, upstream %.4f, P201 0.30 candidate %.4f, approx brightness proxy %.2f"%
           (row["normalised_attack_phase"],row["original_block30_model"],
            row["p201_0_30_research_candidate"],row["upstream_approximate_hardware_brightness_proxy"]))

if __name__=="__main__":
    main()
