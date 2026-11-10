// P226: real in-engine signed32 PRE-CLIP data for the same controlled P222
// factorial scenarios. This tool is native (not a VST3-host claim).
// No original ROM/SF2 ever enters CI, source, or an uploaded artifact.
// The 980-frame chip FIFO, register sequencing, ROM data, output DSP, filter,
// and signed16 render conversion are unchanged by this diagnostic.
#include "Synth.h"
#include "RomGmBank.h"
#include <algorithm>
#include <array>
#include <bit>
#include <cmath>
#include <cstdint>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr int kRate=44100;
constexpr int kFrames=kRate*3;
constexpr int kOff=kRate;
constexpr int kBlock=1024;
struct Summary {
    std::array<int32_t,2> minimum{INT32_MAX,INT32_MAX};
    std::array<int32_t,2> maximum{INT32_MIN,INT32_MIN};
    std::array<uint64_t,2> below{},above{},negRail{},posRail{};
    std::array<double,2> mean{},rms{};
    int firstOverFrame=-1, firstOverChannel=-1;
    int32_t firstOverValue=0;
    uint64_t checked=0;
};
void require(bool condition, const char* what) {
    if (!condition) throw std::runtime_error(what);
}
std::string narrow(const std::filesystem::path& path) {
    const auto u8=path.u8string();
    return std::string(u8.begin(),u8.end());
}
int16_t clip_signed16(int32_t value) noexcept {
    if (value< -32768) return -32768;
    if (value> 32767) return 32767;
    return static_cast<int16_t>(value);
}
Summary examine(const std::vector<int32_t>& raw,
                const std::vector<int16_t>& pcm) {
    require(raw.size()==size_t(kFrames)*2 && pcm.size()==raw.size(),
            "P226 missing/incomplete signed32 or signed16 frames");
    Summary result{};
    std::array<double,2> sq{};
    for(size_t frame=0;frame<size_t(kFrames);++frame) {
        for(size_t ch=0;ch<2;++ch) {
            const size_t pos=frame*2+ch;
            const auto v=raw[pos];
            // Independent exact clamp requirement: detect a misplaced tap,
            // missing samples, signedness mistakes and output postprocessing.
            require(pcm[pos]==clip_signed16(v),
                "P226 native int32 -> int16 mismatch: tap is not directly preclip");
            auto& low=result.minimum[ch];
            auto& high=result.maximum[ch];
            low=std::min(low,v);
            high=std::max(high,v);
            result.below[ch]+=v< -32768;
            result.above[ch]+=v> 32767;
            result.negRail[ch]+=pcm[pos]== -32768;
            result.posRail[ch]+=pcm[pos]==32767;
            if((v< -32768||v>32767)&&result.firstOverFrame<0) {
                result.firstOverFrame=static_cast<int>(frame);
                result.firstOverChannel=static_cast<int>(ch);
                result.firstOverValue=v;
            }
            const auto normalized=static_cast<double>(v)/32768.0;
            result.mean[ch]+=normalized;
            sq[ch]+=normalized*normalized;
            ++result.checked;
        }
    }
    for(size_t ch=0;ch<2;++ch) {
        result.mean[ch]/=kFrames;
        result.rms[ch]=std::sqrt(sq[ch]/kFrames);
    }
    return result;
}
bool oracle_mutation() {
    std::array<int32_t,8> raw={0,1,-32768,32767,-32769,32768,-90000,90000};
    std::array<int16_t,8> pcm{};
    for(size_t i=0;i<raw.size();++i)pcm[i]=clip_signed16(raw[i]);
    for(size_t i=0;i<raw.size();++i)
        if(pcm[i]!=clip_signed16(raw[i]))return false;
    if(pcm[4]!=-32768||pcm[5]!=32767||pcm[6]!=-32768||pcm[7]!=32767)
        return false;
    pcm[5]=32766; // deliberate wrong reference: MUST be rejected
    bool rejected=false;
    for(size_t i=0;i<raw.size();++i)
        if(pcm[i]!=clip_signed16(raw[i]))rejected=true;
    return rejected;
}
std::string case_name(int program,int note,int vel,int stage) {
    const char* names[]={"DRY","REVERB","CHORUS","BOTH"};
    const std::string pp=program==0?"P000":"P021";
    return pp+"-N"+std::to_string(note)+"V"+std::to_string(vel)+
           "-"+names[stage];
}
Summary one(const std::string& rom,const std::string& sf2,
            int program,int note,int velocity,int stage,
            const std::filesystem::path& output) {
    Synth synth(kRate);
    synth.Core().SetDriver(Awe32::Driver::Win95);
    std::string err;
    require(synth.Core().UseBox86Chip(rom,err),
            "P226 EMU8000 chip init failed; original ROM required");
    synth.Core().PowerOnInit();
    const auto banks=AWE125::RomGmBank::LoadBanks(synth,rom,sf2);
    if(!banks.sf2)throw std::runtime_error("P226 SF2 load: "+banks.sf2Error);
    synth.SelectBrowserBank(0);
    synth.ProgramChange(0,static_cast<uint8_t>(program));
    // Zero means genuinely dry, even when SF2 or CC has stored sends.
    synth.SetGuiControl(10,stage==1||stage==3?1.f:0.f);
    synth.SetGuiControl(11,stage==2||stage==3?1.f:0.f);
    // Exactly the VST3 P222 controllers, kept fixed for each quartet.
    synth.ControlChange(0,7,100);
    synth.ControlChange(0,11,127);
    synth.ControlChange(0,1,96);
    synth.ControlChange(0,91,48);
    synth.ControlChange(0,93,32);
    std::vector<int32_t> raw(size_t(kFrames)*2);
    std::vector<int16_t> pcm(size_t(kFrames)*2);
    synth.Core().SetRawChipFrameCapture(raw.data(),kFrames);
    synth.NoteOn(0,static_cast<uint8_t>(note),static_cast<uint8_t>(velocity),1);
    for(int at=0;at<kFrames;) {
        if(at==kOff)synth.NoteOff(0,static_cast<uint8_t>(note));
        int count=std::min(kBlock,kFrames-at);
        if(at<kOff)count=std::min(count,kOff-at);
        synth.RenderBlock(pcm.data()+size_t(at)*2,
                          static_cast<uint32_t>(count));
        at+=count;
    }
    const size_t captured=synth.Core().RawChipFramesCaptured();
    synth.Core().SetRawChipFrameCapture(nullptr,0);
    require(captured==size_t(kFrames),
            "P226 raw chip tap did NOT capture every output frame");
    const auto summary=examine(raw,pcm);
    require(summary.checked==size_t(kFrames)*2,
            "P226 raw channel count incorrect");
    static_assert(std::endian::native==std::endian::little,
                  "P226 raw32le requires an explicit little-endian conversion");
    require(!std::filesystem::exists(output),
            "P226 refuses to overwrite an existing private raw capture");
    std::ofstream out(output,std::ios::binary|std::ios::trunc);
    require(bool(out),"P226 cannot open private raw32 output");
    out.write(reinterpret_cast<const char*>(raw.data()),
              std::streamsize(raw.size()*sizeof(int32_t)));
    require(bool(out),"P226 failed to write complete private raw32 data");
    return summary;
}
int run(const std::vector<std::filesystem::path>& args) {
    if(args.size()==2 && args[1]==std::filesystem::path("--self-test")) {
        require(oracle_mutation(),"P226 did not reject mutated saturation oracle");
        std::cout<<"P226_ORACLE_MUTANT=DETECTED and signed32->signed16 rails checked\n";
        return 0;
    }
    require(args.size()==5 || args.size()==6,
        "Usage: p226-preclip.exe awe32.raw bank.sf2 private-output-dir --full|--synthetic");
    const bool synthetic=args.size()==6 && args[5]=="--synthetic";
    require(args.size()==5 || synthetic ||
            (args.size()==6 && args[5]=="--full"),
            "P226 invalid mode");
    const auto romPath=args[1],fontPath=args[2],outDir=args[3];
    // args[4] is the mandatory mode: do not silently omit user bank parity.
    const bool full=args[4]=="--full";
    const bool synthMode=args[4]=="--synthetic";
    require(full||synthMode,"P226 explicit --full/--synthetic required");
    require(!synthetic,"P226 redundant second mode argument");
    require(std::filesystem::is_regular_file(romPath) &&
            std::filesystem::file_size(romPath)==1048576u,
            "P226 expected 1 MiB owner-original/synthetic wave ROM");
    require(std::filesystem::is_regular_file(fontPath),
            "P226 missing SoundFont");
    std::filesystem::create_directories(outDir);
    const auto csvFile=outDir/"P226-PRECLIP-MATRIX.csv";
    require(!std::filesystem::exists(csvFile),
            "P226 refuses to overwrite existing private measurements");
    std::ofstream csv(csvFile);
    require(bool(csv),"P226 CSV output not writable");
    csv<<"case,program,note,velocity,gui_rev,gui_chor,cc1,cc7,cc11,cc91,cc93,"
          "frames,raw_min_l,raw_min_r,raw_max_l,raw_max_r,"
          "raw_below_l,raw_below_r,raw_above_l,raw_above_r,"
          "pcm_neg_rail_l,pcm_neg_rail_r,pcm_pos_rail_l,pcm_pos_rail_r,"
          "first_over_frame,first_over_channel,first_over_value,"
          "raw_mean_l,raw_mean_r,raw_rms_l,raw_rms_r\n";
    const auto rom=narrow(romPath),sf2=narrow(fontPath);
    int done=0,clipped=0;
    for(int program:{0,21}) {
        if(synthMode && program==21)continue;
        for(const auto [note,vel]:std::array<std::pair<int,int>,2>{{{48,64},{72,120}}}) {
            for(int stage=0;stage<4;++stage) {
                const auto label=case_name(program,note,vel,stage);
                const auto data=one(rom,sf2,program,note,vel,stage,
                                    outDir/(label+".raw32le"));
                const bool over=data.below[0]+data.below[1]+
                                data.above[0]+data.above[1]>0;
                clipped+=over;
                csv<<label<<','<<program<<','<<note<<','<<vel<<','
                   <<((stage==1||stage==3)?10000:0)<<','
                   <<((stage==2||stage==3)?10000:0)<<",96,100,127,48,32,"
                   <<kFrames<<','
                   <<data.minimum[0]<<','<<data.minimum[1]<<','
                   <<data.maximum[0]<<','<<data.maximum[1]<<','
                   <<data.below[0]<<','<<data.below[1]<<','
                   <<data.above[0]<<','<<data.above[1]<<','
                   <<data.negRail[0]<<','<<data.negRail[1]<<','
                   <<data.posRail[0]<<','<<data.posRail[1]<<','
                   <<data.firstOverFrame<<','<<data.firstOverChannel<<','
                   <<data.firstOverValue<<','
                   <<std::setprecision(12)
                   <<data.mean[0]<<','<<data.mean[1]<<','
                   <<data.rms[0]<<','<<data.rms[1]<<'\n';
                require(bool(csv),"P226 CSV data write failed");
                ++done;
                std::cout<<"P226_RAW32 "<<label<<" raw_min="
                         <<data.minimum[0]<<"/"<<data.minimum[1]
                         <<" raw_max="<<data.maximum[0]<<"/"<<data.maximum[1]
                         <<" preclip_overrange="
                         <<(data.below[0]+data.below[1]+data.above[0]+data.above[1])
                         <<" exact_preclip_samples="<<size_t(kFrames)*2
                         <<" status="<<(over?"SATURATED":"NO_PRECLIP_OVERFLOW")
                         <<"\n"<<std::flush;
            }
        }
    }
    require(done==(synthMode?8:16),"P226 missing factorial cases");
    std::cout<<"P226_MATRIX_DONE="<<done<<" PRECLIP_CASES_OVER="<<clipped
             <<" TYPE=ACTUAL_NATIVE_EMU8000_INT32"
             <<" VST3_PROCESS=NOT_RUN IN_THIS_PROBE"
             <<" ORIGINAL_CREATIVE=NOT_RUN RELEASE=BLOCKED\n";
    return 0; // a genuine overrange is data, not a false silent fix
}
} // namespace

#ifdef _WIN32
int wmain(int argc,wchar_t** argv) {
#else
int main(int argc,char** argv) {
#endif
    try {
        std::vector<std::filesystem::path> args;
        for(int i=0;i<argc;++i)args.emplace_back(argv[i]);
        return run(args);
    }catch(const std::exception& e) {
        std::cerr<<"P226_FAIL "<<e.what()<<"\n";
        return 2;
    }
}
