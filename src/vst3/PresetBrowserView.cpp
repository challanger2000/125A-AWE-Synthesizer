#include "PresetBrowserView.h"
#include "vstgui/lib/cgradient.h"
#include "vstgui/lib/cgraphicspath.h"
#include "vstgui/lib/cbitmap.h"
#include "vstgui/lib/cdrawcontext.h"
#include "vstgui/lib/controls/cscrollbar.h"
#include "vstgui/lib/cfont.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <initializer_list>
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
// P156: PCB image is a pure noninteractive BACK layer. The exact 1000x640
// resource is allowed to have dense raised parts everywhere; half-opaque
// control islands on a separate VSTGUI layer protect labels and input hitboxes.
class FunctionalLayoutBackground final : public CView {
public:
    explicit FunctionalLayoutBackground(const CRect& r)
        : CView(r),
          p164_(new CBitmap("125A_P164_PCB_Single_Header_1000x640.png")),
          p160_(new CBitmap("125A_P160_PCB_1000x640.png")),
          fallback_(new CBitmap("125A_PCB_Shared_1000x640.png")) {
        setMouseEnabled(false);
    }
    ~FunctionalLayoutBackground() noexcept override {
        if(p164_)p164_->forget();
        if(p160_)p160_->forget();
        if(fallback_)fallback_->forget();
    }
    bool hasSingleHeader() const noexcept {
        return p164_ && p164_->isLoaded();
    }
    void draw(CDrawContext* c) override {
        // P164: ONE complete photographic board, one LCD frame, one logo,
        // one clean EMU8000 chip. Do NOT overlay another LCD or logo view.
        const bool singleHeader=hasSingleHeader();
        const bool approved=singleHeader || (p160_ && p160_->isLoaded());
        if(singleHeader)
            p164_->draw(c,getViewSize());
        else if(p160_ && p160_->isLoaded())
            p160_->draw(c,getViewSize());
        else if(fallback_ && fallback_->isLoaded())
            fallback_->draw(c,getViewSize());
        else {
            c->setFillColor(CColor(13,17,23,255));
            c->drawRect(getViewSize(),kDrawFilled);
        }
        // The fallback P156 image was not stripped of the original lettering
        // and LCD. Keep that obsolete image safe for builds without new art.
        // The P160 board was deliberately scrubbed in those two rectangles;
        // leave its gold PCB traces fully visible behind the live assets.
        if(!approved) {
            c->setFillColor(CColor(9,12,14,255));
            c->drawRect({16,16,252,163},kDrawFilled);
            c->setFillColor(CColor(9,12,14,255));
            c->drawRect({264,16,776,163},kDrawFilled);
        }
        // P162: one aligned, rounded hardware rail spanning the SAME
        // full-width grid as the browser panel. Every menu/button has a
        // 10px visible outside inset and 8-9px inter-control gutters.
        const CRect rail{16,173,984,224};
        if(auto* p=c->createRoundRectGraphicsPath(rail,7.)) {
            c->setFillColor(CColor(9,12,16,205));
            c->drawGraphicsPath(p,CDrawContext::kPathFilled);
            c->setFrameColor(CColor(190,131,55,220));
            c->setLineWidth(1.);
            c->drawGraphicsPath(p,CDrawContext::kPathStroked);
            p->forget();
        }
        setDirty(false);
    }
private:
    CBitmap* p164_{nullptr};
    CBitmap* p160_{nullptr};
    CBitmap* fallback_{nullptr};
};

// P154: exact gold wordmark extracted from the approved soundcard reference.
// The image stays separate and has an alpha channel; no live text is baked
// into the final PCB and no alternative branding is substituted.
class GoldLogoArtwork final : public CView {
public:
    explicit GoldLogoArtwork(const CRect& rect)
        : CView(rect), bitmap_(new CBitmap("125A_AWE_Gold_Logo_236x147.png")) {
        setMouseEnabled(false);
    }
    ~GoldLogoArtwork() noexcept override {
        if(bitmap_) bitmap_->forget();
    }
    void draw(CDrawContext* ctx) override {
        if(bitmap_ && bitmap_->isLoaded()) {
            // P160: 193x120 exactly, proportional to the approved 236x147 PNG,
            // using a rendering transform rather than inventing new lettering.
            auto r=getViewSize();
            CGraphicsTransform t;
            t.translate(-r.left,-r.top);
            t.scale(193./236.,120./147.);
            t.translate(39.,28.);
            CDrawContext::Transform scaled(*ctx,t);
            bitmap_->draw(ctx,r);
        }
        setDirty(false);
    }
private:
    CBitmap* bitmap_{nullptr};
};

