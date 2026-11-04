#include "MasterOutput.h"
#include <cmath>
#include <iostream>
#include <vector>
#include <utility>
using AWE125::MasterOutput::Gain;
static bool expect(bool test,const char* name) {
    std::cout<<(test?"PASS: ":"FAIL: ")<<name<<"\n";
    return test;
}
int main() {
    bool pass=true;
    Gain g;
    pass &= expect(g.current()==1.f && g.target()==1.f &&
                   g.next()==1.f,
                   "untouched default 100% master is exactly unity");
    g.setTarget(0);
    for(int i=0;i<63;++i) {
        const auto value=g.next();
        if(!(value>=0.f && value<1.f))pass=false;
    }
    pass &= expect(g.next()==0.f && g.target()==0.f,
                   "0% reaches digital silence after deterministic 64 frames");
    g.restore(10000);
    pass &= expect(g.next()==1.f && g.current()==1.f,
                   "project restore at 100% has no fade or gain change");
    g.restore(5000);
    pass &= expect(g.current()==0.5f && g.next()==0.5f,
                   "project restore 50% applies exact half amplitude");
    g.setTarget(10000);
    for(int i=0;i<64;++i)g.next();
    pass &= expect(g.current()==1.f,
                   "gain increases smoothly to full unity");
    g.restore(10000);
    g.setTarget(6000);
    for(int i=0;i<17;++i)g.next();
    const float midway=g.current();
    g.setTarget(2500);
    pass &= expect(g.current()==midway,"retargeting never introduces a value jump");
    for(int i=0;i<64;++i)g.next();
    pass &= expect(std::abs(g.current()-0.25f)<1e-7f,
                   "latest master target wins after 64 frames");
    g.setTarget(2500);
    pass &= expect(g.next()==0.25f,
                   "redundant host update never restarts smoothing");
    g.restore(0);
    pass &= expect(g.current()==0.f && g.next()==0.f,
                   "mute state is recalled without unmuted frame");
    pass &= expect(Gain::fromStored(99999)==1.f,
                   "stored gain cannot exceed unity");
    // P119: same linear automation encoded as a single endpoint or as 64
    // dense points must produce identical PCM gain curves, not step timing.
    {
        struct Points {std::vector<std::pair<int32_t,double>> values;};
        Points sparse{{{63,0.}}};
        Points dense;
        for(int i=0;i<64;++i)
            dense.values.emplace_back(i,1.-double(i+1)/64.);
        const auto reader=+[](void* ctx,int32_t idx,int32_t& off,double& val)->bool {
            const auto& points=static_cast<Points*>(ctx)->values;
            if(idx<0||size_t(idx)>=points.size())return false;
            off=points[size_t(idx)].first;val=points[size_t(idx)].second;
            return true;
        };
        AWE125::MasterOutput::Curve a,b;
        a.reset(&sparse,reader,1,1.);
        b.reset(&dense,reader,64,1.);
        Gain ga,gb;
        bool equal=true;
        for(int i=0;i<64;++i) {
            const auto va=a.valueAt(i),vb=b.valueAt(i);
            if(std::abs(va-vb)>1e-12)equal=false;
            ga.setTarget(static_cast<uint32_t>(std::lround(va*10000.)));
            gb.setTarget(static_cast<uint32_t>(std::lround(vb*10000.)));
            if(std::abs(ga.next()-gb.next())>1e-6f)equal=false;
        }
        pass &= expect(equal,
            "P119 sparse endpoint and dense linear VST3 queues produce identical 64-frame PCM master envelope");
    }
    std::cout<<(pass?"P116_MASTER_VOLUME_PASS":"P116_MASTER_VOLUME_FAIL")<<"\n";
    return pass?0:1;
}
