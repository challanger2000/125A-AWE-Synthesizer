#pragma once
#include "PresetBrowserModel.h"
#include "vstgui/lib/cdatabrowser.h"
#include "vstgui/lib/idatabrowserdelegate.h"
#include "vstgui/lib/controls/coptionmenu.h"
#include "vstgui/lib/controls/ctextedit.h"
#include "vstgui/lib/controls/cbuttons.h"
#include "vstgui/lib/controls/ctextlabel.h"
#include "public.sdk/source/vst/vsteditcontroller.h"
#include <cstdint>
#include <string>
#include <vector>

namespace AWE125 {
// Actual Windows VSTGUI browser, owned by VST3Editor; all operations UI-only.
// The sound engine and audio-thread code remain completely independent.
class PresetBrowserView final : public VSTGUI::CViewContainer,
                                public VSTGUI::DataBrowserDelegateAdapter,
                                public VSTGUI::IControlListener {
public:
    PresetBrowserView(const VSTGUI::CRect& rect,
                      Steinberg::Vst::EditController* controller,
                      const PresetCatalog& sf,const PresetCatalog& fm);
    void onIdle() override;
    void valueChanged(VSTGUI::CControl* c) override;
    int32_t dbGetNumRows(VSTGUI::CDataBrowser*) override;
    int32_t dbGetNumColumns(VSTGUI::CDataBrowser*) override;
    VSTGUI::CCoord dbGetRowHeight(VSTGUI::CDataBrowser*) override;
    VSTGUI::CCoord dbGetCurrentColumnWidth(int32_t,VSTGUI::CDataBrowser*) override;
    void dbDrawCell(VSTGUI::CDrawContext*,const VSTGUI::CRect&,int32_t,int32_t,
                    int32_t,VSTGUI::CDataBrowser*) override;
    VSTGUI::CMouseEventResult dbOnMouseDown(const VSTGUI::CPoint&,
        const VSTGUI::CButtonState&,int32_t,int32_t,VSTGUI::CDataBrowser*) override;
    void dbSelectionChanged(VSTGUI::CDataBrowser*) override;
protected:
    ~PresetBrowserView() noexcept override = default;
private:
    static constexpr int kHardware=3100,kPrevious=3101,kNext=3102,
        kToggle=3103,kFilter=3104,kBank=3105;
    Steinberg::Vst::EditController* controller_;
    const PresetCatalog& sf_;
    const PresetCatalog& fm_;
    int engine_=-1;
    uint16_t bank_=0;
    uint8_t program_=0;
    int bankFilter_=-1;
    bool expanded_=true, syncing_=false;
    std::string searchText_;
    std::vector<uint16_t> filterBanks_;
    std::vector<PresetBrowserModel::Row> rows_;
    VSTGUI::COptionMenu *hardware_=nullptr,*bankMenu_=nullptr;
    VSTGUI::CTextEdit* search_=nullptr;
    VSTGUI::CTextButton *previous_=nullptr,*next_=nullptr,*toggle_=nullptr;
    VSTGUI::CTextLabel *programLabel_=nullptr,*info_=nullptr,*empty_=nullptr,
                       *bankCaption_=nullptr,*searchCaption_=nullptr,
                       *title_=nullptr,*hint_=nullptr;
    VSTGUI::CDataBrowser* table_=nullptr;
    VSTGUI::CTextLabel* MakeLabel(const VSTGUI::CRect&,const char*,
                                  bool secondary=false);
    VSTGUI::CTextButton* MakeButton(const VSTGUI::CRect&,int,const char*);
    void RebuildBanks();
    void RebuildRows();
    void Sync(bool force=false);
    void SetExpanded(bool);
    void Select(uint16_t bank,uint8_t program);
    void ChangeParameter(Steinberg::Vst::ParamID,double normalized);
};
} // namespace AWE125