// P151 separate, text-free amber LCD photo artwork. Dynamic labels are
// native VSTGUI children added AFTER this non-interactive bitmap view.
class AmberLcdArtwork final : public CView {
public:
    explicit AmberLcdArtwork(const CRect& r)
        : CView(r),
          complete_(new CBitmap("125A_P160_Lcd_Complete_512x147.png")),
          bitmap_(new CBitmap("125A_Lcd_Amber_Blank_512x147.png")) {
        setMouseEnabled(false);
    }
    ~AmberLcdArtwork() noexcept override {
        if(complete_)complete_->forget();
        if(bitmap_)bitmap_->forget();
    }
    void draw(CDrawContext* c) override {
        if(complete_ && complete_->isLoaded())
            complete_->draw(c,getViewSize());
        else if(bitmap_ && bitmap_->isLoaded())
            bitmap_->draw(c,getViewSize());
        setDirty(false);
    }
private:
    CBitmap* complete_{nullptr};
    CBitmap* bitmap_{nullptr};
};

// Only on the SYNTH page; the BROWSER receives one undivided canvas.
// All group boundaries align to a deliberately fixed spacing grid.
// These groups render ABOVE the photographic PCB and BELOW every real
// control. The fill is 60 percent opaque (alpha 153/255), showing the PCB.
class SynthPanelGroups final : public CView {
public:
    explicit SynthPanelGroups(const CRect& r):CView(r) {setMouseEnabled(false);}
    void draw(CDrawContext* c) override {
        const auto island=[&](CRect r) {
            auto* border=c->createRoundRectGraphicsPath(r,8.);
            if(!border)return;
            c->setFillColor(CColor(7,11,16,153)); // P160 60% approved preview.
            c->drawGraphicsPath(border,CDrawContext::kPathFilled);
            c->setLineWidth(1.);
            c->setFrameColor(CColor(190,131,55,226));
            c->drawGraphicsPath(border,CDrawContext::kPathStroked);
            border->forget();
            // Thin reflected edge, without solid rectangular helper boxes.
            c->setFrameColor(CColor(240,181,92,100));
            c->drawLine({r.left+13.,r.top+2.},
                        {r.right-13.,r.top+2.});
        };
        // P160 screw-safe silhouettes are polygons, not circles painted
        // over the photo: the photo's original corner screw pixels remain
        // completely untouched. Coordinates are page-local (global Y-232).
        const auto notched=[&](std::initializer_list<CPoint> vertices) {
            auto* p=c->createGraphicsPath();
            if(!p)return;
            bool first=true;
            for(const auto& xy:vertices) {
                if(first){p->beginSubpath(xy);first=false;}
                else p->addLine(xy);
            }
            p->closeSubpath();
            c->setFillColor(CColor(7,11,16,153));
            c->drawGraphicsPath(p,CDrawContext::kPathFilled);
            c->setLineWidth(1.);
            c->setFrameColor(CColor(190,131,55,226));
            c->drawGraphicsPath(p,CDrawContext::kPathStroked);
            p->forget();
        };
        island({16,2,190,177});   // REVERB
        island({200,2,374,177});  // CHORUS
        island({384,2,774,177});  // AMP ADSR
        // Master panel has a relief notch at bottom-right (screw 969,575).
        notched({{784,2},{984,2},{984,319},{969,318},{957,321},{948,329},{944,341},{944,358},{784,358}});
        // Filter ADSR panel has a relief notch at bottom-left (screw 32,575).
        notched({{16,187},{518,187},{518,358},{58,358},{58,343},{55,332},{47,324},{32,318},{20,321},{16,326}});
        island({528,187,774,358});// CUTOFF / RESONANCE
        setDirty(false);
    }
};

