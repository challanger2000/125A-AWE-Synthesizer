#!/usr/bin/env python3
"""Compare SF2-spec additive and legacy Creative fill-only preset composition.

For research, NOT an assertion that a 1996 Creative SF2 VxD used fill-only:
upstream measured fill-only mainly on SF1 banks. No copyrighted/user bank
is embedded or uploaded. This tool NEVER changes the given SF2 or VST3.
"""
import argparse
import json
import struct
from pathlib import Path

OPS = {
    8: "filterFc", 9: "filterQ", 15: "chorus", 16: "reverb",
    17: "pan", 21: "delayModLfo", 22: "freqModLfo",
    23: "delayVibLfo", 24: "freqVibLfo",
    25: "delayModEnv", 26: "attackModEnv", 27: "holdModEnv",
    28: "decayModEnv", 29: "sustainModEnv", 30: "releaseModEnv",
    33: "delayVolEnv", 34: "attackVolEnv", 35: "holdVolEnv",
    36: "decayVolEnv", 37: "sustainVolEnv", 38: "releaseVolEnv",
    41: "instrument", 43: "keyRange", 44: "velRange",
    48: "atten", 51: "coarseTune", 52: "fineTune",
    53: "sampleId", 56: "scaleTuning", 58: "rootKey"
}
TIME = {OPS[x] for x in (21, 23, 25, 26, 27, 28, 30, 33, 34, 35, 36, 38)}
NON_ADD = {"instrument", "sampleId", "keyRange", "velRange", "rootKey"}

def pieces(data, low, high):
    pos = low
    while pos + 8 <= high:
        tag = data[pos:pos+4]
        size = struct.unpack_from("<I", data, pos+4)[0]
        stop = pos + 8 + size
        if stop > high:
            raise ValueError("Invalid RIFF chunk length")
        yield tag, data[pos+8:stop]
        pos = stop + (size & 1)

def unpack(data, pattern):
    width = struct.calcsize(pattern)
    if len(data) % width:
        raise ValueError("Malformed SF2 generator/header table")
    return list(struct.iter_unpack(pattern, data))

def merge(instrument, preset):
    """Return legacy fill-only and P26 additive/defaulted interpretations."""
    fill = dict(preset)
    fill.update(instrument)
    additive = dict(instrument)
    for key, delta in preset.items():
        if key in NON_ADD:
            continue
        default = (-12000 if key in TIME else
                   13500 if key == "filterFc" else
                   100 if key == "scaleTuning" else 0)
        total = additive.get(key, default) + delta
        if key in TIME:
            total = max(-12000, min(8000, total))
        elif key == "filterFc":
            total = max(1500, min(13500, total))
        elif key == "scaleTuning":
            total = max(0, min(1200, total))
        additive[key] = total
    return fill, additive

def in_range(z, name, value):
    if name not in z:
        return True
    raw = z[name] & 0xffff
    return (raw & 255) <= value <= ((raw >> 8) & 255)

