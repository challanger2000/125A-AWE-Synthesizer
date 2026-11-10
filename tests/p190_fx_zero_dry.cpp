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
        // P223: 100% now retains the Creative-derived per-voice send.
        check(AWE125::FxSendLevel::Apply(original,1.f)==original);
        check(AWE125::FxSendLevel::Apply(original,2.f)==original);
        check(AWE125::FxSendLevel::Apply(original,std::numeric_limits<float>::quiet_NaN())==0);
        check(AWE125::FxSendLevel::Apply(original,std::numeric_limits<float>::infinity())==0);
        int previous=-1;
        for(int i=0;i<=1000;++i){
            const int level=AWE125::FxSendLevel::Apply(original,float(i)/1000.f);
            check(level>=previous && level>=0 && level<=original);
            previous=level;
        }
    }
    check(AWE125::FxSendLevel::Apply(255,0.f)==0);
    check(AWE125::FxSendLevel::Apply(242,0.f)==0);
    check(AWE125::FxSendLevel::Apply(28,0.5f)==14);
    check(AWE125::FxSendLevel::Apply(255,0.5f)==128);
    check(AWE125::FxSendLevel::Apply(0,1.f)==0);
    check(AWE125::FxSendLevel::Apply(28,1.f)!=255);
    std::cout<<(ok?"PASS":"FAIL")<<" P223 Creative FX send preserved at 100%; GUI attenuation 0=dry, bounded monotone, never boosts; "<<checks<<" checks\n";
    return ok?0:1;
}
