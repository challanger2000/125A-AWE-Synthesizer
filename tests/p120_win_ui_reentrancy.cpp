#include "WinUiDispatch.h"
#include <atomic>
#include <chrono>
#include <iostream>
#include <memory>
#include <thread>
struct FakeController {
    AWE125::WinUiDispatch dispatch;
    std::atomic<int>* destroyed=nullptr;
    std::atomic<int>* hostCallbacks=nullptr;
    int refs=1;
    explicit FakeController(std::atomic<int>* d,std::atomic<int>* cb)
      : destroyed(d),hostCallbacks(cb) {}
    ~FakeController(){destroyed->fetch_add(1);}
    void retain(){++refs;}
    void release(){if(--refs==0)delete this;}
    static void Retain(void* ctx){static_cast<FakeController*>(ctx)->retain();}
    static void Release(void* ctx){static_cast<FakeController*>(ctx)->release();}
    static bool Callback(void* ctx) {
        auto* owner=static_cast<FakeController*>(ctx);
        owner->hostCallbacks->fetch_add(1);
        // Simulate host synchronously dropping the LAST external reference
        // INSIDE restartComponent(). The dispatcher holds its own reference
        // and must finish timer bookkeeping before deleting the owner.
        owner->release();
        return false;
    }
};
int main() {
    std::atomic<int> destroyed{0},hostCalls{0};
    auto* owner=new FakeController(&destroyed,&hostCalls);
    if(!owner->dispatch.Start(owner,&FakeController::Callback,
                              GetModuleHandleW(nullptr),
                              &FakeController::Retain,&FakeController::Release)) {
        delete owner;
        std::cerr<<"P120_WIN_UI_REENTRANCY_FAIL (Start)\n";
        return 1;
    }
    const auto uiThread=GetCurrentThreadId();
    std::thread producer([&]{owner->dispatch.Post();});
    producer.join();
    const auto deadline=std::chrono::steady_clock::now()+
                        std::chrono::seconds(3);
    while(destroyed.load()==0 &&
          std::chrono::steady_clock::now()<deadline) {
        MSG msg{};
        while(PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)) {
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
    // owner was deleted during a nested message callback; do not use again.
    const bool ok=uiThread==GetCurrentThreadId()&&
                  destroyed.load()==1&&hostCalls.load()==1;
    std::cout<<(ok?"P120_WIN_UI_REENTRANCY_PASS":"P120_WIN_UI_REENTRANCY_FAIL")
             <<" deleted="<<destroyed.load()
             <<" calls="<<hostCalls.load()<<"\n";
    return ok?0:1;
}
