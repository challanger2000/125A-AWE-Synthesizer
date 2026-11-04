#include "MasterOutput.h"
#include <cmath>
#include <iostream>
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
    std::cout<<(pass?"P116_MASTER_VOLUME_PASS":"P116_MASTER_VOLUME_FAIL")<<"\n";
    return pass?0:1;
}
