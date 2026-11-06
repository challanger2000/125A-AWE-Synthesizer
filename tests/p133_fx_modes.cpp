// P133: all sixteen original Creative hardware effect modes must write the
// real EMU8000 INIT/HWCF registers, not merely change unused float FX.
// This fixture needs no proprietary wave ROM, SoundFont or sound card.
#include "Emu8000.h"
#include "Emu8000Effects.h"
#include <cstdint>
#include <iostream>

using namespace Emu8000;
int main() {
    Emu8000Core core(44100);
    core.SetDriver(Awe32::Driver::Win95);
    core.PowerOnInit();
    bool ok=true;
    unsigned comparisons=0;
    auto check=[&](bool v){ ++comparisons;ok&=v; };
    const auto hw=[&](int slot) {
        return core.ReadReg32(MakeSel(1,Port::Data1,slot));
    };
    for(unsigned rev=0;rev<8;++rev) {
        core.ApplyHardwareReverbPreset(rev);
        for(unsigned i=0;i<28;++i) {
            const auto slot=Emu8000Fx::kReverbSlots[i];
            Reg reg=Reg::INIT1;
            if(slot.init==2)reg=Reg::INIT2;
            else if(slot.init==3)reg=Reg::INIT3;
            else if(slot.init==4)reg=Reg::INIT4;
            check(core.Read(reg,slot.slot)==Emu8000Fx::kReverbParm[rev][i]);
        }
        const auto saved=core.Read(Reg::INIT1,0x03);
        core.ApplyHardwareReverbPreset(8); // must never corrupt coefficients
        check(core.Read(Reg::INIT1,0x03)==saved);
    }
    // Every chorus must program exactly five original Creative register
    // fields, including the short delay's nonzero right-tap HWCF4.
    for(unsigned cho=0;cho<8;++cho) {
        core.ApplyHardwareChorusPreset(cho);
        const auto& p=Emu8000Fx::kChorusPresets[cho];
        check(core.Read(Reg::INIT3,0x09)==p.feedback);
        check(core.Read(Reg::INIT3,0x0c)==p.delaySamples);
        check(core.Read(Reg::INIT4,0x03)==p.depth);
        check(hw(Hwcf::kHWCF4)==(cho>=6?0x0006E000u:0u));
        check(hw(Hwcf::kHWCF5)==p.lfoFreq);
        check(hw(Hwcf::kHWCF6)==0x8000u);
        check(hw(Hwcf::kHWCF7)==0u);
        const auto last=hw(Hwcf::kHWCF4);
        core.ApplyHardwareChorusPreset(8); // refuse invalid selections
        check(hw(Hwcf::kHWCF4)==last);
    }
    // A Chorus change must not stomp on Reverb coefficient registers and
    // vice versa. Test every combination, not just the initial defaults.
    for(unsigned rev=0;rev<8;++rev)for(unsigned cho=0;cho<8;++cho) {
        core.ApplyHardwareReverbPreset(rev);
        core.ApplyHardwareChorusPreset(cho);
        check(core.Read(Reg::INIT1,0x03)==Emu8000Fx::kReverbParm[rev][0]);
        check(core.Read(Reg::INIT3,0x09)==Emu8000Fx::kChorusPresets[cho].feedback);
    }
    std::cout<<"P133 actual hardware effect register tests "<<comparisons
             <<", result="<<(ok?"PASS":"FAIL")<<'\n';
    return ok?0:1;
}
