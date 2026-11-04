#include "PresetCatalog.h"
#include "PresetBrowserModel.h"
#include <array>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

using Byte=uint8_t;
using Bytes=std::vector<Byte>;
static void U16(Bytes& b,int v) {b.push_back(Byte(v));b.push_back(Byte(v>>8));}
static void U32(Bytes& b,uint32_t v) {
    for(int i=0;i<4;++i)b.push_back(Byte(v>>(8*i)));
}
static void Ascii(Bytes& b,const char* s) {
    for(int i=0;i<4;++i)b.push_back(Byte(s[i]));
}
static void Chunk(Bytes& b,const char* id,const Bytes& data) {
    Ascii(b,id);U32(b,static_cast<uint32_t>(data.size()));
    b.insert(b.end(),data.begin(),data.end());
    if(data.size()&1)b.push_back(0);
}
static Bytes List(const char* name,const Bytes& body) {
    Bytes data;Ascii(data,name);
    data.insert(data.end(),body.begin(),body.end());
    Bytes result;Chunk(result,"LIST",data);return result;
}
static void Preset(Bytes& b,int program,int bank,const std::string& name,int bag) {
    for(size_t i=0;i<20;++i)b.push_back(i<name.size()?Byte(name[i]):Byte(0));
    U16(b,program);U16(b,bank);U16(b,bag);
    U32(b,0);U32(b,0);U32(b,0);
}
static Bytes SyntheticSf1GmMetadata() {
    // New 100% synthetic metadata-only SoundFont 1.0/SBK fixture.
    // It contains no Creative ROM data, no waveform samples and no sound engine.
    Bytes presets;
    for(int p=0;p<128;++p) {
        char name[20]{};
        std::snprintf(name,sizeof(name),"TEST GM %03d",p);
        Preset(presets,p,0,name,p);
    }
    Preset(presets,0,128,"TEST DRUMKIT",128);
    Preset(presets,0,0,"EOP",129);
    Bytes pdta;Chunk(pdta,"phdr",presets);
    Bytes version;U16(version,1);U16(version,0);
    Bytes info;Chunk(info,"ifil",version);
    Bytes body;Ascii(body,"sfbk");
    const auto infoList=List("INFO",info), pdtaList=List("pdta",pdta);
    body.insert(body.end(),infoList.begin(),infoList.end());
    body.insert(body.end(),pdtaList.begin(),pdtaList.end());
    Bytes riff;Ascii(riff,"RIFF");U32(riff,static_cast<uint32_t>(body.size()));
    riff.insert(riff.end(),body.begin(),body.end());
    return riff;
}
static bool Check(bool good,const char* label) {
    std::cout<<(good?"PASS: ":"FAIL: ")<<label<<"\n";
    return good;
}
int main() {
    bool ok=true;
    const auto path=std::filesystem::temp_directory_path()/"125A_P117_GM_catalog_fixture.sbk";
    const auto data=SyntheticSf1GmMetadata();
    {
        std::ofstream out(path,std::ios::binary|std::ios::trunc);
        if(!out.write(reinterpret_cast<const char*>(data.data()),std::streamsize(data.size())))
            return 2;
    }
    const auto cleanup=[&](){std::error_code ec;std::filesystem::remove(path,ec);};
    AWE125::PresetCatalog catalog;
    std::string error;
    ok&=Check(catalog.LoadSoundFont(path.string(),error),"SF1 RIFF phdr metadata accepted");
    ok&=Check(catalog.Entries().size()==129,
              "129 synthetic GM/drum presets indexed before overlay");
    ok&=Check(catalog.AppendRomGm(path.string(),error),
              "GM metadata copied to explicit ROM browser banks");
    ok&=Check(catalog.Entries().size()==258,
              "ROM metadata keeps regular bank and two explicit ROM banks");
    ok&=Check(catalog.Find(16383,0)!=nullptr&&catalog.Find(16383,127)!=nullptr,
              "GM original bank 16383 covers all 128 programs");
    ok&=Check(catalog.Find(16382,0)!=nullptr,
              "GM drumkit original bank 16382 is selectable");
    ok&=Check(catalog.Find(0,42)!=nullptr&&catalog.Find(128,0)!=nullptr,
              "normal GM and drum banks remain selectable");
    const auto banks=AWE125::PresetBrowserModel::Banks(0,catalog,catalog);
    ok&=Check(banks==std::vector<uint16_t>({0,128,16382,16383}),
              "direct bank selector enumerates both regular and ROM banks");
    const auto progs=AWE125::PresetBrowserModel::Programs(catalog.Entries(),16383);
    ok&=Check(progs.size()==128&&progs.front()==0&&progs.back()==127,
              "direct program dropdown exposes all 128 ROM presets");
    cleanup();
    std::cout<<(ok?"P117_SF1_GM_METADATA_PASS":"P117_SF1_GM_METADATA_FAIL")<<"\n";
    return ok?0:1;
}
