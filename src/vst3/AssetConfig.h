#pragma once
#include "AssetState.h"
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <istream>
#include <string>
#include <utility>

namespace AWE125::AssetConfig {
struct Paths { std::string rom,sf2,ibk; };
inline std::string trim(std::string s) {
    auto ws=[](unsigned char c){return c==' '||c=='\t'||c=='\r'||c=='\n';};
    while(!s.empty()&&ws(static_cast<unsigned char>(s.front())))s.erase(s.begin());
    while(!s.empty()&&ws(static_cast<unsigned char>(s.back())))s.pop_back();
    if(s.size()>=2&&s.front()=='"'&&s.back()=='"')
        s=s.substr(1,s.size()-2);
    return s;
}
inline bool Parse(std::istream& stream,Paths& result) {
    Paths candidate;
    std::string line;
    size_t count=0;
    while(std::getline(stream,line)) {
        if(++count>64||line.size()>8192)return false;
        line=trim(std::move(line));
        if(line.empty()||line[0]=='#'||line[0]==';')continue;
        const auto pos=line.find('=');
        if(pos==std::string::npos)return false;
        auto key=trim(line.substr(0,pos));
        auto value=trim(line.substr(pos+1));
        if(!AssetState::validPath(value))return false;
        if(key=="ROM")candidate.rom=std::move(value);
        else if(key=="SF2")candidate.sf2=std::move(value);
        else if(key=="OPL3_IBK")candidate.ibk=std::move(value);
        else return false; // no silent typo acceptance
    }
    if(stream.bad())return false;
    result=std::move(candidate);
    return true;
}
inline bool Load(Paths& result) {
    // Never called from a VST audio callback; initial activation/state only.
    if(const char* appdata=std::getenv("APPDATA");appdata&&*appdata) {
        const auto path=std::filesystem::path(appdata)/
            "125A"/"AWE Synthesizer"/"assets.cfg";
        std::ifstream in(path,std::ios::binary);
        if(in.is_open())return Parse(in,result);
    }
    Paths fallback;
    if(const char* rom=std::getenv("AWE32_ROM_PATH");rom&&*rom)fallback.rom=rom;
    if(const char* sf2=std::getenv("AWE32_SF2_PATH");sf2&&*sf2)fallback.sf2=sf2;
    if(const char* ibk=std::getenv("AWE32_OPL3_IBK_PATH");ibk&&*ibk)fallback.ibk=ibk;
    if(!AssetState::validPath(fallback.rom)||
       !AssetState::validPath(fallback.sf2)||
       !AssetState::validPath(fallback.ibk))return false;
    result=std::move(fallback);
    return true;
}
}
