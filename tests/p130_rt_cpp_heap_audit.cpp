// P130 AUDIT ONLY. Compile the actual production Steinberg Processor in the
// existing SDK harness. Count C++ operator new / new[] calls made strictly
// inside process() on the calling audio thread, not setup/host event builders.
// This does not count malloc/realloc, OS heap, or other threads: never
// represent it as an exhaustive realtime memory instrumentation.
#define main p128_unused_main_for_alloc_probe
#include "p128_processor_order.cpp"
#undef main
#include <cstdlib>
#include <new>
#include <atomic>
#include <iomanip>

static thread_local bool p130CountAlloc=false;
static thread_local uint64_t p130NewCalls=0;
static thread_local uint64_t p130NewBytes=0;
void* operator new(std::size_t n) {
    if(p130CountAlloc) {
        ++p130NewCalls;
        p130NewBytes+=n;
    }
    if(void* p=std::malloc(n?n:1))return p;
    throw std::bad_alloc();
}
void* operator new[](std::size_t n) {
    if(p130CountAlloc) {
        ++p130NewCalls;
        p130NewBytes+=n;
    }
    if(void* p=std::malloc(n?n:1))return p;
    throw std::bad_alloc();
}
void operator delete(void* p) noexcept {std::free(p);}
void operator delete[](void* p) noexcept {std::free(p);}
void operator delete(void* p,std::size_t) noexcept {std::free(p);}
void operator delete[](void* p,std::size_t) noexcept {std::free(p);}

struct CountGuard {
    CountGuard() {p130CountAlloc=true;}
    ~CountGuard(){p130CountAlloc=false;}
};
int main(int argc,char** argv) {
    try {
        if(argc!=2)return 2;
        assetsDir=std::filesystem::path(argv[1]);
        constexpr int cases=5, repeats=240;
        uint64_t grandNew=0,grandBytes=0;
        for(int test=0;test<cases;++test) {
            Rig rig;
            // All host events and memory are prepared BEFORE entering
            // process() scope. Use real active ROM/SF2 and audible voices.
            int audioBlocks=0;
            uint64_t calls=0,bytes=0;
            for(int i=0;i<repeats;++i) {
                Block block(1024);
                if(test==1) {
                    if(i%8==0)for(int n=0;n<4;++n)
                        block.note(0,48+n,0,true);
                } else if(test==2) {
                    for(int n=0;n<30;++n)
                        block.note(0,45+n,0,true);
                } else if(test==3) {
                    // MIDI, program and two GUI automation events.
                    if(i%4==0)block.note(0,60,128,true);
                    block.param(kVolumeID,0.6,32);
                    block.param(kGuiFirstID,0.4,64);
                    block.param(kProgramID,9./127.,96);
                    block.param(MidiProgramRouting::ParamID(3),7./127.,256);
                } else if(test==4) {
                    // 128 closely spaced host Pitch Bend points each
                    // callback. This exercises the real pitch curve and
                    // live voice-update path without host-side allocations.
                    if(i%4==0)block.note(0,60,0,true);
                    for(int n=0;n<128;++n)
                        block.param(MidiControlMapping::ParamID(0,
                            MidiControlMapping::Index(129)),(n&1)?0.1:0.9,n*8);
                }
                const auto beforeCalls=p130NewCalls;
                const auto beforeBytes=p130NewBytes;
                tresult rc;
                {
                    CountGuard mark;
                    rc=rig.p->process(block.data);
                }
                require(rc==kResultOk,"production processor rejected callback");
                calls+=p130NewCalls-beforeCalls;
                bytes+=p130NewBytes-beforeBytes;
                bool audible=false;
                for(int frame=0;frame<1024&&!audible;++frame)
                    audible=block.l[frame]!=0.f||block.r[frame]!=0.f;
                audioBlocks+=audible;
            }
            if(test!=0)
                require(audioBlocks>=160,"test case unexpectedly silent");
            grandNew+=calls;
            grandBytes+=bytes;
            std::cout<<"P130_AUDIO_HEAP case="<<
                (test==0?"silent":test==1?"held_notes":test==2?"30_retriggered_notes":
                 test==3?"program_gui_events":"dense_pitchbend")
                <<" callbacks="<<repeats
                <<" audible_callbacks="<<audioBlocks
                <<" operator_new_calls="<<calls
                <<" operator_new_bytes="<<bytes
                <<" scope=PROCESS_THREAD_CPP_OPERATOR_NEW_ONLY\n";
        }
        std::cout<<"P130_AUDIO_HEAP_RESULT callbacks="<<(cases*repeats)
            <<" new_calls="<<grandNew<<" new_bytes="<<grandBytes
            <<" UNCOVERED=CRT_malloc_OS_allocations_secondary_threads\n";
        return grandNew==0?0:1;
    } catch(const std::exception& e) {
        p130CountAlloc=false;
        std::cerr<<"P130_AUDIT_FAILURE "<<e.what()<<'\n';
        return 2;
    }
}
