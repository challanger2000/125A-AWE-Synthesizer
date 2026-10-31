#pragma once
#include <array>
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

namespace AWE125::AssetState {
// Legacy V1 was 3 x little-endian int32: "AWE1", version=1, Program.
inline constexpr uint32_t kMagic = 0x31455741u;
inline constexpr uint32_t kVersion = 4u;
inline constexpr uint32_t kMaxPath = 4096u;
struct Data {
    uint32_t program=0;
    uint32_t engine=0; // 0=EMU8000, 1=Yamaha OPL3
    bool pathsSpecified=false;
    std::string romPath;
    std::string sf2Path;
    std::string ibkPath; // user-supplied melodic Creative FM bank
};
inline bool validPath(std::string_view s) {
    return s.size()<=kMaxPath && s.find('\0')==std::string_view::npos;
}
template<class Sink> bool Write(Sink&& sink,const Data& d) {
    if(d.program>127||d.engine>1||!validPath(d.romPath)||!validPath(d.sf2Path)||!validPath(d.ibkPath))return false;
    auto word=[&](uint32_t n){
        const std::array<unsigned char,4> bytes{
          static_cast<unsigned char>(n), static_cast<unsigned char>(n>>8),
          static_cast<unsigned char>(n>>16),static_cast<unsigned char>(n>>24)};
        return sink(bytes.data(),bytes.size());
    };
    auto path=[&](const std::string& p){
        return word(static_cast<uint32_t>(p.size())) &&
               (p.empty()||sink(p.data(),p.size()));
    };
    return word(kMagic)&&word(kVersion)&&word(d.program)&&
           word(d.pathsSpecified?1u:0u)&&path(d.romPath)&&path(d.sf2Path)&&word(d.engine)&&path(d.ibkPath);
}
template<class Source> bool Read(Source&& source,Data& target) {
    auto word=[&]()->std::pair<bool,uint32_t>{
        std::array<unsigned char,4> b{};
        if(!source(b.data(),b.size()))return {false,0};
        return {true,uint32_t(b[0])|(uint32_t(b[1])<<8)|
                     (uint32_t(b[2])<<16)|(uint32_t(b[3])<<24)};
    };
    const auto [ok1,magic]=word();
    const auto [ok2,version]=word();
    const auto [ok3,program]=word();
    if(!ok1||!ok2||!ok3||magic!=kMagic||
       (version!=1u&&version!=2u&&version!=3u&&version!=kVersion)||program>127)return false;
    Data candidate;
    candidate.program=program;
    if(version==1u) {
        target=std::move(candidate); // valid old projects require default paths
        return true;
    }
    const auto [ok4,flag]=word();
    if(!ok4||flag>1u)return false;
    candidate.pathsSpecified=(flag==1u);
    auto readPath=[&](std::string& result){
        const auto [ok,n]=word();
        if(!ok||n>kMaxPath)return false;
        result.resize(n);
        return (!n||source(result.data(),n))&&validPath(result);
    };
    if(!readPath(candidate.romPath)||!readPath(candidate.sf2Path))return false;
    if(!candidate.pathsSpecified &&
       (!candidate.romPath.empty()||!candidate.sf2Path.empty()))return false;
    if(version>=3u) {
        const auto [okEngine,engine]=word();
        if(!okEngine||engine>1u)return false;
        candidate.engine=engine;
    }
    if(version>=4u&&!readPath(candidate.ibkPath))return false;
    if(!candidate.pathsSpecified&&!candidate.ibkPath.empty())return false;
    target=std::move(candidate); // atomic commit, after complete validation
    return true;
}
}
