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
    d.program=104;d.engine=1;d.pathsSpecified=true;
    d.romPath="C:\\ROMs\\awe32.raw";
    d.sf2Path="D:\\Sounds\\Synth 512 Bank.sf2";
    const auto blob=encode(d);
    AssetState::Data out;
    ok &= ck(!blob.empty()&&decode(blob,out)&&out.program==104&&
             out.engine==1&&out.pathsSpecified&&out.romPath==d.romPath&&
             out.sf2Path==d.sf2Path,"V3 program, hardware and asset paths round trip");
    // V2 is identical to V3 up to the last 4 bytes (new hardware mode).
    Bytes v2(blob.begin(),blob.end()-4);
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
    ok &= ck(allRejected,"all truncated V3 states rejected atomically");
    auto corrupt=blob;
    corrupt[4]=90;
    out=d;out.program=7;
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "unknown format version rejected atomically");
    corrupt=blob;corrupt[corrupt.size()-4]=2;
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
    d.romPath=std::string(4097,'x');
    ok &= ck(encode(d).empty(),"oversize path rejected on save");
    AssetConfig::Paths config;
    std::istringstream ini(
        "# private user asset paths\n"
        "ROM = \"C:\\ROMs\\awe32.raw\" \r\n"
        "SF2 = \"D:\\Sounds\\Synth 512 Bank.sf2\"\r\n");
    ok &= ck(AssetConfig::Parse(ini,config)&&
             config.rom=="C:\\ROMs\\awe32.raw"&&
             config.sf2=="D:\\Sounds\\Synth 512 Bank.sf2",
             "Windows paths and quoted spaces parsed");
    AssetConfig::Paths keep{"valid rom","valid sf2"};
    std::istringstream malformed("ROM=valid.raw\nSFX=typo.sf2\n");
    ok &= ck(!AssetConfig::Parse(malformed,keep)&&
             keep.rom=="valid rom"&&keep.sf2=="valid sf2",
             "invalid configuration fails without replacing old paths");
    std::cout<<(ok?"ASSET STATE PASS":"ASSET STATE FAIL")<<'\n';
    return ok?0:1;
}
