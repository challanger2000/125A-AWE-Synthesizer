#!/usr/bin/env python3
"""P165 fail-closed structural contract for the preserved original faceplate."""
from pathlib import Path
import re
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
resource = ROOT / "src/vst3/resource/125A_P165_Original_Faceplate_1000x708.png"
cpp = (ROOT / "src/vst3/PresetBrowserView.cpp").read_text(encoding="utf-8")
cmake = (ROOT / "src/vst3/CMakeLists.txt").read_text(encoding="utf-8")
ui = (ROOT / "src/vst3/resource/awe_test_panel.uidesc").read_text(encoding="utf-8")
factory = (ROOT / "src/vst3/Factory.cpp").read_text(encoding="utf-8")

assert resource.exists(), "P165 original faceplate is missing: refusing fallback"
with Image.open(resource) as face:
    assert face.size == (1000, 708), f"Incorrect image size {face.size}"
    assert face.format == "PNG", "Only lossless original faceplate resource accepted"

source_ratio = 1491 / 1055
scaled_ratio = 1000 / 708
assert abs(source_ratio / scaled_ratio - 1) < 0.001, "Original proportions distorted"
assert "compose_p164_faceplate.py" not in cmake, "Old composited display still built"
assert "P165_FACEPLATE" in cmake
assert 'photo_(new CBitmap("125A_P165_Original_Faceplate_1000x708.png"))' in cpp
assert "new AmberLcdArtwork" not in cpp and "new GoldLogoArtwork" not in cpp
assert 'new PresetBrowserView({0,0,1000,708}' in factory
assert ui.count('1000, 708') == 4, "Editor size not consistent across template/limits"

# Same native visual height; button atlas physical pixel padding differs,
# not the VSTGUI rectangles or hitboxes.
nav = [
    ("bank",26,203,234,273),
    ("previous",212,252,234,273),
    ("preset",261,552,234,273),
    ("next",561,601,234,273),
    ("synth",610,703,234,273),
    ("browser",712,811,234,273),
    ("rom",819,896,234,273),
    ("sf2",904,979,234,273),
]
assert all(y2-y1 == 39 for _,x1,x2,y1,y2 in nav)
assert all(nav[i+1][1]-nav[i][2] in (8,9) for i in range(len(nav)-1))
for name,x1,x2,y1,y2 in nav:
    assert f"{{{x1},{y1},{x2},{y2}}}" in cpp, f"{name} button not in grid"

assert "const CRect rail{16,228,984,279};" in cpp
assert "page=new CViewContainer({0,287,1000,647});" in cpp
assert "return {r.left,r.top-232.,r.right,r.bottom-232.};" in cpp
for unchanged in [
    "AddKnob(10,74,278", "AddKnob(11,258,278",
    "AddKnob(0,408,278", "AddKnob(1,502,278",
    "AddKnob(2,596,278", "AddKnob(3,690,278",
    "AddKnob(4,48,464", "AddKnob(5,169,464",
    "AddKnob(6,290,464", "AddKnob(7,411,464",
    "AddKnob(8,563,464", "AddKnob(9,687,464",
    "PageRect({817,298,951,432})",
    "MakeButton({808,513,960,549}"]:
    assert unchanged in cpp, f"Existing approved control geometry changed: {unchanged}"


# P168 owner DAW screenshot falsification: transparent LCD text must NOT start
# inside the original metal bezel (x ~350..364). This is a source/layout
# contract only; actual Windows EditorHost pixel and DAW acceptance are separate.
lcd_rows = [
    "MakeLabel({370,96,570,112}",
    "MakeLabel({370,118,728,145}",
    "MakeLabel({370,145,728,163}",
    "hint_=MakeLabel({370,166,728,184}",
]
assert all(anchor in cpp for anchor in lcd_rows), "P168: LCD text returned into left metal bezel"
assert "MakeLabel({350,96,570,112}" not in cpp, "P168: first LCD row clips at x350"
assert "hint_=MakeLabel({350,166,728,184}" not in cpp, "P168: status row clips at x350"

print("P165 STRUCTURAL PASS: original image, unchanged lower controls,")
print("  8 equally high buttons, 8-9px gutters and complete faceplate enforced.")
