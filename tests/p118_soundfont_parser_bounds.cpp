#include "SoundFont.h"
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
using Bytes=std::vector<uint8_t>;
static void u16(Bytes& b,uint16_t v){b.push_back(uint8_t(v));b.push_back(uint8_t(v>>8));}
static void u32(Bytes& b,uint32_t v){for(int i=0;i<4;++i)b.push_back(uint8_t(v>>(i*8)));}
static void label(Bytes& b,const std::string& s,size_t n) {
    for(size_t i=0;i<n;++i)b.push_back(i<s.size()?uint8_t(s[i]):0);
}
static void chunk(Bytes& b,const char* name,const Bytes& body){
    label(b,name,4);u32(b,uint32_t(body.size()));b.insert(b.end(),body.begin(),body.end());
    if(body.size()&1)b.push_back(0);
}
static Bytes list(const char* type,const Bytes& nested){
    Bytes b;label(b,type,4);b.insert(b.end(),nested.begin(),nested.end());
    Bytes out;chunk(out,"LIST",b);return out;
}
static void preset(Bytes& b,const char* name,uint16_t program,uint16_t bank,uint16_t idx) {
    label(b,name,20);u16(b,program);u16(b,bank);u16(b,idx);
    u32(b,0);u32(b,0);u32(b,0);
}
static void instrument(Bytes& b,const char* name,uint16_t idx) {
    label(b,name,20);u16(b,idx);
}
static void shdr(Bytes& b,const char* name,uint32_t start,uint32_t end) {
    label(b,name,20);u32(b,start);u32(b,end);u32(b,start+4);u32(b,end-4);
    u32(b,44100);b.push_back(60);b.push_back(0);u16(b,0);u16(b,1);
}
static Bytes fixture(){
    Bytes v;u16(v,2);u16(v,1);
    Bytes info;chunk(info,"ifil",v);
    Bytes pcm(1024,0);Bytes sdta;chunk(sdta,"smpl",pcm);
    Bytes ph; preset(ph,"P118 SYNTH",0,0,0);preset(ph,"EOP",0,0,1);
    Bytes pb;u16(pb,0);u16(pb,0);u16(pb,1);u16(pb,0);
    Bytes pg;u16(pg,41);u16(pg,0);
    Bytes in;instrument(in,"P118 SINE",0);instrument(in,"EOI",1);
    Bytes ib;u16(ib,0);u16(ib,0);u16(ib,2);u16(ib,0);
    Bytes ig;u16(ig,54);u16(ig,1);u16(ig,53);u16(ig,0);
    Bytes sh;shdr(sh,"P118 TEST SAMPLE",0,512);shdr(sh,"EOS",0,8);
    Bytes pd;chunk(pd,"phdr",ph);chunk(pd,"pbag",pb);
    chunk(pd,"pmod",Bytes(10,0));chunk(pd,"pgen",pg);
    chunk(pd,"inst",in);chunk(pd,"ibag",ib);
    chunk(pd,"imod",Bytes(10,0));chunk(pd,"igen",ig);
    chunk(pd,"shdr",sh);
    Bytes body;label(body,"sfbk",4);
    auto a=list("INFO",info),b=list("sdta",sdta),c=list("pdta",pd);
    body.insert(body.end(),a.begin(),a.end());body.insert(body.end(),b.begin(),b.end());
    body.insert(body.end(),c.begin(),c.end());
    Bytes riff;label(riff,"RIFF",4);u32(riff,uint32_t(body.size()));
    riff.insert(riff.end(),body.begin(),body.end());return riff;
}
static size_t chunkPayload(const Bytes& b,const char* id) {
    for(size_t i=12;i+8<=b.size();++i)
        if(b[i]==id[0] && b[i+1]==id[1] && b[i+2]==id[2] && b[i+3]==id[3])
            return i+8;
    return b.size();
}
static bool loadFixture(const Bytes& bytes,const char* label,bool expected){
    static int number=0;
    const auto path=std::filesystem::temp_directory_path()/
        ("125A_P118_parser_"+std::to_string(++number)+".sf2");
    {
        std::ofstream file(path,std::ios::binary|std::ios::trunc);
        file.write(reinterpret_cast<const char*>(bytes.data()),std::streamsize(bytes.size()));
    }
    auto result=SoundFont::Load(path.string());
    std::error_code ec;std::filesystem::remove(path,ec);
    const bool ok=(result.valid==expected);
    std::cout<<(ok?"PASS: ":"FAIL: ")<<label;
    if(!ok)std::cout<<" ("<<result.errorMessage<<")";
    std::cout<<"\n";
    return ok;
}
int main(){
    bool ok=true;
    const auto valid=fixture();
    ok&=loadFixture(valid,"valid original-format SF2 is accepted",true);
    {
        auto bad=valid;const auto off=chunkPayload(bad,"ibag");
        if(off==bad.size())return 2;
        bad[off]=0xfe;bad[off+1]=0xff;bad[off+4]=0xff;bad[off+5]=0xff;
        ok&=loadFixture(bad,"large instrument bag indices rejected without OOB",false);
    }
    {
        auto bad=valid;const auto off=chunkPayload(bad,"smpl");
        if(off==bad.size())return 2;
        bad[off-4]=0x00;bad[off-3]=0x10;bad[off-2]=0x00;bad[off-1]=0x00;
        ok&=loadFixture(bad,"oversized smpl chunk rejected without OOB",false);
    }
    {
        auto bad=valid;bad.resize(bad.size()-15);
        ok&=loadFixture(bad,"truncated RIFF rejected",false);
    }
    {
        auto bad=valid;const auto off=chunkPayload(bad,"pbag");
        if(off==bad.size())return 2;
        bad[off]=0xff;bad[off+1]=0xff;
        ok&=loadFixture(bad,"preset bag index beyond table rejected",false);
    }
    {
        auto bad=valid;const auto off=chunkPayload(bad,"ibag");
        if(off==bad.size())return 2;
        bad[off+4]=0;bad[off+5]=0;bad[off]=1;
        ok&=loadFixture(bad,"descending bag generator references rejected",false);
    }
    std::cout<<(ok?"P118_PARSER_REGRESSION_PASS":"P118_PARSER_REGRESSION_FAIL")<<"\n";
    return ok?0:1;
}
