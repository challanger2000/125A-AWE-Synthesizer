#pragma once
// Testable, non-realtime preset browsing logic. Actual source metadata only.
#include "PresetCatalog.h"
#include <algorithm>
#include <cctype>
#include <cstdint>
#include <cstdio>
#include <string>
#include <string_view>
#include <vector>

namespace AWE125 {
class PresetBrowserModel {
public:
    struct Row {
        uint16_t bank=0;
        uint8_t program=0;
        std::string name;
        bool drums=false;
    };
    static const char* HardwareDescription(int engine) noexcept {
        switch(engine) {
        case 0:return "Sample-Synthesizer mit Wave-ROM und SoundFonts (SF2).";
        case 1:return "Originaler Yamaha-FM-Synthesizer für klassische Sound-Blaster-Klänge.";
        case 2:return "Creatives eigener, OPL3-kompatibler FM-Synthesizer.";
        default:return "Unbekannte Hardware.";
        }
    }
    static const char* HardwareName(int engine) noexcept {
        switch(engine) {
        case 0:return "EMU8000 AWE32/64";
        case 1:return "Yamaha OPL3";
        case 2:return "Creative CQM";
        default:return "Unbekannt";
        }
    }
    static const PresetCatalog& Active(int engine,const PresetCatalog& sf,
                                       const PresetCatalog& fm) noexcept {
        return engine==0?sf:fm;
    }
    static std::vector<uint16_t> Banks(int engine,const PresetCatalog& sf,
                                       const PresetCatalog& fm) {
        std::vector<uint16_t> out;
        for(const auto& p:Active(engine,sf,fm).Entries())out.push_back(p.bank);
        std::sort(out.begin(),out.end());
        out.erase(std::unique(out.begin(),out.end()),out.end());
        return out;
    }
    static std::vector<Row> Filter(int engine,const PresetCatalog& sf,
                                    const PresetCatalog& fm,int bankFilter,
                                    std::string_view search) {
        std::vector<Row> out;
        const auto needle=Lower(search);
        for(const auto& p:Active(engine,sf,fm).Entries()) {
            if(bankFilter>=0&&p.bank!=bankFilter)continue;
            if(!needle.empty()&&Lower(p.name).find(needle)==std::string::npos)continue;
            out.push_back({p.bank,p.program,p.name,p.drums});
        }
        return out;
    }
    static std::string CurrentLabel(int engine,const PresetCatalog& sf,
                                    const PresetCatalog& fm,uint16_t bank,
                                    uint8_t program) {
        const auto& catalog=Active(engine,sf,fm);
        const auto* p=catalog.Find(engine==0?bank:0,program);
        char prefix[36]{};
        if(engine==0)std::snprintf(prefix,sizeof(prefix),"%u:%03u  ",bank,program);
        else std::snprintf(prefix,sizeof(prefix),"%03u  ",program);
        return std::string(prefix)+(p?p->name:"Nicht in der Bank vorhanden");
    }
    // PREV/NEXT navigates actual entries rather than nonexistent SF2 slots.
    // Search/filter does not alter normal instrument navigation.
    static int Neighbor(int engine,const PresetCatalog& sf,
                        const PresetCatalog& fm,uint16_t bank,
                        uint8_t program,int step) {
        const auto& entries=Active(engine,sf,fm).Entries();
        std::vector<uint8_t> programs;
        for(const auto& p:entries)
            if(p.bank==(engine==0?bank:0))programs.push_back(p.program);
        if(programs.empty())return -1;
        std::sort(programs.begin(),programs.end());
        programs.erase(std::unique(programs.begin(),programs.end()),programs.end());
        const auto it=std::lower_bound(programs.begin(),programs.end(),program);
        if(step>0) {
            auto next=it;
            if(next!=programs.end()&&*next==program)++next;
            return next==programs.end()?programs.front():*next;
        }
        if(it==programs.begin())return programs.back();
        return *(it-1);
    }
private:
    static std::string Lower(std::string_view v) {
        std::string out;
        out.reserve(v.size());
        for(unsigned char c:v)out.push_back(static_cast<char>(
            c<128?std::tolower(c):c));
        return out;
    }
};
} // namespace AWE125
