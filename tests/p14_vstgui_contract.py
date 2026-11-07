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
assert templates[0].attrib["size"]=="1000, 640"
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
assert "new PresetBrowserView({0,0,1000,640},this,sfCatalog_,fmCatalog_," in f
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
assert 'MakeButton({805,103,882,144},kLoadRom,"ROM")' in b
assert 'NativeChooseFile(path,true)' in b and 'NativeChooseFile(path,false)' in b
assert 'GetOpenFileNameW(&ofn)' in b
assert 'getBinary("Path",bytes,bytesCount)' in f
assert 'sf2Ack("OK")' in f
assert '"125A_HW_INFO:"' in f and 'HardwareDescriptor()' in f
assert 'core.ChipVariant()!=Emu8000Core::Chip::Box86' in f
assert 'CORE: INAKTIV' in f and 'ROM: ERFORDERLICH' in f
assert 'core.ChipRamWords()' in f and 'BankAt(i).sampleData.size()' in f
assert 'hardwareInfoProvider_' in h and 'hardwareInfoLabel_' in h
assert 'addView(new FunctionalLayoutBackground({0,0,1000,640}))' in b
assert '125A_PCB_' not in b  # P149 still has no photographic faceplate
assert 'new CBitmap(isMaster' in b
assert 'frames_->draw(ctx,getViewSize(),{0.,frameSize_*index})' in b
assert 'int(std::lround(double(getValue())*32.))' in b
assert 'class SynthPanelGroups final : public CView' in b
assert 'new SynthPanelGroups(PageRect({0,232,1000,592}))' in b
assert 'return {r.left,r.top-232.,r.right,r.bottom-232.};' in b
assert 'setMouseEnabled(false)' in b
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
assert 'tab->setStyle(CTextButton::kOnOffStyle)' in b
assert 'if(control->getValue()>0.5f)' in b
assert 'kVersion = 11u' in state and 'kControlCount = 12' in state
assert 'candidate.channelPrograms.fill(program)' in state
assert 'kVolumeID=MasterOutput::kParamID' in f
assert 'rtMaster_' in f and 'volumeGain_.setTarget(' in f
assert 'masterVolume_' in h and 'masterVolumeValue_' in h
assert 'new HardwareKnob(PageRect({817,298,951,432})' in b
assert 'controller_->getParamNormalized(kMasterVolume)' in b
assert 'activeBankMenu_=new COptionMenu({75,179,232,218},this,kActiveBank)' in b
assert 'programMenu_=new COptionMenu({292,179,710,218},this,kDirectPreset)' in b
assert 'RebuildActiveMenus();' in b and 'SyncActiveMenuSelection();' in b
assert 'sf_.Find(bank_,id)' in b
assert 'ChooseExistingProgram(' in b
assert 'kActiveBank=3109,kDirectPreset=3110' in h
assert 'm_guiControls[11]' in syn
assert 'brand=MakeLabel({30,25,237,69},"125A",false)' in b
assert 'programLabel_=MakeLabel({286,66,755,105},"NO PRESET",false)' in b
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
assert 'kReverbPresetID=1200' in f and 'kChorusPresetID=1201' in f
assert 'kReverbType=1200,kChorusType=1201' in h
assert 'reverbMenu_=new COptionMenu' in b and 'chorusMenu_=new COptionMenu' in b
assert 'ApplyPendingFxIntents(synth_)' in f
assert 'ApplyHardwareReverbPreset(' in f and 'ApplyHardwareChorusPreset(' in f
assert 'reverbPreset' in state and 'chorusPreset' in state
assert 'kMainPage=3111' in h and 'kEditPage' not in h
assert 'AddKnob(3,690,278,"RELEASE")' in b and 'AddKnob(7,411,464,"RELEASE")' in b
assert 'AddToCurrentPage(reverbMenu_)' in b and 'AddToCurrentPage(chorusMenu_)' in b
assert 'pageButtons_[1]=toggle_' in b and 'buildingPanel_=pages_[1];' in b
assert 'std::array<VSTGUI::CViewContainer*,2> pages_' in h
assert 'currentPage_=std::clamp(page,0,1);' in b
assert 'AddToCurrentPage(reverbMenu_)' in b and 'AddToCurrentPage(chorusMenu_)' in b
assert 'PageRect({28,299,972,576})' in b
assert 'SetPage(0);' in b and 'SetPage(1);' in b and 'SetPage(2);' not in b
assert 'AddKnob(0,408,278,"ATTACK")' in b
assert 'AddKnob(9,687,464,"RESONANCE")' in b
assert 'AddKnob(10,74,278,"SEND")' in b
assert 'AddKnob(11,258,278,"SEND")' in b
assert 'reverbMenu_=new COptionMenu(PageRect({32,382,174,405})' in b
assert 'chorusMenu_=new COptionMenu(PageRect({216,382,358,405})' in b
assert 'MakeLabel({25,430,508,452},"FILTER ENVELOPE",false)' in b
assert 'MakeLabel({537,430,766,452},"FILTER",false)' in b
assert 'reset_=MakeButton({808,535,960,571},kReset,"MOD RESET")' in b
assert 'masterVolume_->setDefaultValue(1.f)' in b
for image in ("125A_PCB_Shared_1000x640.png","125A_PCB_MAIN_1000x640.png"):
    assert (root/"src/vst3/resource"/image).is_file(),image
    assert ("resource/"+image) not in cmake,image
