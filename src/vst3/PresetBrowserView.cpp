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
        surface({11,7,1029,57},CColor(35,43,52),CColor(110,122,134));
        surface({12,67,1028,136},CColor(16,22,29),CColor(77,92,106));
        surface({12,145,1028,209},CColor(24,31,39),CColor(78,94,107));
        surface({13,221,630,359},CColor(24,31,38),CColor(82,96,108));
        surface({13,366,630,529},CColor(24,31,38),CColor(82,96,108));
        surface({13,535,630,646},CColor(24,31,38),CColor(82,96,108));
        surface({643,222,1028,646},CColor(18,24,30),CColor(82,96,108));
        surface({12,650,1028,679},CColor(14,20,26),CColor(83,96,108));
        c->setFrameColor(CColor(51,62,72,255));
        c->drawLine({17,61},{1025,61});
        c->drawLine({17,141},{1025,141});
        c->drawLine({17,214},{1025,214});
        c->setFrameColor(CColor(114,126,138,255));
        c->drawLine({20,222},{622,222});
        c->drawLine({20,359},{622,359});
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
        :CControl(r,listener,tag,nullptr) {setMin(0.f);setMax(1.f);}
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
    std::function<uint64_t()> sf2CatalogRevision)
    : CViewContainer(rect),controller_(controller),sf_(sf),fm_(legacyFm),
      sf2StatusProvider_(std::move(sf2StatusProvider)),
      hardwareInfoProvider_(std::move(hardwareInfoProvider)),
      romLoadRequest_(std::move(romLoadRequest)),
      sf2LoadRequest_(std::move(sf2LoadRequest)),
      sf2CurrentPath_(std::move(sf2CurrentPath)),
      sf2CatalogRevision_(std::move(sf2CatalogRevision)) {
    setBackgroundColor(kBack);
    addView(new HardwareFaceplate({0,0,1040,680}));
    addView(new MasterLogoView({18,11,150,51},exactLogoPath));
    MakeLabel({170,12,746,50},"125A  AWE SYNTHESIZER",false);
    addView(new ChipPackage({793,13,1021,51}));
    MakeLabel({830,14,1006,34},"EMU8000",false);
    MakeLabel({830,33,1006,49},"32 VOICES  /  44.1 kHz",true);

    MakeLabel({25,80,149,123},"SOUNDFONT",true);
    fileLabel_=MakeLabel({152,78,658,103},"",false);
    hardwareInfoLabel_=MakeLabel({154,102,660,132},"EMU8000: Hardwarestatus wird ermittelt...",true);
    hardwareInfoLabel_->setTextTruncateMode(CTextLabel::kTruncateTail);
    loadRom_=MakeButton({677,83,826,122},kLoadRom,"ROM LADEN");
    loadSf2_=MakeButton({836,83,1010,122},kLoadSf2,"SF2 LADEN");
    MakeLabel({25,156,143,193},"INSTRUMENT",true);
    previous_=MakeButton({152,159,198,195},kPrevious,"<");
    programLabel_=MakeLabel({212,157,752,199},"",false);
    next_=MakeButton({768,159,813,195},kNext,">");
    toggle_=MakeButton({835,159,1008,195},kToggle,"BROWSER");
    toggle_->setStyle(CTextButton::kOnOffStyle);
    toggle_->setValue(1.f);

    MakeLabel({27,232,500,254},"AMP ENVELOPE",true);
    AddKnob(0,87,257,"ATTACK");
    AddKnob(1,227,257,"DECAY");
    AddKnob(2,367,257,"SUSTAIN -");
    AddKnob(3,507,257,"RELEASE");
    MakeLabel({27,368,583,392},"FILTER ENVELOPE + TONE",true);
    AddKnob(4,41,392,"ATTACK");
    AddKnob(5,137,392,"DECAY");
    AddKnob(6,233,392,"SUSTAIN -");
    AddKnob(7,329,392,"RELEASE");
    AddKnob(8,425,392,"CUTOFF -");
    AddKnob(9,521,392,"RESONANCE +");
    MakeLabel({27,548,488,571},"EFFECT SENDS",true);
    AddKnob(10,222,536,"HALL +");
    AddKnob(11,431,536,"CHORUS +");
    reset_=MakeButton({503,550,615,578},kReset,"RESET");
    MakeLabel({26,601,200,619},"0% = ORIGINAL",true);
    MakeLabel({26,621,211,640},"WIRKT AB NEUER NOTE",true);

    MakeLabel({658,231,990,257},"SOUND BROWSER",true);
    bankCaption_=MakeLabel({656,266,715,293},"BANK",true);
    bankMenu_=new COptionMenu({724,261,1008,298},this,kBankFilter);
    bankMenu_->setBackColor(kBezel);
    bankMenu_->setFontColor(kPaper);
    bankMenu_->setFrameColor(kStroke);
    addView(bankMenu_);
    searchCaption_=MakeLabel({656,306,716,335},"SUCHE",true);
    search_=new CTextEdit({724,304,1008,339},this,kFilter,"");
    search_->setPlaceholderString("Instrument suchen...");
    search_->setImmediateTextChange(true);
    search_->setBackColor(kBezel);
    search_->setFontColor(kPaper);
    search_->setFrameColor(kStroke);
    addView(search_);
    table_=new CDataBrowser({654,346,1015,650},this,
             CScrollView::kVerticalScrollbar|
             CScrollView::kAutoHideScrollbars);
    table_->setBackgroundColor(kRaised);
    table_->setWantsFocus(true);
    addView(table_);
    empty_=MakeLabel({669,359,1009,410},"",true);

    hint_=MakeLabel({27,653,1010,678},
        "SF2-Audiostatus noch nicht vom Prozessor bestaetigt.",true);
    hint_->setTextTruncateMode(CTextLabel::kTruncateTail);
    SetExpanded(true);
    setWantsIdle(true);
    Sync(true);
}
void PresetBrowserView::AddKnob(int index,int x,int y,const char* title) {
    auto* ctrl=new HardwareKnob({CCoord(x),CCoord(y),CCoord(x+58),CCoord(y+58)},
                                this,kGuiFirst+index);
    controls_[size_t(index)]=ctrl;
    addView(ctrl);
    auto* lab=MakeLabel({CCoord(x-20),CCoord(y+61),CCoord(x+82),CCoord(y+81)},title,true);
    lab->setHoriAlign(kCenterText);
    auto* val=MakeLabel({CCoord(x-20),CCoord(y+82),CCoord(x+82),CCoord(y+101)},"0%",false);
    val->setHoriAlign(kCenterText);
    values_[size_t(index)]=val;
}
CTextLabel* PresetBrowserView::MakeLabel(const CRect& r,const char* s,bool secondary) {
    auto* label=new CTextLabel(r,s);
    label->setTransparency(true);
    label->setFont(secondary?kNormalFontSmall:kNormalFont);
    label->setFontColor(secondary?kMuted:kPaper);
    label->setHoriAlign(kLeftText);
    if(!secondary)label->setTextTruncateMode(CTextLabel::kTruncateTail);
    addView(label);
    return label;
}
CTextButton* PresetBrowserView::MakeButton(const CRect& r,int tag,const char* s) {
    auto* button=new CTextButton(r,this,tag,s);
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
    addView(button);
    return button;
}
void PresetBrowserView::ChangeParameter(Steinberg::Vst::ParamID tag,double norm) {
    if(!controller_)return;
    norm=std::clamp(norm,0.,1.);
    controller_->beginEdit(tag);
    controller_->setParamNormalized(tag,norm);
    controller_->performEdit(tag,norm);
    controller_->endEdit(tag);
}
void PresetBrowserView::Select(uint16_t bank,uint8_t program) {
    if(bank!=bank_)ChangeParameter(kBankParam,double(bank)/16383.);
    ChangeParameter(kProgram,double(program)/127.);
    // Reflect the clicked instrument immediately. The following idle
    // compares bank/program back with the controller: an unaccepted host
    // edit is not silently painted as a successful selection.
    bank_=bank;
    program_=program;
    programLabel_->setText(PresetBrowserModel::CurrentLabel(
        0,sf_,fm_,bank_,program_).c_str());
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
        empty_->setVisible(expanded_);
    } else empty_->setVisible(false);
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
    SyncSf2Status();
    SyncHardwareInfo();
    if(!force&&bank==bank_&&program==program_)return;
    bank_=bank;program_=program;
    programLabel_->setText(PresetBrowserModel::CurrentLabel(
        0,sf_,fm_,bank_,program_).c_str());
    if(force)RebuildBanks();
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
void PresetBrowserView::SetExpanded(bool value) {
    expanded_=value;
    bankCaption_->setVisible(value);
    bankMenu_->setVisible(value);
    searchCaption_->setVisible(value);
    search_->setVisible(value);
    table_->setVisible(value);
    empty_->setVisible(value&&rows_.empty());
    hint_->setVisible(true);
    toggle_->setTitle(value?"BROWSER SCHLIESSEN":"BROWSER OEFFNEN");
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
    if(tag>=kGuiFirst && tag<kGuiFirst+kGuiCount) {
        const int idx=tag-kGuiFirst;
        ChangeParameter(static_cast<Steinberg::Vst::ParamID>(tag),
                        std::clamp(double(control->getValue()),0.,1.));
        return;
    }
    if(tag==kLoadRom) {
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
    } else if(tag==kToggle)SetExpanded(control->getValue()>0.5f);
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
CCoord PresetBrowserView::dbGetCurrentColumnWidth(int32_t,CDataBrowser*) {return 315.;}
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