// BROWSER is intentionally different: a single translucent dark sheet
// behind the existing search/table so the native selected rows remain legible.
class BrowserPanelBacking final : public CView {
public:
    explicit BrowserPanelBacking(const CRect& r):CView(r) {setMouseEnabled(false);}
    void draw(CDrawContext* c) override {
        // Cut both lower corners away from the PCB's gold screw heads.
        auto* border=c->createGraphicsPath();
        if(border) {
            border->beginSubpath({16,2});
            for(const CPoint p:std::initializer_list<CPoint>{
                {984,2},{984,319},{969,318},{957,321},{948,329},{944,341},{944,356},
                {58,356},{58,343},{55,332},{47,324},{32,318},{20,321},{16,326}
            }) border->addLine(p);
            border->closeSubpath();
        }
        if(border) {
            // Keep the whole PCB visible at the same overall opacity as P160.
            // The muted gold edge is shared with the SYNTH control islands.
            c->setFillColor(CColor(7,11,16,153));
            c->drawGraphicsPath(border,CDrawContext::kPathFilled);
            c->setFrameColor(CColor(190,131,55,220));
            c->setLineWidth(1.);
            c->drawGraphicsPath(border,CDrawContext::kPathStroked);
            border->forget();
        }
        // P163: the rail's last button and BOTH recessed gold-field right
        // edges finish at X=974 (10px inside the X=984 outer bezel).
        // Preserve 394px width of the bank and search control surfaces.
        // Bezel views remain non-interactive; input controls are unchanged.
        const auto recessed=[&](const CRect& r,CCoord radius,
                                 CColor backing,CColor edge) {
            auto* p=c->createRoundRectGraphicsPath(r,radius);
            if(!p)return;
            c->setFillColor(backing);
            c->drawGraphicsPath(p,CDrawContext::kPathFilled);
            c->setFrameColor(edge);
            c->setLineWidth(1.3);
            c->drawGraphicsPath(p,CDrawContext::kPathStroked);
            p->forget();
            c->setFrameColor(CColor(250,204,126,195));
            c->setLineWidth(1.);
            c->drawLine({r.left+radius+3.,r.top+2.},
                        {r.right-radius-3.,r.top+2.});
        };
        recessed({580,15,974,52},6.,CColor(11,13,15,230),
                 CColor(192,132,58,245)); // search
        recessed({24,63,974,349},7.,CColor(11,14,16,242),
                 CColor(191,136,65,240)); // program table
        setDirty(false);
    }
};
// P153: photographic hardware atlas. Each button uses a native-size
// rectangle (no scaling), with a second 44px-spaced frame for physical depression.
// The text remains a live VSTGUI label; the image provides the real bevel.
class GoldButton final : public CTextButton {
public:
    GoldButton(const CRect& r,IControlListener* listener,int tag,
               const char* caption,CCoord sourceX)
        :CTextButton(r,listener,tag,caption),
         caption_(caption),sourceX_(sourceX),
         atlas_(new CBitmap("125A_Button_Atlas_Hardware_Normal_Pressed.png")) {}
    ~GoldButton() noexcept override {
        if(atlas_)atlas_->forget();
    }
    void draw(CDrawContext* c) override {
        if(!atlas_ || !atlas_->isLoaded()) {
            // Keep the controls usable even if a resource is missing;
            // GUI acceptance will explicitly reject this fallback.
            CTextButton::draw(c);
            return;
        }
        const bool active=getValue()>0.5f;
        atlas_->draw(c,getViewSize(),{sourceX_,active?44.:0.});
        c->setFont(getFont());
        c->setFontColor(active?CColor(255,232,173,255):
                              CColor(241,201,127,255));
        CRect textRect=getViewSize();
        // The keycap text follows the depressed surface by one pixel.
        if(active) {
            textRect.top+=1.;
            textRect.bottom+=1.;
        }
        c->drawString(caption_.c_str(),textRect,kCenterText);
        setDirty(false);
    }
private:
    std::string caption_;
    CCoord sourceX_;
    CBitmap* atlas_{nullptr};
};

