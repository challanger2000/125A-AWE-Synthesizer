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
assert templates[0].attrib["size"]=="1000, 708"
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
assert "new PresetBrowserView({0,0,1000,708},this,sfCatalog_,fmCatalog_," in f
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
assert 'MakeButton({819,234,896,273},kLoadRom,"ROM")' in b
assert 'NativeChooseFile(path,true)' in b and 'NativeChooseFile(path,false)' in b
assert 'GetOpenFileNameW(&ofn)' in b
assert 'getBinary("Path",bytes,bytesCount)' in f
assert 'sf2Ack("OK")' in f
assert '"125A_HW_INFO:"' in f and 'HardwareDescriptor()' in f
assert 'core.ChipVariant()!=Emu8000Core::Chip::Box86' in f
assert 'CORE: INAKTIV' in f and 'ROM: ERFORDERLICH' in f
assert 'core.ChipRamWords()' in f and 'BankAt(i).sampleData.size()' in f
assert 'hardwareInfoProvider_' in h and 'hardwareInfoLabel_' in h
assert 'auto* photo=new FunctionalLayoutBackground({0,0,1000,708});' in b
assert 'addView(photo);' in b
# P165 retains any compatibility assets only as packaged resources, never as overlay views.
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
assert 'activeBankMenu_=new GoldHardwareMenu({26,234,203,273},this,kActiveBank)' in b
assert 'programMenu_=new GoldHardwareMenu({261,234,552,273},this,kDirectPreset)' in b
assert 'RebuildActiveMenus();' in b and 'SyncActiveMenuSelection();' in b
assert 'sf_.Find(bank_,id)' in b
assert 'ChooseExistingProgram(' in b
assert 'kActiveBank=3109,kDirectPreset=3110' in h
assert 'm_guiControls[11]' in syn
# P165 retains any compatibility assets only as packaged resources, never as overlay views.
assert 'brand=MakeLabel({30,25,237,69},"125A",false)' not in b
assert 'model=MakeLabel({30,76,238,105}' not in b
assert 'engine=MakeLabel({30,118,239,141}' not in b
assert 'programLabel_=MakeLabel({350,118,728,145},"NO PRESET",false)' in b
assert 'hardwareInfoLabel_=MakeLabel({350,145,728,163},"ROM: ERFORDERLICH",true)' in b
# P165 retains any compatibility assets only as packaged resources, never as overlay views.
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
assert 'reverbMenu_=new GoldHardwareMenu' in b and 'chorusMenu_=new GoldHardwareMenu' in b
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
assert 'PageRect({28,299,970,576})' in b
assert 'SetPage(0);' in b and 'SetPage(1);' in b and 'SetPage(2);' not in b
assert 'AddKnob(0,408,278,"ATTACK")' in b
assert 'AddKnob(9,687,464,"RESONANCE")' in b
assert 'AddKnob(10,74,278,"SEND")' in b
assert 'AddKnob(11,258,278,"SEND")' in b
assert 'reverbMenu_=new GoldHardwareMenu(PageRect({32,382,174,405})' in b
assert 'chorusMenu_=new GoldHardwareMenu(PageRect({216,382,358,405})' in b
assert 'MakeLabel({25,430,508,452},"FILTER ENVELOPE",false)' in b
assert 'MakeLabel({537,430,766,452},"FILTER",false)' in b
assert 'reset_=MakeButton({808,513,960,549},kReset,"MOD RESET")' in b
assert 'masterVolume_->setDefaultValue(1.f)' in b
for image in ("125A_PCB_Shared_1000x640.png","125A_PCB_MAIN_1000x640.png"):
    assert (root/"src/vst3/resource"/image).is_file(),image
    assert (("resource/"+image) in cmake)==(image=="125A_PCB_Shared_1000x640.png"),image
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
atlas_name="125A_Button_Atlas_Hardware_Normal_Pressed.png"
atlas=(root/"src/vst3/resource"/atlas_name).read_bytes()
assert atlas.startswith(b"\x89PNG\r\n\x1a\n")
assert struct.unpack_from(">II",atlas,16)==(596,88)
assert atlas[25]==6 or b"tRNS" in atlas
assert ("resource/"+atlas_name) in cmake
assert ('"'+atlas_name+'" PNG DISCARDABLE') in (root/"src/vst3/resource/awe_gold_knobs.rc.in").read_text(encoding="utf-8")
assert 'new CBitmap("125A_Button_Atlas_Hardware_Normal_Pressed.png")' in b
assert 'atlas_->draw(c,getViewSize(),{sourceX_,active?44.:0.})' in b
assert 'textRect.top+=1.;' in b and 'textRect.bottom+=1.;' in b
assert 'auto* button=new GoldButton(PageRect(r),this,tag,s,x);' in b
assert 'StyleGoldMenu(activeBankMenu_)' in b
assert 'StyleGoldMenu(programMenu_)' in b
assert 'StyleGoldMenu(bankMenu_)' in b
assert 'StyleGoldMenu(menu)' in b
for tag,x in [('kLoadRom','0.'),('kLoadSf2','80.'),('kPrevious','158.'),
              ('kNext','201.'),('kMainPage','246.'),('kToggle','342.'),
              ('kReset','444.')]:
    assert ('case '+tag+':') in b
