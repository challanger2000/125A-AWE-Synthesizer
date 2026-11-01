#include "PresetCatalog.h"
#include "PresetBrowserModel.h"
#include <algorithm>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
namespace {
using Bytes=std::vector<uint8_t>;
void w16(Bytes& b,uint32_t v) {b.push_back(uint8_t(v));b.push_back(uint8_t(v>>8));}
void w32(Bytes& b,uint32_t v) {w16(b,v);w16(b,v>>16);}
void append(Bytes& b,const char* name) {b.insert(b.end(),name,name+4);}
void chunk(Bytes& b,const char* id,const Bytes& payload) {
    append(b,id);w32(b,static_cast<uint32_t>(payload.size()));
    b.insert(b.end(),payload.begin(),payload.end());
    if(payload.size()%2)b.push_back(0);
}
void record(Bytes& b,const char* n,uint16_t program,uint16_t bank) {
    for(size_t i=0;i<20;++i)b.push_back(i<std::strlen(n)?uint8_t(n[i]):0);
    w16(b,program);w16(b,bank);w16(b,0);
    w32(b,0);w32(b,0);w32(b,0);
}
Bytes makeSf(uint16_t lastBank=128,bool duplicate=false,bool hasEnd=true) {
    Bytes phdr;
    record(phdr,"Piano Factory",0,0);
    record(phdr,duplicate?"Piano 2":"Retro Lead",duplicate?0:4,duplicate?0:2);
    record(phdr,"Room Drum Kit",0,lastBank);
    if(hasEnd)record(phdr,"EOP",0,0);
    Bytes pdta;
    chunk(pdta,"phdr",phdr);
    Bytes pdtaList;append(pdtaList,"pdta");
    pdtaList.insert(pdtaList.end(),pdta.begin(),pdta.end());
    Bytes root;append(root,"sfbk");
    Bytes sound(512*1024,0); // intentionally large non-preset data
    Bytes sdta;append(sdta,"sdta");
    chunk(sdta,"smpl",sound);
    chunk(root,"LIST",sdta);
    chunk(root,"LIST",pdtaList);
    Bytes riff;append(riff,"RIFF");
    w32(riff,static_cast<uint32_t>(root.size()));
    riff.insert(riff.end(),root.begin(),root.end());
    return riff;
}
bool save(const std::filesystem::path& p,const Bytes& b) {
    std::ofstream out(p,std::ios::binary|std::ios::trunc);
    out.write(reinterpret_cast<const char*>(b.data()),
              static_cast<std::streamsize>(b.size()));
    return out.good();
}
bool check(bool yes,const char* label) {
    std::cout<<(yes?"PASS: ":"FAIL: ")<<label<<'\n';return yes;
}
}
int main(int argc,char** argv) {
    if(argc!=2)return 3;
    const auto sf=std::filesystem::temp_directory_path()/"125a_p16_preset_index_test.sf2";
    struct Remove {std::filesystem::path p;~Remove(){std::error_code ec;std::filesystem::remove(p,ec);}} cleanup{sf};
    bool ok=true;
    AWE125::PresetCatalog catalog;
    std::string error;
    ok&=check(save(sf,makeSf())&&catalog.LoadSoundFont(sf.string(),error),
              "large SF2 index loads without decoding 512KB sample chunk");
    ok&=check(catalog.Entries().size()==3&&
        catalog.Find(0,0)&&catalog.Find(0,0)->name=="Piano Factory"&&
        catalog.Find(2,4)&&catalog.Find(2,4)->name=="Retro Lead"&&
        catalog.Find(128,0)&&catalog.Find(128,0)->name=="Room Drum Kit"&&
        catalog.Find(128,0)->drums,
        "exact SF2 phdr names, MIDI bank/program and drum-bank metadata");
    // P17 model regression uses actual SF2 phdr names, not a GM lookup.
    AWE125::PresetCatalog fmCatalog;
    const auto names=AWE125::PresetBrowserModel::Filter(0,catalog,fmCatalog,-1,"rEtRo");
    ok&=check(names.size()==1&&names[0].bank==2&&names[0].program==4&&
              names[0].name=="Retro Lead",
              "browser search is case-insensitive and returns actual SF2 name");
    const auto bankOnly=AWE125::PresetBrowserModel::Filter(0,catalog,fmCatalog,128,"");
    ok&=check(bankOnly.size()==1&&bankOnly[0].drums&&
              bankOnly[0].name=="Room Drum Kit",
              "browser filters real SF2 bank 128 drum kits");
    const auto banks=AWE125::PresetBrowserModel::Banks(0,catalog,fmCatalog);
    ok&=check(banks==std::vector<uint16_t>({0,2,128})&&
              AWE125::PresetBrowserModel::Neighbor(0,catalog,fmCatalog,2,4,1)==4&&
              AWE125::PresetBrowserModel::Neighbor(0,catalog,fmCatalog,2,4,-1)==4&&
              AWE125::PresetBrowserModel::Neighbor(0,catalog,fmCatalog,3,0,1)==-1,
              "browser navigates only actual programs, missing bank gives no false preset");
    ok&=check(AWE125::PresetBrowserModel::CurrentLabel(0,catalog,fmCatalog,2,4)
                    .find("Retro Lead")!=std::string::npos&&
              std::string(AWE125::PresetBrowserModel::HardwareDescription(2))
                    .find("OPL3")!=std::string::npos,
              "browser main label and hardware explanation use correct hardware");
    const auto oldCount=catalog.Entries().size();
    ok&=check(save(sf,makeSf(16384))&&!catalog.LoadSoundFont(sf.string(),error)&&
        catalog.Entries().size()==oldCount,
        "unsupported bank 16384 rejected without damaging prior catalog");
    ok&=check(save(sf,makeSf(128,true))&&!catalog.LoadSoundFont(sf.string(),error)&&
        catalog.Entries().size()==oldCount,
        "duplicate SoundFont bank/program rejected atomically");
    ok&=check(save(sf,makeSf(128,false,false))&&!catalog.LoadSoundFont(sf.string(),error)&&
        catalog.Entries().size()==oldCount,
        "missing EOP terminator rejected atomically");
    auto partial=makeSf();
    partial.resize(partial.size()-42);
    ok&=check(save(sf,partial)&&!catalog.LoadSoundFont(sf.string(),error)&&
        catalog.Entries().size()==oldCount,
        "truncated RIFF rejected atomically");
    ok&=check(catalog.LoadFmIbk(argv[1],error)&&
        catalog.Entries().size()==128&&catalog.Find(0,0)&&
        !catalog.Find(0,0)->name.empty()&&catalog.Find(0,127)&&
        !catalog.Find(0,127)->name.empty(),
        "real historical IBK bank yields 128 named FM preset entries");
    const auto fmNames=AWE125::PresetBrowserModel::Filter(2,fmCatalog,catalog,-1,"");
    ok&=check(fmNames.size()==128&&
              AWE125::PresetBrowserModel::Neighbor(2,fmCatalog,catalog,0,0,1)==1&&
              AWE125::PresetBrowserModel::Neighbor(2,fmCatalog,catalog,0,127,1)==0&&
              AWE125::PresetBrowserModel::Neighbor(1,fmCatalog,catalog,0,0,-1)==127,
              "both FM chips browse all actual 128 historic IBK patches with wrap");
    ok&=check(!catalog.LoadFmIbk("does_not_exist.ibk",error)&&
        catalog.Entries().size()==128,
        "missing user IBK does not erase valid metadata");
    std::cout<<"NOT RUN: integrated VST3 browser UI and Studio One state/UI\n";
    return ok?0:1;
}