def audit(path, programs, key, velocity):
    data = Path(path).read_bytes()
    if len(data) < 12 or data[:4] != b"RIFF" or data[8:12] != b"sfbk":
        raise ValueError("Expected an SF2 SoundFont RIFF/sfbk file")
    pd = {}
    for tag, chunk in pieces(data, 12, len(data)):
        if tag == b"LIST" and chunk[:4] == b"pdta":
            pd = dict(pieces(chunk, 4, len(chunk)))
    required = ("phdr", "pbag", "pgen", "inst", "ibag", "igen")
    if any(k.encode() not in pd for k in required):
        raise ValueError("Missing SF2 pdta chunk(s)")
    ph = [(raw[:20].split(b"\0")[0].decode("latin1"), prog, bank, bag)
          for raw, prog, bank, bag, _, _, _ in unpack(pd[b"phdr"], "<20sHHHIII")]
    inst = [(raw[:20].split(b"\0")[0].decode("latin1"), bag)
            for raw, bag in unpack(pd[b"inst"], "<20sH")]
    pbag = unpack(pd[b"pbag"], "<HH")
    ibag = unpack(pd[b"ibag"], "<HH")
    pgen = unpack(pd[b"pgen"], "<Hh")
    igen = unpack(pd[b"igen"], "<Hh")

    def zones(bags, gens, start, stop):
        result = []
        for i in range(start, stop):
            if not (0 <= i < len(bags)-1):
                raise ValueError("Bad zone index")
            g = {OPS.get(op, f"unknown_{op}"): value
                 for op, value in gens[bags[i][0]:bags[i+1][0]]}
            result.append(g)
        return result

    result = []
    for i, (name, program, bank, bag_start) in enumerate(ph[:-1]):
        if bank != 0 or program not in programs:
            continue
        pz = zones(pbag, pgen, bag_start, ph[i+1][3])
        global_p = {}
        if pz and "instrument" not in pz[0]:
            global_p = pz.pop(0)
        for zone in pz:
            if not (in_range(zone, "keyRange", key) and
                    in_range(zone, "velRange", velocity)):
                continue
            instrument_id = zone.get("instrument")
            if instrument_id is None or not 0 <= instrument_id < len(inst)-1:
                continue
            instrument_name, istart = inst[instrument_id]
            iz = zones(ibag, igen, istart, inst[instrument_id+1][1])
            global_i = {}
            if iz and "sampleId" not in iz[0]:
                global_i = iz.pop(0)
            for layer in iz:
                if "sampleId" not in layer:
                    continue
                if not (in_range(layer, "keyRange", key) and
                        in_range(layer, "velRange", velocity)):
                    continue
                instrument = {**global_i, **layer}
                preset = {**global_p, **zone}
                fill, additive = merge(instrument, preset)
                differences = {
                    k: {"legacy_fill": fill.get(k), "p26_additive": additive.get(k)}
                    for k in sorted(set(fill) | set(additive))
                    if k not in NON_ADD and fill.get(k) != additive.get(k)
                }
                result.append({
                    "bank": bank, "program": program, "preset": name,
                    "instrument": instrument_name, "sample_id": layer["sampleId"],
                    "differences": differences
                })
    return result

def self_test():
    ins = {"filterQ": 100, "chorus": 0, "fineTune": -5,
           "attackVolEnv": -7973}
    pre = {"filterQ": -110, "chorus": 400, "fineTune": -1,
           "delayVolEnv": -3986, "attackVolEnv": -3986}
    fill, add = merge(ins, pre)
    assert fill["filterQ"] == 100 and add["filterQ"] == -10
    assert fill["chorus"] == 0 and add["chorus"] == 400
    assert fill["fineTune"] == -5 and add["fineTune"] == -6
    assert fill["delayVolEnv"] == -3986 and add["delayVolEnv"] == -12000
    assert fill["attackVolEnv"] == -7973 and add["attackVolEnv"] == -11959
    assert in_range({"keyRange": 0x4500}, "keyRange", 48)
    assert not in_range({"keyRange": 0x4500}, "keyRange", 70)
    print("P32 alternative-generator merge arithmetic self-test PASS")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("soundfont", nargs="?", help="Local bank path, never uploaded")
    ap.add_argument("--program", type=int, action="append")
    ap.add_argument("--key", type=int, default=48)
    ap.add_argument("--velocity", type=int, default=100)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    if not args.soundfont:
        ap.error("A local .sf2 path is required")
    if not (0 <= args.key <= 127 and 1 <= args.velocity <= 127):
        ap.error("MIDI key/velocity out of range")
    result = audit(args.soundfont, set(args.program or (0, 7)),
                   args.key, args.velocity)
    print(json.dumps({
        "disclaimer": "Two candidate models; NOT proof of Creative VxD behavior",
        "key": args.key, "velocity": args.velocity,
        "regions": result
    }, indent=2))
    print(f"Evaluated {len(result)} playable layers; "
          f"{sum(bool(r['differences']) for r in result)} differ.")

if __name__ == "__main__":
    main()