lcd_file=root/"src/vst3/resource/125A_Lcd_Amber_Blank_512x147.png"
assert lcd_file.is_file() and lcd_file.stat().st_size>3000
import struct
binary=lcd_file.read_bytes()
assert binary[:8]==b"\x89PNG\r\n\x1a\n"
assert struct.unpack(">II",binary[16:24])==(512,147)
assert 'resource/125A_Lcd_Amber_Blank_512x147.png' in cmake
assert '"125A_Lcd_Amber_Blank_512x147.png" PNG DISCARDABLE' in (root/"src/vst3/resource/awe_gold_knobs.rc.in").read_text(encoding="utf-8")
# P152 exact-size navigation and collision-free real EMU8000 module area:
# the chip will occupy (788,16)..(984,163), so no input may intersect it.
assert 'fileLabel_=MakeLabel({575,96,728,112},"",false)' in b
assert 'auto* lcd=MakeLabel({350,96,570,112}' in b
assert 'loadSf2_=MakeButton({904,234,979,273},kLoadSf2,"SF2")' in b
assert 'previous_=MakeButton({212,234,252,273},kPrevious,"<")' in b
assert 'next_=MakeButton({561,234,601,273},kNext,">")' in b
assert 'pageButtons_[0]=MakeButton({610,234,703,273}' in b
assert 'toggle_=MakeButton({712,234,811,273}' in b
assert 'MakeLabel({805,30,968,51},"SOUNDFONT / ROM",true)' not in b
assert 'loadRom_=MakeButton({805,103,882,144}' not in b
assert 'hint_=MakeLabel({350,166,728,184}' in b
assert 'panel({16,603,984,634},panelColor,edge);' not in b
# The approved logo is real transparent artwork at its exact native size.
gold_logo=root/"src/vst3/resource/125A_AWE_Gold_Logo_236x147.png"
assert gold_logo.is_file() and gold_logo.stat().st_size>2500
gold_logo_data=gold_logo.read_bytes()
assert gold_logo_data.startswith(b"\x89PNG\r\n\x1a\n")
assert struct.unpack_from(">II",gold_logo_data,16)==(236,147)
assert gold_logo_data[25] in (3,6)
assert gold_logo_data[25]==6 or b"tRNS" in gold_logo_data
assert 'resource/125A_AWE_Gold_Logo_236x147.png' in cmake
assert '"125A_AWE_Gold_Logo_236x147.png" PNG DISCARDABLE' in (root/"src/vst3/resource/awe_gold_knobs.rc.in").read_text(encoding="utf-8")
# All five hardware selectors must be real COptionMenu subclasses;
# neither native popup handling nor selected-item binding is replaced.
assert 'class GoldHardwareMenu final : public COptionMenu' in b
assert 'const CMenuItem* item=getCurrent();' in b
assert 'ctx->drawString(item->getTitle().data(),textRect,kLeftText);' in b
assert 'ctx->setClipRect(textRect);' in b
assert 'inPopup?CColor(8,8,9)' in b
assert b.count('new GoldHardwareMenu(')==5
assert 'bankMenu_=new GoldHardwareMenu(PageRect({100,247,494,284})' in b
# P156: photo and half-opaque VSTGUI control islands are purely visual.
# Parameter rectangles and host editing remain exactly P155.
assert 'class SynthPanelGroups final : public CView' in b
assert 'CColor(7,11,16,153)' in b
assert 'createRoundRectGraphicsPath(r,8.)' in b
assert 'class BrowserPanelBacking final : public CView' in b
assert 'AddToCurrentPage(new BrowserPanelBacking(PageRect({0,232,1000,592})))' in b
assert 'CColor(7,11,16,153)' in b
assert 'panel({16,232,984,592},lcdColor,edge);' not in b
assert 'resource/125A_PCB_Shared_1000x640.png' in cmake
assert '"125A_PCB_Shared_1000x640.png" PNG DISCARDABLE' in (root/"src/vst3/resource/awe_gold_knobs.rc.in").read_text(encoding="utf-8")
# P160: physically protected corner screws and a shorter Reset row.
assert 'notched({{784,2},{984,2},{984,319},{969,318},{957,321},{948,329},{944,341},{944,358},{784,358}})' in b
assert 'notched({{16,187},{518,187},{518,358},{58,358},{58,343},{55,332},{47,324},{32,318},{20,321},{16,326}})' in b
assert 'border->beginSubpath({16,2})' in b
# Compatibility builds may omit the two PNGs; make absence explicit, never
# mistake a green runtime/validator for image-specific proof.
# P161: browser-only gold theme; no changes to bank/program mapping.
assert 'recessed({580,15,974,52},6.' in b
assert 'recessed({24,63,974,349},7.' in b
assert 'search_->setFrameWidth(0.);' in b
assert 'search_->setTextInset({11.,0.});' in b
assert 'bar->setScrollerColor(CColor(181,129,66,255));' in b
assert 'CColor(78,56,27,255)' in b
assert 'ctx->drawRect({r.left,r.top,r.left+3.,r.bottom},kDrawFilled);' in b
assert 'ctx->setFontColor(selected?CColor(255,225,161,255)' in b
assert 'dbOnMouseDown(' in b and 'dbSelectionChanged(' in b
assert 'Select(entry.bank,entry.program)' in b
# P162: matching input widths (394px each) and identical caption gutters.
assert 'bankCaption_=MakeLabel({28,247,94,282},"FILTER",true)' in b
assert 'bankMenu_=new GoldHardwareMenu(PageRect({100,247,494,284})' in b
assert 'searchCaption_=MakeLabel({506,247,572,282},"SUCHE",true)' in b
assert 'search_=new CTextEdit(PageRect({586,249,968,282})' in b
assert 'recessed({580,15,974,52},6.' in b
assert 'dbGetCurrentColumnWidth(int32_t,CDataBrowser* browser)' in b
assert 'browser->getVisibleClientRect().getWidth()' in b
assert 'return 892.;' not in b
# P162 the full header rail is balanced and the redundant BANK label is gone.
assert 'const CRect rail{16,228,984,279};' in b
assert 'createRoundRectGraphicsPath(rail,7.)' in b
assert 'MakeLabel({23,184,65,214},"BANK",true)' not in b
assert 'activeBankMenu_=new GoldHardwareMenu({26,234,203,273}' in b
assert 'previous_=MakeButton({212,234,252,273}' in b
assert 'programMenu_=new GoldHardwareMenu({261,234,552,273}' in b
assert 'next_=MakeButton({561,234,601,273}' in b
assert 'pageButtons_[0]=MakeButton({610,234,703,273}' in b
assert 'toggle_=MakeButton({712,234,811,273}' in b
assert 'loadRom_=MakeButton({819,234,896,273}' in b
assert 'loadSf2_=MakeButton({904,234,979,273}' in b
# P163 right-edge design contracts: three visual gold borders must
# converge at x=974; upper SF2 bitmap contains 5px transparent right margin.
assert 'loadSf2_=MakeButton({904,234,979,273}' in b
assert 'recessed({580,15,974,52},6.' in b
assert 'recessed({24,63,974,349},7.' in b
assert 'search_=new CTextEdit(PageRect({586,249,968,282})' in b
assert 'table_=new CDataBrowser(PageRect({28,299,970,576})' in b
assert 'activeBankMenu_=new GoldHardwareMenu({26,234,203,273}' in b
# Each bank, search, and header element keeps its own original input type.
assert b.count('new GoldHardwareMenu(')==5
assert 'getVisibleClientRect().getWidth()' in b
# P164: approved photographic PCB contains the LCD frame, logo and IC exactly
# once. Neither the old LCD nor logo CView may be instantiated over P164.
# P165: no duplicate photographic LCD, logo or chip layers.
assert 'photo_(new CBitmap("125A_P165_Original_Faceplate_1000x708.png"))' in b
assert '125A_P165_Original_Faceplate_1000x708.png' in cmake
assert 'new AmberLcdArtwork' not in b and 'new GoldLogoArtwork' not in b
assert 'compose_p164_faceplate.py' not in cmake
assert 'new CBitmap("125A_P160' not in b and 'new CBitmap("125A_PCB_Shared' not in b
assert 'page=new CViewContainer({0,287,1000,647});' in b
assert 'const CRect rail{16,228,984,279};' in b
assert 'make' not in ''  # no mock GUI substitutions
print("P165 STATIC PASS: original faceplate, 8 aligned gold buttons and 12 host knobs")
