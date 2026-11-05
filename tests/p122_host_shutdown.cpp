#include "HostNotificationRetry.h"
#include "WinUiDispatch.h"
#include <windows.h>
#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
using namespace AWE125;
static bool check(bool yes,const char* what) {
    std::cout<<(yes?"PASS: ":"FAIL: ")<<what<<"\n";
    return yes;
}
struct Receiver {
    std::atomic<int> callbacks{0};
    static bool RetryForever(void* ctx) {
        static_cast<Receiver*>(ctx)->callbacks.fetch_add(1);
        return true; // pending latency event: dispatcher will arm a timer
    }
};
static void PumpFor(std::chrono::milliseconds duration) {
    auto end=std::chrono::steady_clock::now()+duration;
    while(std::chrono::steady_clock::now()<end) {
        MSG message{};
        while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)) {
            TranslateMessage(&message);
            DispatchMessageW(&message);
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
}
int main() {
    bool ok=true;
    HostNotificationRetry retries;
    ok&=check(retries.ShouldRetry(5,false) &&
              retries.ShouldRetry(5,false) &&
              !retries.ShouldRetry(5,false),
              "rejected restartComponent stops after three attempts");
    ok&=check(retries.ShouldRetry(6,false) &&
              !retries.ShouldRetry(6,true),
              "new status generation retries independently and success clears pending");
    ok&=check(retries.ShouldRetry(7,false) &&
              retries.ShouldRetry(7,false) &&
              !retries.ShouldRetry(7,false),
              "a second rejecting generation is bounded");
    Receiver owner;
    {
        WinUiDispatch dispatch;
        ok&=check(dispatch.Start(&owner,&Receiver::RetryForever,
                        GetModuleHandleW(nullptr)),
                  "persistent UI dispatcher starts");
        std::thread worker([&] {dispatch.Post();});
        worker.join();
        PumpFor(std::chrono::milliseconds(100));
        ok&=check(owner.callbacks.load()==1,
                  "one pending ACK callback arms retry timer");
        // Destroy on the owning UI thread *with* a pending retry timer.
    }
    const int before=owner.callbacks.load();
    PumpFor(std::chrono::milliseconds(650));
    ok&=check(owner.callbacks.load()==before,
              "closing controller cancels pending restart timer and callbacks");
    std::cout<<(ok?"P122_HOST_SHUTDOWN_PASS":"P122_HOST_SHUTDOWN_FAIL")<<"\n";
    return ok?0:1;
}
