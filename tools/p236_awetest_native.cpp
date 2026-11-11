// P236: exact AWETEST v25 "direct-EMU8000" Q/cutoff hardware stimulus.
// Test-only current 125A chip, real wave-ROM. DSP, interpolator, filter source
// and SoundFont translations remain completely unchanged.
// Register values follow turican0/AWE32Emu tools/awetest/AWETEST.C
// ToneDefaults/ToneSetup/ToneTrigger/VoiceOff; source-pinned physical audio
// and cap-frame log are evaluated by tools/p236_awetest_compare.py.
#include "Emu8000.h"
#include <array>
#include <cstdint>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <algorithm>
namespace fs=std::filesystem;
using Emu8000::Reg;
static void require(bool b,const std::string& s){if(!b)throw std::runtime_error(s);}
static void u16(std::ofstream& f,uint16_t x){f.put(char(x&255));f.put(char(x>>8));}
static void u32(std::ofstream& f,uint32_t x){u16(f,uint16_t(x));u16(f,uint16_t(x>>16));}
static void wavhead(std::ofstream& f,uint32_t frames) {
    uint32_t bytes=frames*4;
    f.write("RIFF",4);u32(f,36+bytes);f.write("WAVEfmt ",8);
    u32(f,16);u16(f,1);u16(f,2);u32(f,44100);u32(f,176400);
    u16(f,4);u16(f,16);f.write("data",4);u32(f,bytes);
}
static void writeTone(Emu8000Core& core,int cutoff,int Q) {
    // AWETEST.C: physical voice V_TEST, reconstructed exact default register
    // stimulus from code; *not* a newly recorded per-write hardware trace.
    constexpr int v=29; // AWETEST.C defines V_TEST=29; V_MARK=28
    const uint32_t sampleStart=458995, loopStart=459001, loopEnd=467282;
    core.Write(Reg::DCYSUSV,v,0x0080);
    core.Write(Reg::VTFT,v,0x0000FFFF);
    core.Write(Reg::CVCF,v,0x0000FFFF);
    core.Write(Reg::PSST,v,(128u<<24)|loopStart);
    core.Write(Reg::CSL,v,loopEnd);                     // chorus send 0
    core.Write(Reg::CCCA,v,(uint32_t(Q)<<28)|sampleStart);
    core.Write(Reg::IP,v,0xE000);
    core.Write(Reg::IFATN,v,(uint32_t(cutoff)<<8));      // dry, attenuation=0
    core.Write(Reg::PEFE,v,0);
    core.Write(Reg::FMMOD,v,0);
    core.Write(Reg::TREMFRQ,v,0);
    core.Write(Reg::FM2FRQ2,v,0);
    core.Write(Reg::ENVVAL,v,0x8000);
    core.Write(Reg::ATKHLD,v,0x7F7F);
    core.Write(Reg::DCYSUS,v,0x7F00);
    core.Write(Reg::ENVVOL,v,0x8000);
    core.Write(Reg::ATKHLDV,v,0x7F7F);
    core.Write(Reg::LFO1VAL,v,0x8000);
    core.Write(Reg::LFO2VAL,v,0x8000);
    core.Write(Reg::PTRX,v,0x40000000);                  // reverb send 0
    // Physical hardware itself triggered the note by its final DCYSUSV.
    core.Write(Reg::DCYSUSV,v,0x7F00);
}
static void capture(Emu8000Core& core,const fs::path& out,int cutoff,int Q) {
    // 500ms note + 600ms silence as v25 block6. No gain normalization.
    std::ofstream f(out,std::ios::binary|std::ios::trunc);
    require(bool(f),"cannot open private PCM WAV");
    constexpr uint32_t n=44100u*11/10;
    wavhead(f,n);
    std::vector<int16_t> buffer(1024*2);
    writeTone(core,cutoff,Q);
    uint32_t frames=0;unsigned long long rail=0,nonzero=0;
    auto render=[&](uint32_t end){
        while(frames<end){
            const uint32_t block=std::min<uint32_t>(1024,end-frames);
            core.RenderBlock(buffer.data(),block);
            f.write(reinterpret_cast<const char*>(buffer.data()),block*4);
            for(uint32_t i=0;i<block*2;i++){
                int32_t x=buffer[i];nonzero+=x!=0;rail+=x==32767||x==-32768;
            }
            frames+=block;
        }
    };
    render(22050);
    core.Write(Reg::DCYSUSV,29,0x0080);
    core.Write(Reg::VTFT,29,0x0000FFFF);
    render(n);
    require(bool(f)&&nonzero>50,"AWETEST current core silence or failed output");
    std::cout<<"P236_AWETEST_NATIVE_PCM "<<cutoff<<" Q "<<Q<<" samples "<<n
             <<" rail "<<rail<<" nonzero "<<nonzero<<"\n";
}
int main(int argc,char** argv){
    if(argc!=3 && argc!=4){std::cerr<<"Usage: awe32_p236_awetest_native awe32.raw PRIVATE_OUTDIR [--hardware-eq]\n";return 2;}
    const bool exactCardEq=(argc==4 && std::string(argv[3])=="--hardware-eq");
    if(argc==4 && !exactCardEq){std::cerr<<"Unknown AWETEST fixture flag\n";return 2;}
    try{
        const fs::path root=argv[2];fs::create_directories(root);
        Emu8000Core core(44100);
        core.SetDriver(Awe32::Driver::Dos);
        std::string e;
        require(core.UseBox86Chip(argv[1],e),"not real ROM/125A chip: "+e);
        core.PowerOnInit();
        core.MuteEffectReturns(true,true);
        // Compare genuine card EQ INIT readback (v25 awetest.log) with the
        // register-programmed native state. DOS init can use nibble-swapped
        // coefficients which 86Box correctly decodes as equivalent.
        constexpr std::array<std::pair<Reg,int>,10> eq_ids = {{
            {Reg::INIT4,0x01},{Reg::INIT4,0x11},
            {Reg::INIT3,0x11},{Reg::INIT3,0x13},{Reg::INIT3,0x1B},
            {Reg::INIT4,0x07},{Reg::INIT4,0x0B},{Reg::INIT4,0x0D},
            {Reg::INIT4,0x17},{Reg::INIT4,0x19}
        }};
        constexpr std::array<uint16_t,10> physical_eq = {{
            0xC208,0xC308,0x821E,0xD208,0x031E,
            0xD308,0x0219,0xD26E,0x8319,0xD36E
        }};
        bool equivalent = true;
        std::cout << "P236_AWETEST_EQ_HARDWARE_VS_CURRENT";
        for (size_t i=0;i<eq_ids.size();i++) {
            const uint16_t x=static_cast<uint16_t>(core.Read(eq_ids[i].first,eq_ids[i].second));
            const uint16_t swapped=static_cast<uint16_t>((x&0xFF00u) |
                ((x&0x000Fu)<<4) | ((x&0x00F0u)>>4));
            equivalent &= x==physical_eq[i] || swapped==physical_eq[i];
            std::cout << " " << std::hex << x << std::dec;
        }
        std::cout << " register_equivalent=" << (equivalent ? "YES" : "NO") << "\n";
        if (exactCardEq) {
            // This is a disposable audio-reference state, never a 125A
            // production EQ or chip algorithm change. The recorded v25 card
            // had precisely these 10 INIT slots in awetest.log.
            for (size_t i=0;i<eq_ids.size();i++)
                core.Write(eq_ids[i].first,eq_ids[i].second,physical_eq[i]);
        }
        std::cout << "P236_AWETEST_NATIVE_EQ_MODE "
                  << (exactCardEq ? "EXACT_V25_CARD_EQ_REGISTERS" : "125A_DOS_INIT_EQ")
                  << "\n";
        // v25 AWETEST: filter cutoff block 6, Q=0. Include high-cutoff
        // reference 252 to compare relative spectra without analog gain fit.
        const std::array<int,13> cuts={0,16,32,48,64,80,96,112,128,160,192,224,252};
        for(int c:cuts)capture(core,root/("cutoff_"+std::to_string(c)+".wav"),c,0);
        // Block 7: 6 cutoff levels x 16 resonance steps in AWETEST.C.
        // Two physical cutoff families are enough for this targeted audit,
        // not a claim to have audited all 96 resonance notes.
        const std::array<int,5> qs={0,4,8,12,15};
        for(int c:{96,192})for(int q:qs)capture(core,root/("resonance_"+std::to_string(c)+"_"+std::to_string(q)+".wav"),c,q);
        std::cout<<"P236_DIRECT_REAL_AWE32_V25_TONE_REGISTER_RECONSTRUCTION_COMPLETE 23 notes; no production DSP edit\n";
        return 0;
    }catch(const std::exception& ex){
        std::cerr<<"P236_AWETEST_ABORT "<<ex.what()<<"\n";return 3;
    }
}