// P155: independent hardware selector surface. COptionMenu remains the
// actual input component and still owns native, keyboard-accessible popups,
// item IDs, value changes and DAW automation. Only the CLOSED control is
// custom-painted to match P149 knobs / P153 physical gold buttons.
class GoldHardwareMenu final : public COptionMenu {
public:
    GoldHardwareMenu(const CRect& rect, IControlListener* listener, int32_t tag)
        : COptionMenu(rect,listener,tag) {}
    void draw(CDrawContext* ctx) override {
        ctx->saveGlobalState();
        const auto fillRounded=[&](const CRect& r,CCoord radius,
                                   const CColor& upper,const CColor& lower) {
            auto* p=ctx->createRoundRectGraphicsPath(r,radius);
            if(!p)return;
            auto* g=CGradient::create(0.,1.,upper,lower);
            ctx->fillLinearGradient(p,*g,{r.left,r.top},{r.left,r.bottom});
            g->forget();p->forget();
        };
        CRect r=getViewSize();
        r.inset(.25,.25);
        const bool thin=r.getHeight()<29.;
        const auto rad=thin?4.:6.;
        // Stable black chassis, bright metal relief, and inset dark display.
        fillRounded(r,rad+1.,CColor(7,7,9),CColor(7,7,9));
        CRect rim=r;rim.inset(1.,1.);
        fillRounded(rim,rad,CColor(246,204,119),CColor(112,70,29));
        CRect brass=rim;brass.inset(1.4,1.4);
        fillRounded(brass,rad-1.,CColor(97,61,32),CColor(235,163,69));
        CRect well=brass;well.inset(1.8,1.8);
        fillRounded(well,std::max(2.,rad-2.),
                    inPopup?CColor(8,8,9):CColor(18,17,17),
                    inPopup?CColor(43,29,16):CColor(36,28,22));
        // Fine bezel reflection and recessed inner shadow.
        ctx->setLineWidth(1.);
        ctx->setFrameColor(CColor(251,219,146,190));
        ctx->drawLine({rim.left+rad+1.,rim.top+1.},
                      {rim.right-rad-1.,rim.top+1.});
        ctx->setFrameColor(CColor(5,5,5,210));
        ctx->drawLine({well.left+rad,well.top+1.},
                      {well.right-rad,well.top+1.});
        const CCoord edge=well.right-(thin?21.:25.);
        ctx->setFrameColor(CColor(132,91,39,200));
        ctx->drawLine({edge,well.top+3.},{edge,well.bottom-3.});
        ctx->setFrameColor(CColor(25,17,12,255));
        ctx->drawLine({edge+1.,well.top+3.},{edge+1.,well.bottom-3.});
        // Arrow is part of the hardware surface, not an extra hit target.
        const CCoord ax=edge+(well.right-edge)*.50;
        const CCoord ay=(well.top+well.bottom)*.5;
        auto* arrow=ctx->createGraphicsPath();
        if(arrow) {
            const double dx=thin?4.5:5.5,dy=thin?2.7:3.3;
            arrow->beginSubpath({ax-dx,ay-dy*.5});
            arrow->addLine({ax+dx,ay-dy*.5});
            arrow->addLine({ax,ay+dy});
            arrow->closeSubpath();
            ctx->setFillColor(inPopup?CColor(255,222,151):CColor(234,180,90));
            ctx->drawGraphicsPath(arrow,CDrawContext::kPathFilled);
            arrow->forget();
        }
        // The currently selected item is always native data, never drawn
        // into a bitmap. Explicit clip keeps long SF2 names out of the arrow.
        const CMenuItem* item=getCurrent();
        if(item) {
            CRect textRect=well;
            textRect.left+=thin?8.:11.;
            textRect.right=edge-5.;
            ctx->setFont(getFont());
            ctx->setFontColor(CColor(244,200,118));
            ctx->setClipRect(textRect);
            ctx->drawString(item->getTitle().data(),textRect,kLeftText);
        }
        ctx->restoreGlobalState();
        setDirty(false);
    }
};

