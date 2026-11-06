// AUDIT ONLY – 125A AWE product-specific Windows callback timing.
// Compile the EXACT production Processor from Factory.cpp via the existing
// P128 extracted Processor header. No mocked engine, ROM, or state snapshots.
//
// On a shared Windows 2022 runner, these timings are diagnostic only:
// they do not establish an actual audio-driver/ASIO deadline guarantee.
#define main p128_unused_regression_main
#include "p128_processor_order.cpp"
#undef main
#include <atomic>
#include <cmath>
#include <iomanip>
#include <numeric>
#include <thread>

using RTClock=std::chrono::steady_clock;
constexpr int kRate=44100;
constexpr int kCallbacks=500;

struct Result {
    int frames=0,overruns=0,missedOutput=0,audible=0,saves=0,recalls=0;
    double avg=0,p95=0,p99=0,max=0,maxSchedulingLate=0;
};

Result measureCase(int frames,int controlMode,std::ofstream& csv) {
    const char* mode=controlMode==0?"render":controlMode==1?"save":"save_recall";
    Rig rig(state(),true,kRate);
    // Emulate an actual low-buffer host configuration. P128's generic
    // test Rig starts with maxSamplesPerBlock=1024; override that to match.
    require(rig.p->setProcessing(false)==kResultOk,"stop processing to resize");
    ProcessSetup setup{kRealtime,kSample32,frames,double(kRate)};
    require(rig.p->setupProcessing(setup)==kResultOk,
            "small buffer host setupProcessing");
    require(rig.p->setProcessing(true)==kResultOk,
            "resume small buffer processor");

    std::atomic<bool> started{false},stop{false},error{false};
    std::atomic<int> saveCount{0},recallCount{0};
    std::thread worker;
    if(controlMode!=0) {
        worker=std::thread([&] {
            while(!started.load(std::memory_order_acquire))
                std::this_thread::yield();
            while(!stop.load(std::memory_order_acquire)) {
                MemoryStream snap;
                if(rig.p->getState(&snap)!=kResultOk) {
                    error.store(true,std::memory_order_release);break;
                }
                const int count=saveCount.fetch_add(1)+1;
                if(controlMode==2&&count%12==0) {
                    MemoryStream restore;
                    const State fresh=state(0,0);
                    if(!writeState(restore,fresh) ||
                       rig.p->setState(&restore)!=kResultOk) {
                        error.store(true,std::memory_order_release);break;
                    }
                    recallCount.fetch_add(1);
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(2));
            }
        });
    }
    std::vector<double> durations;
    durations.reserve(kCallbacks);
    Result result; result.frames=frames;
    const double budgetMs=1000.*double(frames)/double(kRate);
    const auto duration=std::chrono::duration<double>(
        double(frames)/double(kRate));
    const auto origin=RTClock::now()+std::chrono::milliseconds(20);
    started.store(true,std::memory_order_release);
    // Four actual MIDI notes are sent at the beginning of EVERY block,
    // including after a recall, so a dormant processor cannot fake a PASS.
    // This is a deliberate stress scenario rather than a musical workload.
    for(int i=0;i<kCallbacks;++i) {
        const auto target=origin+std::chrono::duration_cast<RTClock::duration>(
            duration*i);
        std::this_thread::sleep_until(target);
        Block block(frames);
        for(int k=0;k<4;++k)
            block.note(0,48+((i*4+k)%16),0,true);
        const auto begin=RTClock::now();
        const tresult rc=rig.p->process(block.data);
        const auto finish=RTClock::now();
        if(rc!=kResultOk) {error=true;break;}
        const double processMs=std::chrono::duration<double,std::milli>(
            finish-begin).count();
        const double lateMs=std::max(0.,std::chrono::duration<double,std::milli>(
            begin-target).count());
        const auto scheduledFinish=target+
            std::chrono::duration_cast<RTClock::duration>(duration);
        const bool missed=finish>scheduledFinish;
        bool heard=false;
        for(int n=0;n<frames&&!heard;++n)
            heard=block.l[n]!=0.f||block.r[n]!=0.f;
        result.audible+=heard;
        result.overruns+=processMs>budgetMs;
        result.missedOutput+=missed;
        result.maxSchedulingLate=std::max(result.maxSchedulingLate,lateMs);
        durations.push_back(processMs);
        csv<<frames<<","<<mode<<","<<i<<","
           <<std::fixed<<std::setprecision(6)
           <<processMs<<","<<lateMs<<","<<int(missed)<<","
           <<int(heard)<<"\n";
    }
    stop.store(true,std::memory_order_release);
    if(worker.joinable())worker.join();
    require(!error.load(std::memory_order_acquire) &&
            durations.size()==kCallbacks,
            "processor failed during low-buffer stress test");
    require(result.audible>=400,
            "inaudible blocks: cannot claim realtime PCM workload");
    result.saves=saveCount.load();
    result.recalls=recallCount.load();
    if(controlMode>=1)
        require(result.saves>=10,"control thread saved too few states");
    if(controlMode==2)
        require(result.recalls>=1,"control thread never recalled state");
    std::sort(durations.begin(),durations.end());
    const auto pct=[&](double f) {
        return durations[static_cast<size_t>(std::ceil(f*kCallbacks))-1];
    };
    result.avg=std::accumulate(durations.begin(),durations.end(),0.)/
               double(kCallbacks);
    result.p95=pct(.95);result.p99=pct(.99);result.max=durations.back();
    std::cout<<std::fixed<<std::setprecision(4)
        <<"RT_SMALL_BUFFER frames="<<frames<<" case="<<mode
        <<" budget_ms="<<budgetMs
        <<" callbacks="<<kCallbacks
        <<" audible_blocks="<<result.audible
        <<" notes_per_callback=4"
        <<" mean_ms="<<result.avg
        <<" p95_ms="<<result.p95
        <<" p99_ms="<<result.p99
        <<" max_ms="<<result.max
        <<" process_overruns="<<result.overruns
        <<" missed_scheduled_deadlines="<<result.missedOutput
        <<" max_scheduling_late_ms="<<result.maxSchedulingLate
        <<" saves="<<result.saves
        <<" recalls="<<result.recalls
        <<" ENV=WINDOWS_2022_SHARED_VM_NOT_ASIO\n";
    return result;
}
int main(int argc,char** argv) {
    try {
        if(argc!=3) {
            std::cerr<<"usage: p129_smallbuffer_save_recall ASSETS OUTPUT.csv\n";
            return 2;
        }
        assetsDir=std::filesystem::path(argv[1]);
        std::ofstream csv(argv[2],std::ios::trunc);
        require(csv.good(),"cannot write callback-level CSV");
        csv<<"frames,case,callback,process_ms,scheduling_late_ms,"
              "missed_scheduled_deadline,audible_pcm\n";
        int processOverruns=0,missedOutputs=0;
        for(int frames:{128,256,1024}) {
            for(int mode=0;mode<3;++mode) {
                const auto metrics=measureCase(frames,mode,csv);
                processOverruns+=metrics.overruns;
                missedOutputs+=metrics.missedOutput;
            }
        }
        csv.flush();
        require(csv.good(),"incomplete output CSV");
        std::cout<<"RT_SMALL_BUFFER_RESULT callbacks=4500 "
            <<"process_overruns="<<processOverruns
            <<" missed_scheduled_deadlines="<<missedOutputs
            <<" NOTE=CI_DIAGNOSTIC_NOT_RELEASE_OR_ASIO_PASS\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"RT_SMALL_BUFFER_TEST_ERROR "<<e.what()<<std::endl;
        return 1;
    }
}
