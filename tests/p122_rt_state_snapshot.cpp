#include "RealtimeStateVersion.h"
#include <array>
#include <atomic>
#include <cstdint>
#include <iostream>
#include <thread>

using namespace AWE125;

int main() {
    RealtimeStateVersion version;
    std::array<std::atomic<uint32_t>,16> programs{};
    std::atomic<uint32_t> bank{0}, globalProgram{0}, mask{0};
    std::atomic<bool> start{false}, audioDidWork{false};
    std::atomic<bool> bad{false};
    constexpr int kIterations=30000;

    // Unlike the old P122 test, these workers mutate the SAME fields. Merely
    // having separate audio/control epochs did not prevent a stable final
    // mixture; control recall must publish a complete transaction.
    auto writeTuple=[&](uint32_t value) {
        globalProgram.store(value,std::memory_order_release);
        bank.store(value,std::memory_order_release);
        mask.store(0,std::memory_order_release);
        for(auto& p:programs)p.store(value,std::memory_order_release);
    };
    std::thread audio([&] {
        while(!start.load(std::memory_order_acquire))std::this_thread::yield();
        for(int i=0;i<kIterations;++i) {
            RealtimeStateVersion::Writer w(version,RealtimeStateVersion::Domain::Audio);
            if(w) {writeTuple(7);audioDidWork.store(true);}
        }
    });
    std::thread control([&] {
        while(!start.load(std::memory_order_acquire))std::this_thread::yield();
        for(int i=0;i<kIterations;++i) {
            RealtimeStateVersion::Writer w(version,RealtimeStateVersion::Domain::Control);
            writeTuple(9);
        }
    });
    start.store(true,std::memory_order_release);
    int coherent=0;
    for(int i=0;i<100000;++i) {
        const auto stamp=version.Capture();
        if(!version.Readable(stamp))continue;
        const uint32_t gp=globalProgram.load(std::memory_order_acquire);
        const uint32_t b=bank.load(std::memory_order_acquire);
        const uint32_t m=mask.load(std::memory_order_acquire);
        std::array<uint32_t,16> channels{};
        for(int c=0;c<16;++c)
            channels[c]=programs[c].load(std::memory_order_acquire);
        if(!version.Unchanged(stamp))continue;
        ++coherent;
        if(gp!=b || m!=0)bad.store(true);
        for(const auto c:channels)if(c!=gp)bad.store(true);
    }
    audio.join();
    control.join();
    const auto end=version.Capture();
    uint32_t final=globalProgram.load();
    bool ok=audioDidWork.load() && !bad.load() && final==bank.load() &&
        version.Unchanged(end) && version.Readable(end);
    for(const auto& p:programs)if(p.load()!=final)ok=false;

    // A real audio callback can be rendering for milliseconds without
    // touching persistent state. Do NOT guard its entire duration. During
    // this ordinary playback scenario, every one of 500 save snapshots
    // must be available, even with no program automation.
    std::atomic<bool> rendering{true};
    std::thread ordinaryPlayback([&] {
        for(int i=0;i<5000;++i)std::this_thread::yield();
        rendering.store(false,std::memory_order_release);
    });
    int saves=0;
    for(int i=0;i<500;++i) {
        for(int attempt=0;attempt<4096;++attempt) {
            const auto s=version.Capture();
            if(version.Readable(s) && version.Unchanged(s)) {
                ++saves;
                break;
            }
        }
    }
    ordinaryPlayback.join();
    ok &= saves==500;
    std::cout<<(ok?"P122_REALTIME_SNAPSHOT_PASS":"P122_REALTIME_SNAPSHOT_FAIL")
             <<" coherent_reads="<<coherent<<" successful_saves="<<saves
             <<" final_program="<<final<<"\n";
    return ok?0:1;
}
