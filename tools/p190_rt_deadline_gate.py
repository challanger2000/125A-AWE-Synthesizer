"""P190 hard gate: a green functional CI run is not a realtime deadline PASS.

This gate executes AFTER both preview and numerical artifacts are uploaded,
so raw timing evidence remains available even when the RT gate fails.
No private ROM/SF2 or physical ASIO is involved in this lab test.
"""
import json
import os
import sys
from pathlib import Path


def verdict(summary):
    if not isinstance(summary, dict):
        raise ValueError("summary is not a JSON object")
    cells = summary.get("rt_cells")
    if not isinstance(cells, list) or len(cells) != 72:
        raise ValueError("expected all 72 RT matrix cells")
    total = late = 0
    worst = []
    for c in cells:
        if not isinstance(c, dict):
            raise ValueError("invalid RT cell")
        n = c.get("n")
        misses = c.get("late")
        if (type(n) is not int or type(misses) is not int
                or n != 200 or misses < 0 or misses > n):
            raise ValueError("missing, incomplete or contradictory RT cell")
        for key in ("frames", "notes", "scenario"):
            if type(c.get(key)) is not int:
                raise ValueError("unidentified RT cell")
        total += n
        late += misses
        if misses:
            worst.append((misses, c["frames"], c["notes"], c["scenario"]))
    if (summary.get("measured_callbacks") != total
            or summary.get("deadline_misses") != late
            or summary.get("commercial_release") != "NO-GO"
            or not isinstance(summary.get("source_sha"), str)
            or len(summary["source_sha"]) != 40):
        raise ValueError("inconsistent/invalid RT measurements or provenance")
    return total, late, sorted(worst, reverse=True)


def main(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
        total, missed, worst = verdict(data)
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        print("::error title=P190 RT evidence invalid::" + str(exc))
        print("P190_RT_VERDICT=NOT_VALIDATED")
        return 2

    # The GitHub workflow's all-green status must never disguise real misses.
    state = "FAIL_DEADLINE_MISSES" if missed else "PASS_LAB_ONLY"
    print(f"P190_RT_VERDICT={state} DEADLINES={missed}/{total}")
    report = (
        f"### P190 callback timing verdict: {state}\n\n"
        f"Measured: **{missed}/{total} deadline overruns** in 72 cells. "
        "Host: shared Windows CI runner; this is not a physical ASIO / "
        "MMCSS / independent hardware audio acceptance.\n\n"
        "ETW scheduling causality has NOT been proven by this test. "
        "A scheduler-preemption hypothesis is not evidence.\n\n"
        "**Commercial release is always NO-GO until the separately required "
        "user-ROM/SF2, DAW/ASIO and independent audio-fidelity gates pass.**\n"
    )
    if worst:
        detail = "; ".join(
            f"{misses} misses @ {frames} frames / {notes} voices / scenario {scenario}"
            for misses, frames, notes, scenario in worst[:5]
        )
        report += "\nWorst measured cells: " + detail + "\n"
        print("::error title=P190 real-time deadline FAIL::"
              f"{missed}/{total} callbacks exceeded their budget; {detail}. "
              "No RT PASS; inspect raw P171 callback CSV and ETW attribution.")
    out = os.environ.get("GITHUB_STEP_SUMMARY")
    if out:
        with open(out, "a", encoding="utf-8") as f:
            f.write(report)
    return 1 if missed else 0


def self_test():
    good = {
        "rt_cells": [
            {"frames": (128, 256, 512, 1024)[i // 18],
             "notes": (1, 16, 30)[(i // 6) % 3],
             "scenario": i % 6,
             "n": 200, "late": 0}
            for i in range(72)
        ],
        "measured_callbacks": 14400,
        "deadline_misses": 0,
        "source_sha": "0" * 40,
        "commercial_release": "NO-GO"
    }
    assert verdict(good)[1] == 0
    good["rt_cells"][0]["late"] = 25
    good["deadline_misses"] = 25
    assert verdict(good)[1] == 25
    good["deadline_misses"] = 0
    try:
        verdict(good)
        raise AssertionError("tampered totals were accepted")
    except ValueError:
        pass
    good["deadline_misses"] = 25
    good["rt_cells"].pop()
    try:
        verdict(good)
        raise AssertionError("incomplete matrix was accepted")
    except ValueError:
        pass
    print("P190 RT gate selftest PASS: zero, overrun, tampered, incomplete")


if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--self-test":
        self_test()
    elif len(sys.argv) == 2:
        sys.exit(main(sys.argv[1]))
    else:
        sys.exit("usage: p190_rt_deadline_gate.py --self-test | P170-P171-SUMMARY.json")