static void StyleGoldMenu(COptionMenu* menu) {
    if(!menu)return;
    menu->setBackColor(CColor(22,19,18,255));
    menu->setFontColor(CColor(244,198,112,255));
    menu->setFrameColor(CColor(181,122,55,255));
    menu->setFont(menu->getViewSize().getHeight()<29.?kNormalFontSmall:kNormalFont);
}
// Mouse-driven, modern hardware-like knob. Uses native VSTGUI controls,
// never paints values that differ from the host's normalized parameters.
class HardwareKnob final : public CControl {
public:
    HardwareKnob(const CRect& r,IControlListener* listener,int tag)
        :CControl(r,listener,tag,nullptr) {
        setMin(0.f);setMax(1.f);
        setDefaultValue(0.f);
        // Exactly 33 equal-size vertical frames. The larger master receives
        // a separate 134px PNG; no runtime image scaling or frame rotation.
        const bool isMaster=r.getWidth()>90.;
        frameSize_=isMaster?134.:58.;
        frames_=new CBitmap(isMaster
            ? "125A_Knob_Master_33frames_134px.png"
            : "125A_Knob_Standard_33frames_58px.png");
    }
    ~HardwareKnob() noexcept override {
        if(frames_)frames_->forget();
    }
    void draw(CDrawContext* ctx) override {
        if(frames_&&frames_->isLoaded()) {
            const int index=std::clamp(
                int(std::lround(double(getValue())*32.)),0,32);
            // VSTGUI source offset selects exactly one square frame.
            frames_->draw(ctx,getViewSize(),{0.,frameSize_*index});
            setDirty(false);
            return;
        }
        // Visible, functional fallback if a PNG resource is unavailable.
        // The Windows GUI acceptance explicitly rejects this fallback.
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
        ctx->setLineWidth(3);
        ctx->setFrameColor(getValue()>0.0001f?kOrange:kMuted);
        ctx->drawLine({cx+std::cos(angle)*8,cy+std::sin(angle)*8},
                      {cx+std::cos(angle)*(outer.getWidth()-9)*.5,
                       cy+std::sin(angle)*(outer.getHeight()-9)*.5});
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
    CBitmap* frames_{nullptr};
    CCoord frameSize_{0.};
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
    auto* photo=new FunctionalLayoutBackground({0,0,1000,640});
    addView(photo);
    // P164 already includes the fully intact LCD bezel, gold lettering
    // and EMU8000 chip IN ONE IMAGE. Duplicating either bitmap here was
    // the source of the ghost screws and overlapping LCD right frame.
    // Compatibility for older build trees is retained, but never active
    // when the deterministic P164 photo is present.
    if(!photo->hasSingleHeader()) {
        addView(new AmberLcdArtwork({264,16,776,163}));
        addView(new GoldLogoArtwork({16,16,252,163}));
    }
    // Native dynamic status, bank/program and filename remain on top.

    // P152: the amber LCD owns the complete live status line, including
    // the current filename. Its labels remain real host-driven VSTGUI views.
    auto* lcd=MakeLabel({310,48,534,64},"EMU8000  |  SOUNDFONT ENGINE",true);
    lcd->setFontColor(CColor(219,169,70,255));
    fileLabel_=MakeLabel({546,48,737,64},"",false);
    fileLabel_->setFont(kNormalFontSmall);
    fileLabel_->setFontColor(CColor(221,174,91,255));
    fileLabel_->setTextTruncateMode(CTextLabel::kTruncateTail);
    programLabel_=MakeLabel({310,66,737,94},"NO PRESET",false);
    programLabel_->setFont(kNormalFontBig);
    programLabel_->setFontColor(CColor(245,193,78,255));
    hardwareInfoLabel_=MakeLabel({310,96,737,113},"ROM: ERFORDERLICH",true);
    hardwareInfoLabel_->setFontColor(CColor(221,174,91,255));
    hardwareInfoLabel_->setTextTruncateMode(CTextLabel::kTruncateTail);

    // Full 196 x 147 top-right region (788..984,16..163) is now strictly
    // reserved for the *real* decorative EMU8000 chip and its components.
    // Native-size button assets (ROM 77x41, SF2 75x41) were moved onto the
    // compact, consistently aligned navigation strip without scaling.
    // P163 visual-pixel alignment: physical hardware button atlases
    // include ~5px of transparent right-side shadow/padding. The SF2
    // view ends at x=979, but its actual gold right edge lands at x=974,
    // matching both browser inset fields (whose vector edges are x=974).
    // Distribute the 5px correction as five 9px + two 8px gutters so
    // the hardware controls retain original/native widths and look even.
    // A duplicate BANK caption cramped this entire band; the dropdown
    // already displays "Bank 0". Use the freed width for the live menu.
    activeBankMenu_=new GoldHardwareMenu({26,179,203,218},this,kActiveBank);
    StyleGoldMenu(activeBankMenu_);
    addView(activeBankMenu_);
    previous_=MakeButton({212,179,252,218},kPrevious,"<");
    programMenu_=new GoldHardwareMenu({261,179,552,218},this,kDirectPreset);
    StyleGoldMenu(programMenu_);
    addView(programMenu_);
    next_=MakeButton({561,179,601,218},kNext,">");
    pageButtons_[0]=MakeButton({610,179,703,218},kMainPage,"SYNTH");
    toggle_=MakeButton({712,179,811,218},kToggle,"BROWSER");
    loadRom_=MakeButton({819,177,896,218},kLoadRom,"ROM");
    loadSf2_=MakeButton({904,177,979,218},kLoadSf2,"SF2");
    pageButtons_[1]=toggle_;
    for(auto* tab:pageButtons_)
        tab->setStyle(CTextButton::kOnOffStyle);

    for(auto*& page:pages_) {
        page=new CViewContainer({0,232,1000,592});
        page->setTransparency(true);
        addView(page);
    }
    buildingPanel_=pages_[0];
    AddToCurrentPage(new SynthPanelGroups(PageRect({0,232,1000,592})));

    auto* reverbTitle=MakeLabel({23,247,183,270},"REVERB",false);
    reverbTitle->setHoriAlign(kCenterText);
    auto* chorusTitle=MakeLabel({207,247,367,270},"CHORUS",false);
    chorusTitle->setHoriAlign(kCenterText);
    auto* ampTitle=MakeLabel({395,247,764,270},"AMP ENVELOPE",false);
    ampTitle->setHoriAlign(kCenterText);
    auto* masterTitle=MakeLabel({792,247,975,270},"MASTER VOLUME",false);
    masterTitle->setHoriAlign(kCenterText);
    for(auto* title:{reverbTitle,chorusTitle,ampTitle,masterTitle})
        title->setFontColor(CColor(222,181,104,255));

    AddKnob(10,74,278,"SEND");
    AddKnob(11,258,278,"SEND");
    AddKnob(0,408,278,"ATTACK");
    AddKnob(1,502,278,"DECAY");
    AddKnob(2,596,278,"SUSTAIN");
    AddKnob(3,690,278,"RELEASE");

    reverbMenu_=new GoldHardwareMenu(PageRect({32,382,174,405}),this,kReverbType);
    chorusMenu_=new GoldHardwareMenu(PageRect({216,382,358,405}),this,kChorusType);
    for(auto* menu:{reverbMenu_,chorusMenu_})
        StyleGoldMenu(menu);
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

    masterVolume_=new HardwareKnob(PageRect({817,298,951,432}),
                                  this,kMasterVolume);
    masterVolume_->setDefaultValue(1.f);
    masterVolume_->setValue(1.f);
    AddToCurrentPage(masterVolume_);
    masterVolumeValue_=MakeLabel({810,446,960,483},"100%",false);
    masterVolumeValue_->setHoriAlign(kCenterText);
    masterVolumeValue_->setFont(kNormalFontBig);

    auto* filterEnv=MakeLabel({25,430,508,452},"FILTER ENVELOPE",false);
    filterEnv->setHoriAlign(kCenterText);
    auto* filterTone=MakeLabel({537,430,766,452},"FILTER",false);
    filterTone->setHoriAlign(kCenterText);
    for(auto* title:{filterEnv,filterTone})
        title->setFontColor(CColor(222,181,104,255));

    AddKnob(4,48,464,"ATTACK");
    AddKnob(5,169,464,"DECAY");
    AddKnob(6,290,464,"SUSTAIN");
    AddKnob(7,411,464,"RELEASE");
    AddKnob(8,563,464,"CUTOFF");
    AddKnob(9,687,464,"RESONANCE");
    reset_=MakeButton({808,513,960,549},kReset,"MOD RESET");

    // BROWSER: no permanent 400px sidebar. It uses the available width,
    // retains true SF2 bank filtering, search and exact program selection.
    buildingPanel_=pages_[1];
    AddToCurrentPage(new BrowserPanelBacking(PageRect({0,232,1000,592})));
    bankCaption_=MakeLabel({28,247,94,282},"FILTER",true);
    bankMenu_=new GoldHardwareMenu(PageRect({100,247,494,284}),this,kBankFilter);
    StyleGoldMenu(bankMenu_);
    AddToCurrentPage(bankMenu_);
    searchCaption_=MakeLabel({506,247,572,282},"SUCHE",true);
    search_=new CTextEdit(PageRect({586,249,968,282}),this,kFilter,"");
    search_->setPlaceholderString("Instrument suchen...");
    search_->setImmediateTextChange(true);
    // Underlying CTextEdit still owns typing, caret, search and focus.
    // Its metal bezel is a separate non-interactive view behind the edit.
    search_->setBackColor(CColor(18,19,18,255));
    search_->setFontColor(CColor(244,204,136,255));
    search_->setFrameColor(CColor(18,19,18,255));
    search_->setFrameWidth(0.);
    search_->setTextInset({11.,0.});
    AddToCurrentPage(search_);
    table_=new CDataBrowser(PageRect({28,299,970,576}),this,
             CScrollView::kVerticalScrollbar|
             CScrollView::kAutoHideScrollbars);
    table_->setBackgroundColor(CColor(18,21,22,255));
    if(auto* bar=table_->getVerticalScrollbar()) {
        bar->setScrollerColor(CColor(181,129,66,255));
        bar->setBackgroundColor(CColor(17,19,20,255));
        bar->setFrameColor(CColor(114,80,43,255));
    }
    table_->setWantsFocus(true);
    AddToCurrentPage(table_);
    empty_=MakeLabel({34,324,966,359},"",true);
    // All browser captions are gold, not the temporary steel-blue palette.
    for(auto* label:{bankCaption_,searchCaption_})
        label->setFontColor(CColor(224,181,108,255));
    empty_->setFontColor(CColor(204,167,108,255));

    buildingPanel_=nullptr;
    hint_=MakeLabel({310,114,737,131},
        "SF2-Audiostatus noch nicht vom Prozessor bestaetigt.",true);
    hint_->setTextTruncateMode(CTextLabel::kTruncateTail);
    SetPage(0);
    setWantsIdle(true);
    Sync(true);
}
VSTGUI::CRect PresetBrowserView::PageRect(const VSTGUI::CRect& r) const {
    if (!buildingPanel_) return r;
    // The active page starts at logical Y=232; all named controls continue
    // to use one stable, explicit desktop coordinate system.
    return {r.left,r.top-232.,r.right,r.bottom-232.};
}
void PresetBrowserView::AddToCurrentPage(VSTGUI::CView* v) {
    if (buildingPanel_) buildingPanel_->addView(v);
    else addView(v);
}
void PresetBrowserView::AddKnob(int index,int x,int y,const char* title) {
    auto* ctrl=new HardwareKnob(PageRect({CCoord(x),CCoord(y),CCoord(x+58),CCoord(y+58)}),
                                this,kGuiFirst+index);
    controls_[size_t(index)]=ctrl;
    AddToCurrentPage(ctrl);
    auto* lab=MakeLabel({CCoord(x-16),CCoord(y+63),CCoord(x+74),CCoord(y+80)},title,true);
    lab->setHoriAlign(kCenterText);
    auto* val=MakeLabel({CCoord(x-16),CCoord(y+81),CCoord(x+74),CCoord(y+98)},"0%",false);
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
    // Source X is the first pixel of the exact-size atlas column.
    // Read-only bitmap is shared by resource name, not resampled.
    CCoord x=0.;
    switch(tag) {
        case kLoadRom:  x=0.;   break; // 77 x 41
        case kLoadSf2:  x=80.;  break; // 75 x 41
        case kPrevious: x=158.; break; // 40 x 39
        case kNext:     x=201.; break; // 42 x 39
        case kMainPage: x=246.; break; // 93 x 39
        case kToggle:   x=342.; break; // 99 x 39
        case kReset:    x=444.; break; // 152 x 36
        default:        x=0.;   break;
    }
    auto* button=new GoldButton(PageRect(r),this,tag,s,x);
    button->setFont(kNormalFont);
    // Gold fallback if the PNG resource is temporarily unavailable.
    button->setTextColor(CColor(241,201,127,255));
    button->setTextColorHighlighted(CColor(255,232,173,255));
    button->setFrameColor(CColor(157,112,52,255));
    button->setFrameColorHighlighted(CColor(235,182,82,255));
    button->setRoundRadius(6.);
    auto* base=CGradient::create(0.,1.,
        CColor(56,44,29,255),CColor(24,23,22,255));
    auto* pressed=CGradient::create(0.,1.,
        CColor(112,75,33,255),CColor(55,41,25,255));
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
        empty_->setVisible(currentPage_==1);
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
    hint_->setFontColor(err?CColor(255,143,122,255):CColor(213,168,93,255));
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
    currentPage_=std::clamp(page,0,1);
    for(size_t i=0;i<pages_.size();++i) {
        if(pages_[i])pages_[i]->setVisible(int(i)==currentPage_);
        if(pageButtons_[i]) {
            pageButtons_[i]->setValue(int(i)==currentPage_?1.f:0.f);
            pageButtons_[i]->invalid();
        }
    }
    if(empty_)empty_->setVisible(currentPage_==1&&rows_.empty());
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
    else if(tag==kToggle)SetPage(1);
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
CCoord PresetBrowserView::dbGetCurrentColumnWidth(int32_t,CDataBrowser* browser) {
    // P162: fill the current client area instead of the legacy 892px strip.
    // The native vertical scrollbar is already excluded from this viewport.
    // This also handles auto-hidden scrollbars and UI zoom without guessing
    // a fixed 16px width or leaving a 52px dark gap on the right.
    if (!browser) return 942.;
    const CCoord visible=browser->getVisibleClientRect().getWidth();
    return visible>0. ? visible : 942.;
}
void PresetBrowserView::dbDrawCell(CDrawContext* ctx,const CRect& r,
                                  int32_t row,int32_t,int32_t flags,CDataBrowser*) {
    if(row<0||size_t(row)>=rows_.size())return;
    // P161: hardware-black rows, subdued copper separators and a warm
    // brass selection instead of the old blue-gray list box.
    const bool selected=(flags&IDataBrowserDelegate::kRowSelected)!=0;
    ctx->setFillColor(selected ? CColor(78,56,27,255)
                               : (row%2 ? CColor(21,23,22,255)
                                        : CColor(17,20,20,255)));
    ctx->drawRect(r,kDrawFilled);
    if(selected) {
        ctx->setFillColor(CColor(235,178,83,255));
        ctx->drawRect({r.left,r.top,r.left+3.,r.bottom},kDrawFilled);
        ctx->setFrameColor(CColor(181,130,67,255));
        ctx->setLineWidth(1.);
        ctx->drawLine({r.left+3.,r.top},{r.right,r.top});
        ctx->drawLine({r.left+3.,r.bottom-1.},{r.right,r.bottom-1.});
    }
    ctx->setFont(kNormalFontSmall);
    ctx->setFontColor(selected?CColor(255,225,161,255)
                              :CColor(229,205,162,255));
    const auto& p=rows_[size_t(row)];
    char id[24]{};
    std::snprintf(id,sizeof(id),"%03u:%03u  ",p.bank,p.program);
    const auto text=std::string(id)+p.name;
    CRect inset=r;inset.left+=11;inset.right-=5;
    ctx->drawString(text.c_str(),inset,kLeftText);
    if(!selected) {
        ctx->setFrameColor(CColor(86,66,41,155));
        ctx->setLineWidth(1.);
        ctx->drawLine({r.left+6.,r.bottom-1.},{r.right-5.,r.bottom-1.});
    }
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
