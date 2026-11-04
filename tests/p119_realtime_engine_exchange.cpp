#include "RealtimeEngineExchange.h"
#include <atomic>
#include <chrono>
#include <iostream>
#include <memory>
#include <thread>
struct Engine {
    int id=0;
    std::atomic<int>* destroyed=nullptr;
    ~Engine(){if(destroyed)destroyed->fetch_add(1);}
};
static bool check(bool ok,const char* label) {
    std::cout<<(ok?"PASS: ":"FAIL: ")<<label<<"\n";return ok;
}
int main() {
    std::atomic<int> destroyed{0};
    bool ok=true;
    {
        AWE125::RealtimeEngineExchange<Engine> slot;
        auto initial=std::make_unique<Engine>();
        initial->id=1;initial->destroyed=&destroyed;
        slot.Publish(std::move(initial));
        std::atomic<bool> readerStarted{false};
        std::atomic<bool> readerDone{false};
        std::thread reader([&] {
            auto view=slot.Read();
            readerStarted.store(true,std::memory_order_release);
            for(int k=0;k<180000;++k) {
                if(!view||view->id!=1)std::terminate();
                if(k%4000==0)std::this_thread::yield();
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(80));
            readerDone.store(true,std::memory_order_release);
        });
        while(!readerStarted.load(std::memory_order_acquire))
            std::this_thread::yield();
        auto next=std::make_unique<Engine>();next->id=2;next->destroyed=&destroyed;
        const auto start=std::chrono::steady_clock::now();
        slot.Publish(std::move(next));
        const auto elapsed=std::chrono::steady_clock::now()-start;
        ok&=check(elapsed<std::chrono::milliseconds(20),
           "control thread publishes engine without waiting 80 ms for audio read");
        ok&=check(destroyed.load()==0 && slot.RetiredCountForTest()==1,
           "old active engine is retained while an audio callback uses it");
        {
            auto current=slot.Read();
            ok&=check(current&&current->id==2,
                "new audio callback obtains committed replacement without lock");
        }
        reader.join();
        slot.Collect();
        ok&=check(destroyed.load()==1&&slot.RetiredCountForTest()==0,
            "old engine destroyed on control thread after audio callback exits");
        slot.Publish(nullptr);
        // P120 reclamation is intentionally asynchronous and occurs off the
        // audio callback. Never assert synchronous destruction at Publish().
        const auto deadline=std::chrono::steady_clock::now()+
                            std::chrono::seconds(2);
        while(destroyed.load()!=2 &&
              std::chrono::steady_clock::now()<deadline)
            std::this_thread::sleep_for(std::chrono::milliseconds(2));
        ok&=check(destroyed.load()==2,
           "retired engine is autonomously destroyed on non-audio thread");
    }
    std::cout<<(ok?"P119_ENGINE_EXCHANGE_PASS":"P119_ENGINE_EXCHANGE_FAIL")<<"\n";
    return ok?0:1;
}
