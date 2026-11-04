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
    d.program=104;d.engine=2;d.bank=128;d.pathsSpecified=true;
    d.romPath="C:\\ROMs\\awe32.raw";
    d.sf2Path="D:\\Sounds\\Synth 512 Bank.sf2";
    d.ibkPath="C:\\FM\\Creative melodic.ibk";
    d.drumIbkPath="C:\\FM\\Creative drums.ibk";
    d.controls[0]=7500;
    d.controls[8]=2500;
    d.masterVolume=4300; // 43%, preserved separately from SF2 overlays
    const auto blob=encode(d);
    AssetState::Data out;
    ok &= ck(!blob.empty()&&decode(blob,out)&&out.program==104&&
             out.engine==2&&out.bank==128&&out.pathsSpecified&&out.romPath==d.romPath&&
             out.sf2Path==d.sf2Path&&out.ibkPath==d.ibkPath&&
             out.drumIbkPath==d.drumIbkPath&&out.controls==d.controls&&
             out.masterVolume==4300,
             "V9 state round-trip with 43% master volume and 12 GUI controls");
    // V9 only appends one uint32 volume word. V8 projects restore to unity.
    Bytes v8(blob.begin(),blob.end()-4);
    v8[4]=8;
    ok &= ck(decode(v8,out)&&out.masterVolume==MasterOutput::kDefault&&
             out.controls==d.controls&&out.bank==128,
             "legacy V8 restores unity master without altering SF2 overlays");
    // V8 appends exactly 12 uint32 overlay parameters to V7, never to old saves.
    Bytes v7(v8.begin(),v8.end()-4*AssetState::kControlCount);
    v7[4]=7;
    ok &= ck(decode(v7,out)&&out.bank==128&&
             std::all_of(out.controls.begin(),out.controls.end(),[](uint32_t v){return v==0;}),
             "legacy V7 restore preserves bank and neutral overlay");
    ok &= ck(out.masterVolume==MasterOutput::kDefault,
             "legacy V7 project defaults master volume to 100%");
    // V7 appended one uint32 SF2-bank word to the unchanged V6 bytes.
    Bytes v6(v7.begin(),v7.end()-4);
    v6[4]=6;
    ok &= ck(decode(v6,out)&&out.engine==2&&out.bank==0&&
             out.program==104&&out.sf2Path==d.sf2Path,
             "legacy V6 restores default SF2 bank 0");
    Bytes v5(v6);
    v5[4]=5; // historical v5, Yamaha only
    // Engine word occurs before melodic and drum-IBK paths.
    const size_t engineIndex=v5.size()-4-d.drumIbkPath.size()-4-d.ibkPath.size()-4;
    v5[engineIndex]=1;
    ok &= ck(decode(v5,out)&&out.engine==1&&
             out.drumIbkPath==d.drumIbkPath&&out.bank==0,
             "legacy V5 rhythm state migrates");
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
    ok &= ck(allRejected,"all truncated V9 states rejected atomically");
    auto corrupt=blob;
    corrupt[4]=90;
    out=d;out.program=7;
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "unknown format version rejected atomically");
    corrupt=blob;
    // Hardware word precedes the IBK strings, bank and V8 control values.
    const size_t engineOffset=corrupt.size()-4-4*AssetState::kControlCount-4-4-d.drumIbkPath.size()-4-d.ibkPath.size()-4;
    corrupt[engineOffset]=3;
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "out-of-range hardware mode rejected atomically");
    corrupt=blob;
    // V7 bank word precedes V8's 12 control words.
    const size_t bankOffset=corrupt.size()-4-4*AssetState::kControlCount-4;
    corrupt[bankOffset]=0x00;
    corrupt[bankOffset+1]=0x40; // exact little-endian bank 16384
    out=d;out.program=7;
    ok &= ck(!decode(corrupt,out)&&out.program==7&&out.bank==128,
             "invalid SF2 bank 16384 rejected without state mutation");
    corrupt=blob;
    corrupt[corrupt.size()-8]=0xFF;corrupt[corrupt.size()-7]=0xFF;
    out=d;out.program=7;
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "invalid V8 overlay control range rejected atomically");
    corrupt=blob;
    corrupt[corrupt.size()-4]=0xFF;
    corrupt[corrupt.size()-3]=0xFF;
    out=d;out.program=7;
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "invalid V9 master volume rejected atomically");
    AssetState::Data maxVolume=d;maxVolume.masterVolume=10000;
    ok &= ck(decode(encode(maxVolume),out)&&out.masterVolume==10000,
             "master 100% is exactly saved and restored");
    maxVolume.masterVolume=0;
    ok &= ck(decode(encode(maxVolume),out)&&out.masterVolume==0,
             "master 0% mute is exactly saved and restored");
    maxVolume.masterVolume=10001;
    ok &= ck(encode(maxVolume).empty(),
             "out-of-range master volume cannot be serialized");
    AssetState::Data boundary=d;boundary.bank=AssetState::kMaxBank;
    ok &= ck(decode(encode(boundary),out)&&out.bank==AssetState::kMaxBank,
             "maximum SF2 bank 16383 round-trips");
    boundary.bank=AssetState::kMaxBank+1;
    ok &= ck(encode(boundary).empty(),"bank 16384 rejected on serialization");
    corrupt=blob;corrupt[8]=255;
    out=d;out.program=7; // do not accidentally inherit the prior successful round-trip
    ok &= ck(!decode(corrupt,out)&&out.program==7,
             "invalid Program rejected atomically");
    corrupt=blob;corrupt[16]=255;corrupt[17]=255;
    ok &= ck(!decode(corrupt,out),"oversize ROM path rejected");
    AssetState::Data blank;blank.program=11;
    ok &= ck(decode(encode(blank),out)&&!out.pathsSpecified&&
             out.masterVolume==10000,
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
