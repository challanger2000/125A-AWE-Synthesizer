#include "RealtimeStateVersion.h"
#include <array>
#include <atomic>
#include <cstdint>
#include <iostream>
#include <thread>
using namespace AWE125;
int main() {
    RealtimeStateVersion version;
    std::array<std::atomic<uint32_t>,16> program{};
    std::array<std::atomic<uint32_t>,4> recall{};
    std::atomic<bool> start{false};
    std::thread audio([&] {
        while(!start.load(std::memory_order_acquire))std::this_thread::yield();
        for(uint32_t generation=1;generation<=20000;++generation) {
            RealtimeStateVersion::Writer write(version.Audio());
            for(auto& v:program)v.store(generation,std::memory_order_release);
        }
    });
    std::thread control([&] {
        while(!start.load(std::memory_order_acquire))std::this_thread::yield();
        for(uint32_t generation=1;generation<=20000;++generation) {
            RealtimeStateVersion::Writer write(version.Control());
            for(auto& v:recall)v.store(generation,std::memory_order_release);
        }
    });
    start.store(true,std::memory_order_release);
    int consistent=0;
    bool ok=true;
    for(int attempt=0;attempt<100000;++attempt) {
        const auto before=version.Capture();
        if(!version.Readable(before))continue;
        std::array<uint32_t,16> p{};
        std::array<uint32_t,4> r{};
        for(size_t i=0;i<p.size();++i)p[i]=program[i].load(std::memory_order_acquire);
        for(size_t i=0;i<r.size();++i)r[i]=recall[i].load(std::memory_order_acquire);
        if(!version.Unchanged(before))continue;
        ++consistent;
        for(auto v:p)if(v!=p[0])ok=false;
        for(auto v:r)if(v!=r[0])ok=false;
    }
    audio.join();
    control.join();
    // Verify a stable final snapshot, even on heavily contended runners.
    const auto end=version.Capture();
    ok &= version.Unchanged(end) && version.Readable(end);
    ok &= program[0].load()==20000 && program[15].load()==20000;
    ok &= recall[0].load()==20000 && recall[3].load()==20000;
    std::cout<<(ok?"P122_REALTIME_SNAPSHOT_PASS":"P122_REALTIME_SNAPSHOT_FAIL")
             <<" coherent_reads="<<consistent<<"\n";
    return ok?0:1;
}
