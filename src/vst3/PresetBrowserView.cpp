#include "PresetBrowserView.h"
#include "MasterLogoView.h"
#include "vstgui/lib/cgradient.h"
#include "vstgui/lib/cdrawcontext.h"
#include "vstgui/lib/cfont.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <commdlg.h>
#endif

namespace AWE125 {
using namespace VSTGUI;
namespace {
constexpr CColor kBack(22,27,34,255), kRaised(42,52,63,255),
                 kPaper(226,230,233,255), kMuted(151,168,184,255),
                 kSel(51,86,103,255), kGrid(56,68,80,255),
                 kBezel(11,16,22,255), kStroke(85,100,113,255),
                 kOrange(220,151,87,255);
constexpr Steinberg::Vst::ParamID kProgram=1000,kBankParam=1002;
class HardwareFaceplate final : public CView {
public:
    explicit HardwareFaceplate(const CRect& r):CView(r) {setMouseEnabled(false);}
    void draw(CDrawContext* c) override {
        const auto surface=[&](CRect r,CColor fill,CColor edge) {
            c->setFillColor(fill);c->drawRect(r,kDrawFilled);
            c->setFrameColor(edge);c->drawRect(r,kDrawStroked);
        };
        const CColor edge(105,89,62), black(15,18,22), dark(24,28,34);
        // P142: one compact 1000 x 640 logical surface. Panel tabs switch
        // actual VSTGUI child containers; nothing is scaled, rasterized or
        // positioned outside its host view.
        surface({12,8,988,55},dark,edge);     // unit identity
        surface({12,64,666,203},black,edge); // live hardware/LCD status
        surface({677,64,988,203},dark,edge); // file/ROM operations
        surface({12,210,988,261},dark,edge); // bank / program / nav
        surface({12,267,988,305},dark,edge); // MAIN / EDIT / BROWSER
        surface({12,310,988,604},dark,edge); // active page
        surface({12,609,988,635},black,edge);// meaningful status/error
        c->setFrameColor(CColor(155,121,69,255));
        c->drawLine({24,57},{976,57});
    }
};
// A stylized EMU8000 chip package; pin count is decorative, not a claim
// about the actual silicon package. Live RAM/ROM status appears below.
class ChipPackage final : public CView {
public:
    explicit ChipPackage(const CRect& r):CView(r) {setMouseEnabled(false);}
    void draw(CDrawContext* c) override {
        c->setFillColor(CColor(10,14,19,255));
        c->drawRect({798,13,1016,51},kDrawFilled);
        c->setFrameColor(CColor(101,115,125,255));
        c->drawRect({798,13,1016,51},kDrawStroked);
        c->setFrameColor(CColor(169,179,186,255));
        for(int i=0;i<7;++i) {
            const CCoord y=17.5+i*4.6;
            c->drawLine({793,y},{798,y});
            c->drawLine({1016,y},{1021,y});
        }
        c->setFillColor(CColor(95,104,111,255));
        c->drawEllipse({803,19,808,24},kDrawFilled);
    }
};
// Mouse-driven, modern hardware-like knob. Uses native VSTGUI controls,
// never paints values that differ from the host's normalized parameters.
class HardwareKnob final : public CControl {
public:
    HardwareKnob(const CRect& r,IControlListener* listener,int tag)
        :CControl(r,listener,tag,nullptr) {
        setMin(0.f);setMax(1.f);
        setDefaultValue(0.f); // P118: neutral for all 12 SF2 overlays
    }
    void draw(CDrawContext* ctx) override {
        const CRect outer=getViewSize();
        CRect inner=outer;inner.inset(4,4);
        CRect core=inner;core.inset(5,5);
        ctx->setFillColor(kBezel);
        ctx->drawEllipse(outer,kDrawFilled);
        ctx->setFrameColor(CColor(87,101,113,255));
        ctx->setLineWidth(2);
        ctx->drawEllipse(outer,kDrawStroked);
        ctx->setFillColor(CColor(58,70,81,255));
        ctx->drawEllipse(inner,kDrawFilled);
        ctx->setFrameColor(CColor(126,136,145,255));
        ctx->drawEllipse(inner,kDrawStroked);
        ctx->setFillColor(CColor(32,42,51,255));
        ctx->drawEllipse(core,kDrawFilled);
        ctx->setFrameColor(CColor(16,22,28,255));
        ctx->drawEllipse(core,kDrawStroked);
        const double cx=(outer.left+outer.right)*.5;
        const double cy=(outer.top+outer.bottom)*.5;
        const double angle=(135.0+270.0*getValue())*3.141592653589793/180.;
        const double dx=std::cos(angle),dy=std::sin(angle);
        const double rad=(outer.getWidth()-9)*.5;
        ctx->setLineWidth(3);
        ctx->setFrameColor(getValue()>0.0001f?kOrange:kMuted);
        ctx->drawLine({cx+dx*8,cy+dy*8},{cx+dx*rad,cy+dy*rad});
        ctx->setLineWidth(1);
        setDirty(false);
    }
    CMouseEventResult onMouseDown(CPoint& where,const CButtonState& buttons) override {
        if(!(buttons&kLButton))return kMouseEventNotHandled;
        // Explicit Ctrl-click neutral/unity reset. Our custom drag handler
        // must not rely on an inherited CControl shortcut being invoked.
        if(buttons&kControl) {
            if(getValue()!=getDefaultValue()) {
                beginEdit();
                setValue(getDefaultValue());
                valueChanged();
                endEdit();
                invalid();
            }
            return kMouseEventHandled;
        }
        lastX_=where.x;lastY_=where.y;dragging_=true;
        beginEdit();
        return kMouseEventHandled;
    }
    CMouseEventResult onMouseMoved(CPoint& where,const CButtonState&) override {
        if(!dragging_)return kMouseEventNotHandled;
        const double delta=(lastY_-where.y)+.25*(where.x-lastX_);
        lastX_=where.x;lastY_=where.y;
        const auto next=std::clamp(float(getValue()+delta/170.),0.f,1.f);
        if(next!=getValue()) {setValue(next);valueChanged();invalid();}
        return kMouseEventHandled;
    }
    CMouseEventResult onMouseUp(CPoint&,const CButtonState&) override {
        if(dragging_) {dragging_=false;endEdit();}
        return kMouseEventHandled;
    }
    CMouseEventResult onMouseCancel() override {
        if(dragging_) {dragging_=false;endEdit();}
        return kMouseEventHandled;
    }
    CLASS_METHODS_NOCOPY(HardwareKnob,CControl)
private:
    bool dragging_=false;
    CCoord lastX_=0.,lastY_=0.;
};
std::string BankLabel(uint16_t id) {
    if(id==16383)return "GM ROM - Original";
    if(id==16382)return "GM ROM - Drumkit";
    return id==128 ? "Bank 128 - Drumkits" : "Bank "+std::to_string(id);
}
std::string DisplayName(const std::string& path) {
    if(path.empty())return "Noch keine SoundFont ausgewaehlt";
    const auto i=path.find_last_of("/\\");
    return i==std::string::npos?path:path.substr(i+1);
}
bool NativeChooseFile(std::string& chosen,bool forRom) {
#if defined(_WIN32)
    wchar_t file[32768]{};
    OPENFILENAMEW ofn{};
    ofn.lStructSize=sizeof(ofn);
    ofn.hwndOwner=GetForegroundWindow();
    ofn.lpstrFile=file;
    ofn.nMaxFile=32768;
    ofn.lpstrFilter=forRom
        ? L"EMU8000 Wave-ROM (*.raw;*.rom;*.bin)\0*.raw;*.rom;*.bin\0Alle Dateien (*.*)\0*.*\0\0"
        : L"SoundFont 2 (*.sf2)\0*.sf2\0Alle Dateien (*.*)\0*.*\0\0";
    ofn.nFilterIndex=1;
    ofn.lpstrDefExt=forRom?L"raw":L"sf2";
    ofn.Flags=OFN_EXPLORER|OFN_FILEMUSTEXIST|OFN_PATHMUSTEXIST;
    if(!GetOpenFileNameW(&ofn))return false;
    const int n=WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,
                                     file,-1,nullptr,0,nullptr,nullptr);
    if(n<=1||n>4097)return false;
    std::string path(static_cast<size_t>(n),'\0');
    if(WideCharToMultiByte(CP_UTF8,WC_ERR_INVALID_CHARS,
                           file,-1,path.data(),n,nullptr,nullptr)!=n)return false;
    path.pop_back();
    chosen=std::move(path);
    return true;
#else
    (void)chosen;
    (void)forRom;
    return false;
#endif
}
} // namespace

