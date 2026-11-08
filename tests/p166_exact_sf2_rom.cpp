// P166: public synthetic, independently specified SF2 + ROM preset oracle.
// No Creative ROM, private SF2 or copyrighted samples are stored or loaded.
// Audio runs through the actual EMU8000 86Box core, not a preset-map mock.
#include "Synth.h"
#include "RomGmBank.h"
#include "PresetCatalog.h"
#include "PresetBrowserModel.h"
#include "AssetState.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <utility>
#include <vector>

namespace {
namespace fs=std::filesystem;
using Bytes=std::vector<uint8_t>;
using AWE125::PresetCatalog;
using AWE125::PresetBrowserModel;
void U16(Bytes& b,unsigned v){b.push_back(v&255u);b.push_back((v>>8)&255u);}
void U32(Bytes& b,uint32_t v){U16(b,v);U16(b,v>>16);}
void Four(Bytes& b,const char* n){b.insert(b.end(),n,n+4);}
void Name(Bytes& b,const std::string& v){
    for(size_t i=0;i<20;++i)b.push_back(i<v.size()?uint8_t(v[i]):0);
}
void Chunk(Bytes& b,const char* id,const Bytes& v){
    Four(b,id);U32(b,static_cast<uint32_t>(v.size()));
    b.insert(b.end(),v.begin(),v.end());if(v.size()&1u)b.push_back(0);
}
void List(Bytes& b,const char* id,const Bytes& v){
    Bytes payload;Four(payload,id);payload.insert(payload.end(),v.begin(),v.end());
    Chunk(b,"LIST",payload);
}
bool Save(const fs::path& path,const Bytes& data){
    std::ofstream f(path,std::ios::binary|std::ios::trunc);
    f.write(reinterpret_cast<const char*>(data.data()),std::streamsize(data.size()));
    return f.good();
}
struct Spec {uint16_t bank;uint8_t program;uint16_t instrument;};
Bytes MakeSoundFont(const std::vector<Spec>& specs,bool sf1=false){
    Bytes info,version,romName,inam;
    U16(version,sf1?1:2);U16(version,sf1?0:1);
    Chunk(info,"ifil",version);
    inam={'1','2','5','A',' ','P','1','6','6',0};
    Chunk(info,"INAM",inam);
    if(sf1){romName={'1','M','G','M',0};Chunk(info,"irom",romName);}
    Bytes sdta,smpl,snam;
    constexpr unsigned N=2048;
    if(!sf1){
        for(int sample=0;sample<2;++sample)
            for(unsigned n=0;n<N;++n) {
                const double pi=3.14159265358979323846;
                const double freq=(sample==0?64.:37.);
                const int16_t v=int16_t(std::lround(
                    std::sin(2.*pi*double(n%unsigned(freq))/freq)*12500.));
                U16(smpl,uint16_t(v));
            }
        for(int k=0;k<46;++k)U16(smpl,0);
        Chunk(sdta,"smpl",smpl);
    } else {
        Name(snam,"*P166 sine A");Name(snam,"*P166 sine B");
        Chunk(sdta,"snam",snam);
    }
    Bytes phdr,pbag,pgen,inst,ibag,igen,shdr,pdta;
    for(size_t i=0;i<specs.size();++i){
        const auto& spec=specs[i];
        Name(phdr,"P166 "+std::to_string(spec.bank)+":"+std::to_string(spec.program));
        U16(phdr,spec.program);U16(phdr,spec.bank);U16(phdr,unsigned(i));
        U32(phdr,0);U32(phdr,0);U32(phdr,0);
        U16(pbag,unsigned(i));U16(pbag,0);
        U16(pgen,41);U16(pgen,spec.instrument);
    }
    Name(phdr,"EOP");U16(phdr,0);U16(phdr,0);
    U16(phdr,unsigned(specs.size()));U32(phdr,0);U32(phdr,0);U32(phdr,0);
    U16(pbag,unsigned(specs.size()));U16(pbag,0);
    for(int i=0;i<2;++i) {
        Name(inst,"P166 Synth Sample "+std::to_string(i));
        U16(inst,unsigned(i));
        U16(ibag,unsigned(i));U16(ibag,0);
        U16(igen,53);U16(igen,unsigned(i));
    }
    Name(inst,"EOI");U16(inst,2);U16(ibag,2);U16(ibag,0);
    for(int i=0;i<2;++i) {
        const unsigned start=unsigned(i)*N;
        if(sf1) {
            U32(shdr,start);U32(shdr,start+N);
            U32(shdr,start+16);U32(shdr,start+N-16);
        } else {
            Name(shdr,"P166 Sine "+std::to_string(i));
            U32(shdr,start);U32(shdr,start+N);
            U32(shdr,start+16);U32(shdr,start+N-16);
            U32(shdr,44100);shdr.push_back(69);shdr.push_back(0);
            U16(shdr,0);U16(shdr,1);
        }
    }
    if(!sf1) {
        Name(shdr,"EOS");for(int i=0;i<5;++i)U32(shdr,0);
        shdr.push_back(0);shdr.push_back(0);U16(shdr,0);U16(shdr,1);
    }
    Chunk(pdta,"phdr",phdr);Chunk(pdta,"pbag",pbag);
    Chunk(pdta,"pmod",Bytes(10,0));Chunk(pdta,"pgen",pgen);
    Chunk(pdta,"inst",inst);Chunk(pdta,"ibag",ibag);
    Chunk(pdta,"imod",Bytes(10,0));Chunk(pdta,"igen",igen);
    Chunk(pdta,"shdr",shdr);
    Bytes body;Four(body,"sfbk");
    List(body,"INFO",info);List(body,"sdta",sdta);List(body,"pdta",pdta);
    Bytes out;Chunk(out,"RIFF",body);return out;
}
bool MakeSyntheticRom(const fs::path& path) {
    std::vector<int16_t> rom(1048576u/2u,0);
    const double pi=3.14159265358979323846;
    for(int wave=0;wave<2;++wave)
        for(unsigned n=0;n<2048;++n) {
            const int period=wave?37:64;
            rom[495+unsigned(wave)*2048+n]=int16_t(std::lround(
                std::sin(2.*pi*(n%unsigned(period))/period)*14000.));
        }
    std::ofstream f(path,std::ios::binary|std::ios::trunc);
    f.write(reinterpret_cast<const char*>(rom.data()),
            std::streamsize(rom.size()*sizeof(int16_t)));
    return f.good();
}
bool Check(bool cond,const std::string& label) {
    std::cout<<(cond?"PASS ":"FAIL ")<<label<<"\n";return cond;
}
size_t Held(const Synth& synth){
    const auto notes=synth.CaptureHeldNotes();
    return std::count_if(notes.begin(),notes.end(),[](auto n){return n.sequence!=0;});
}
struct Heard {
    bool ready=false;
    bool note=false;
    bool audio=false;
    uint64_t energy=0;
    size_t banks=0;
};
Heard Play(const fs::path& rom,const fs::path& sf2,
           uint16_t bank,uint8_t program,
           int channel=0,int midiBank=-1,bool legacy=false) {
    Synth synth(44100);
    synth.Core().SetDriver(Awe32::Driver::Win95);
    std::string error;
    if(!synth.Core().UseBox86Chip(rom.string(),error)) {
        std::cerr<<"ROM init: "<<error<<"\n";return {};
    }
    synth.Core().PowerOnInit();
    const auto loaded=AWE125::RomGmBank::LoadBanks(synth,rom.string(),sf2.string());
    if(!loaded.sf2||!loaded.gm) {
        std::cerr<<"Banks: SF2="<<loaded.sf2<<" GM="<<loaded.gm
                 <<" "<<loaded.sf2Error<<" "<<loaded.gmError<<"\n";
        return {};
    }
    if(legacy)synth.SetStrictPresetSelection(false); // oracle sensitivity
    synth.SelectBrowserBank(bank);
    if(midiBank>=0)synth.ControlChange(uint8_t(channel),0,uint8_t(midiBank));
    synth.ProgramChange(uint8_t(channel),program);
    synth.NoteOn(uint8_t(channel),69,115,123);
    Heard h;h.ready=true;h.banks=synth.BankCount();h.note=Held(synth)!=0;
    std::vector<int16_t> pcm(32768,0);
    synth.RenderBlock(pcm.data(),16384);
    for(const auto v:pcm)h.energy+=uint64_t(std::abs(int(v)));
    h.audio=h.energy>1000;
    return h;
}
std::vector<Spec> Synth512Shape(){
    std::vector<Spec> p;
    // Deliberately reversed phdr order: original MIDI program IDs 0..77
    // except 63, with precisely 77 actual SF2 patches.
    for(int i=77;i>=0;--i)if(i!=63)p.push_back({0,uint8_t(i),0});
    return p;
}
std::vector<Spec> SparseShape(){
    return {{128,0,1},{5,70,1},{0,77,0},{5,2,1},{0,7,0},{0,0,0}};
}
std::vector<Spec> RomShape(){
    std::vector<Spec> p;
    for(int i=0;i<128;++i)p.push_back({0,uint8_t(i),uint16_t(i&1)});
    p.push_back({128,0,1});
    return p;
}
}

