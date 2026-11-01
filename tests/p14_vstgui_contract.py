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
assert tags == {"Hardware": 1001, "Program": 1000, "SF2Bank": 1002}, tags
custom = [node for node in doc.findall(".//view")
          if node.attrib.get("custom-view-name") == "AwePresetBrowser"]
assert len(custom) == 1, "P17 actual custom browser must replace P14 popup"
assert templates[0].attrib["size"] == "860, 612"
assert not any(node.attrib.get("control-tag") == "Program"
               for node in doc.findall(".//view")), "old 128-row popup forbidden"
factory = (root / "src/vst3/Factory.cpp").read_text(encoding="utf-8")
cmake = (root / "CMakeLists.txt").read_text(encoding="utf-8")
target = (root / "src/vst3/CMakeLists.txt").read_text(encoding="utf-8")
browser = (root / "src/vst3/PresetBrowserView.cpp").read_text(encoding="utf-8")
assert 'new VSTGUI::VST3Editor(this,"view","awe_test_panel.uidesc")' in factory
assert 'editor->setDelegate(this)' in factory
assert 'new PresetBrowserView({0,0,860,612},this,sfCatalog_,fmCatalog_,' in factory
assert 'FactoryBank(L"125A_Logo_Master_FINAL.svg")' in factory
assert 'new MasterLogoView({18,8,150,53},exactLogoPath)' in browser
assert 'kPathFilledEvenOdd' in (root / "src/vst3/MasterLogoView.cpp").read_text(encoding="utf-8")
assert (root / "src/vst3/resource/125A_Logo_Master_FINAL.svg").is_file()
assert "resource/125A_Logo_Master_FINAL.svg" in target
assert "static_cast<double>(model.engine)/2." in factory, "mode 1 should restore as normalized 0.5"
assert "kProgramID=1000" in factory and "kEngineID=1001" in factory
# Critical regression: generic numeric parameter displays normalized decimal
# steps in VSTGUI. Program needs an actual 128-step StringListParameter.
assert 'new StringListParameter(STR16("Program"),kProgramID)' in factory
assert 'for(int index=0;index<128;++index)' in factory
assert '"%03d"' in factory and 'programs->appendString(label);' in factory
assert 'parameters.addParameter(programs);' in factory
assert 'parameters.addParameter(STR16("Program")' not in factory

assert 'kBank=1002' in browser and 'kProgram=1000' in browser and 'kEngine=1001' in browser
assert 'getParamNormalized(kBank)' in browser
assert 'dbOnMouseDown' in browser and 'search_->setImmediateTextChange(true)' in browser
assert 'HardwareDescription(engine_)' in browser
assert 'PresetBrowserModel::Filter(' in browser
assert 'PresetBrowserModel::Neighbor(' in browser
# Actual Win32 EditorHost test exposed double callback on CTextButton::kKickStyle:
# one click produced valueChanged(ON) and valueChanged(OFF).
assert 'toggle_->setStyle(CTextButton::kOnOffStyle)' in browser
assert 'SetExpanded(c->getValue()>0.5f)' in browser
assert 'if(c->getValue()>0.5f)' in browser, "PREV/NEXT must ignore kick reset callback"
assert 'FactoryBank(L"MAUIFM.IBK")' in factory
assert 'FactoryBank(L"DRUM.IBK")' in factory
assert 'state_.ibkPath.empty()' in factory and 'state_.drumIbkPath.empty()' in factory
assert "resource/MAUIFM.IBK resource/DRUM.IBK resource/IBK_License.txt" in target
assert "tools/fetch_ibk_resources.py" in target
assert "SMTG_ENABLE_VSTGUI_SUPPORT ON" in cmake
assert "vstgui_support" in target
# The SDK VSTGUI module initializer needs a Windows moduleHandle definition.
# P14 initial CI failed LNK2019 when dllmain.cpp was absent.
assert '"${CMAKE_SOURCE_DIR}/external/vst3sdk/public.sdk/source/main/dllmain.cpp"' in target
assert "${SDK_ROOT}/public.sdk/source/main/dllmain.cpp" not in target, "undefined SDK_ROOT would silently resolve to /public.sdk"
assert "resource/awe_test_panel.uidesc" in target
print("P17 STATIC PASS: custom browser, 3 stable IDs, search, bank, parameter routing")
print("NOT RUN: physical Studio One editor interaction, bitmap visual oracle")
