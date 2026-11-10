#include "FxSendLevel.h"
#include <cmath>
#include <cstdint>
#include <iostream>
#include <limits>

int main() {
    unsigned checks=0;bool ok=true;
    const auto check=[&](bool good){++checks;ok &= good;};
    for (int original: {0,1,28,64,127,242,255}) {
        // Every preset obeys the same explicit hardware register semantics.
        check(AWE125::FxSendLevel::Apply(original,0.f)==0);
        check(AWE125::FxSendLevel::Apply(original,-1.f)==0);
        check(AWE125::FxSendLevel::Apply(original,1.f)==255);
        check(AWE125::FxSendLevel::Apply(original,2.f)==255);
        check(AWE125::FxSendLevel::Apply(original,0.5f)==128);
        check(AWE125::FxSendLevel::Apply(original,std::numeric_limits<float>::quiet_NaN())==0);
        check(AWE125::FxSendLevel::Apply(original,std::numeric_limits<float>::infinity())==0);
        int previous=-1;
        for (int i=0;i<=1000;++i) {
            const int level=AWE125::FxSendLevel::Apply(original,float(i)/1000.f);
            check(level>=previous && level>=0 && level<=255);
            previous=level;
        }
    }
    // In particular, a patch with no SF2/CC send can still be made wet.
    check(AWE125::FxSendLevel::Apply(0,1.f)==255);
    check(AWE125::FxSendLevel::Apply(0,0.5f)==128);
    check(AWE125::FxSendLevel::Apply(28,1.f)==255);
    // Two different Creative driver base sends have identical output when
    // the user requests the same direct hardware register send.
    check(AWE125::FxSendLevel::Apply(28,0.5f)==
          AWE125::FxSendLevel::Apply(242,0.5f));
    std::cout<<(ok?"PASS":"FAIL")
             <<" P223 direct 8-bit hardware-send 0..255 mapping, "
             <<"zero-base wet, no preset-dependent GUI curve; "
             <<checks<<" checks\n";
    return ok?0:1;
}
