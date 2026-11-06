// P131 AUDIT ONLY: attribute rare Windows process() wall-time outliers.
// Uses actual production Factory.cpp Processor + Steinberg SDK + synthetic ROM/SF2.
// No production changes; never interpret shared-VM data as an ASIO release pass.
// QueryThreadCycleTime is reported as RAW CYCLES, not converted into elapsed
// CPU milliseconds: virtualized clocks, turbo and migration can distort it.
#define main p128_unused_main_for_p131_probe
#include "p128_processor_order.cpp"
#undef main

#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <atomic>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <numeric>
#include <thread>
#include <vector>

struct P131Sample {
    double wallUs=0;
    uint64_t cycles=0;
    bool cyclesValid=false;
    bool overrun=false;
    uint32_t coreBefore=0;
    uint32_t coreAfter=0;
};
static double p131Percentile(std::vector<double> values,double fraction) {
    if(values.empty())return 0;
    std::sort(values.begin(),values.end());
    const size_t idx=static_cast<size_t>(std::ceil(fraction*values.size())-1);
    return values[std::min(idx,values.size()-1)];
}
static const char* p131Mode(int mode) {
    return mode==0?"render":mode==1?"save":"save_recall";
}
static bool p131Run(int frames,int mode,LONGLONG qpcHz,std::ofstream& csv) {
    constexpr int kCallbacks=500;
    Rig rig;
    std::atomic<bool> stop{false},controlError{false};
    std::atomic<unsigned> saves{0},recallAttempts{0},recallSuccesses{0};
    std::thread control;
    if(mode) {
        control=std::thread([&] {
            try {
                unsigned iteration=0;
                while(!stop.load(std::memory_order_acquire)) {
                    const auto saved=save(*rig.p);
                    (void)saved;
                    ++saves;
                    ++iteration;
                    if(mode==2 && (iteration%5)==0) {
                        ++recallAttempts;
                        const auto response=recall(
                            *rig.p,state((iteration/5)%2==0?5:0,
                                         (iteration/5)%2==0?9:0));
                        if(response==kResultOk)++recallSuccesses;
                        // kResultFalse is an allowed superseded control intent.
                        else if(response!=kResultFalse)
                            controlError.store(true,std::memory_order_release);
                    }
                    std::this_thread::sleep_for(std::chrono::milliseconds(15));
                }
            } catch(...) {
                controlError.store(true,std::memory_order_release);
            }
        });
    }
    std::vector<P131Sample> measurements;
    measurements.reserve(kCallbacks);
    int audibleBlocks=0;
    bool processError=false;
    const double budgetUs=1'000'000.*double(frames)/44'100.;
    const auto scheduleStart=std::chrono::steady_clock::now();
    for(int i=0;i<kCallbacks;++i) {
        // Pacing is deliberately OUTSIDE process(), so scheduler wake-up
        // delay is not mistaken for the duration of the processor itself.
        const auto due=scheduleStart+
            std::chrono::duration_cast<std::chrono::steady_clock::duration>(
                std::chrono::duration<double>(double(i*frames)/44'100.));
        std::this_thread::sleep_until(due);
        Block block(frames);
        // Keep playing across every run: real NoteOns, not silent tail blocks.
        for(int note=0;note<4;++note)block.note(0,48+note,0,true);
        LARGE_INTEGER begin{},end{};
        ULONG64 cyclesBegin=0,cyclesEnd=0;
        const DWORD core0=GetCurrentProcessorNumber();
        const BOOL firstCycle=QueryThreadCycleTime(GetCurrentThread(),&cyclesBegin);
        QueryPerformanceCounter(&begin);
        const tresult rc=rig.p->process(block.data);
        QueryPerformanceCounter(&end);
        const BOOL lastCycle=QueryThreadCycleTime(GetCurrentThread(),&cyclesEnd);
        const DWORD core1=GetCurrentProcessorNumber();
        if(rc!=kResultOk || end.QuadPart<=begin.QuadPart) {
            processError=true;
            break;
        }
        P131Sample sample;
        sample.wallUs=1'000'000.*double(end.QuadPart-begin.QuadPart)/double(qpcHz);
        sample.cyclesValid=firstCycle && lastCycle && cyclesEnd>=cyclesBegin;
        sample.cycles=sample.cyclesValid ? cyclesEnd-cyclesBegin : 0;
        sample.overrun=sample.wallUs>budgetUs;
        sample.coreBefore=core0;
        sample.coreAfter=core1;
        bool audible=false;
        for(int j=0;j<frames && !audible;++j)
            audible=block.l[size_t(j)]!=0.f || block.r[size_t(j)]!=0.f;
        audibleBlocks+=audible;
        measurements.push_back(sample);
        csv<<frames<<','<<p131Mode(mode)<<','<<i<<','
            <<std::fixed<<std::setprecision(3)<<sample.wallUs<<','
            <<budgetUs<<','<<(sample.overrun?1:0)<<','
            <<sample.cycles<<','<<(sample.cyclesValid?1:0)<<','
            <<core0<<','<<core1<<','<<(audible?1:0)<<'\n';
    }
    stop.store(true,std::memory_order_release);
    if(control.joinable())control.join();
    std::vector<double> walls;
    walls.reserve(measurements.size());
    unsigned overruns=0,validCycles=0,migrations=0;
    for(const auto& sample:measurements) {
        walls.push_back(sample.wallUs);
        overruns+=sample.overrun;
        validCycles+=sample.cyclesValid;
        migrations+=(sample.coreBefore!=sample.coreAfter);
    }
    std::cout<<std::fixed<<std::setprecision(3)
        <<"P131_PROFILE frames="<<frames
        <<" mode="<<p131Mode(mode)
        <<" callbacks="<<measurements.size()
        <<" audible="<<audibleBlocks
        <<" budget_us="<<budgetUs
        <<" wall_median_us="<<p131Percentile(walls,0.5)
        <<" wall_p99_us="<<p131Percentile(walls,0.99)
        <<" wall_max_us="<<p131Percentile(walls,1.)
        <<" wall_overruns="<<overruns
        <<" qtc_valid="<<validCycles
        <<" core_migrations="<<migrations
        <<" saves="<<saves.load()
        <<" recall_attempts="<<recallAttempts.load()
        <<" recall_successes="<<recallSuccesses.load()
        <<" diagnostic_only=1\n";
    // Hard failures are invalid measurements, NOT timing threshold breaches:
    // deadline failures must remain visible in raw evidence without hiding
    // them behind a green/bad test execution status.
    return !processError && !controlError.load()
        && measurements.size()==kCallbacks
        && audibleBlocks>=350
        && (mode==0 || saves.load()>0)
        && (mode!=2 || recallAttempts.load()>0);
}
int main(int argc,char** argv) {
    try {
        if(argc!=3)return 2;
        assetsDir=std::filesystem::path(argv[1]);
        LARGE_INTEGER hz{};
        require(QueryPerformanceFrequency(&hz) && hz.QuadPart>0,
                "no monotonic QPC frequency");
        std::ofstream csv(argv[2],std::ios::trunc);
        require(bool(csv),"unable to open P131 CSV");
        csv<<"frames,mode,callback,process_wall_us,budget_us,wall_overrun,"
              "qtc_raw_cycles,qtc_valid,core_before,core_after,audible\n";
        bool valid=true;
        for(int frames:{128,256,1024})
            for(int mode=0;mode<3;++mode)
                valid=p131Run(frames,mode,hz.QuadPart,csv) && valid;
        csv.flush();
        require(bool(csv),"P131 evidence write failed");
        std::cout<<"P131_VERDICT measurement_complete="<<(valid?1:0)
            <<" deadline_release_approved=0"
            <<" qtc_is_raw_cycles_not_cpu_ms=1"
            <<" asio_host_tested=0\n";
        return valid?0:1;
    } catch(const std::exception& e) {
        std::cerr<<"P131_INCOMPLETE "<<e.what()<<'\n';
        return 2;
    }
}
#else
int main(){return 2;}
#endif