assert 'configure_file(resource/awe_pcb.rc.in' not in cmake
assert 'configure_file(resource/awe_gold_knobs.rc.in' in cmake
assert (root/"src/vst3/resource/awe_gold_knobs.rc.in").is_file()
assert (root/"src/vst3/resource/awe_pcb.rc.in").is_file()
import struct
for filename,size in (
    ("125A_Knob_Standard_33frames_58px.png",58),
    ("125A_Knob_Master_33frames_134px.png",134),
):
    data=(root/"src/vst3/resource"/filename).read_bytes()
    assert data.startswith(b"\x89PNG\r\n\x1a\n"),filename
    assert struct.unpack_from(">II",data,16)==(size,size*33),filename
    assert data[25] in (3,6), (filename,data[25])
    assert data[25]==6 or b"tRNS" in data, filename
    assert "resource/"+filename in cmake,filename
    assert 'new CBitmap(isMaster' in b,filename
# P150: the button atlas is one exact-size PNG with seven native rectangles;
# button text and mouse hit targets remain real VSTGUI controls.
atlas_name="125A_Button_Atlas_Normal_Pressed.png"
atlas=(root/"src/vst3/resource"/atlas_name).read_bytes()
assert atlas.startswith(b"\x89PNG\r\n\x1a\n")
assert struct.unpack_from(">II",atlas,16)==(596,88)
assert atlas[25]==6 or b"tRNS" in atlas
assert ("resource/"+atlas_name) in cmake
assert ('"'+atlas_name+'" PNG DISCARDABLE') in (root/"src/vst3/resource/awe_gold_knobs.rc.in").read_text(encoding="utf-8")
assert 'new CBitmap("125A_Button_Atlas_Normal_Pressed.png")' in b
assert 'atlas_->draw(c,getViewSize(),{sourceX_,active?44.:0.})' in b
assert 'auto* button=new GoldButton(PageRect(r),this,tag,s,x);' in b
assert 'StyleGoldMenu(activeBankMenu_)' in b
assert 'StyleGoldMenu(programMenu_)' in b
assert 'StyleGoldMenu(bankMenu_)' in b
assert 'StyleGoldMenu(menu)' in b
for tag,x in [('kLoadRom','0.'),('kLoadSf2','80.'),('kPrevious','158.'),
              ('kNext','201.'),('kMainPage','246.'),('kToggle','342.'),
              ('kReset','444.')]:
    assert ('case '+tag+':') in b
print("P150 STATIC PASS: native 7-button gold atlas, live VSTGUI text and pressed states, styled four native menus, unchanged knobs")
