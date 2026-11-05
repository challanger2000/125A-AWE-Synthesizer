#include "Synth.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

// P121 independent production Synth + real 86Box chip with synthetic ROM.
// No Creative ROM/SBK content is stored here. The 86Box write queue is tested
// using real register writes, actual audio, and the 980-frame chip FIFO.
namespace fs=std::filesystem;
static bool check(bool yes,const char* text) {
    std::cout<<(yes?"PASS: ":"FAIL: ")<<text<<"\n";
    return yes;
}
struct Rig {
    Synth synth{44100};
    bool Init(const fs::path& path,int notes=1) {
        auto& chip=synth.Core();
        chip.SetChipRamKb(512);
        std::string error;
        if(!chip.UseBox86Chip(path.string(),error)) {
            std::cerr<<"ROM init failed: "<<error<<"\n";
            return false;
        }
        chip.SetDriver(Awe32::Driver::Win95);
        chip.PowerOnInit();
        auto* const ram=chip.ChipRam();
        if(!ram||chip.ChipRamWords()<72||chip.DramSize()<72)return false;
        std::copy_n(chip.DramData(),72,ram);
        for(int n=0;n<notes;++n)
            synth.NoteOn(0,static_cast<uint8_t>(60+n),120);
        return true;
    }
};
static bool audible(const std::vector<int16_t>& data) {
    return std::any_of(data.begin()+std::min<size_t>(data.size(),2u*2000u),
                       data.end(),[](int16_t v){return v!=0;});
}
int main(){
    const fs::path rom=fs::temp_directory_path()/"125A_p121_synthetic_rom.raw";
    struct Cleanup {
        fs::path path;
        ~Cleanup(){std::error_code ec;fs::remove(path,ec);}
    } cleanup{rom};
    {
        std::ofstream f(rom,std::ios::binary|std::ios::trunc);
        std::vector<char> zero(1048576,0);
        f.write(zero.data(),static_cast<std::streamsize>(zero.size()));
        if(!f)return 2;
    }
    bool ok=true;
    {
        // 16 voices play on MIDI channel 1. Bend channel 16 densely.
        // Win95 free-voice state 0x0FFE aliases the high byte of channel 16.
        // In P120 this traffic flooded the 86Box queue and muted channel 1.
        Rig reference,automated;
        if(!reference.Init(rom,16)||!automated.Init(rom,16))return 2;
        ok &= check(!automated.synth.HasPlayingVoicesOnChannel(15),
                    "MIDI channel 16 has no allocated voice");
        ok &= check(automated.synth.HasPlayingVoicesOnChannel(0),
                    "16 sounding voices are allocated to MIDI channel 1");
        constexpr int frames=4096;
        std::vector<int16_t> a(frames*2),b(frames*2);
        reference.synth.ControlChange(0,10,10);  // moving Win95 pan
        automated.synth.ControlChange(0,10,10);
        for(int frame=0;frame<128;++frame) {
            automated.synth.PitchBendAutomated(15,
                static_cast<int16_t>(-8192+(frame*128)));
            reference.synth.RenderBlock(a.data()+2*frame,1);
            automated.synth.RenderBlock(b.data()+2*frame,1);
        }
        reference.synth.RenderBlock(a.data()+256,frames-128);
        automated.synth.RenderBlock(b.data()+256,frames-128);
        ok &= check(audible(a),"unmodified 16-voice reference emits PCM");
        ok &= check(a==b,
                    "128-point unused-channel-16 bend leaves 16 voices and pan PCM bit-exact");
    }
    {
        // Pressure test the actual bounded 32,768-entry PortWrite buffer.
        // Before P121 it latched overflowed and permanently silenced output.
        Rig rig;
        if(!rig.Init(rom))return 2;
        for(int n=0;n<760;++n)
            rig.synth.PitchBend(15,
                static_cast<int16_t>(((n*59)%16384)-8192));
        std::vector<int16_t> out(4096*2);
        rig.synth.RenderBlock(out.data(),4096);
        ok &= check(audible(out),
                    "over 32768 historical Win95 free-voice register writes cannot permanently mute chip");
    }
    {
        // The new gated automation must still alter a genuinely active
        // channel and preserve its exact stored pitch for following notes.
        Rig normal,bending;
        if(!normal.Init(rom)||!bending.Init(rom))return 2;
        std::vector<int16_t> a(4096*2),b(4096*2);
        for(int frame=0;frame<128;++frame) {
            bending.synth.PitchBendAutomated(0,
                static_cast<int16_t>(frame*48));
            normal.synth.RenderBlock(a.data()+2*frame,1);
            bending.synth.RenderBlock(b.data()+2*frame,1);
        }
        normal.synth.RenderBlock(a.data()+256,4096-128);
        bending.synth.RenderBlock(b.data()+256,4096-128);
        ok &= check(audible(a)&&audible(b),
                    "genuine channel-1 automated bend retains audible PCM");
        ok &= check(a!=b,
                    "genuine channel-1 automated bend changes pitched PCM");
    }
    {
        // Heavy but valid: 16 allocated voices on the same automated
        // channel with a changing bend over multiple 980-frame chip windows.
        // It exercises the actual queue drain, not only the idle-channel gate.
        Rig busy;
        if(!busy.Init(rom,16))return 2;
        constexpr int total=6144;
        std::vector<int16_t> pcm(total*2);
        for(int frame=0;frame<2048;++frame) {
            const int value=((frame*29)%16384)-8192;
            busy.synth.PitchBendAutomated(0,static_cast<int16_t>(value));
            busy.synth.RenderBlock(pcm.data()+2*frame,1);
        }
        busy.synth.RenderBlock(pcm.data()+2*2048,total-2048);
        ok &= check(audible(pcm),
            "2048 continuous pitch frames with 16 active voices never latch chip silence");
    }
    std::cout<<(ok?"P121_PITCHBEND_AUDIO_PASS":"P121_PITCHBEND_AUDIO_FAIL")<<"\n";
    return ok?0:1;
}
