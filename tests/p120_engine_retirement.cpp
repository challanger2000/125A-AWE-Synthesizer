#include "RealtimeEngineExchange.h"
#include <atomic>
#include <chrono>
#include <iostream>
#include <future>
#include <algorithm>
#include <memory>
#include <thread>
struct Engine {
    unsigned id=0;
    std::atomic<unsigned>* destroyed=nullptr;
    std::atomic<unsigned>* wrongThread=nullptr;
    std::thread::id audioThread{};
    ~Engine() {
        if(std::this_thread::get_id()==audioThread)
            wrongThread->fetch_add(1);
        destroyed->fetch_add(1);
    }
};
int main() {
    constexpr unsigned kSwaps=1000;
    std::atomic<unsigned> destroyed{0},wrongThread{0};
    std::atomic<unsigned> ready{0},advance{0},finished{0};
    std::promise<std::thread::id> announced;
    auto audioId=announced.get_future();
    std::atomic<bool> initialized{false};
    AWE125::RealtimeEngineExchange<Engine> exchange;
    std::thread audio([&] {
        announced.set_value(std::this_thread::get_id());
        while(!initialized.load(std::memory_order_acquire))
            std::this_thread::yield();
        for(unsigned i=1;i<=kSwaps;++i) {
            {
                auto guard=exchange.Read();
                if(!guard||guard->id!=i)std::terminate();
                ready.store(i,std::memory_order_release);
                while(advance.load(std::memory_order_acquire)<i)
                    std::this_thread::yield();
            }
            finished.store(i,std::memory_order_release);
        }
    });
    const auto audioThread=audioId.get();
    auto make=[&](unsigned id) {
        auto p=std::make_unique<Engine>();
        p->id=id;p->destroyed=&destroyed;p->wrongThread=&wrongThread;
        p->audioThread=audioThread;
        return p;
    };
    exchange.Publish(make(1));
    initialized.store(true,std::memory_order_release);
    unsigned maxRetired=0;
    for(unsigned i=1;i<=kSwaps;++i) {
        while(ready.load(std::memory_order_acquire)<i)
            std::this_thread::yield();
        exchange.Publish(make(i+1));  // retiring engine i DURING its reader
        maxRetired=std::max<unsigned>(maxRetired,
            static_cast<unsigned>(exchange.RetiredCountForTest()));
        advance.store(i,std::memory_order_release);
        while(finished.load(std::memory_order_acquire)<i)
            std::this_thread::yield();
    }
    audio.join();
    const auto deadline=std::chrono::steady_clock::now()+
                         std::chrono::seconds(5);
    // No Collect() or extra Publish() call. The collector must wake itself.
    while(destroyed.load()<kSwaps &&
          std::chrono::steady_clock::now()<deadline)
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    const bool released=destroyed.load()==kSwaps &&
        exchange.RetiredCountForTest()==0;
    const bool bounded=maxRetired<=exchange.kRetiredLimit;
    const bool safeThread=wrongThread.load()==0;
    std::cout<<"P120 retention: retired_peak="<<maxRetired
             <<" destroyed="<<destroyed.load()
             <<" releases_on_audio_thread="<<wrongThread.load()<<"\n";
    const bool ok=released&&bounded&&safeThread;
    std::cout<<(ok?"P120_ENGINE_RETIREMENT_PASS":"P120_ENGINE_RETIREMENT_FAIL")<<"\n";
    return ok?0:1;
}
