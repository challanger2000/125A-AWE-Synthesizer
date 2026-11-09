#include "FxSendLevel.h"
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>
int main() {
    unsigned checks=0;bool ok=true;
    const auto check=[&](bool good){++checks;ok &= good;};
    for(int original: {0,1,28,64,127,242,255}){
        check(AWE125::FxSendLevel::Apply(original,0.f)==0);
        check(AWE125::FxSendLevel::Apply(original,-1.f)==0);
        check(AWE125::FxSendLevel::Apply(original,1.f)==255);
        check(AWE125::FxSendLevel::Apply(original,2.f)==255);
        check(AWE125::FxSendLevel::Apply(original,std::numeric_limits<float>::quiet_NaN())==0);
        check(AWE125::FxSendLevel::Apply(original,std::numeric_limits<float>::infinity())==0);
        int previous=-1;
        for(int i=0;i<=1000;++i){
            const int level=AWE125::FxSendLevel::Apply(original,float(i)/1000.f);
            check(level>=previous && level>=0 && level<=255);
            previous=level;
        }
    }
    // Nonzero SF2 generator plus maximum channel MIDI send must NEVER
    // override a user's explicitly dry GUI setting, for either FX bus.
    check(AWE125::FxSendLevel::Apply(255,0.f)==0);
    check(AWE125::FxSendLevel::Apply(242,0.f)==0);
    std::cout<<(ok?"PASS":"FAIL")<<" P190 absolute FX send 0=dry, bounded monotone, nonfinite rejected; "<<checks<<" checks\n";
    return ok?0:1;
}
