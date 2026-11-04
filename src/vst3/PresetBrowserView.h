#pragma once
#include "PresetBrowserModel.h"
#include "MasterOutput.h"
#include "vstgui/lib/cdatabrowser.h"
#include "vstgui/lib/idatabrowserdelegate.h"
#include "vstgui/lib/controls/coptionmenu.h"
#include "vstgui/lib/controls/ctextedit.h"
#include "vstgui/lib/controls/cbuttons.h"
#include "vstgui/lib/controls/ctextlabel.h"
#include "vstgui/lib/controls/ccontrol.h"
#include "public.sdk/source/vst/vsteditcontroller.h"
#include <array>
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace AWE125 {
// Single-hardware AWE editor. Browser remains tied to host bank/program IDs;
// UI overlays use 1100..1111 and leave SF2 values unchanged at zero.
class PresetBrowserView final : public VSTGUI::CViewContainer,
                                public VSTGUI::DataBrowserDelegateAdapter,
                                public VSTGUI::IControlListener {
public:
    PresetBrowserView(const VSTGUI::CRect& rect,
                      Steinberg::Vst::EditController* controller,
                      const PresetCatalog& sf, const PresetCatalog& legacyFm,
                      const std::string& exactLogoPath,
                      std::function<std::string()> sf2StatusProvider,
                      std::function<std::string()> hardwareInfoProvider,
                      std::function<bool(const std::string&)> romLoadRequest,
                      std::function<bool(const std::string&)> sf2LoadRequest,
                      std::function<std::string()> sf2CurrentPath,
                      std::function<uint64_t()> sf2CatalogRevision);
    void onIdle() override;
    void valueChanged(VSTGUI::CControl*) override;
    int32_t dbGetNumRows(VSTGUI::CDataBrowser*) override;
    int32_t dbGetNumColumns(VSTGUI::CDataBrowser*) override;
    VSTGUI::CCoord dbGetRowHeight(VSTGUI::CDataBrowser*) override;
    VSTGUI::CCoord dbGetCurrentColumnWidth(int32_t,VSTGUI::CDataBrowser*) override;
    void dbDrawCell(VSTGUI::CDrawContext*,const VSTGUI::CRect&,
                    int32_t,int32_t,int32_t,VSTGUI::CDataBrowser*) override;
    VSTGUI::CMouseEventResult dbOnMouseDown(const VSTGUI::CPoint&,
                    const VSTGUI::CButtonState&,int32_t,int32_t,VSTGUI::CDataBrowser*) override;
    void dbSelectionChanged(VSTGUI::CDataBrowser*) override;
protected:
    ~PresetBrowserView() noexcept override = default;
private:
    static constexpr int kPrevious=3101,kNext=3102,kToggle=3103,
                         kFilter=3104,kBankFilter=3105,kLoadSf2=3106,kReset=3107,
                         kLoadRom=3108,kActiveBank=3109,kDirectPreset=3110;
    static constexpr int kGuiFirst=1100,kGuiCount=12;
    static constexpr int kMasterVolume=static_cast<int>(MasterOutput::kParamID);
    Steinberg::Vst::EditController* controller_;
    const PresetCatalog& sf_;
    const PresetCatalog& fm_; // legacy catalog only; never user-selectable
    std::function<std::string()> sf2StatusProvider_;
    std::function<std::string()> hardwareInfoProvider_;
    std::function<bool(const std::string&)> romLoadRequest_;
    std::function<bool(const std::string&)> sf2LoadRequest_;
    std::function<std::string()> sf2CurrentPath_;
    std::function<uint64_t()> sf2CatalogRevision_;
    uint64_t lastCatalogRevision_=0;
    std::string lastStatus_,lastPath_,lastHardwareInfo_;
    uint16_t bank_=0;
    uint8_t program_=0;
    int bankFilter_=-1;
    bool expanded_=true,syncing_=false,selectingRowFromMouse_=false;
    std::string searchText_;
    std::vector<uint16_t> filterBanks_;
    std::vector<uint16_t> activeBanks_;
    std::vector<uint8_t> activePrograms_;
    std::vector<PresetBrowserModel::Row> rows_;
    VSTGUI::CControl* masterVolume_=nullptr;
    VSTGUI::CTextLabel* masterVolumeValue_=nullptr;
    std::array<VSTGUI::CControl*,kGuiCount> controls_{};
    std::array<VSTGUI::CTextLabel*,kGuiCount> values_{};
    VSTGUI::COptionMenu* bankMenu_=nullptr;
    VSTGUI::COptionMenu* activeBankMenu_=nullptr;
    VSTGUI::COptionMenu* programMenu_=nullptr;
    VSTGUI::CTextEdit* search_=nullptr;
    VSTGUI::CTextButton *previous_=nullptr,*next_=nullptr,*toggle_=nullptr,
                         *loadSf2_=nullptr,*loadRom_=nullptr,*reset_=nullptr;
    VSTGUI::CTextLabel *programLabel_=nullptr,*fileLabel_=nullptr,
                       *hardwareInfoLabel_=nullptr,
                       *empty_=nullptr,*bankCaption_=nullptr,
                       *searchCaption_=nullptr,*hint_=nullptr;
    VSTGUI::CDataBrowser* table_=nullptr;
    VSTGUI::CTextLabel* MakeLabel(const VSTGUI::CRect&,const char*,
                                 bool secondary=false);
    VSTGUI::CTextButton* MakeButton(const VSTGUI::CRect&,int,const char*);
    void AddKnob(int index,int x,int y,const char* title);
    void RebuildBanks();
    void RebuildActiveMenus();
    void SyncActiveMenuSelection();
    void RebuildRows();
    void SyncBrowserSelection();
    void Sync(bool force=false);
    void SyncSf2Status();
    void SyncHardwareInfo();
    void SetExpanded(bool);
    void Select(uint16_t bank,uint8_t program);
    void ChangeParameter(Steinberg::Vst::ParamID,double normalized);
    void ChooseSf2();
    void ChooseRom();
};
} // namespace AWE125
