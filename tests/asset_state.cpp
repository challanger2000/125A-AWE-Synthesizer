#include "AssetState.h"
#include "AssetConfig.h"
#include <cstring>
#include <iostream>
#include <sstream>
#include <vector>
using namespace AWE125;
using Bytes=std::vector<unsigned char>;
static Bytes encode(const AssetState::Data& d) {
    Bytes out;
    const auto push=[&](const void* p,size_t n){
        const auto* b=static_cast<const unsigned char*>(p);
        out.insert(out.end(),b,b+n);return true;};
    if(!AssetState::Write(push,d))return {};
    return out;
}
static bool decode(const Bytes& b,AssetState::Data& d) {
    size_t offset=0;
    auto read=[&](void* dst,size_t n) {
        if(offset>b.size()||n>b.size()-offset)return false;
        std::memcpy(dst,b.data()+offset,n);offset+=n;return true;};
    return AssetState::Read(read,d);
}
static bool ck(bool v,const char* label) {
    std::cout<<(v?"PASS: ":"FAIL: ")<<label<<'\n';return v;
}
int main() {
    bool ok=true;
    AssetState::Data d;
    d.program=104;d.engine=2;d.pathsSpecified=true;
    d.romPath="C:\\ROMs\\awe32.raw";
    d.sf2Path="D:\\Sounds\\Synth 512 Bank.sf2";
    d.ibkPath="C:\\FM\\Creative melodic.ibk";
    d.drumIbkPath="C:\\FM\\Creative drums.ibk";
    const auto blob=encode(d);
    AssetState::Data out;
    ok &= ck(!blob.empty()&&decode(blob,out)&&out.program==104&&
             out.engine==2&&out.pathsSpecified&&out.romPath==d.romPath&&
             out.sf2Path==d.sf2Path&&out.ibkPath==d.ibkPath&&
             out.drumIbkPath==d.drumIbkPath,
             "V6 CQM hardware mode, melodic and percussion banks round trip");
    // The v6 layout is unchanged from v5 except for hardware enum extension.
    Bytes v5(blob);
    v5[4]=5; // historical v5, Yamaha only
    // Engine word occurs before melodic and drum-IBK paths.
    const size_t engineIndex=v5.size()-4-d.drumIbkPath.size()-4-d.ibkPath.size()-4;
    v5[engineIndex]=1;
    ok &= ck(decode(v5,out)&&out.engine==1&&
             out.drumIbkPath==d.drumIbkPath,"legacy V5 rhythm state migrates");
    // Historical V4 ends before V5's appended drum bank path.
    Bytes v4(v5.begin(),v5.end()-4-d.drumIbkPath.size());
    v4[4]=4;
    ok &= ck(decode(v4,out)&&out.engine==1&&
             out.ibkPath==d.ibkPath&&out.drumIbkPath.empty(),
             "legacy V4 melodic bank and engine recall");
    Bytes v3(v4.begin(),v4.end()-4-d.ibkPath.size());
    // V3 carried the hardware word without IBK paths.
    v3[4]=3;
    ok &= ck(decode(v3,out)&&out.program==104&&out.engine==1&&
             out.ibkPath.empty()&&out.sf2Path==d.sf2Path,
             "legacy V3 hardware state restores without IBK path");
    // V2 excludes V3's hardware mode and V4's IBK path.
    Bytes v2(v3.begin(),v3.end()-4);
    v2[4]=2;
    ok &= ck(decode(v2,out)&&out.program==104&&out.engine==0&&
             out.pathsSpecified&&out.sf2Path==d.sf2Path,
             "legacy V2 restores as EMU8000");
    Bytes legacy(blob.begin(),blob.begin()+12);
    legacy[4]=1;
    ok &= ck(decode(legacy,out)&&out.program==104&&
             !out.pathsSpecified&&out.engine==0&&out.romPath.empty()&&out.sf2Path.empty(),
             "legacy V1 project state loads");
    bool allRejected=true;
    for(size_t n=0;n<blob.size();++n) {
        AssetState::Data target=d;target.program=3;
        Bytes partial(blob.begin(),blob.begin()+n);
        if(decode(partial,target)||target.program!=3||
           target.sf2Path!=d.sf2Path)allRejected=false;
    }
    ok &= ck(allRejected,"all truncated V6 states rejected atomically");
    auto corrupt=blob;
    corrupt[4]=90;
    out=d;out.program=7;
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "unknown format version rejected atomically");
    corrupt=blob;
    // Hardware word is positioned before the final IBK string record.
    const size_t engineOffset=corrupt.size()-4-d.drumIbkPath.size()-4-d.ibkPath.size()-4;
    corrupt[engineOffset]=3;
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "out-of-range hardware mode rejected atomically");
    corrupt=blob;corrupt[8]=255;
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "invalid Program rejected atomically");
    corrupt=blob;corrupt[16]=255;corrupt[17]=255;
    ok &= ck(!decode(corrupt,out),"oversize ROM path rejected");
    AssetState::Data blank;blank.program=11;
    ok &= ck(decode(encode(blank),out)&&!out.pathsSpecified,
             "unresolved paths flag preserved for initial configuration");
    d.drumIbkPath=std::string(4097,'x');
    ok &= ck(encode(d).empty(),"oversize drum IBK path rejected on save");
    d.drumIbkPath.clear();
    d.ibkPath=std::string(4097,'x');
    ok &= ck(encode(d).empty(),"oversize IBK path rejected on save");
    d.ibkPath.clear();
    d.romPath=std::string(4097,'x');
    ok &= ck(encode(d).empty(),"oversize path rejected on save");
    AssetConfig::Paths config;
    std::istringstream ini(
        "# private user asset paths\n"
        "ROM = \"C:\\ROMs\\awe32.raw\" \r\n"
        "SF2 = \"D:\\Sounds\\Synth 512 Bank.sf2\"\r\n"
        "OPL3_IBK = \"C:\\FM\\Creative melodic.ibk\"\r\n"
        "OPL3_DRUM_IBK = \"C:\\FM\\Creative drums.ibk\"\r\n");
    ok &= ck(AssetConfig::Parse(ini,config)&&
             config.rom=="C:\\ROMs\\awe32.raw"&&
             config.sf2=="D:\\Sounds\\Synth 512 Bank.sf2"&&
             config.ibk=="C:\\FM\\Creative melodic.ibk"&&
             config.drumIbk=="C:\\FM\\Creative drums.ibk",
             "Windows paths and quoted spaces parsed");
    AssetConfig::Paths keep{"valid rom","valid sf2"};
    std::istringstream malformed("ROM=valid.raw\nSFX=typo.sf2\n");
    ok &= ck(!AssetConfig::Parse(malformed,keep)&&
             keep.rom=="valid rom"&&keep.sf2=="valid sf2",
             "invalid configuration fails without replacing old paths");
    std::cout<<(ok?"ASSET STATE PASS":"ASSET STATE FAIL")<<'\n';
    return ok?0:1;
}
