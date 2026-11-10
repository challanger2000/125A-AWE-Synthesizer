// P229: actual native EMU8000 signed32 PRECLIP diagnostics on real owner SF2s.
// Private user media stays on analysis machine: this program contains no
// built-in ROM/SF2, and public CI only compiles/tests the executable.
// STRICT bank selection prevents fallback GM samples (false positive).
// Each case gets a fresh isolated chip, SF2 bank and note to avoid FX tails.
#include "Synth.h"
#include <algorithm>
#include <array>
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
constexpr int SR=44100;
constexpr int FRAMES=SR*2;
struct Trial {std::string file;int bank,program,note,velocity;};
void check(bool ok,const std::string& msg) {
    if(!ok)throw std::runtime_error("P228 FAILED: "+msg);
}
std::vector<std::string> csv_columns(const std::string& line) {
    std::vector<std::string> items;
    std::string cell;
    bool quoted=false;
    for(size_t i=0;i<line.size();++i){
        char c=line[i];
        if(c=='"'){
            if(quoted && i+1<line.size() && line[i+1]=='"'){cell+='"';++i;}
            else quoted=!quoted;
        }else if(c==',' && !quoted){items.push_back(cell);cell.clear();}
        else cell+=c;
    }
    check(!quoted,"unterminated CSV quote");
    items.push_back(cell);
    return items;
}
std::vector<Trial> read_plan(const std::filesystem::path& plan,
                             const std::string& name,size_t cap) {
    std::ifstream input(plan,std::ios::binary);
    check(bool(input),"matrix CSV not found");
    std::string line;
    check(bool(std::getline(input,line)),"empty matrix");
    std::vector<Trial> rows;
    size_t seen=0;
    while(std::getline(input,line)) {
        // Python csv.writer and Windows tools emit CRLF. std::getline removes
        // LF only; a retained CR in the last cell must never reject genuine
        // 2000 ms audio-test rows.
        if(!line.empty() && line.back()=='\r')line.pop_back();
        if(line.empty())continue;
        auto c=csv_columns(line);
        check(c.size()==11,"bad P228 matrix column count");
        if(c[0]!=name)continue;
        Trial t{c[0],std::stoi(c[2]),std::stoi(c[3]),
                std::stoi(c[5]),std::stoi(c[6])};
        check(t.bank>=0 && t.bank<=16383 && t.program>=0 && t.program<128 &&
              t.note>=0 && t.note<128 && t.velocity>0 && t.velocity<128,
              "illegal MIDI case");
        check(c[7]=="0" && c[8]=="0" && c[9]=="dry" && c[10]=="2000",
              "unexpected FX state or duration in P228 manifest");
        if(++seen>100000)throw std::runtime_error("P228 too many cases");
        if(cap==0||rows.size()<cap)rows.push_back(t);
    }
    check(!rows.empty(),"no P228 cases for bank "+name);
    return rows;
}
void selftest(){
    check(csv_columns("a,\"b,c\",d")==std::vector<std::string>({"a","b,c","d"}),
          "CSV quoted comma accepted");
    check(csv_columns("a,\"b\"\"c\",d")==std::vector<std::string>({"a","b\"c","d"}),
          "CSV double quote accepted");
    bool rejected=false;
    try{csv_columns("\"broken");}catch(const std::exception&){rejected=true;}
    check(rejected,"CSV truncation negative mutation not rejected");
    std::cout<<"P229_MATRIX_PARSER_POSITIVE_AND_MUTATION_PASS\n";
}
struct Metrics{
    uint64_t nonzero=0,neg_rail=0,pos_rail=0;
    double squares=0.0,mean=0.0;
    int peak=0,first=-1;
    size_t live=0;
    size_t nonzeroFXVoices=0;
    size_t activeChipVoices=0;
    int32_t rawMin=std::numeric_limits<int32_t>::max();
    int32_t rawMax=std::numeric_limits<int32_t>::min();
    uint64_t rawOverPos=0,rawOverNeg=0,rawClipMismatches=0;
    int firstRawOverflowFrame=-1;
    double rawSquares=0.0,rawSum=0.0;
};
Metrics run(const std::string& rom,const std::string& sf2,const Trial& t,bool positiveFxWitness=false) {
    Synth synth(SR);
    synth.Core().SetDriver(Awe32::Driver::Win95);
    synth.SetStrictPresetSelection(true);
    std::string err;
    check(synth.Core().UseBox86Chip(rom,err),"original ROM chip init: "+err);
    synth.Core().PowerOnInit();
    check(synth.LoadBank(sf2,err),"SoundFont rejected: "+err);
    check(synth.BankCount()==1u,"unexpected ROM fallback or multiple imported banks");
    synth.SelectBrowserBank(static_cast<uint16_t>(t.bank));
    synth.ProgramChange(0,static_cast<uint8_t>(t.program));
    // Deliberately maximal incoming MIDI FX CCs. GUI 0 MUST OVERRIDE
    // both the SF2 preset generators and all incoming controller sends.
    synth.ControlChange(0,7,100);
    synth.ControlChange(0,11,127);
    synth.ControlChange(0,91,127);
    synth.ControlChange(0,93,127);
    synth.SetGuiControl(10,positiveFxWitness?1.f:0.f);
    synth.SetGuiControl(11,positiveFxWitness?1.f:0.f);
    check((positiveFxWitness && synth.GuiControl(10)==1.f &&
           synth.GuiControl(11)==1.f) ||
          (!positiveFxWitness && synth.GuiControl(10)==0.f &&
           synth.GuiControl(11)==0.f), "GUI FX state not retained");
    // Capture actual chip output before RenderBlock int16 clamp.
    std::vector<int32_t> raw(static_cast<size_t>(FRAMES)*2,0);
    std::vector<int16_t> pcm(static_cast<size_t>(FRAMES)*2,0);
    synth.Core().SetRawChipFrameCapture(raw.data(),FRAMES);
    synth.NoteOn(0,static_cast<uint8_t>(t.note),
                 static_cast<uint8_t>(t.velocity),1);
    Metrics m;
    const auto held=synth.CaptureHeldNotes();
    for(const auto& item:held)m.live+=item.sequence!=0;
    // Read physical driver-register sends for actually active voices;
    // don't inspect free voices with stale power-on register data.
    for(int v=0;v<Synth::kMaxVoices;++v){
        if(!synth.Core().IsVoiceActive(v))continue;
        ++m.activeChipVoices;
        const auto ptrx=synth.Core().ReadDriver(Emu8000::Reg::PTRX,v);
        const auto csl=synth.Core().ReadDriver(Emu8000::Reg::CSL,v);
        if(((ptrx>>8)&255u)||((csl>>24)&255u))++m.nonzeroFXVoices;
    }
    check(m.activeChipVoices>0,"FX register witness vacuous: no active physical EMU8000 voice");
    // Always measure real chip PCM, never the RIFF inventory or a fake
    // built-in test oscillator. No normalisation, no limiter, no effect FX.
    std::array<int16_t,1024*2> frames{};
    for(int at=0;at<FRAMES;){
        if(at==SR)synth.NoteOff(0,static_cast<uint8_t>(t.note));
        int count=std::min(1024,FRAMES-at);
        if(at<SR)count=std::min(count,SR-at);
        synth.RenderBlock(frames.data(),static_cast<uint32_t>(count));
        for(int i=0;i<count*2;++i){
            int v=frames[static_cast<size_t>(i)];
            pcm[static_cast<size_t>(at)*2+static_cast<size_t>(i)]=static_cast<int16_t>(v);
            const int absolute=v<0?-v:v;
            m.peak=std::max(m.peak,absolute);
            m.squares+=double(v)*double(v);
            m.mean+=v;
            if(v){++m.nonzero;if(m.first<0)m.first=at+(i/2);}
            m.neg_rail+=v==-32768;
            m.pos_rail+=v==32767;
        }
        at+=count;
    }
    const size_t captured=synth.Core().RawChipFramesCaptured();
    synth.Core().SetRawChipFrameCapture(nullptr,0);
    check(captured==FRAMES,"actual 86Box signed32 capture incomplete");
    for(size_t i=0;i<raw.size();++i) {
        const int32_t x=raw[i];
        m.rawMin=std::min(m.rawMin,x);m.rawMax=std::max(m.rawMax,x);
        m.rawSquares+=double(x)*x;m.rawSum+=x;
        if(x>32767){++m.rawOverPos;
            if(m.firstRawOverflowFrame<0)m.firstRawOverflowFrame=static_cast<int>(i/2);}
        if(x< -32768){++m.rawOverNeg;
            if(m.firstRawOverflowFrame<0)m.firstRawOverflowFrame=static_cast<int>(i/2);}
        const int16_t clipped=static_cast<int16_t>(std::clamp(x,-32768,32767));
        m.rawClipMismatches+=clipped!=pcm[i];
    }
    check(m.rawClipMismatches==0,"native 32bit-to-16bit sample mismatch");
    return m;
}
} // namespace

