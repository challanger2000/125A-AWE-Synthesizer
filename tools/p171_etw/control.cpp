// Audit-only sleep/busy ETW positive controls, never linked into the plugin.
#include <windows.h>
#include <fstream>
#include <filesystem>
#include <iomanip>
#include <cstdint>
int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 2;
    std::ofstream out{std::filesystem::path(argv[1])};if(!out)return 2;
    out<<"phase,qpc_start,qpc_end,qpc_frequency,pid,tid\n";
    LARGE_INTEGER f{};QueryPerformanceFrequency(&f);
    volatile uint64_t value=17;
    for(int n=0;n<4;++n) {
        LARGE_INTEGER a{},b{};QueryPerformanceCounter(&a);
        if(n%2)Sleep(30);
        else do { value=value*1664525+1013904223;QueryPerformanceCounter(&b); }
             while(b.QuadPart-a.QuadPart<f.QuadPart*30/1000);
        QueryPerformanceCounter(&b);
        out<<(n%2?"sleep":"busy")<<','<<a.QuadPart<<','<<b.QuadPart<<','<<f.QuadPart
           <<','<<GetCurrentProcessId()<<','<<GetCurrentThreadId()<<'\n';
    }
    return out?0:2;
}
