"""Independent same-runner PCM/register A/B and advisory timing (no auto-release)."""
from pathlib import Path
import csv
import hashlib
import json
import os
import statistics
import subprocess
import sys
import tempfile

def run(exe, rom, sf2, out, label, rate, block, voices):
    root = out/label
    root.mkdir(parents=True, exist_ok=True)
    pcm, timing = root/"pcm.s16le",root/"timing.csv"
    cmd=[str(exe),str(rom),str(sf2),str(pcm),str(timing),
         str(rate),str(block),str(voices)]
    subprocess.run(cmd,check=True,timeout=120)
    raw=pcm.read_bytes()
    values=[float(row["wall_us"]) for row in csv.DictReader(timing.open(newline=""))]
    assert len(values)==220, "P192 timing population incomplete"
    assert any(raw), "P192 unexpected silence"
    return dict(pcm_sha256=hashlib.sha256(raw).hexdigest(),
                reg_sha256=hashlib.sha256(Path(str(pcm)+".registers").read_bytes()).hexdigest(),
                median_us=statistics.median(values[20:]),
                p99_us=sorted(values[20:])[int(200*.99)-1],
                worst_us=max(values[20:]),
                early_us=values[:8],
                pcm_bytes=len(raw))

def main():
    if len(sys.argv)!=4:
        raise SystemExit("usage: p192_compare.py BASELINE_EXE CANDIDATE_EXE OUTDIR")
    old,new=map(lambda x:Path(x).resolve(),sys.argv[1:3])
    out=Path(sys.argv[3]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="p192-same-fixture-") as temp:
        root=Path(temp)
        subprocess.run([sys.executable,"tests/p128_synthetic_assets.py",str(root)],check=True)
        rom=root/"zero.rom";sf2=root/"bank-filter-stress.sf2"
        assert rom.stat().st_size==1048576 and sf2.stat().st_size>2048
        cases=[(44100,128,1),(44100,128,16),(44100,128,30),
               (48000,256,30),(96000,511,30)]
        results=[]
        for rate,frames,voices in cases:
            name=f"{rate}-{frames}-{voices}"
            a=run(old,rom,sf2,out,f"{name}-A",rate,frames,voices)
            b=run(new,rom,sf2,out,f"{name}-B",rate,frames,voices)
            for key in ("pcm_sha256","reg_sha256","pcm_bytes"):
                if a[key]!=b[key]:
                    raise AssertionError(f"PCM/register bit-identity FAIL {name}: {key} {a[key]} != {b[key]}")
            results.append(dict(name=name,old=a,new=b,
                  median_ratio=b["median_us"]/a["median_us"]))
            print("P192 BIT-IDENTICAL",name,
                  "PCM",a["pcm_sha256"][:16],
                  "regs",a["reg_sha256"][:16],
                  "median-A/B",round(a["median_us"],1),round(b["median_us"],1),flush=True)
        # ABBA repeat on the exact P190 30-voice/128-frame stress geometry.
        repeated=[]
        for i,tag in enumerate(("A","B","B","A","A","B","B","A")):
            measurements=run(old if tag=="A" else new,rom,sf2,out,
                             f"repeat-{i}-{tag}",44100,128,30)
            reference=results[2]["old" if tag=="A" else "new"]
            assert measurements["pcm_sha256"]==reference["pcm_sha256"]
            assert measurements["reg_sha256"]==reference["reg_sha256"]
            repeated.append((tag,measurements["median_us"]))
        aa=[v for k,v in repeated if k=="A"]
        bb=[v for k,v in repeated if k=="B"]
        ratio=statistics.median(bb)/statistics.median(aa)
        summary=dict(source="P192 same-runner synthetic paired benchmark",
                     comparison="compile flag disables ONLY the shadow pitch cache",
                     bit_identical_cases=5,cases=results,
                     repeated_128_30=repeated,median_ratio=ratio,
                     note="not a host-VST3 process() test; no ETW or ASIO attribution",
                     release_approved=False)
        (out/"P192-RESULT.json").write_text(json.dumps(summary,indent=2))
        print("P192 ABBA 128/30 median cache-vs-uncached ratio:",round(ratio,4),flush=True)
        print("P192 PCM/REG IDENTITY: PASS; Product VST3 RT: NOT RUN",flush=True)
if __name__=="__main__": main()
