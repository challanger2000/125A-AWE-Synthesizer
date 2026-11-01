#!/usr/bin/env python3
"""P14 VSTGUI source/resource contract. Static only, not a DAW editor test."""
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

root = Path(sys.argv[1]).resolve()
gui = root / "src/vst3/resource/awe_test_panel.uidesc"
doc = ET.parse(gui).getroot()
assert doc.tag == "vstgui-ui-description"
templates = doc.findall("template")
assert len(templates) == 1 and templates[0].attrib.get("name") == "view"
tags = {item.attrib["name"]: int(item.attrib["tag"])
        for item in doc.findall("./control-tags/control-tag")}
assert tags == {"Hardware": 1001, "Program": 1000}, tags
menus = {node.attrib.get("control-tag"): node
         for node in doc.findall(".//view")
         if node.attrib.get("class") == "COptionMenu"}
assert set(menus) == {"Hardware", "Program"}, menus
assert menus["Hardware"].attrib.get("max-value") == "2"
assert menus["Program"].attrib.get("max-value") == "127"
factory = (root / "src/vst3/Factory.cpp").read_text(encoding="utf-8")
cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
target = (root / "src/vst3/CMakeLists.txt").read_text(encoding="utf-8")
assert "new VSTGUI::VST3Editor(this,\"view\",\"awe_test_panel.uidesc\")" in factory
assert "static_cast<double>(model.engine)/2." in factory, "mode 1 should restore as normalized 0.5"
assert "kProgramID=1000" in factory and "kEngineID=1001" in factory
assert "SMTG_ENABLE_VSTGUI_SUPPORT ON" in cmake
assert "vstgui_support" in target
# The SDK VSTGUI module initializer needs a Windows moduleHandle definition.
# P14 initial CI failed LNK2019 when dllmain.cpp was absent.
assert "${SDK_ROOT}/public.sdk/source/main/dllmain.cpp" in target
assert "resource/awe_test_panel.uidesc" in target
print("P14 STATIC PASS: editor resource, two live parameter tags, VST3 persistence mapping")
print("NOT RUN: Windows VSTGUI attach, DAW interaction, bank playback, asset browse")
