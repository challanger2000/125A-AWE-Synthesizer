#include "MasterLogoView.h"
#include "vstgui/lib/cdrawcontext.h"
#include "vstgui/lib/cgraphicspath.h"
#include <algorithm>

namespace AWE125 {
using namespace VSTGUI;
MasterLogoView::MasterLogoView(const CRect& rect,const std::string& path)
    : CView(rect) {
    setMouseEnabled(false);
    std::string error;
    logo_.Load(path,error); // failure leaves view empty, no fake replacement logo
}
void MasterLogoView::draw(CDrawContext* ctx) {
    if(!ctx||logo_.Shapes().empty())return;
    const auto r=getViewSize();
    constexpr double x0=163.,y0=103.,w=1609.-163.,h=806.-103.;
    const double s=std::min(r.getWidth()/w,r.getHeight()/h);
    if(s<=0.)return;
    const double dx=r.left+(r.getWidth()-w*s)*0.5-x0*s;
    const double dy=r.top +(r.getHeight()-h*s)*0.5-y0*s;
    for(const auto& shape:logo_.Shapes()) {
        auto* path=ctx->createGraphicsPath();
        if(!path)continue;
        for(const auto& c:shape.commands) {
            if(c.type=='M')path->beginSubpath(dx+c.x*s,dy+c.y*s);
            else if(c.type=='L')path->addLine(dx+c.x*s,dy+c.y*s);
            else if(c.type=='Z')path->closeSubpath();
        }
        ctx->setFillColor(shape.red?CColor(215,25,32):CColor(217,217,217));
        // The original master explicitly uses fill-rule=evenodd; without
        // this, letters with holes in compound silver paths become solid.
        ctx->drawGraphicsPath(path,CDrawContext::kPathFilledEvenOdd);
        path->forget();
    }
}
} // namespace AWE125
