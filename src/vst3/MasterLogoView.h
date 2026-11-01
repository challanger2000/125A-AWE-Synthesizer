#pragma once
#include "LogoGeometry.h"
#include "vstgui/lib/cview.h"
#include <string>

namespace AWE125 {
class MasterLogoView final : public VSTGUI::CView {
public:
    MasterLogoView(const VSTGUI::CRect& rect,const std::string& path);
    void draw(VSTGUI::CDrawContext* ctx) override;
    bool HasExactMasterGeometry() const noexcept {return !logo_.Shapes().empty();}
protected:
    ~MasterLogoView() noexcept override = default;
private:
    MasterLogoGeometry logo_;
};
} // namespace AWE125
