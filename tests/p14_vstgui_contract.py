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
assert templates[0].attrib["size"]=="1200, 780"
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
assert "new PresetBrowserView({0,0,1200,780},this,sfCatalog_,fmCatalog_," in f
assert 'new VSTGUI::VST3Editor(this,"view","awe_test_panel.uidesc")' in f
assert 'sendTextMessage(("125A_SF2_STATUS:"+status).c_str())' in f
assert 'AllowEmuNoteOn(entry&&(entry->sf2Configured||entry->gmLoaded),' in f
assert 'entry&&(entry->sf2Loaded||entry->gmLoaded),' in f
assert 'RomGmBank::LoadBanks(' in f
assert 'RomGmBank::AdjacentFile(romPath_)' in f
assert 'romAck("OK")' in f
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
assert 'romAck("OK")' in f
assert 'romLoadRequest_' in h and 'kLoadRom=3108' in h
assert 'MakeButton({906,139,1033,174},kLoadRom,"ROM LADEN")' in b
assert 'NativeChooseFile(path,true)' in b and 'NativeChooseFile(path,false)' in b
assert 'GetOpenFileNameW(&ofn)' in b
assert 'getBinary("Path",bytes,bytesCount)' in f
assert 'sf2Ack("OK")' in f
assert '"125A_HW_INFO:"' in f and 'HardwareDescriptor()' in f
assert 'core.ChipVariant()!=Emu8000Core::Chip::Box86' in f
assert 'CORE: INAKTIV' in f and 'ROM: ERFORDERLICH' in f
assert 'core.ChipRamWords()' in f and 'BankAt(i).sampleData.size()' in f
assert 'hardwareInfoProvider_' in h and 'hardwareInfoLabel_' in h
assert 'addView(new HardwareFaceplate({0,0,1200,780}))' in b and '32 VOICES  /  44.1 kHz' in b
assert 'SyncHardwareInfo();' in b
assert 'sfCatalog_=std::move(sf2PendingCatalog_)' in f
assert 'std::try_to_lock' not in f
assert 'auto engineRead=engines_.Read()' in f
assert 'std::unique_lock<std::mutex> lock(engineMutex_)' not in f
assert 'RealtimeEngineExchange<Engine> engines_' in f
assert 'getMidiControllerAssignment(' in f and 'IMidiMapping' in f
assert 'MidiControlMapping::Decode(id)' in f
assert 'sampleOffset' in f and 'ParameterCursor' in f
assert 'assetGeneration_' in f and 'ApplyRtParameters(*synth_)' in f
assert 'engines_.Publish(Pack(' in f
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
assert 'kVersion = 10u' in state and 'kControlCount = 12' in state
assert 'candidate.channelPrograms.fill(program)' in state
assert 'kVolumeID=MasterOutput::kParamID' in f
assert 'rtMaster_' in f and 'volumeGain_.setTarget(' in f
assert 'masterVolume_' in h and 'masterVolumeValue_' in h
assert 'new HardwareKnob({115,626,177,688},this,kMasterVolume)' in b
assert 'controller_->getParamNormalized(kMasterVolume)' in b
assert 'activeBankMenu_=new COptionMenu({85,211,235,252},this,kActiveBank)' in b
assert 'programMenu_=new COptionMenu({303,211,685,252},this,kDirectPreset)' in b
assert 'RebuildActiveMenus();' in b and 'SyncActiveMenuSelection();' in b
assert 'sf_.Find(bank_,id)' in b
assert 'ChooseExistingProgram(' in b
assert 'kActiveBank=3109,kDirectPreset=3110' in h
assert 'm_guiControls[11]' in syn
assert 'MakeLabel({30,14,206,65},"125A",false)' in b
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
print("P117 STATIC PASS: AWE-only VST3, SF2 picker IPC, browser, 12 overlay knobs, master volume, V9 recall")
