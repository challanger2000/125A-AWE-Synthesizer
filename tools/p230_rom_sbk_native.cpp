// P230: genuine user-provided Wave ROM + SYNTHGM.SBK, native PCM only.
// No private ROM/SBK or generated original audio is included in this source.
#include "Synth.h"
#include "RomGmBank.h"
#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace fs=std::filesystem;
namespace {
constexpr uint32_t kRate=44100,kFrames=kRate*2;
struct Case {unsigned bank,program,note,velocity,channel;};
void require(bool okay,const std::string& msg){
    if(!okay)throw std::runtime_error("P230: "+msg);
}
void u16(std::ostream& o,uint16_t n){o.put(char(n&255));o.put(char(n>>8));}
void u32(std::ostream& o,uint32_t n){u16(o,uint16_t(n));u16(o,uint16_t(n>>16));}
std::vector<Case> plan(){
    std::vector<Case> result;
    for(unsigned p=0;p<128;++p)
      for(unsigned note:{48u,60u,72u})result.push_back({16383,p,note,100,0});
    for(unsigned note:{35u,36u,38u,42u,46u,49u,51u,56u,60u,64u,69u,76u,81u})
      result.push_back({16382,0,note,100,9});
    return result;
}
std::string name(const Case& c){
    const auto pad=[](unsigned n,unsigned w){
        auto s=std::to_string(n);return std::string(w>s.size()?w-s.size():0,'0')+s;
    };
    return std::string(c.bank==16383?"gm":"drum")+"_b"+pad(c.bank,5)+
           "_p"+pad(c.program,3)+"_n"+pad(c.note,3)+"_v"+pad(c.velocity,3)+".wav";
}
void write_wav(const fs::path& path,const std::vector<int16_t>& pcm){
    require(pcm.size()==kFrames*2ull,"wrong PCM frame count");
    const uint32_t bytes=uint32_t(pcm.size()*2u);
    std::ofstream out(path,std::ios::binary|std::ios::trunc);
    require(bool(out),"cannot create output WAV");
    out.write("RIFF",4);u32(out,36+bytes);out.write("WAVEfmt ",8);
    u32(out,16);u16(out,1);u16(out,2);u32(out,kRate);
    u32(out,kRate*4);u16(out,4);u16(out,16);
    out.write("data",4);u32(out,bytes);
    for(auto sample:pcm)u16(out,uint16_t(sample));
    require(bool(out),"PCM write failed");
}
struct Result {size_t active=0,nonzero=0,rails=0;};
Result render(const fs::path& rom,const Case& c,std::vector<int16_t>& pcm){
    Synth s(kRate);s.Core().SetDriver(Awe32::Driver::Win95);
    std::string err;
    require(s.Core().UseBox86Chip(rom.string(),err),"ROM chip init: "+err);
    s.Core().PowerOnInit();
    const auto load=AWE125::RomGmBank::LoadBanks(s,rom.string(),"");
    require(load.gm&&!load.sf2&&s.BankCount()==1&&s.StrictPresetSelection(),
            "genuine ROM/SBK not loaded as sole strict bank: "+load.gmError);
    s.SelectBrowserBank(uint16_t(c.bank));
    s.ProgramChange(uint8_t(c.channel),uint8_t(c.program));
    s.ControlChange(uint8_t(c.channel),7,100);
    s.ControlChange(uint8_t(c.channel),11,127);
    s.ControlChange(uint8_t(c.channel),10,64);
    s.ControlChange(uint8_t(c.channel),91,0);
    s.ControlChange(uint8_t(c.channel),93,0);
    s.SetGuiControl(10,0.f);s.SetGuiControl(11,0.f);
    s.NoteOn(uint8_t(c.channel),uint8_t(c.note),uint8_t(c.velocity),1);
    Result result;
    for(auto note:s.CaptureHeldNotes())if(note.sequence)++result.active;
    std::array<int16_t,1024*2> block{};
    for(uint32_t at=0;at<kFrames;){
        if(at==kRate)s.NoteOff(uint8_t(c.channel),uint8_t(c.note));
        uint32_t count=std::min<uint32_t>(1024,kFrames-at);
        if(at<kRate)count=std::min(count,kRate-at);
        s.RenderBlock(block.data(),count);
        for(uint32_t j=0;j<count*2;++j){
            auto v=block[j];
            pcm[2ull*at+j]=v;
            result.nonzero+=v!=0;
            result.rails+=v==-32768||v==32767;
        }
        at+=count;
    }
    return result;
}
}
int main(int argc,char** argv){
 try{
    if(argc==2&&std::string(argv[1])=="--list"){
        for(auto c:plan())
          std::cout<<name(c)<<','<<c.bank<<','<<c.program<<','<<c.note
                   <<','<<c.velocity<<','<<c.channel<<'\n';
        return 0;
    }
    require(argc==3,"usage: p230_rom_sbk_native awe32.raw PRIVATE_OUTPUT_DIR"
                    " (SYNTHGM.SBK adjacent to ROM); or --list");
    const fs::path rom=argv[1],dir=argv[2];
    require(fs::is_regular_file(rom)&&fs::file_size(rom)==1048576,
            "original 1MiB Wave ROM required");
    const auto sbk=AWE125::RomGmBank::AdjacentFile(rom.string());
    std::string err;
    require(!sbk.empty()&&AWE125::RomGmBank::ValidDescriptor(sbk,err),
            "valid 1MGM SYNTHGM.SBK next to ROM required: "+err);
    require(!fs::exists(dir),"refuse overwrite existing output");
    require(fs::create_directories(dir),"cannot create output");
    std::ofstream manifest(dir/"cases.csv");
    require(bool(manifest),"cannot create manifest");
    manifest<<"file,bank,program,note,velocity,channel,voices,nonzero,rails\n";
    std::array<bool,128> gmAudible{};
    bool drumAudible=false;
    size_t silent=0,missing=0,clipped=0;
    for(auto c:plan()){
        std::vector<int16_t> pcm(kFrames*2ull,0);
        auto r=render(rom,c,pcm);
        const auto filename=name(c);
        write_wav(dir/filename,pcm);
        manifest<<filename<<','<<c.bank<<','<<c.program<<','<<c.note
                <<','<<c.velocity<<','<<c.channel<<','<<r.active<<','
                <<r.nonzero<<','<<r.rails<<'\n';
        silent+=r.nonzero==0;missing+=r.active==0;clipped+=r.rails!=0;
        if(r.nonzero&&c.bank==16383)gmAudible[c.program]=true;
        if(r.nonzero&&c.bank==16382)drumAudible=true;
    }
    require(bool(manifest),"manifest write failed");
    const auto missingGm=std::count(gmAudible.begin(),gmAudible.end(),false);
    std::cout<<"P230_REAL_ROM_SBK_NATIVE cases="<<plan().size()
             <<" silent_cases="<<silent<<" no_voice_cases="<<missing
             <<" clipped_cases="<<clipped<<" silent_gm_programs="<<missingGm
             <<" any_drums_audible="<<drumAudible
             <<" ORIGINAL_CREATIVE_PCM=NOT_RUN PHYSICAL_CARD=NOT_RUN"
             <<" RELEASE=BLOCKED\n";
    return missingGm||!drumAudible?3:0;
 }catch(const std::exception& e){std::cerr<<e.what()<<'\n';return 2;}
}