int main(int argc,char** argv) {
    try {
        if(argc==2 && std::string(argv[1])=="--self-test") {
            selftest();return 0;
        }
        check(argc==6,
              "usage: p228-dry rom.raw bank.sf2 matrix.csv report.csv [case_limit]");
        const std::filesystem::path rom=argv[1],sf2=argv[2],plan=argv[3],report=argv[4];
        // argc 6: one extra positional argument is required to avoid accidental
        // huge jobs; zero means all cases.
        const size_t cap=static_cast<size_t>(std::stoull(argv[5]));
        check(argc==6,"unexpected P228 extra arguments");
        check(std::filesystem::is_regular_file(rom) &&
              std::filesystem::file_size(rom)==1048576,
              "expected genuine 1MiB local original EMU8000 wave ROM");
        check(std::filesystem::is_regular_file(sf2),"SoundFont missing");
        const auto bank=sf2.filename().string();
        const auto cases=read_plan(plan,bank,cap);
        check(!std::filesystem::exists(report),"refuse overwrite P228 evidence");
        std::ofstream out(report,std::ios::binary);
        check(bool(out),"failed opening output report");
        out<<"case,bank,program,note,velocity,active_note_count,"
              "nonzero_fx_register_voices,nonzero_samples,first_nonzero_frame,"
              "rms_dbfs,peak_dbfs,neg_rails,pos_rails,dc_normalized,"
              "raw_min,raw_max,raw_over_pos,raw_over_neg,raw_first_over_frame,"
              "raw_peak_dbfs,raw_rms_dbfs,raw_dc,raw_clip_mismatches,"
              "active_chip_voices\n";
        size_t completed=0,voices_missing=0,fx_leaks=0,allsilent=0;
        for(const auto& t:cases){
            const auto m=run(rom.string(),sf2.string(),t);
            ++completed;
            voices_missing+=m.live==0;
            fx_leaks+=m.nonzeroFXVoices>0;
            allsilent+=m.nonzero==0;
            const double rms=m.squares>0?std::sqrt(m.squares/double(FRAMES*2))/32768.0:0.0;
            const double peak=m.peak>0?double(m.peak)/32768.0:0.0;
            const double rmsdb=rms>0?20*std::log10(rms):-300.0;
            const double peakdb=peak>0?20*std::log10(peak):-300.0;
            out<<completed<<','<<t.bank<<','<<t.program<<','<<t.note<<','
               <<t.velocity<<','<<m.live<<','<<m.nonzeroFXVoices<<','
               <<m.nonzero<<','<<m.first<<','
               <<std::setprecision(12)<<rmsdb<<','<<peakdb<<','
               <<m.neg_rail<<','<<m.pos_rail<<','
               <<m.mean/double(FRAMES*2*32768)<<','
               <<m.rawMin<<','<<m.rawMax<<','<<m.rawOverPos<<','
               <<m.rawOverNeg<<','<<m.firstRawOverflowFrame<<','
               <<20.*std::log10(double(std::max<int64_t>(
                     -static_cast<int64_t>(m.rawMin),m.rawMax))/32768.)<<','
               <<20.*std::log10(std::sqrt(m.rawSquares/double(FRAMES*2))/32768.)<<','
               <<m.rawSum/double(FRAMES*2*32768)<<','
               <<m.rawClipMismatches<<','<<m.activeChipVoices<<'\n';
            check(bool(out),"result output truncated");
            if(completed%50==0) {
                out.flush();
                std::cout<<"P228_PROGRESS "<<bank<<" "<<completed<<"/"<<cases.size()
                         <<" zero_voices="<<voices_missing<<" fx_leaks="<<fx_leaks
                         <<" silent="<<allsilent<<"\n"<<std::flush;
            }
        }
        const Metrics witness=run(rom.string(),sf2.string(),cases[0],true);
        check(witness.activeChipVoices>0 && witness.nonzeroFXVoices>0,
              "positive witness FAIL: nonzero FX registers cannot be observed");
        std::cout<<"P229_WET_POSITIVE_CONTROL=PASS chipVoices="
                 <<witness.activeChipVoices<<" nonzeroFxRegisterVoices="
                 <<witness.nonzeroFXVoices<<"\\n";
        std::cout<<"P229_RAW32_NATIVE_EMU8000 bank="<<bank
                 <<" note_cases="<<completed
                 <<" no_voice="<<voices_missing<<" nonzero_FX_register_cases="<<fx_leaks
                 <<" silent_pcm_cases="<<allsilent<<" result="<<report.string()
                 <<" REAL_AUDIO=YES EXPORTED_VST3=NOT_RUN ORIGINAL_CREATIVE=NOT_RUN"
                 <<" RELEASE=BLOCKED\n";
        return fx_leaks==0?0:3;
    }catch(const std::exception& e) {
        std::cerr<<e.what()<<'\n';
        return 2;
    }
}
