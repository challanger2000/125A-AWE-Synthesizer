#!/usr/bin/env python3
"""P106 AWE-only VSTGUI static contract; actual Win32 GUI tested separately."""
from pathlib import Path
from xml.etree import ElementTree as ET
import sys
root=Path(sys.argv[1]).resolve()
uidesc=ET.parse(root/"src/vst3/resource/awe_test_panel.uidesc").getroot()
assert uidesc.tag=="vstgui-ui-description"
templates=uidesc.findall("template")
assert len(templates)==1
assert templates[0].attrib["size"]=="1040, 680"
tags={it.attrib["name"]:int(it.attrib["tag"])
      for it in uidesc.findall("./control-tags/control-tag")}
assert tags=={"Program":1000,"SF2Bank":1002},tags
custom=uidesc.findall(".//view")
assert sum(v.attrib.get("custom-view-name")=="AwePresetBrowser" for v in custom)==1
f=(root/"src/vst3/Factory.cpp").read_text(encoding="utf-8")
b=(root/"src/vst3/PresetBrowserView.cpp").read_text(encoding="utf-8")
h=(root/"src/vst3/PresetBrowserView.h").read_text(encoding="utf-8")
state=(root/"src/vst3/AssetState.h").read_text(encoding="utf-8")
syn=(root/"src/engine/Synth.cpp").read_text(encoding="utf-8")
cmake=(root/"src/vst3/CMakeLists.txt").read_text(encoding="utf-8")
assert 'kGuiFirstID=1100' in f
assert 'new RangeParameter(labels[i],kGuiFirstID+i' in f
assert "kEngineID" not in f and 'STR16("Hardware")' not in f
assert "opl_->" not in f and "cqm_->" not in f
assert "new PresetBrowserView({0,0,1040,680},this,sfCatalog_,fmCatalog_," in f
assert 'new VSTGUI::VST3Editor(this,"view","awe_test_panel.uidesc")' in f
assert 'sendTextMessage(("125A_SF2_STATUS:"+status).c_str())' in f
assert 'AllowEmuNoteOn(sf2Configured_,sf2Loaded_,' in f
assert 'synth_->Core().ChipVariant()==Emu8000Core::Chip::Box86))' in f
assert 'Original-Wave-ROM erforderlich: ROM LADEN' in f
assert 'hostActive_=true;' in f and 'hostActive_=false;' in f
assert 'active=hostActive_;' in f
assert 'if(active&&romReady)' in f
assert 'ROM: ERFORDERLICH' in f
assert 'return sf2Configured && sf2Loaded && romBacked86BoxActive;' in (root/'src/vst3/Sf2LoadPolicy.h').read_text(encoding='utf-8')
assert 'msg->setMessageID("125A_SF2_LOAD")' in f
assert 'msg->setMessageID("125A_ROM_LOAD")' in f
assert 'FIDStringsEqual(msg->getMessageID(),"125A_ROM_LOAD")' in f
assert 'sendTextMessage("125A_ROM_ACK:OK")' in f
assert 'romLoadRequest_' in h and 'kLoadRom=3108' in h
assert 'MakeButton({677,83,826,122},kLoadRom,"ROM LADEN")' in b
assert 'NativeChooseFile(path,true)' in b and 'NativeChooseFile(path,false)' in b
assert 'GetOpenFileNameW(&ofn)' in b
assert 'getBinary("Path",bytes,bytesCount)' in f
assert 'sendTextMessage("125A_SF2_ACK:OK")' in f
assert '"125A_HW_INFO:"' in f and 'HardwareDescriptor()' in f
assert 'core.ChipVariant()==Emu8000Core::Chip::Box86' in f
assert 'CORE: INAKTIV' in f and 'ROM: ERFORDERLICH' in f
assert 'core.ChipRamWords()' in f and 'BankAt(i).sampleData.size()' in f
assert 'hardwareInfoProvider_' in h and 'hardwareInfoLabel_' in h
assert 'addView(new ChipPackage(' in b and '32 VOICES  /  44.1 kHz' in b
assert 'SyncHardwareInfo();' in b
assert 'sfCatalog_=std::move(sf2PendingCatalog_)' in f
assert 'std::try_to_lock' in f
assert 'GetOpenFileNameW(&ofn)' in b
assert 'NativeChooseFile(path,false)' in b
assert 'AddKnob(0,' in b and 'AddKnob(11,' in b
assert 'if(tag>=kGuiFirst && tag<kGuiFirst+kGuiCount)' in b
assert 'std::array<VSTGUI::CControl*,kGuiCount>' in h
assert "kHardware" not in h and "hardware_" not in h
assert 'PresetBrowserModel::Filter(0,sf_,fm_' in b
assert 'PresetBrowserModel::Neighbor(0,sf_,fm_' in b
assert 'toggle_->setStyle(CTextButton::kOnOffStyle)' in b
assert 'if(control->getValue()>0.5f)' in b
assert 'kVersion = 8u' in state and 'kControlCount = 12' in state
assert 'm_guiControls[11]' in syn
assert 'MasterLogoView({18,11,150,51},exactLogoPath)' in b
assert (root/"src/vst3/resource/125A_Logo_Master_FINAL.svg").is_file()
assert 'resource/125A_Logo_Master_FINAL.svg' in cmake
assert 'resource/MAUIFM.IBK' not in cmake
assert 'target_link_libraries(125A_AWE_Synthesizer PRIVATE comdlg32)' in cmake
assert "kFilter=3104,kBankFilter=3105" in h
assert "kProgram=1000,kBankParam=1002" in b
assert "ChangeParameter(kBankParam,double(bank)/16383.)" in b
assert "controller_->getParamNormalized(kBankParam)*16383." in b
assert "this,kBankFilter" in b and "tag==kBankFilter" in b
assert "this,kBank)" not in b and "getParamNormalized(kBank)" not in b
print("P106 STATIC PASS: AWE-only VST3, SF2 picker IPC, browser, 12 knobs, V8 recall")
