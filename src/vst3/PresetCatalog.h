#pragma once
// Non-realtime, read-only preset index for the future graphical browser.
// Reads only SoundFont 'phdr' metadata; never loads sample data or ROMs.
// No I/O from the VST3 audio callback.
#include <algorithm>
#include <array>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <limits>
#include <span>
#include <string>
#include <string_view>
#include <vector>
#include "IbkBank.h"

namespace AWE125 {
struct PresetEntry {
    uint16_t bank=0;
    uint8_t program=0;
    std::string name;
    bool drums=false;
};
class PresetCatalog {
public:
    const std::vector<PresetEntry>& Entries() const noexcept {return entries_;}
    const PresetEntry* Find(uint16_t bank,uint8_t program) const noexcept {
        for(const auto& p:entries_) if(p.bank==bank&&p.program==program)return &p;
        return nullptr;
    }
    // Load into temporary candidate and commit only when complete.
    // CF: 'phdr' is an SF2 preset table (38 bytes/entry), final record EOP.
    bool LoadSoundFont(const std::string& path,std::string& error) {
        namespace fs=std::filesystem;
        std::ifstream in(fs::u8path(path),std::ios::binary);
        if(!in) {error="Preset catalog: cannot open SF2";return false;}
        in.seekg(0,std::ios::end);
        const auto end=in.tellg();
        if(end<12) {error="Preset catalog: short RIFF";return false;}
        const uint64_t fileSize=static_cast<uint64_t>(end);
        in.seekg(0);
        std::array<uint8_t,12> header{};
        if(!in.read(reinterpret_cast<char*>(header.data()),12)||
            !equal4(header.data(),"RIFF")||!equal4(header.data()+8,"sfbk")) {
            error="Preset catalog: invalid SoundFont RIFF";return false;
        }
        const uint64_t riffEnd=8ull+le32(header.data()+4);
        if(riffEnd>fileSize||riffEnd<12) {
            error="Preset catalog: truncated RIFF";return false;
        }
        std::vector<PresetEntry> candidate;
        bool seen=false;
        uint64_t off=12;
        while(off+8<=riffEnd) {
            std::array<uint8_t,8> chunk{};
            if(!readAt(in,off,chunk.data(),chunk.size()))break;
            const uint64_t len=le32(chunk.data()+4);
            const uint64_t data=off+8;
            if(len>riffEnd-data) {
                error="Preset catalog: invalid RIFF chunk size";return false;
            }
            if(equal4(chunk.data(),"LIST")&&len>=4) {
                std::array<uint8_t,4> kind{};
                if(!readAt(in,data,kind.data(),4)) {
                    error="Preset catalog: missing LIST type";return false;
                }
                if(equal4(kind.data(),"pdta")) {
                    uint64_t sub=data+4;
                    const uint64_t listEnd=data+len;
                    while(sub+8<=listEnd) {
                        std::array<uint8_t,8> subHeader{};
                        if(!readAt(in,sub,subHeader.data(),8)) {
                            error="Preset catalog: unreadable pdta";return false;
                        }
                        const uint64_t n=le32(subHeader.data()+4);
                        const uint64_t begin=sub+8;
                        if(n>listEnd-begin) {
                            error="Preset catalog: invalid pdta chunk";return false;
                        }
                        if(equal4(subHeader.data(),"phdr")) {
                            if(seen||n<76||n%38!=0||n>38ull*32769ull) {
                                error="Preset catalog: malformed/duplicate phdr";return false;
                            }
                            seen=true;
                            const uint64_t count=n/38;
                            candidate.reserve(static_cast<size_t>(count-1));
                            for(uint64_t i=0;i<count;++i) {
                                std::array<uint8_t,38> p{};
                                if(!readAt(in,begin+i*38,p.data(),p.size())) {
                                    error="Preset catalog: truncated phdr";return false;
                                }
                                if(i==count-1) {
                                    if(!equal3(p.data(),"EOP")) {
                                        error="Preset catalog: phdr missing EOP";return false;
                                    }
                                    continue;
                                }
                                const uint32_t program=le16(p.data()+20);
                                const uint32_t bank=le16(p.data()+22);
                                if(program>127||bank>16383) {
                                    error="Preset catalog: bank/program not addressable";return false;
                                }
                                std::string name=cleanName(p.data(),20);
                                if(name.empty())name="Program "+std::to_string(program);
                                candidate.push_back({static_cast<uint16_t>(bank),
                                    static_cast<uint8_t>(program),std::move(name),bank==128});
                            }
                        }
                        sub=begin+n+(n&1u);
                    }
                    if(sub!=listEnd) {
                        error="Preset catalog: pdta padding mismatch";return false;
                    }
                }
            }
            off=data+len+(len&1u);
        }
        if(off!=riffEnd||!seen||candidate.empty()) {
            error="Preset catalog: no valid phdr";return false;
        }
        // The audio engine selects last-loaded banks first; within one
        // SoundFont, duplicate bank/program pairs are ambiguous. Reject.
        std::sort(candidate.begin(),candidate.end(),[](const auto& a,const auto& b){
            return a.bank!=b.bank?a.bank<b.bank:a.program<b.program;
        });
        for(size_t i=1;i<candidate.size();++i) {
            if(candidate[i].bank==candidate[i-1].bank&&
                candidate[i].program==candidate[i-1].program) {
                error="Preset catalog: duplicate bank/program";return false;
            }
        }
        entries_=std::move(candidate);
        error.clear();
        return true;
    }
    // Append the user's original GM ROM preset metadata; no waveform is copied.
    // Standard bank 0 remains available beneath a later overriding SF2.
    // Banks 16383/16382 are reserved for explicit original ROM GM/drums.
    bool AppendRomGm(const std::string& path,std::string& error) {
        PresetCatalog gm;
        if(!gm.LoadSoundFont(path,error))return false;
        auto candidate=entries_;
        for(const auto& e:gm.Entries()) {
            if(e.bank!=0 && e.bank!=128)continue;
            const uint16_t virtualBank=e.bank==0?16383:16382;
            if(!Find(e.bank,e.program))candidate.push_back(e);
            PresetEntry rom=e;
            rom.bank=virtualBank;
            rom.name="ROM: "+rom.name;
            candidate.erase(std::remove_if(candidate.begin(),candidate.end(),
                [&](const PresetEntry& p){
                    return p.bank==rom.bank && p.program==rom.program;
                }),candidate.end());
            candidate.push_back(std::move(rom));
        }
        std::sort(candidate.begin(),candidate.end(),[](const auto& a,const auto& b){
            return a.bank!=b.bank?a.bank<b.bank:a.program<b.program;
        });
        entries_.swap(candidate);
        error.clear();
        return true;
    }
    bool LoadFmIbk(const std::string& path,std::string& error) {
        IbkBank bank;
        if(!bank.Load(path,error))return false;
        std::vector<PresetEntry> candidate;
        candidate.reserve(128);
        for(int i=0;i<128;++i) {
            const auto& n=bank.At(static_cast<uint8_t>(i)).name;
            auto name=cleanName(reinterpret_cast<const uint8_t*>(n.data()),9);
            if(name.empty())name="Program "+std::to_string(i);
            candidate.push_back({0,static_cast<uint8_t>(i),std::move(name),false});
        }
        entries_=std::move(candidate);
        error.clear();
        return true;
    }
private:
    static uint16_t le16(const uint8_t* p) {
        return static_cast<uint16_t>(p[0]|(uint16_t(p[1])<<8));
    }
    static uint32_t le32(const uint8_t* p) {
        return uint32_t(p[0])|(uint32_t(p[1])<<8)|
               (uint32_t(p[2])<<16)|(uint32_t(p[3])<<24);
    }
    static bool equal4(const uint8_t* p,const char* literal) {
        return p[0]==literal[0]&&p[1]==literal[1]&&
               p[2]==literal[2]&&p[3]==literal[3];
    }
    static bool equal3(const uint8_t* p,const char* literal) {
        return p[0]==literal[0]&&p[1]==literal[1]&&p[2]==literal[2];
    }
    static bool readAt(std::ifstream& f,uint64_t offset,void* dest,size_t n) {
        if(offset>static_cast<uint64_t>(std::numeric_limits<std::streamoff>::max()))
            return false;
        f.clear();
        f.seekg(static_cast<std::streamoff>(offset));
        return static_cast<bool>(f.read(reinterpret_cast<char*>(dest),
                                        static_cast<std::streamsize>(n)));
    }
    static std::string cleanName(const uint8_t* data,size_t n) {
        size_t end=0;
        while(end<n&&data[end]!=0)++end;
        while(end>0&&(data[end-1]==' '||data[end-1]==0))--end;
        std::string out;
        out.reserve(end);
        for(size_t i=0;i<end;++i) {
            // Preserve non-ASCII bytes for later code-page-aware UI conversion.
            // Strip control bytes to avoid malicious/invisible menu labels.
            if(data[i]>=32&&data[i]!=127)
                out.push_back(static_cast<char>(data[i]));
        }
        return out;
    }
    std::vector<PresetEntry> entries_;
};
} // namespace AWE125
