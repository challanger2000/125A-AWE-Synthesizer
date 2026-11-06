// P132 laboratory host for the REAL normal and separately linked diagnostic VST3 DLL.
// No timing/heap/voice code is inserted in Processor::process().
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <mmsystem.h>
#include "pluginterfaces/base/ipluginbase.h"
#include "pluginterfaces/vst/ivstcomponent.h"
#include "pluginterfaces/vst/ivstaudioprocessor.h"
#include "public.sdk/source/common/memorystream.h"
#include "public.sdk/source/vst/hosting/parameterchanges.h"
#include "public.sdk/source/vst/hosting/eventlist.h"
#include "AssetState.h"
#include "MidiControlMapping.h"
#include "probe_api.h"
#include <algorithm>
#include <array>
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <stdexcept>
#include <thread>
#include <vector>
using namespace Steinberg;
using namespace Steinberg::Vst;
using State=AWE125::AssetState::Data;
namespace fs=std::filesystem;
static void must(bool v,const char* what){if(!v)throw std::runtime_error(what);}
static std::ofstream moduleMap;
static int64_t tick(){LARGE_INTEGER q;QueryPerformanceCounter(&q);return q.QuadPart;}
static int64_t hz(){LARGE_INTEGER q;must(QueryPerformanceFrequency(&q)!=0,"QPC frequency");return q.QuadPart;}
static State model(const fs::path& assets){State s;s.pathsSpecified=true;s.romPath=(assets/"zero.rom").string();s.sf2Path=(assets/"bank.sf2").string();return s;}
static void encode(MemoryStream& out,const State& s){auto put=[&](const void* p,size_t n){int32 done=0;return out.write(const_cast<void*>(p),int32(n),&done)==kResultOk&&done==int32(n);};must(AWE125::AssetState::Write(put,s),"encode V10");out.seek(0,IBStream::kIBSeekSet,nullptr);}
struct Plugin {
    HMODULE module=nullptr;IPluginFactory* factory=nullptr;IComponent* component=nullptr;IAudioProcessor* audio=nullptr;
    P132ReadVoices census=nullptr;P132HeapControl heapControl=nullptr;
    Plugin(const fs::path& dll,const State& s){
        module=LoadLibraryW(dll.c_str());must(module!=nullptr,"LoadLibrary VST3");
        auto* dos=reinterpret_cast<IMAGE_DOS_HEADER*>(module);auto* nt=reinterpret_cast<IMAGE_NT_HEADERS*>(reinterpret_cast<char*>(module)+dos->e_lfanew);
        moduleMap<<reinterpret_cast<uintptr_t>(module)<<','<<nt->OptionalHeader.SizeOfImage<<','<<dll.string()<<'\n';moduleMap.flush();
        auto get=reinterpret_cast<IPluginFactory*(*)()>(GetProcAddress(module,"GetPluginFactory"));must(get!=nullptr,"GetPluginFactory");factory=get();
        for(int32 i=0;i<factory->countClasses();++i){PClassInfo c{};factory->getClassInfo(i,&c);if(std::strcmp(c.category,kVstAudioEffectClass)==0){factory->createInstance(c.cid,IComponent::iid,reinterpret_cast<void**>(&component));break;}}
        must(component&&component->initialize(nullptr)==kResultOk,"initialize component");
        must(component->queryInterface(IAudioProcessor::iid,reinterpret_cast<void**>(&audio))==kResultOk,"IAudioProcessor");
        ProcessSetup setup{kRealtime,kSample32,1024,44100.};must(audio->setupProcessing(setup)==kResultOk,"setupProcessing");
        MemoryStream stream;encode(stream,s);must(component->setState(&stream)==kResultOk,"initial state");
        must(component->setActive(true)==kResultOk&&audio->setProcessing(true)==kResultOk,"activate");
        census=reinterpret_cast<P132ReadVoices>(GetProcAddress(module,"p132ReadVoices"));
        heapControl=reinterpret_cast<P132HeapControl>(GetProcAddress(module,"p132HeapControl"));
    }
    ~Plugin(){if(audio)audio->setProcessing(false);if(component){component->setActive(false);component->terminate();}if(audio)audio->release();if(component)component->release();if(factory)factory->release();if(module)FreeLibrary(module);}
    P132Voices voices(){P132Voices v{};if(census)must(census(audio,&v)!=0,"voice census");return v;}
    State save(){MemoryStream m;must(component->getState(&m)==kResultOk,"getState");m.seek(0,IBStream::kIBSeekSet,nullptr);State s;auto read=[&](void* p,size_t n){int32 done=0;return m.read(p,int32(n),&done)==kResultOk&&done==int32(n);};must(AWE125::AssetState::Read(read,s),"decode saved V10");return s;}
};
struct Block {
    std::array<float,1024> left{},right{};float* channels[2]{left.data(),right.data()};
    AudioBusBuffers bus{};ProcessData data{};ParameterChanges parameters{64};EventList events{64};
    explicit Block(int frames){bus.numChannels=2;bus.channelBuffers32=channels;data.processMode=kRealtime;data.symbolicSampleSize=kSample32;data.numSamples=frames;data.numOutputs=1;data.outputs=&bus;data.inputEvents=&events;data.inputParameterChanges=&parameters;}
    void note(int key){Event e{};e.type=Event::kNoteOnEvent;e.noteOn.channel=0;e.noteOn.pitch=key;e.noteOn.velocity=.85f;e.noteOn.noteId=key;must(events.addEvent(e)==kResultOk,"event");}
    void parameter(ParamID id,double value,int at=0){int32 slot=0;auto* q=parameters.addParameterData(id,slot);must(q&&q->addPoint(at,value,slot)==kResultOk,"parameter");}
    void cc(int number,double value,int at=0){auto id=AWE125::MidiControlMapping::ParamID(0,AWE125::MidiControlMapping::Index(number));parameter(id,value,at);}
};
struct Row {
    int caseId=0,pass=0,frames=0,voices=0,mode=0,index=0;const char* phase="measure";
    DWORD pid=0,tid=0,core0=0,core1=0;int64_t begin=0,end=0,due=0;ULONG64 cycles=0;
    P132Voices pre{},post{};uint64_t hash=0;double energy=0;bool clockValid=false;
};
static uint64_t pcmHash(const Block& b){uint64_t h=1469598103934665603ull;for(int i=0;i<b.data.numSamples;++i)for(float v:{b.left[i],b.right[i]}){uint32_t bits=0;std::memcpy(&bits,&v,4);for(int k=0;k<4;++k){h^=(bits>>(8*k))&255;h*=1099511628211ull;}}return h;}
static Row invoke(Plugin& p,Block& b,Row row){
    row.pid=GetCurrentProcessId();row.tid=GetCurrentThreadId();row.pre=p.voices();
    ULONG64 c0=0,c1=0;row.core0=GetCurrentProcessorNumber();BOOL ok0=QueryThreadCycleTime(GetCurrentThread(),&c0);
    row.begin=tick();auto rc=p.audio->process(b.data);row.end=tick();
    BOOL ok1=QueryThreadCycleTime(GetCurrentThread(),&c1);row.core1=GetCurrentProcessorNumber();
    must(rc==kResultOk&&row.end>=row.begin,"process/clock");row.post=p.voices();row.clockValid=ok0&&ok1&&c1>=c0;row.cycles=row.clockValid?c1-c0:0;
    row.hash=pcmHash(b);for(int i=0;i<b.data.numSamples;++i)row.energy+=double(b.left[i])*b.left[i]+double(b.right[i])*b.right[i];return row;
}
static void writeRows(const fs::path& path,const std::vector<Row>& rows,int64_t frequency){
    std::ofstream f(path);must(bool(f),"CSV open");
    f<<"case,pass,frames,voices,mode,index,phase,pid,tid,qpc_begin,qpc_end,qpc_due,qpc_hz,wall_us,budget_us,start_late_us,cycles,cycles_valid,core_before,core_after,allocated_before,allocated_after,nonzero_before,nonzero_after,envelopes_before,envelopes_after,generation_before,generation_after,pending_before,pending_after,pcm_fnv64,energy,matched\n";
    f<<std::setprecision(17);
    for(const auto& r:rows){bool matched=r.pre.allocated==r.voices&&r.post.allocated==r.voices&&r.pre.nonzero==r.voices&&r.post.nonzero==r.voices&&r.pre.generation==r.post.generation;
        f<<r.caseId<<','<<r.pass<<','<<r.frames<<','<<r.voices<<','<<r.mode<<','<<r.index<<','<<r.phase<<','<<r.pid<<','<<r.tid<<','<<r.begin<<','<<r.end<<','<<r.due<<','<<frequency<<','<<1e6*double(r.end-r.begin)/frequency<<','<<1e6*r.frames/44100.<<','<<(r.due?1e6*double(r.begin-r.due)/frequency:0)<<','<<r.cycles<<','<<r.clockValid<<','<<r.core0<<','<<r.core1<<','<<r.pre.allocated<<','<<r.post.allocated<<','<<r.pre.nonzero<<','<<r.post.nonzero<<','<<r.pre.envelopes<<','<<r.post.envelopes<<','<<r.pre.generation<<','<<r.post.generation<<','<<r.pre.pending<<','<<r.post.pending<<','<<r.hash<<','<<r.energy<<','<<matched<<'\n';}
    must(bool(f),"CSV write");
}
static void seed(Plugin& p,int n,int frames,std::vector<Row>* rows=nullptr,Row base={}){
    Block reset(0);reset.cc(120,1);for(int i=0;i<n;++i)reset.note(45+i);base.frames=0;base.phase="seed";auto row=invoke(p,reset,base);if(rows)rows->push_back(row);
    int warm=(4096+frames-1)/frames;
    for(int i=0;i<warm;++i){Block b(frames);base.frames=frames;base.phase="warmup";base.index=i;auto r=invoke(p,b,base);if(rows)rows->push_back(r);}
    if(p.census){auto v=p.voices();must(v.allocated==n&&v.nonzero==n,"warmup did not establish requested PHYSICAL voice count");}
}
static void qualify(const fs::path& normal,const fs::path& diagnostic,const fs::path& assets,const fs::path& out){
    std::ofstream f(out/"qualification.txt");
    std::ofstream timing(out/"qualification-timing.csv");timing<<"frames,voices,index,normal_wall_us,diagnostic_wall_us\n";const auto frequency=hz();
    for(int frames:{128,256,512,1024})for(int n:{1,16,30}){
        Plugin a(normal,model(assets)),b(diagnostic,model(assets));must(!a.census&&b.census,"normal/diagnostic DLL identity");seed(a,n,frames);seed(b,n,frames);
        for(int i=0;i<128;++i){Block x(frames),y(frames);int64_t a0=0,a1=0,b0=0,b1=0;
            auto runA=[&]{a0=tick();must(a.audio->process(x.data)==kResultOk,"normal qualify process");a1=tick();};
            auto runB=[&]{b0=tick();must(b.audio->process(y.data)==kResultOk,"diagnostic qualify process");b1=tick();};
            if(i%2){runB();runA();}else{runA();runB();}
            timing<<frames<<','<<n<<','<<i<<','<<1e6*double(a1-a0)/frequency<<','<<1e6*double(b1-b0)/frequency<<'\n';must(x.left==y.left&&x.right==y.right,"diagnostic instrumentation changed PCM");must(std::any_of(x.left.begin(),x.left.begin()+frames,[](float v){return v!=0;}),"qualifier unexpectedly silent");auto v=b.voices();must(v.nonzero==n&&v.allocated==n,"physical voice count changed");}
        auto sa=a.save(),sb=b.save();MemoryStream ma,mb;encode(ma,sa);encode(mb,sb);must(ma.getSize()==mb.getSize()&&std::memcmp(ma.getData(),mb.getData(),size_t(ma.getSize()))==0,"diagnostic changed V10");
        f<<"PASS frames="<<frames<<" physical_voices="<<n<<" pcm_bit_exact=1 state_v10_equal=1\n";
    }
    std::cout<<"P132_QUALIFICATION cases=12 pcm_callbacks_compared=128_each real_dll=1 PASS\n";
}
struct DelayedStream:MemoryStream {
    std::atomic<bool>* stop=nullptr;std::atomic<unsigned>* begun=nullptr;HANDLE primed=nullptr;unsigned ticket=0;bool first=true;
    tresult PLUGIN_API read(void* p,int32 n,int32* r) override {
        if(first){first=false;begun->store(ticket,std::memory_order_release);while(!stop->load()&&WaitForSingleObject(primed,50)!=WAIT_OBJECT_0){}}
        return MemoryStream::read(p,n,r);
    }
};
static void matrix(const fs::path& diagnostic,const fs::path& assets,const fs::path& out,int pass,bool memory){
    std::vector<Row> rows;rows.reserve(100000);std::ofstream cases(out/"cases.csv");
    cases<<"case,frames,voices,mode,measured_callbacks,saves,recalls,primings,control_error,thread_cpu_100ns,wall_qpc,thread_priority\n";
    const auto frequency=hz();unsigned caseId=0;
    // Calibration intervals use the same QPC domain but are NEVER real callbacks.
    {
        Plugin p(diagnostic,model(assets));must(p.heapControl,"heap positive control export");
        for(int i=0;i<2000;++i){Row r;r.phase="calibration_empty";r.pid=GetCurrentProcessId();r.tid=GetCurrentThreadId();r.begin=tick();r.end=tick();rows.push_back(r);}
        for(const char* phase:{"calibration_sleep","calibration_busy","calibration_heap"}){
            Row r;r.phase=phase;r.pid=GetCurrentProcessId();r.tid=GetCurrentThreadId();r.begin=tick();
            if(std::strcmp(phase,"calibration_sleep")==0)Sleep(20);
            else if(std::strcmp(phase,"calibration_busy")==0){volatile uint64_t sum=1;while(tick()-r.begin<frequency/50)sum=sum*1664525+1013904223;}
            else p.heapControl();r.end=tick();rows.push_back(r);
        }
    }
    std::vector<std::array<int,3>> configurations;
    for(int frames:{128,256,512,1024})for(int n:{1,16,30})for(int mode=0;mode<5;++mode)configurations.push_back({frames,n,mode});
    if(std::getenv("P132_REVERSE"))std::reverse(configurations.begin(),configurations.end());
    for(auto configuration:configurations){int frames=configuration[0],n=configuration[1],mode=configuration[2];
        if(memory&&mode!=0&&mode!=4)continue;
        Plugin p(diagnostic,model(assets));must(p.census,"diagnostic census export");
        Row base;base.caseId=++caseId;base.pass=pass;base.frames=frames;base.voices=n;base.mode=mode;
        seed(p,n,frames,&rows,base);
        std::atomic<bool> stop=false,error=false;std::atomic<unsigned> begun=0,saves=0,recalls=0;
        HANDLE primed=CreateEventW(nullptr,FALSE,FALSE,nullptr);must(primed!=nullptr,"control event");
        std::thread control;
        if(mode)control=std::thread([&]{try{unsigned iteration=0;while(!stop.load()){
            auto s=p.save();must(s.program<=127&&s.bank<=16383,"saved values");for(int ch=0;ch<16;++ch)if(!(s.channelProgramMask&(1u<<ch)))must(s.channelPrograms[ch]==s.program,"torn saved program tuple");++saves;
            if((mode==2||mode==4)&&++iteration%10==0&&!stop.load()){
                DelayedStream stream;stream.stop=&stop;stream.begun=&begun;stream.primed=primed;stream.ticket=recalls.load()+1;encode(stream,model(assets));
                auto rc=p.component->setState(&stream);must(rc==kResultOk||rc==kResultFalse,"recall result");++recalls;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(15));
        }}catch(const std::exception& e){std::cerr<<"P132_CONTROL_ERROR "<<e.what()<<std::endl;error=true;}});
        if(mode)while(saves.load()==0&&!error.load())Sleep(1); // host prelude, OUTSIDE process
        unsigned primings=0,seen=0;int count=memory?60:((frames==128&&n==30&&(mode==0||mode==1||mode==2))?3000:600);
        auto schedule=std::chrono::steady_clock::now();FILETIME create{},exit{},k0{},u0{},k1{},u1{};
        GetThreadTimes(GetCurrentThread(),&create,&exit,&k0,&u0);auto caseBegin=tick();
        for(int i=0;i<count;++i){
            unsigned ticket=begun.load(std::memory_order_acquire);
            if(ticket>seen){seed(p,n,frames,&rows,base);seen=ticket;++primings;SetEvent(primed);schedule=std::chrono::steady_clock::now()-std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(double(i)*frames/44100.));}
            auto due=schedule+std::chrono::duration_cast<std::chrono::steady_clock::duration>(std::chrono::duration<double>(double(i)*frames/44100.));
            if(!memory)std::this_thread::sleep_until(due);
            Block b(frames);
            if(mode==3){b.parameter(1002,(i%2?5.:0.)/16383.);b.parameter(1000,(i%2?9.:7.)/127.);}
            if(mode==4){for(int j=0;j<128;++j)b.cc(129,j%2?.6:.4,j*(frames-1)/127);b.cc(10,i%2?.3:.7);b.cc(1,.2);b.parameter(AWE125::MasterOutput::kParamID,.9);b.parameter(1108,.2);}
            base.index=i;base.phase=memory?"memory":"measure";base.due=tick()+int64_t(std::chrono::duration<double>(due-std::chrono::steady_clock::now()).count()*frequency);
            rows.push_back(invoke(p,b,base));
        }
        auto caseEnd=tick();GetThreadTimes(GetCurrentThread(),&create,&exit,&k1,&u1);
        stop=true;SetEvent(primed);if(control.joinable())control.join();CloseHandle(primed);
        auto ft=[](FILETIME t){return (uint64_t(t.dwHighDateTime)<<32)|t.dwLowDateTime;};
        cases<<caseId<<','<<frames<<','<<n<<','<<mode<<','<<count<<','<<saves<<','<<recalls<<','<<primings<<','<<error<<','<<ft(k1)+ft(u1)-ft(k0)-ft(u0)<<','<<caseEnd-caseBegin<<','<<GetThreadPriority(GetCurrentThread())<<'\n';
        if(error.load()||(mode!=0&&saves==0)){writeRows(out/"callbacks.csv",rows,frequency);throw std::runtime_error("control workload incomplete");}
        std::cout<<"P132_CASE id="<<caseId<<" frames="<<frames<<" voices="<<n<<" mode="<<mode<<" rows="<<count<<" saves="<<saves<<" recalls="<<recalls<<" primings="<<primings<<std::endl;
    }
    writeRows(out/"callbacks.csv",rows,frequency);
    std::ofstream info(out/"host.txt");info<<"pid="<<GetCurrentProcessId()<<"\ntid="<<GetCurrentThreadId()<<"\nqpc_hz="<<frequency<<"\nlogical_processors="<<GetActiveProcessorCount(ALL_PROCESSOR_GROUPS)<<"\nqtc_is_raw_cycles=1\nthread_times_are_case_aggregate_only=1\nasio_tested=0\n";
}
int main(int argc,char** argv){try{
    if(argc!=6)return 2;fs::path out=argv[5];fs::create_directories(out);
    moduleMap.open(out/"modules.csv");moduleMap<<"base,size,path\n";
    timeBeginPeriod(1);
    std::string mode=argv[1];if(mode=="qualify")qualify(argv[2],argv[3],argv[4],out);
    else matrix(argv[3],argv[4],out,mode=="untraced"?1:0,mode=="memory");
    timeEndPeriod(1);return 0;
}catch(const std::exception& e){std::cerr<<"P132_INCOMPLETE "<<e.what()<<std::endl;timeEndPeriod(1);return 1;}}
