// P112 - exhaustive preset audit for current P110/P111 engine, private assets only.
// Measures 77 user SF2 presets and 129 original GM-ROM presets with real 86Box.
// Does not export audio, ROM bytes, sample data, or user asset paths.
#include "Synth.h"
#include "SoundFont.h"
#include "RomGmBank.h"
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
namespace {
struct Level {int peak=0; double rms=0;};
Level meter(Synth& synth,int frames) {
    std::array<int16_t,4096*2> pcm{};
    double squares=0.;
    int peak=0;
    for(int offset=0;offset<frames;) {
        const int n=std::min(4096,frames-offset);
        synth.RenderBlock(pcm.data(),static_cast<uint32_t>(n));
        for(int i=0;i<n*2;++i) {
            const int a=pcm[static_cast<size_t>(i)];
            peak=std::max(peak,std::abs(a));
            squares+=double(a)*a;
        }
        offset+=n;
    }
    return {peak,std::sqrt(squares/(double(frames)*2.))/32768.};
}
std::string csv(const std::string& v) {
    std::string out="\"";
    for(char c:v) { if(c=='"')out+='\"';out+=c; }
    return out+"\"";
}
struct Case {
    std::string source,name;
    int bank=0,program=0,note=60;
};
bool hasZone(const SoundFont::Bank& source,int bank,int program,int note) {
    // Velocity 100 matches the previous P109 diagnosis.
    return !source.Select(bank,program,note,100).empty();
}
int findKey(const SoundFont::Bank& bank,int b,int program) {
    for(int key : {48,60,69,72,36,84,96,24})
        if(hasZone(bank,b,program,key))return key;
    for(int key=0;key<128;++key)
        if(hasZone(bank,b,program,key))return key;
    return -1;
}
struct Outcome {Level held{},released{}; std::string result;};
Outcome run(const Case& item,const std::string& rom,const std::string& gm,
            const std::string& sf2) {
    Synth synth(44100);
    synth.Core().SetDriver(Awe32::Driver::Win95);
    std::string err;
    if(!synth.Core().UseBox86Chip(rom,err) ||
       synth.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
        throw std::runtime_error("86Box/ROM: "+err);
    synth.Core().PowerOnInit();
    if(!synth.LoadBank(gm,err,true,0))
        throw std::runtime_error("SYNTHGM standard: "+err);
    if(!synth.LoadBank(sf2,err))
        throw std::runtime_error("SF2: "+err);
    if(!synth.LoadBank(gm,err,true,AWE125::RomGmBank::kBrowserBank,
                                     AWE125::RomGmBank::kBrowserDrums))
        throw std::runtime_error("SYNTHGM browser: "+err);
    synth.SelectBrowserBank(static_cast<uint16_t>(item.bank));
    synth.ProgramChange(0,static_cast<uint8_t>(item.program));
    synth.NoteOn(0,static_cast<uint8_t>(item.note),100);
    Outcome out;
    out.held=meter(synth,44100);      // identical 1-second hold to P109
    synth.NoteOff(0,static_cast<uint8_t>(item.note));
    out.released=meter(synth,22050); // 0.5-second release
    if(out.held.peak<=32 && out.released.peak>32)
        out.result="NUR_NACH_LOSLASSEN";
    else if(out.held.peak<=32 && out.released.peak<=32)
        out.result="STUMM";
    else if(out.held.rms<0.0005)
        out.result="SEHR_LEISE";
    else out.result="HOERBAR";
    return out;
}
}
int main(int argc,char** argv) {
    try {
        namespace fs=std::filesystem;
        std::string rom,gm,sf2;
        fs::path outPath="125A-P112-Alle-Presets.csv";
        for(int i=1;i<argc;i+=2) {
            if(i+1>=argc){std::cerr<<"Fehlender Parameter\n";return 2;}
            const std::string key=argv[i],val=argv[i+1];
            if(key=="--rom")rom=val;
            else if(key=="--gm")gm=val;
            else if(key=="--sf2")sf2=val;
            else if(key=="--out")outPath=fs::u8path(val);
            else {std::cerr<<"Unbekannter Parameter\n";return 2;}
        }
        if(rom.empty()||gm.empty()||sf2.empty()){
            std::cerr<<"--rom, --gm und --sf2 erforderlich\n";return 2;
        }
        std::string err;
        if(!AWE125::RomGmBank::ValidDescriptor(gm,err))
            throw std::runtime_error("Ungueltige GM-ROM-Bank: "+err);
        const auto gmBank=SoundFont::Load(gm);
        const auto userBank=SoundFont::Load(sf2);
        if(!userBank.valid)throw std::runtime_error("SF2 unlesbar: "+userBank.errorMessage);
        std::vector<Case> cases;
        for(const auto& p:userBank.presets) {
            if(p.bank<0||p.bank>16383||p.program<0||p.program>127)
                continue;
            cases.push_back({"SF2",p.name,p.bank,p.program,
                             findKey(userBank,p.bank,p.program)});
        }
        for(const auto& p:gmBank.presets) {
            if(p.bank==0 && p.program>=0 && p.program<=127) {
                cases.push_back({"GM_ROM",p.name,
                    AWE125::RomGmBank::kBrowserBank,p.program,
                    findKey(gmBank,p.bank,p.program)});
            } else if(p.bank==128 && p.program==0) {
                // Each drum key is an instrument in its own right. The first
                // eight are a representative GM drum sound check.
                for(int key:{36,38,42,46,49,51,45,41})
                    cases.push_back({"GM_DRUM",p.name,
                        AWE125::RomGmBank::kBrowserDrums,0,
                        hasZone(gmBank,128,0,key)?key:-1});
            }
        }
        const size_t expected=userBank.presets.size()+128+8;
        if(cases.size()!=expected)
            throw std::runtime_error("Unvollstaendiges Preset-Inventar");
        // Preflight ROM and all three P111 bank loads before producing any CSV.
        {
            Synth check(44100);
            check.Core().SetDriver(Awe32::Driver::Win95);
            if(!check.Core().UseBox86Chip(rom,err) ||
               check.Core().ChipVariant()!=Emu8000Core::Chip::Box86)
                throw std::runtime_error("Original-ROM nicht ladbar: "+err);
            check.Core().PowerOnInit();
            if(!check.LoadBank(gm,err,true,0) ||
               !check.LoadBank(sf2,err) ||
               !check.LoadBank(gm,err,true,
                   AWE125::RomGmBank::kBrowserBank,
                   AWE125::RomGmBank::kBrowserDrums))
                throw std::runtime_error("ROM/SF2/GM Ladefolge fehlgeschlagen: "+err);
        }
        std::ofstream csvOut(outPath,std::ios::binary|std::ios::trunc);
        if(!csvOut)throw std::runtime_error("CSV kann nicht geschrieben werden");
        csvOut<<"Source,Bank,Program,Name,Note,Velocity,HoldPeak,HoldRMS,"
                 "ReleasePeak,ReleaseRMS,Result\n";
        int good=0,quiet=0,releaseOnly=0,silent=0,noZone=0;
        std::cout<<"P112: ROM + SF2 + originale GM-Sounds | REAL 86Box EMU8000\n";
        std::cout<<"SF2-Presets: "<<userBank.presets.size()
                 <<" | GM: 128 | Drum-Schlaege: 8\n";
        for(size_t i=0;i<cases.size();++i) {
            const auto& item=cases[i];
            Outcome result;
            if(item.note<0)result.result="KEINE_ZONE";
            else result=run(item,rom,gm,sf2);
            if(result.result=="HOERBAR")++good;
            else if(result.result=="SEHR_LEISE")++quiet;
            else if(result.result=="NUR_NACH_LOSLASSEN")++releaseOnly;
            else if(result.result=="STUMM")++silent;
            else ++noZone;
            csvOut<<item.source<<","<<item.bank<<","<<item.program<<","
                  <<csv(item.name)<<","<<item.note<<",100,"
                  <<result.held.peak<<","<<result.held.rms<<","
                  <<result.released.peak<<","<<result.released.rms<<","
                  <<result.result<<"\n";
            if(i%16==0 || result.result!="HOERBAR")
                std::cout<<"["<<i+1<<"/"<<cases.size()<<"] "
                         <<item.source<<" "<<item.bank<<":"<<item.program
                         <<" note="<<item.note<<" -> "<<result.result<<"\n";
        }
        csvOut.flush();
        if(!csvOut)throw std::runtime_error("CSV schreiben fehlgeschlagen");
        std::cout<<"ERGEBNIS: HOERBAR="<<good<<" SEHR_LEISE="<<quiet
                 <<" NUR_NACH_LOSLASSEN="<<releaseOnly
                 <<" STUMM="<<silent<<" KEINE_ZONE="<<noZone<<"\n";
        std::cout<<"Datei: "<<outPath.string()<<"\n";
        // A successful run indicates completed measurement, not a passed
        // audio-quality test: user must review any failing CSV rows.
        return 0;
    }catch(const std::exception& e) {
        std::cerr<<"P112 FEHLER: "<<e.what()<<"\n";return 1;
    }
}
