#include "WinUiDispatch.h"
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
struct State {
    std::atomic<int> deliveries{0};
    std::atomic<DWORD> callbackThread{0};
};
static bool Deliver(void* p) {
    auto& s=*static_cast<State*>(p);
    s.callbackThread.store(GetCurrentThreadId());
    return s.deliveries.fetch_add(1)==0; // retry once via hidden WM_TIMER
}
int main() {
    State s;
    AWE125::WinUiDispatch dispatch;
    const DWORD uiThread=GetCurrentThreadId();
    bool ok=dispatch.Start(&s,&Deliver,GetModuleHandleW(nullptr));
    if(!ok){std::cerr<<"FAIL: hidden Windows UI dispatcher initialization\n";return 1;}
    std::thread worker([&] {dispatch.Post();});
    worker.join();
    auto until=std::chrono::steady_clock::now()+std::chrono::seconds(3);
    while(s.deliveries.load()<2 && std::chrono::steady_clock::now()<until) {
        MSG msg{};
        while(PeekMessageW(&msg,nullptr,0,0,PM_REMOVE)){
            TranslateMessage(&msg);
            DispatchMessageW(&msg);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    ok=s.deliveries.load()>=2 && s.callbackThread.load()==uiThread;
    std::cout<<(ok?"P119_HOST_UI_DISPATCH_PASS":"P119_HOST_UI_DISPATCH_FAIL")
             <<" deliveries="<<s.deliveries.load()<<"\n";
    return ok?0:1;
}