int main(){
    namespace fs=std::filesystem;
    const auto root=fs::temp_directory_path()/"125A_P166_exact_preset_rom_isolation";
    std::error_code ec;fs::remove_all(root,ec);
    if(!fs::create_directories(root))return 2;
    struct Clean {fs::path p;~Clean(){std::error_code e;fs::remove_all(p,e);}} guard{root};
    const auto sf=root/"synth512shape.sf2",sparse=root/"sparse.sf2";
    const auto reserved=root/"reserved.sf2",rom=root/"P166-Wave-ROM.raw";
    const auto gm=root/"SYNTHGM.SBK"; // must be adjacent to ROM by contract
    if(!Save(sf,MakeSoundFont(Synth512Shape()))||
       !Save(sparse,MakeSoundFont(SparseShape()))||
       !Save(reserved,MakeSoundFont({{16383,20,0}}))||
       !Save(gm,MakeSoundFont(RomShape(),true))||
       !MakeSyntheticRom(rom))return 2;
    bool ok=true;
    std::string err;
    PresetCatalog c;
    ok&=Check(c.LoadSoundFont(sf.string(),err),"77-shape SF2 metadata parsed: "+err);
    ok&=Check(c.Entries().size()==77&&c.Find(0,0)&&c.Find(0,62)&&
       !c.Find(0,63)&&c.Find(0,64)&&c.Find(0,77)&&!c.Find(0,78),
       "77 exact presets, absent 63 and 78+, original program IDs retained");
    ok&=Check(AWE125::RomGmBank::ValidDescriptor(gm.string(),err),
       "independently generated SF1 129-preset ROM descriptor valid: "+err);
    ok&=Check(c.AppendRomGm(gm.string(),err),"ROM catalog append: "+err);
    ok&=Check(c.Entries().size()==206 &&
       PresetBrowserModel::Filter(0,c,c,0,"").size()==77 &&
       PresetBrowserModel::Programs(c.Entries(),0).size()==77 &&
       PresetBrowserModel::Filter(0,c,c,16383,"").size()==128 &&
       PresetBrowserModel::Filter(0,c,c,16382,"").size()==1 &&
       !c.Find(0,63)&&c.Find(16383,63)&&
       PresetBrowserModel::Banks(0,c,c)==
         std::vector<uint16_t>({0,16382,16383}),
       "browser contains exactly 77 SF2 + two separate explicit ROM banks");
    ok&=Check(PresetBrowserModel::Neighbor(0,c,c,0,62,1)==64 &&
       PresetBrowserModel::Neighbor(0,c,c,0,64,-1)==62 &&
       PresetBrowserModel::Neighbor(0,c,c,0,77,1)==0 &&
       PresetBrowserModel::Neighbor(0,c,c,0,0,-1)==77 &&
       PresetBrowserModel::ChooseExistingProgram(c.Entries(),0,63)==0,
       "PREV NEXT wrap, skip hole, direct selection preserves real IDs");
    ok&=Check(PresetBrowserModel::CurrentLabel(0,c,c,0,63)
        .find("Nicht in der Bank vorhanden")!=std::string::npos,
       "missing SF2 program renders explicit unavailable label, not ROM name");

    PresetCatalog s;
    ok&=Check(s.LoadSoundFont(sparse.string(),err)&&s.Entries().size()==6 &&
       s.Find(5,2)&&s.Find(5,70)&&!s.Find(5,0)&&
       PresetBrowserModel::Neighbor(0,s,s,5,2,1)==70,
       "sparse unsorted multi-bank SF2 keeps physical bank/program numbers");
    PresetCatalog collision;
    ok&=Check(collision.LoadSoundFont(reserved.string(),err)&&
       !collision.AppendRomGm(gm.string(),err)&&
       collision.Entries().size()==1&&collision.Find(16383,20),
       "reserved ROM-bank collision fails atomically, never renumbers SF2");

    // Validate genuine 86Box NoteOn and rendered PCM. Baseline control:
    // disabling strict selection must make the missing-preset oracle FAIL.
    const auto available=Play(rom,sf,0,64);
    const auto hole=Play(rom,sf,0,63);
    const auto missing128=Play(rom,sf,0,100);
    const auto rom63=Play(rom,sf,16383,63);
    const auto romDrum=Play(rom,sf,16382,0,9);
    const auto wrongDrum=Play(rom,sf,16382,63,9);
    const auto legacyHole=Play(rom,sf,0,63,0,-1,true);
    const auto sparse70=Play(rom,sparse,5,70);
    const auto sparseMissing=Play(rom,sparse,5,3);
    const auto midiBank0=Play(rom,sparse,5,0,0,0);
    const auto midiBank5=Play(rom,sparse,0,70,0,5);
    ok&=Check(available.ready&&available.note&&available.audio,
       "SF2 program 64 drives an actual audible 86Box voice");
    ok&=Check(hole.ready&&!hole.note&&!hole.audio &&
       missing128.ready&&!missing128.note&&!missing128.audio,
       "missing 63/100 produce NO voice and digital silence (not GM, not sine)");
    ok&=Check(rom63.ready&&rom63.note&&rom63.audio &&
       romDrum.ready&&romDrum.note&&romDrum.audio &&
       wrongDrum.ready&&!wrongDrum.note&&!wrongDrum.audio,
       "explicit ROM GM program 63 and ROM drumkit are audible; missing ROM drum silent");
    ok&=Check(legacyHole.ready&&legacyHole.note,
       "negative-control: disabling strict mode reintroduces wrong fallback voice");
    ok&=Check(sparse70.ready&&sparse70.note&&sparse70.audio &&
       sparseMissing.ready&&!sparseMissing.note&&!sparseMissing.audio,
       "other sparse bank supports only existing programs, no bank-0 GM substitution");
    ok&=Check(midiBank0.ready&&midiBank0.note&&midiBank0.audio &&
       midiBank5.ready&&midiBank5.note&&midiBank5.audio,
       "MIDI CC0 overrides global browser bank with exact target selection");
    ok&=Check(available.banks==2&&rom63.banks==2,
       "engine loads only real SF2 and virtual GM ROM bank, NO physical GM bank 0");
    // Project state preserves sparse bank/program identifiers. The actual
    // production VST3 processor concurrency/host tests run separately.
    AWE125::AssetState::Data state;
    state.bank=5;state.program=70;
    state.channelProgramMask=2;state.channelPrograms[1]=2;
    state.pathsSpecified=true;state.romPath=rom.string();state.sf2Path=sparse.string();
    std::vector<uint8_t> bytes;
    const auto put=[&](const void* p,size_t n){
        const auto* q=static_cast<const uint8_t*>(p);
        bytes.insert(bytes.end(),q,q+n);return true;
    };
    bool saved=AWE125::AssetState::Write(put,state);
    AWE125::AssetState::Data restored;size_t cursor=0;
    const auto read=[&](void* p,size_t n){
        if(n>bytes.size()-cursor)return false;
        std::memcpy(p,bytes.data()+cursor,n);cursor+=n;return true;
    };
    const bool loaded=saved&&AWE125::AssetState::Read(read,restored);
    ok&=Check(loaded&&restored.bank==5&&restored.program==70&&
        restored.channelProgramMask==2&&restored.channelPrograms[1]==2 &&
        restored.romPath==rom.string()&&restored.sf2Path==sparse.string(),
        "V11 save/reload retains sparse bank/program and channel automation state");
    std::cout<<(ok?"P166_EXACT_PRESETS_FULL_PASS":"P166_EXACT_PRESETS_FAIL")<<"\n";
    return ok?0:1;
}