PresetBrowserView::PresetBrowserView(const CRect& rect,
    Steinberg::Vst::EditController* controller,
    const PresetCatalog& sf,const PresetCatalog& legacyFm,
    const std::string& exactLogoPath,
    std::function<std::string()> sf2StatusProvider,
    std::function<std::string()> hardwareInfoProvider,
    std::function<bool(const std::string&)> romLoadRequest,
    std::function<bool(const std::string&)> sf2LoadRequest,
    std::function<std::string()> sf2CurrentPath,
    std::function<uint64_t()> sf2CatalogRevision,
    std::function<bool(uint16_t)> browserBankReselect)
    : CViewContainer(rect),controller_(controller),sf_(sf),fm_(legacyFm),
      sf2StatusProvider_(std::move(sf2StatusProvider)),
      hardwareInfoProvider_(std::move(hardwareInfoProvider)),
      romLoadRequest_(std::move(romLoadRequest)),
      sf2LoadRequest_(std::move(sf2LoadRequest)),
      sf2CurrentPath_(std::move(sf2CurrentPath)),
      sf2CatalogRevision_(std::move(sf2CatalogRevision)),
      browserBankReselect_(std::move(browserBankReselect)) {
    setBackgroundColor(kBack);
    addView(new HardwareFaceplate({0,0,1000,640}));

    // Permanent identity and engine status; all values are supplied by
    // the real processor, never painted as an unconditional green LED.
    auto* brand=MakeLabel({27,14,157,49},"125A",false);
    brand->setFontColor(CColor(218,179,103,255));
    auto* title=MakeLabel({162,15,718,49},"AWE SYNTHESIZER",false);
    title->setFontColor(CColor(218,179,103,255));
    MakeLabel({824,16,976,37},"EMU8000",false);
    MakeLabel({820,38,978,51},"32 VOICES / 44.1 kHz",true);

    auto* lcd=MakeLabel({28,74,633,96},"EMU8000  |  SOUNDFONT ENGINE",true);
    lcd->setFontColor(CColor(221,174,94,255));
    programLabel_=MakeLabel({28,104,640,138},"NO PRESET",false);
    programLabel_->setFontColor(CColor(239,202,114,255));
    hardwareInfoLabel_=MakeLabel({28,151,641,193},"ROM: ERFORDERLICH",true);
    hardwareInfoLabel_->setFontColor(CColor(205,164,94,255));
    hardwareInfoLabel_->setTextTruncateMode(CTextLabel::kTruncateTail);

    MakeLabel({689,75,973,99},"SOUNDFONT",true);
    fileLabel_=MakeLabel({688,102,974,136},"",false);
    fileLabel_->setTextTruncateMode(CTextLabel::kTruncateTail);
    loadRom_=MakeButton({690,151,821,187},kLoadRom,"ROM LADEN");
    loadSf2_=MakeButton({835,151,974,187},kLoadSf2,"SF2 LADEN");

    MakeLabel({24,217,77,250},"BANK",true);
    activeBankMenu_=new COptionMenu({79,215,251,254},this,kActiveBank);
    activeBankMenu_->setBackColor(kBezel);
    activeBankMenu_->setFontColor(kPaper);
    activeBankMenu_->setFrameColor(kStroke);
    addView(activeBankMenu_);
    previous_=MakeButton({263,215,312,254},kPrevious,"<");
    programMenu_=new COptionMenu({325,215,823,254},this,kDirectPreset);
    programMenu_->setBackColor(kBezel);
    programMenu_->setFontColor(kPaper);
    programMenu_->setFrameColor(kStroke);
    addView(programMenu_);
    next_=MakeButton({837,215,983,254},kNext,"NEXT >");

    // Three mutually exclusive, native VSTGUI child layouts. No modal
    // dialogs or ghost/offscreen knobs; the host-facing params are shared.
    pageButtons_[0]=MakeButton({23,271,151,302},kMainPage,"MAIN");
    pageButtons_[1]=MakeButton({161,271,289,302},kEditPage,"EDIT");
    toggle_=MakeButton({299,271,443,302},kToggle,"BROWSER");
    pageButtons_[2]=toggle_;
    for(auto* tab:pageButtons_)
        tab->setStyle(CTextButton::kOnOffStyle);
    MakeLabel({493,273,974,302},"BANK / PRESET / ROM / SF2 BLEIBEN IMMER SICHTBAR",true);
    for(auto*& page:pages_) {
        page=new CViewContainer({0,310,1000,604});
        page->setTransparency(true);
        addView(page);
    }

    // MAIN: essentials only. Master is intentionally independent from the
    // two non-destructive SF2 SEND boosts. FX types are still eight discrete
    // original Creative hardware modes per block.
    buildingPanel_=pages_[0];
    MakeLabel({29,326,470,349},"PERFORMANCE",false);
    MakeLabel({522,326,970,348},"MASTER / SENDS / CREATIVE FX",true);
    masterVolume_=new HardwareKnob(PageRect({139,390,215,466}),
                                  this,kMasterVolume);
    masterVolume_->setDefaultValue(1.f);
    masterVolume_->setValue(1.f);
    AddToCurrentPage(masterVolume_);
    auto* masterTitle=MakeLabel({116,468,238,485},"MASTER",true);
    masterTitle->setHoriAlign(kCenterText);
    masterVolumeValue_=MakeLabel({116,488,238,512},"100%",false);
    masterVolumeValue_->setHoriAlign(kCenterText);
    AddKnob(10,441,395,"HALL SEND");
    AddKnob(11,711,395,"CHORUS SEND");

    MakeLabel({333,509,564,526},"REVERB TYPE",true);
    MakeLabel({603,509,835,526},"CHORUS TYPE",true);
    reverbMenu_=new COptionMenu(PageRect({331,530,570,570}),this,kReverbType);
    chorusMenu_=new COptionMenu(PageRect({600,530,842,570}),this,kChorusType);
    for(auto* menu:{reverbMenu_,chorusMenu_}) {
        menu->setBackColor(kBezel);
        menu->setFontColor(kPaper);
        menu->setFrameColor(kStroke);
    }
    for(const char* label:{"Room 1","Room 2","Room 3","Hall 1",
                            "Hall 2","Plate","Delay","Panning Delay"})
        reverbMenu_->addEntry(label);
    for(const char* label:{"Chorus 1","Chorus 2","Chorus 3","Chorus 4",
                            "Feedback","Flanger","Short Delay","Short Delay + FB"})
        chorusMenu_->addEntry(label);
    reverbMenu_->setValue(4.f);
    chorusMenu_->setValue(2.f);
    AddToCurrentPage(reverbMenu_);
    AddToCurrentPage(chorusMenu_);
    MakeLabel({35,564,301,586},"SEND = SF2-KLANGOFFSET",true);

    // EDIT: precisely all ten remaining overlay controls. Two deliberate
    // rows give envelope and tone families predictable, stable locations.
    buildingPanel_=pages_[1];
    MakeLabel({27,322,395,347},"AMP ENVELOPE",false);
    reset_=MakeButton({840,322,965,357},kReset,"MOD RESET");
    AddKnob(0,131,363,"ATTACK");
    AddKnob(1,351,363,"DECAY");
    AddKnob(2,571,363,"SUSTAIN -");
    AddKnob(3,791,363,"RELEASE");
    MakeLabel({27,468,595,486},"FILTER ENVELOPE + TONE",true);
    AddKnob(4,79,483,"ATTACK");
    AddKnob(5,229,483,"DECAY");
    AddKnob(6,379,483,"SUSTAIN -");
    AddKnob(7,529,483,"RELEASE");
    AddKnob(8,679,483,"CUTOFF -");
    AddKnob(9,829,483,"RESONANCE +");

    // BROWSER: no permanent 400px sidebar. It uses the available width,
    // retains true SF2 bank filtering, search and exact program selection.
    buildingPanel_=pages_[2];
    bankCaption_=MakeLabel({27,324,106,354},"FILTER",true);
    bankMenu_=new COptionMenu(PageRect({107,322,312,358}),this,kBankFilter);
    bankMenu_->setBackColor(kBezel);
    bankMenu_->setFontColor(kPaper);
    bankMenu_->setFrameColor(kStroke);
    AddToCurrentPage(bankMenu_);
    searchCaption_=MakeLabel({332,324,400,354},"SUCHE",true);
    search_=new CTextEdit(PageRect({404,322,966,358}),this,kFilter,"");
    search_->setPlaceholderString("Instrument suchen...");
    search_->setImmediateTextChange(true);
    search_->setBackColor(kBezel);
    search_->setFontColor(kPaper);
    search_->setFrameColor(kStroke);
    AddToCurrentPage(search_);
    table_=new CDataBrowser(PageRect({25,373,971,594}),this,
             CScrollView::kVerticalScrollbar|
             CScrollView::kAutoHideScrollbars);
    table_->setBackgroundColor(kRaised);
    table_->setWantsFocus(true);
    AddToCurrentPage(table_);
    empty_=MakeLabel({33,398,960,436},"",true);

    buildingPanel_=nullptr;
    hint_=MakeLabel({26,610,972,632},
        "SF2-Audiostatus noch nicht vom Prozessor bestaetigt.",true);
    hint_->setTextTruncateMode(CTextLabel::kTruncateTail);
    SetPage(0);
    setWantsIdle(true);
    Sync(true);
}
VSTGUI::CRect PresetBrowserView::PageRect(const VSTGUI::CRect& r) const {
    if (!buildingPanel_) return r;
    // The active page starts at logical Y=310; all named controls continue
    // to use one stable, explicit desktop coordinate system.
    return {r.left,r.top-310.,r.right,r.bottom-310.};
}
void PresetBrowserView::AddToCurrentPage(VSTGUI::CView* v) {
    if (buildingPanel_) buildingPanel_->addView(v);
    else addView(v);
}
void PresetBrowserView::AddKnob(int index,int x,int y,const char* title) {
    auto* ctrl=new HardwareKnob({CCoord(x),CCoord(y),CCoord(x+58),CCoord(y+58)},
                                this,kGuiFirst+index);
    controls_[size_t(index)]=ctrl;
    AddToCurrentPage(ctrl);
    auto* lab=MakeLabel({CCoord(x-20),CCoord(y+61),CCoord(x+82),CCoord(y+81)},title,true);
    lab->setHoriAlign(kCenterText);
    auto* val=MakeLabel({CCoord(x-20),CCoord(y+82),CCoord(x+82),CCoord(y+101)},"0%",false);
    val->setHoriAlign(kCenterText);
    values_[size_t(index)]=val;
}
CTextLabel* PresetBrowserView::MakeLabel(const CRect& r,const char* s,bool secondary) {
    auto* label=new CTextLabel(PageRect(r),s);
    label->setTransparency(true);
    label->setFont(secondary?kNormalFontSmall:kNormalFont);
    label->setFontColor(secondary?kMuted:kPaper);
    label->setHoriAlign(kLeftText);
    if(!secondary)label->setTextTruncateMode(CTextLabel::kTruncateTail);
    AddToCurrentPage(label);
    return label;
}
CTextButton* PresetBrowserView::MakeButton(const CRect& r,int tag,const char* s) {
    auto* button=new CTextButton(PageRect(r),this,tag,s);
    button->setFont(kNormalFont);
    button->setTextColor(kPaper);
    button->setTextColorHighlighted(kPaper);
    button->setFrameColor(kStroke);
    button->setFrameColorHighlighted(CColor(132,155,172));
    button->setRoundRadius(4.);
    auto* base=CGradient::create(0.,1.,CColor(66,79,92),CColor(33,44,56));
    auto* pressed=CGradient::create(0.,1.,CColor(89,113,132),CColor(55,75,91));
    button->setGradient(base);
    button->setGradientHighlighted(pressed);
    base->forget();pressed->forget();
    AddToCurrentPage(button);
    return button;
}
int PresetBrowserView::GestureIndex(int tag) noexcept {
    if(tag>=kGuiFirst&&tag<kGuiFirst+kGuiCount)return tag-kGuiFirst;
    if(tag==kMasterVolume)return kGuiCount;
    if(tag==kReverbType)return kGuiCount+1;
    if(tag==kChorusType)return kGuiCount+2;
    return -1;
}
void PresetBrowserView::controlBeginEdit(CControl* control) {
    if(!control||!controller_)return;
    const int index=GestureIndex(control->getTag());
    if(index<0||activeHostGestures_[size_t(index)])return;
    activeHostGestures_[size_t(index)]=true;
    controller_->beginEdit(static_cast<Steinberg::Vst::ParamID>(control->getTag()));
}
void PresetBrowserView::controlEndEdit(CControl* control) {
    if(!control||!controller_)return;
    const int index=GestureIndex(control->getTag());
    if(index<0||!activeHostGestures_[size_t(index)])return;
    activeHostGestures_[size_t(index)]=false;
    controller_->endEdit(static_cast<Steinberg::Vst::ParamID>(control->getTag()));
}
void PresetBrowserView::ChangeParameter(Steinberg::Vst::ParamID tag,double norm) {
    if(!controller_)return;
    norm=std::clamp(norm,0.,1.);
    // CControl::beginEdit/endEdit already own the host gesture during a
    // knob drag, Ctrl-click or COptionMenu selection. Opening another host
    // gesture for *every* valueChanged() event splits DAW automation into
    // dozens of disconnected touches, and some hosts reject nested edits.
    const int index=GestureIndex(static_cast<int>(tag));
    const bool alreadyEditing=index>=0&&activeHostGestures_[size_t(index)];
    if(!alreadyEditing)controller_->beginEdit(tag);
    if(controller_->setParamNormalized(tag,norm)==Steinberg::kResultOk)
        controller_->performEdit(tag,norm);
    if(!alreadyEditing)controller_->endEdit(tag);
}
void PresetBrowserView::Select(uint16_t bank,uint8_t program) {
    // Host automation may coalesce an edit when the normalized bank value is
    // unchanged, although an intervening MIDI CC0 switched the *audio* bank.
    // Reassert through the controller-to-processor message path in that case.
    const bool sameHostBank=controller_ &&
        std::lround(controller_->getParamNormalized(kBankParam)*16383.)==bank;
    if(sameHostBank&&(!browserBankReselect_ ||
                      !browserBankReselect_(bank))) {
        // Without the explicit message the host may discard this unchanged
        // parameter edit while CC0 continues to select a different bank.
        // Do not pretend a new program selection succeeded.
        if(hint_) {
            hint_->setText("Bank-Neuauswahl fehlgeschlagen: Verbindung zum Prozessor pruefen.");
            hint_->setFontColor(CColor(255,143,122,255));
        }
        return;
    }
    // An earlier failed same-bank message painted a local red error. Once
    // the host accepts a later re-selection, restore the authoritative
    // status text instead of retaining a stale warning across successful UI.
    lastStatus_.clear();
    SyncSf2Status();
    ChangeParameter(kBankParam,double(bank)/16383.);
    ChangeParameter(kProgram,double(program)/127.);
    // Reflect the clicked instrument immediately. The following idle
    // compares bank/program back with the controller: an unaccepted host
    // edit is not silently painted as a successful selection.
    const bool changedBank=(bank_!=bank);
    bank_=bank;
    program_=program;
    programLabel_->setText(PresetBrowserModel::CurrentLabel(
        0,sf_,fm_,bank_,program_).c_str());
    if(changedBank)RebuildActiveMenus();
    else SyncActiveMenuSelection();
    SyncBrowserSelection(); // PREV/NEXT and host selection must follow browser highlight
}
void PresetBrowserView::RebuildActiveMenus() {
    // These menus are neither search-filtered nor limited to 0..127 GM.
    // They expose exactly the active bank's known SoundFont entries.
    if(!activeBankMenu_ || !programMenu_)return;
    activeBanks_=PresetBrowserModel::Banks(0,sf_,fm_);
    activeBankMenu_->removeAllEntry();
    if(activeBanks_.empty())activeBankMenu_->addEntry("Keine Bank geladen");
    else for(const auto bank:activeBanks_)
        activeBankMenu_->addEntry(BankLabel(bank).c_str());

    activePrograms_=PresetBrowserModel::Programs(sf_.Entries(),bank_);
    programMenu_->removeAllEntry();
    if(activePrograms_.empty())programMenu_->addEntry("Keine Presets in der Bank");
    else for(const auto id:activePrograms_) {
        const auto* p=sf_.Find(bank_,id);
        char label[8]{};
        std::snprintf(label,sizeof(label),"%03d",id);
        const auto name=std::string(label)+"  "+(p?p->name:"?");
        programMenu_->addEntry(name.c_str());
    }
    SyncActiveMenuSelection();
}
void PresetBrowserView::SyncActiveMenuSelection() {
    if(activeBankMenu_) {
        const auto bank=std::find(activeBanks_.begin(),activeBanks_.end(),bank_);
        activeBankMenu_->setValue(bank==activeBanks_.end()?0.f:
            static_cast<float>(bank-activeBanks_.begin()));
    }
    if(programMenu_) {
        const auto current=std::find(activePrograms_.begin(),activePrograms_.end(),program_);
        programMenu_->setValue(current==activePrograms_.end()?0.f:
            static_cast<float>(current-activePrograms_.begin()));
    }
}
void PresetBrowserView::RebuildBanks() {
    filterBanks_=PresetBrowserModel::Banks(0,sf_,fm_);
    bankMenu_->removeAllEntry();
    bankMenu_->addEntry("Alle Baenke");
    bool exists=false;
    for(const auto id:filterBanks_) {
        bankMenu_->addEntry(BankLabel(id).c_str());
        if(int(id)==bankFilter_)exists=true;
    }
    if(!exists)bankFilter_=-1;
    int selected=0;
    for(size_t i=0;i<filterBanks_.size();++i)
        if(int(filterBanks_[i])==bankFilter_)selected=static_cast<int>(i+1);
    bankMenu_->setValue(static_cast<float>(selected));
}
void PresetBrowserView::RebuildRows() {
    rows_=PresetBrowserModel::Filter(0,sf_,fm_,bankFilter_,searchText_);
    table_->recalculateLayout();
    if(rows_.empty()) {
        empty_->setText(sf_.Entries().empty()?
            "Keine SF2 geladen. Oben auf SF2 LADEN klicken.":
            "Keine Treffer. Suche oder Bankfilter aendern.");
        empty_->setVisible(currentPage_==2);
    } else empty_->setVisible(false);
    SyncBrowserSelection();
}
void PresetBrowserView::SyncBrowserSelection() {
    if(!table_)return;
    int selected=-1;
    for(size_t i=0;i<rows_.size();++i)
        if(rows_[i].program==program_&&rows_[i].bank==bank_) {
            selected=int(i);break;
        }
    syncing_=true;
    if(selected>=0)table_->setSelectedRow(selected,true);
    else table_->unselectAll();
    syncing_=false;
}
void PresetBrowserView::Sync(bool force) {
    if(!controller_)return;
    if(sf2CatalogRevision_) {
        const auto revision=sf2CatalogRevision_();
        if(revision!=lastCatalogRevision_) {
            lastCatalogRevision_=revision;
            force=true;
            bankFilter_=-1;
            searchText_.clear();
            search_->setText("");
        }
    }
    if(sf2CurrentPath_) {
        const auto path=sf2CurrentPath_();
        if(force||path!=lastPath_) {
            lastPath_=path;
            fileLabel_->setText(DisplayName(path).c_str());
        }
    }
    const auto bank=static_cast<uint16_t>(std::clamp(int(std::lround(
        controller_->getParamNormalized(kBankParam)*16383.)),0,16383));
    const auto program=static_cast<uint8_t>(std::clamp(int(std::lround(
        controller_->getParamNormalized(kProgram)*127.)),0,127));
    for(int i=0;i<kGuiCount;++i) {
        const auto value=static_cast<float>(std::clamp(
            controller_->getParamNormalized(kGuiFirst+i),0.,1.));
        auto* knob=controls_[size_t(i)];
        if(!knob->isEditing() && std::abs(knob->getValue()-value)>.0005f) {
            knob->setValue(value);knob->invalid();
        }
        char label[16]{};
        std::snprintf(label,sizeof(label),"%d%%",int(std::lround(value*100.)));
        values_[size_t(i)]->setText(label);
    }
    // State/host automation owns the visible selection; never leave a
    // painted preset different from the actual controller parameter.
    for(const auto& entry:std::array<std::pair<COptionMenu*,int>,2>{{
        {reverbMenu_,kReverbType},{chorusMenu_,kChorusType}}}) {
        if(!entry.first)continue;
        const int preset=std::clamp(int(std::lround(
            controller_->getParamNormalized(
                static_cast<Steinberg::Vst::ParamID>(entry.second))*7.)),0,7);
        if(!entry.first->isEditing() &&
           int(std::lround(entry.first->getValue()))!=preset) {
            entry.first->setValue(static_cast<float>(preset));
            entry.first->invalid();
        }
    }
    const auto master=static_cast<float>(std::clamp(
        controller_->getParamNormalized(kMasterVolume),0.,1.));
    if(masterVolume_ && !masterVolume_->isEditing() &&
       std::abs(masterVolume_->getValue()-master)>.0005f) {
        masterVolume_->setValue(master);
        masterVolume_->invalid();
    }
    if(masterVolumeValue_) {
        char volumeLabel[16]{};
        std::snprintf(volumeLabel,sizeof(volumeLabel),"%d%%",
                      int(std::lround(master*100.)));
        masterVolumeValue_->setText(volumeLabel);
    }
    SyncSf2Status();
    SyncHardwareInfo();
    if(!force&&bank==bank_&&program==program_)return;
    const bool bankChanged=force||bank!=bank_;
    bank_=bank;program_=program;
    programLabel_->setText(PresetBrowserModel::CurrentLabel(
        0,sf_,fm_,bank_,program_).c_str());
    if(force)RebuildBanks();
    if(bankChanged)RebuildActiveMenus();
    else SyncActiveMenuSelection();
    RebuildRows();
}
void PresetBrowserView::SyncSf2Status() {
    if(!hint_||!sf2StatusProvider_)return;
    std::string text=sf2StatusProvider_();
    if(text.empty())text="SF2-Status noch nicht verfuegbar.";
    if(text==lastStatus_)return;
    lastStatus_=text;
    hint_->setText(text.c_str());
    const bool err=text.find("Fehler")!=std::string::npos;
    hint_->setFontColor(err?CColor(255,143,122,255):kMuted);
}
void PresetBrowserView::SyncHardwareInfo() {
    if(!hardwareInfoLabel_||!hardwareInfoProvider_)return;
    const std::string state=hardwareInfoProvider_();
    if(state==lastHardwareInfo_)return;
    lastHardwareInfo_=state;
    hardwareInfoLabel_->setText(state.empty()
        ? "32 STIMMEN | 44,1 kHz | RAM/ROM: nicht ermittelt"
        : state.c_str());
}
void PresetBrowserView::SetPage(int page) {
    currentPage_=std::clamp(page,0,2);
    for(size_t i=0;i<pages_.size();++i) {
        if(pages_[i])pages_[i]->setVisible(int(i)==currentPage_);
        if(pageButtons_[i]) {
            pageButtons_[i]->setValue(int(i)==currentPage_?1.f:0.f);
            pageButtons_[i]->invalid();
        }
    }
    if(empty_)empty_->setVisible(currentPage_==2&&rows_.empty());
}
void PresetBrowserView::ChooseSf2() {
    std::string path;
    if(NativeChooseFile(path,false)&&sf2LoadRequest_)
        sf2LoadRequest_(path);
}
void PresetBrowserView::ChooseRom() {
    std::string path;
    if(NativeChooseFile(path,true)&&romLoadRequest_)
        romLoadRequest_(path);
}
void PresetBrowserView::valueChanged(CControl* control) {
    if(!control||syncing_)return;
    const int tag=control->getTag();
    if(tag==kReverbType || tag==kChorusType) {
        ChangeParameter(static_cast<Steinberg::Vst::ParamID>(tag),
            double(std::clamp(int(std::lround(control->getValue())),0,7))/7.);
        return;
    }
    if(tag==kMasterVolume) {
        ChangeParameter(static_cast<Steinberg::Vst::ParamID>(tag),
                        std::clamp(double(control->getValue()),0.,1.));
        return;
    }
    if(tag>=kGuiFirst && tag<kGuiFirst+kGuiCount) {
        const int idx=tag-kGuiFirst;
        ChangeParameter(static_cast<Steinberg::Vst::ParamID>(tag),
                        std::clamp(double(control->getValue()),0.,1.));
        return;
    }
    if(tag==kActiveBank) {
        const auto idx=static_cast<int>(std::lround(activeBankMenu_->getValue()));
        if(idx>=0&&size_t(idx)<activeBanks_.size()) {
            const uint16_t candidate=activeBanks_[size_t(idx)];
            const auto available=PresetBrowserModel::Programs(sf_.Entries(),candidate);
            if(!available.empty()) {
                const auto next=PresetBrowserModel::ChooseExistingProgram(
                    sf_.Entries(),candidate,program_);
                Select(candidate,next);
                RebuildRows(); // changed host bank may alter browser selection
            }
        }
        return;
    } else if(tag==kDirectPreset) {
        const auto idx=static_cast<int>(std::lround(programMenu_->getValue()));
        if(idx>=0&&size_t(idx)<activePrograms_.size()) {
            Select(bank_,activePrograms_[size_t(idx)]);
            RebuildRows();
        }
        return;
    } else if(tag==kLoadRom) {
        if(control->getValue()>0.5f)ChooseRom();
    } else if(tag==kLoadSf2) {
        if(control->getValue()>0.5f)ChooseSf2();
    } else if(tag==kReset) {
        if(control->getValue()>0.5f)
            for(int i=0;i<kGuiCount;++i)ChangeParameter(kGuiFirst+i,0.);
    } else if(tag==kPrevious||tag==kNext) {
        if(control->getValue()>0.5f) {
            const int target=PresetBrowserModel::Neighbor(0,sf_,fm_,
                bank_,program_,tag==kNext?1:-1);
            if(target>=0)Select(bank_,static_cast<uint8_t>(target));
        }
    } else if(tag==kMainPage)SetPage(0);
    else if(tag==kEditPage)SetPage(1);
    else if(tag==kToggle)SetPage(2);
    else if(tag==kFilter) {
        searchText_=search_->getText().data();
        RebuildRows();
    } else if(tag==kBankFilter) {
        const int index=int(std::lround(bankMenu_->getValue()));
        bankFilter_=(index>=1&&size_t(index-1)<filterBanks_.size())?
                    filterBanks_[size_t(index-1)]:-1;
        RebuildRows();
    }
}
void PresetBrowserView::onIdle() {Sync();}
int32_t PresetBrowserView::dbGetNumRows(CDataBrowser*) {
    return static_cast<int32_t>(rows_.size());
}
int32_t PresetBrowserView::dbGetNumColumns(CDataBrowser*) {return 1;}
CCoord PresetBrowserView::dbGetRowHeight(CDataBrowser*) {return 27.;}
CCoord PresetBrowserView::dbGetCurrentColumnWidth(int32_t,CDataBrowser*) {return 892.;}
void PresetBrowserView::dbDrawCell(CDrawContext* ctx,const CRect& r,
                                  int32_t row,int32_t,int32_t flags,CDataBrowser*) {
    if(row<0||size_t(row)>=rows_.size())return;
    ctx->setFillColor((flags&IDataBrowserDelegate::kRowSelected)?kSel:kRaised);
    ctx->drawRect(r,kDrawFilled);
    ctx->setFont(kNormalFontSmall);
    ctx->setFontColor(kPaper);
    const auto& p=rows_[size_t(row)];
    char id[24]{};
    std::snprintf(id,sizeof(id),"%03u:%03u  ",p.bank,p.program);
    const auto text=std::string(id)+p.name;
    CRect inset=r;inset.left+=9;inset.right-=5;
    ctx->drawString(text.c_str(),inset,kLeftText);
    ctx->setFrameColor(kGrid);
    ctx->drawLine({r.left,r.bottom-1},{r.right,r.bottom-1});
}
CMouseEventResult PresetBrowserView::dbOnMouseDown(const CPoint&,
    const CButtonState&,int32_t row,int32_t,CDataBrowser* browser) {
    if(row>=0&&size_t(row)<rows_.size()) {
        const auto entry=rows_[size_t(row)];
        selectingRowFromMouse_=true;
        browser->setSelectedRow(row,true);
        selectingRowFromMouse_=false;
        // A CDataBrowser mouse click can highlight without firing the
        // deferred selection-change callback. Commit the actual VST3 host
        // bank + program now; keyboard selection uses dbSelectionChanged.
        Select(entry.bank,entry.program);
    }
    return kMouseDownEventHandledButDontNeedMovedOrUpEvents;
}
void PresetBrowserView::dbSelectionChanged(CDataBrowser* browser) {
    if(syncing_||selectingRowFromMouse_||!browser)return;
    const int row=browser->getSelectedRow();
    if(row<0||size_t(row)>=rows_.size())return;
    const auto entry=rows_[size_t(row)];
    Select(entry.bank,entry.program);
}
} // namespace AWE125
