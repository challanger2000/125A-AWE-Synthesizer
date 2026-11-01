#include "PresetBrowserView.h"
#include "MasterLogoView.h"
#include "vstgui/lib/cgradient.h"
#include "vstgui/lib/cdrawcontext.h"
#include "vstgui/lib/cfont.h"
#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

namespace AWE125 {
using namespace VSTGUI;
namespace {
constexpr CColor kBack(22,27,34,255),kRaised(40,50,62,255),
                 kPaper(225,230,235,255),kMuted(151,168,184,255),
                 kSel(50,84,102,255),kGrid(55,68,80,255),
                 kBezel(12,16,22,255),kStroke(83,99,111,255);
class HardwareFaceplate final : public CView {
public:
    explicit HardwareFaceplate(const CRect& r):CView(r) {setMouseEnabled(false);}
    void draw(CDrawContext* c) override {
        const auto surface=[&](CRect r,CColor fill,CColor edge) {
            c->setFillColor(fill);
            c->drawRect(r,kDrawFilled);
            c->setFrameColor(edge);
            c->drawRect(r,kDrawStroked);
        };
        // Dark, anodized metal enclosure: three functional surfaces.
        surface({11,7,849,55},CColor(34,42,51),CColor(104,117,128));
        surface({13,146,838,199},CColor(13,19,25),CColor(66,80,94));
        surface({16,276,832,570},CColor(19,25,31),CColor(78,94,106));
        // Fine brushed-metal separators, no imitation rack screws.
        c->setFrameColor(CColor(75,91,102));
        c->drawLine({18,55},{841,55});
        c->drawLine({17,201},{840,201});
        c->drawLine({17,269},{840,269});
        c->setFrameColor(CColor(38,50,58));
        c->drawLine({17,55.8},{841,55.8});
        c->drawLine({17,269.8},{840,269.8});
    }
};
constexpr Steinberg::Vst::ParamID kProgram=1000,kEngine=1001,kBank=1002;
std::string BankLabel(uint16_t bank) {
    if(bank==128)return "Bank 128 - Drumkits";
    return "Bank "+std::to_string(bank);
}
}

PresetBrowserView::PresetBrowserView(const CRect& rect,
    Steinberg::Vst::EditController* controller,
    const PresetCatalog& sf,const PresetCatalog& fm,
    const std::string& exactLogoPath)
    : CViewContainer(rect),controller_(controller),sf_(sf),fm_(fm) {
    setBackgroundColor(kBack);
    addView(new HardwareFaceplate({0,0,860,612}));
    addView(new MasterLogoView({18,11,150,50},exactLogoPath));
    title_=MakeLabel({167,15,827,49},"AWE SYNTHESIZER   /   SOUND BLASTER SERIES");
    MakeLabel({24,62,155,91},"HARDWARE",true);
    hardware_=new COptionMenu({176,61,565,95},this,kHardware);
    for(int i=0;i<3;++i)hardware_->addEntry(PresetBrowserModel::HardwareName(i));
    hardware_->setBackColor(kBezel);
    hardware_->setFontColor(kPaper);
    hardware_->setFrameColor(kStroke);
    addView(hardware_);
    info_=MakeLabel({24,107,822,139},"",true);
    MakeLabel({24,156,156,187},"INSTRUMENT",true);
    previous_=MakeButton({176,155,225,190},kPrevious,"<");
    programLabel_=MakeLabel({239,154,733,193},"000",false);
    next_=MakeButton({744,155,793,190},kNext,">");
    toggle_=MakeButton({654,61,819,96},kToggle,"BROWSER");
    // CTextButton::kKickStyle invokes valueChanged TWICE per click: ON,
    // then OFF. Persistent browser visibility MUST use kOnOffStyle.
    toggle_->setStyle(CTextButton::kOnOffStyle);
    toggle_->setValue(1.f);
    bankCaption_=MakeLabel({24,226,150,256},"BANK",true);
    bankMenu_=new COptionMenu({145,225,443,260},this,kBank);
    bankMenu_->setBackColor(kBezel);
    bankMenu_->setFontColor(kPaper);
    bankMenu_->setFrameColor(kStroke);
    addView(bankMenu_);
    searchCaption_=MakeLabel({464,226,530,256},"SUCHE",true);
    search_=new CTextEdit({532,225,821,260},this,kFilter,"");
    search_->setPlaceholderString("Instrument suchen...");
    search_->setImmediateTextChange(true);
    search_->setBackColor(kBezel);
    search_->setFontColor(kPaper);
    search_->setFrameColor(kStroke);
    addView(search_);
    table_=new CDataBrowser({24,282,821,566},this,
                             CScrollView::kVerticalScrollbar|
                             CScrollView::kAutoHideScrollbars);
    table_->setBackgroundColor(kRaised);
    table_->setWantsFocus(true);
    addView(table_);
    empty_=MakeLabel({35,293,786,335},"",true);
    hint_=MakeLabel({24,571,822,601},
                    "Instrument waehlen  |  PREV/NEXT: Programme der aktiven Bank",
                    true);
    SetExpanded(true);
    setWantsIdle(true);
    Sync(true);
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
    button->setFrameColorHighlighted(CColor(116,154,171));
    button->setRoundRadius(4.);
    auto* base=CGradient::create(0.,1.,CColor(66,79,92),CColor(33,44,56));
    auto* active=CGradient::create(0.,1.,CColor(85,119,138),CColor(51,77,93));
    button->setGradient(base);
    button->setGradientHighlighted(active);
    base->forget();
    active->forget();
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
    // Rebuild on the next UI idle, not while CDataBrowser is dispatching
    // a selected-row mouse event. Avoids reentrant layout invalidation.
}
void PresetBrowserView::Select(uint16_t bank,uint8_t program) {
    // Both parameters are written in one UI gesture. Their original host
    // IDs and normalized ranges remain unchanged. No I/O or sample loading.
    if(engine_==0&&bank!=bank_)ChangeParameter(kBank,double(bank)/16383.);
    ChangeParameter(kProgram,double(program)/127.);
}
void PresetBrowserView::RebuildBanks() {
    filterBanks_=PresetBrowserModel::Banks(engine_,sf_,fm_);
    bankMenu_->removeAllEntry();
    bankMenu_->addEntry("Alle Baenke");
    bool exists=false;
    for(const auto id:filterBanks_) {
        bankMenu_->addEntry(BankLabel(id).c_str());
        if(int(id)==bankFilter_)exists=true;
    }
    if(!exists)bankFilter_=-1;
    int index=0;
    for(size_t i=0;i<filterBanks_.size();++i)
        if(int(filterBanks_[i])==bankFilter_)index=static_cast<int>(i+1);
    bankMenu_->setValue(static_cast<float>(index));
}
void PresetBrowserView::RebuildRows() {
    rows_=PresetBrowserModel::Filter(engine_,sf_,fm_,bankFilter_,searchText_);
    table_->recalculateLayout();
    if(rows_.empty()) {
        empty_->setText(engine_==0&&sf_.Entries().empty()?
              "Keine SF2-Presets geladen. SoundFont in assets.cfg konfigurieren.":
              "Keine Treffer. Suche oder Bankfilter aendern.");
        empty_->setVisible(expanded_);
    } else empty_->setVisible(false);
    // Selection highlight follows the same VST3 parameters as the DAW.
    int selected=-1;
    for(size_t i=0;i<rows_.size();++i)
        if(rows_[i].program==program_&&
           rows_[i].bank==(engine_==0?bank_:0)) {selected=int(i);break;}
    syncing_=true;
    if(selected>=0)table_->setSelectedRow(selected,true);
    else table_->unselectAll();
    syncing_=false;
}
void PresetBrowserView::Sync(bool force) {
    if(!controller_)return;
    const int engine=std::clamp(int(std::lround(
        controller_->getParamNormalized(kEngine)*2.)),0,2);
    const auto bank=static_cast<uint16_t>(std::clamp(int(std::lround(
        controller_->getParamNormalized(kBank)*16383.)),0,16383));
    const auto program=static_cast<uint8_t>(std::clamp(int(std::lround(
        controller_->getParamNormalized(kProgram)*127.)),0,127));
    if(!force&&engine==engine_&&bank==bank_&&program==program_)return;
    const bool newEngine=engine!=engine_;
    engine_=engine;
    bank_=bank;
    program_=program;
    hardware_->setValue(static_cast<float>(engine));
    info_->setText(PresetBrowserModel::HardwareDescription(engine_));
    programLabel_->setText(PresetBrowserModel::CurrentLabel(
        engine_,sf_,fm_,bank_,program_).c_str());
    if(newEngine||force)RebuildBanks();
    RebuildRows();
}
void PresetBrowserView::onIdle() { Sync(); }
void PresetBrowserView::SetExpanded(bool value) {
    expanded_=value;
    bankCaption_->setVisible(value);
    bankMenu_->setVisible(value);
    searchCaption_->setVisible(value);
    search_->setVisible(value);
    table_->setVisible(value);
    hint_->setVisible(value);
    empty_->setVisible(value&&rows_.empty());
    toggle_->setTitle(value?"BROWSER SCHLIESSEN":"BROWSER OEFFNEN");
}
void PresetBrowserView::valueChanged(CControl* c) {
    if(!c||syncing_)return;
    const int tag=c->getTag();
    if(tag==kHardware) {
        ChangeParameter(kEngine,std::clamp(int(std::lround(c->getValue())),0,2)/2.);
    } else if(tag==kPrevious||tag==kNext) {
        // Ignore the second, kKickStyle reset-to-zero callback, otherwise
        // one user click advances TWO programs.
        if(c->getValue()>0.5f) {
            const int target=PresetBrowserModel::Neighbor(engine_,sf_,fm_,
                bank_,program_,tag==kNext?1:-1);
            if(target>=0)Select(engine_==0?bank_:0,static_cast<uint8_t>(target));
        }
    } else if(tag==kToggle)SetExpanded(c->getValue()>0.5f);
    else if(tag==kFilter) {
        searchText_=search_->getText().data();
        RebuildRows();
    } else if(tag==kBank) {
        const int index=int(std::lround(bankMenu_->getValue()));
        bankFilter_=(index>=1&&size_t(index-1)<filterBanks_.size())?
                    filterBanks_[size_t(index-1)]:-1;
        RebuildRows();
    }
}
int32_t PresetBrowserView::dbGetNumRows(CDataBrowser*) {
    return static_cast<int32_t>(rows_.size());
}
int32_t PresetBrowserView::dbGetNumColumns(CDataBrowser*) {return 1;}
CCoord PresetBrowserView::dbGetRowHeight(CDataBrowser*) {return 29.;}
CCoord PresetBrowserView::dbGetCurrentColumnWidth(int32_t,CDataBrowser*) {
    return 740.;
}
void PresetBrowserView::dbDrawCell(CDrawContext* ctx,const CRect& r,int32_t row,
                                 int32_t,int32_t flags,CDataBrowser*) {
    if(row<0||size_t(row)>=rows_.size())return;
    ctx->setFillColor((flags&IDataBrowserDelegate::kRowSelected)?kSel:kRaised);
    ctx->drawRect(r,kDrawFilled);
    ctx->setFont(kNormalFont);
    ctx->setFontColor(kPaper);
    const auto& p=rows_[size_t(row)];
    char id[24]{};
    std::snprintf(id,sizeof(id),"%03u:%03u  ",p.bank,p.program);
    const auto label=std::string(id)+p.name;
    CRect inset=r;
    inset.left+=12;
    inset.right-=8;
    ctx->drawString(label.c_str(),inset,kLeftText);
    ctx->setFrameColor(kGrid);
    ctx->drawLine({r.left,r.bottom-1},{r.right,r.bottom-1});
}
CMouseEventResult PresetBrowserView::dbOnMouseDown(const CPoint&,
    const CButtonState&,int32_t row,int32_t,CDataBrowser* browser) {
    if(row>=0&&size_t(row)<rows_.size())browser->setSelectedRow(row,true);
    return kMouseDownEventHandledButDontNeedMovedOrUpEvents;
}
void PresetBrowserView::dbSelectionChanged(CDataBrowser* browser) {
    if(syncing_||!browser)return;
    const int row=browser->getSelectedRow();
    if(row<0||size_t(row)>=rows_.size())return;
    // Snapshot before host parameter callbacks possibly rebuild the table.
    const auto entry=rows_[size_t(row)];
    Select(entry.bank,entry.program);
}
} // namespace AWE125
