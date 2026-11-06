#pragma once
#include <algorithm>
#include <array>
#include "MasterOutput.h"
#include <cstdint>
#include <string>
#include <string_view>
#include <utility>

namespace AWE125::AssetState {
// Legacy V1 was 3 x little-endian int32: "AWE1", version=1, Program.
inline constexpr uint32_t kMagic = 0x31455741u;
inline constexpr uint32_t kVersion = 11u; // V11 appends 8-way effect preset indices; V1-V10 migrate
inline constexpr int kControlCount = 12;
inline constexpr uint32_t kControlScale = 10000u;
inline constexpr uint32_t kFxMaxPreset = 7u;
inline constexpr uint32_t kDefaultReverbPreset = 4u; // Creative Hall 2
inline constexpr uint32_t kDefaultChorusPreset = 2u; // Creative Chorus 3
inline constexpr uint32_t kMaxBank = 16383u; // MIDI-compatible bank-selection range
inline constexpr uint32_t kMaxPath = 4096u;
struct Data {
    uint32_t program=0;
    uint32_t engine=0; // 0=EMU8000, 1=Yamaha OPL3, 2=Creative CQM
    uint32_t bank=0; // browser/SF2 bank, 128=SoundFont drum bank
    uint32_t masterVolume=MasterOutput::kDefault; // 10000=unity, 0=mute
    uint32_t reverbPreset=kDefaultReverbPreset;
    uint32_t chorusPreset=kDefaultChorusPreset;
    uint32_t channelProgramMask=0; // bits 0..15: per-channel MIDI program overrides
    std::array<uint32_t,16> channelPrograms{}; // defaults resolved to global program
    std::array<uint32_t,kControlCount> controls{}; // 0 = original SF2, 10000 = full overlay
    bool pathsSpecified=false;
    std::string romPath;
    std::string sf2Path;
    std::string ibkPath; // user-supplied melodic Creative FM bank
    std::string drumIbkPath; // user-supplied hardware-rhythm IBK
};
inline bool validPath(std::string_view s) {
    return s.size()<=kMaxPath && s.find('\0')==std::string_view::npos;
}
template<class Sink> bool Write(Sink&& sink,const Data& d) {
    if(d.program>127||d.engine>2||d.bank>kMaxBank||
       d.masterVolume>MasterOutput::kScale||
       d.reverbPreset>kFxMaxPreset||d.chorusPreset>kFxMaxPreset||
       d.channelProgramMask>0xffffu||
       std::any_of(d.channelPrograms.begin(),d.channelPrograms.end(),
           [](uint32_t value){return value>127u;})||
       std::any_of(d.controls.begin(),d.controls.end(),[](uint32_t value){return value>kControlScale;})||
       !validPath(d.romPath)||!validPath(d.sf2Path)||!validPath(d.ibkPath)||!validPath(d.drumIbkPath))return false;
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
           word(d.pathsSpecified?1u:0u)&&path(d.romPath)&&path(d.sf2Path)&&word(d.engine)&&path(d.ibkPath)&&path(d.drumIbkPath)&&word(d.bank)&&
           [&](){for(uint32_t v:d.controls)if(!word(v))return false;return true;}() &&
           word(d.masterVolume)&&word(d.channelProgramMask)&&
           [&](){for(uint32_t p:d.channelPrograms)if(!word(p))return false;return true;}() &&
           word(d.reverbPreset)&&word(d.chorusPreset);
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
       (version<1u||version>kVersion)||program>127)return false;
    Data candidate;
    candidate.program=program;
    candidate.channelPrograms.fill(program);
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
        if(!okEngine||engine>2u)return false;
        candidate.engine=engine;
    }
    if(version>=4u&&!readPath(candidate.ibkPath))return false;
    if(version>=5u&&!readPath(candidate.drumIbkPath))return false;
    if(!candidate.pathsSpecified&&
       (!candidate.ibkPath.empty()||!candidate.drumIbkPath.empty()))return false;
    if(version>=7u) {
        const auto [okBank,bank]=word();
        if(!okBank||bank>kMaxBank)return false;
        candidate.bank=bank;
    }
    if(version>=8u) {
        for(auto& v:candidate.controls) {
            const auto [ok,val]=word();
            if(!ok||val>kControlScale)return false;
            v=val;
        }
    }
    if(version>=9u) {
        const auto [okMaster,volume]=word();
        if(!okMaster||volume>MasterOutput::kScale)return false;
        candidate.masterVolume=volume;
    }
    if(version>=10u) {
        const auto [okMask,mask]=word();
        if(!okMask||mask>0xffffu)return false;
        candidate.channelProgramMask=mask;
        for(auto& ch: candidate.channelPrograms) {
            const auto [okProgram,value]=word();
            if(!okProgram||value>127u)return false;
            ch=value;
        }
    }
    if(version>=11u) {
        const auto [okRev,rev]=word();
        const auto [okCho,cho]=word();
        if(!okRev||!okCho||rev>kFxMaxPreset||cho>kFxMaxPreset)return false;
        candidate.reverbPreset=rev;
        candidate.chorusPreset=cho;
    }
    target=std::move(candidate); // atomic commit, after complete validation
    return true;
}
}
