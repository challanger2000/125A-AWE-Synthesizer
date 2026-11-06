// Native ETL decoder: raw QPC CSwitch intervals, target-thread heap events and
// sampled instruction pointers. No conversion of thread cycles into CPU time.
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <evntrace.h>
#include <evntcons.h>
#include <tdh.h>
#include <dbghelp.h>
#include <algorithm>
#include <cstdint>
#include <climits>
#include <cstdio>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <vector>
#pragma comment(lib,"tdh.lib")
namespace fs=std::filesystem;
static std::set<ULONG> tids;
static std::ofstream switches,profiles,heaps,schemas;
static uint64_t allEvents=0,csEvents=0,profileEvents=0,heapEvents=0;
static std::map<uint64_t,std::string> symbols;
struct Schema {bool context=false,profile=false,heap=false;std::string provider,task,opcode;};
static std::map<std::string,Schema> cache;
static std::string ascii(const wchar_t* s){std::string out;if(s)while(*s){out+=*s<128?char(*s):'?';++s;}return out;}
static std::string clean(std::string s){for(auto& c:s)if(c==','||c=='\r'||c=='\n')c=';';return s;}
static std::string key(EVENT_RECORD* r){auto& g=r->EventHeader.ProviderId;char text[160];snprintf(text,sizeof(text),"%08lx-%04x-%04x-%02x%02x%02x%02x%02x%02x%02x%02x/%u/%u/%u",g.Data1,g.Data2,g.Data3,g.Data4[0],g.Data4[1],g.Data4[2],g.Data4[3],g.Data4[4],g.Data4[5],g.Data4[6],g.Data4[7],r->EventHeader.EventDescriptor.Id,r->EventHeader.EventDescriptor.Opcode,r->EventHeader.EventDescriptor.Version);return text;}
static bool number(EVENT_RECORD* r,const wchar_t* name,uint64_t& out){
    PROPERTY_DATA_DESCRIPTOR d{};d.PropertyName=reinterpret_cast<ULONGLONG>(name);d.ArrayIndex=ULONG_MAX;
    ULONG size=0;if(TdhGetPropertySize(r,0,nullptr,1,&d,&size)!=ERROR_SUCCESS||size==0||size>8)return false;
    out=0;return TdhGetProperty(r,0,nullptr,1,&d,size,reinterpret_cast<PBYTE>(&out))==ERROR_SUCCESS;
}
static Schema& schema(EVENT_RECORD* r){
    const auto k=key(r);auto found=cache.find(k);if(found!=cache.end())return found->second;
    Schema s;ULONG n=0;TdhGetEventInformation(r,0,nullptr,nullptr,&n);std::vector<BYTE> buf(n);auto* info=reinterpret_cast<TRACE_EVENT_INFO*>(buf.data());
    if(n&&TdhGetEventInformation(r,0,nullptr,info,&n)==ERROR_SUCCESS){
        auto text=[&](ULONG offset){return offset?ascii(reinterpret_cast<wchar_t*>(buf.data()+offset)):std::string{};};
        s.provider=text(info->ProviderNameOffset);s.task=text(info->TaskNameOffset);s.opcode=text(info->OpcodeNameOffset);
        bool a=false,b=false,ip=false;std::string fields;
        for(ULONG i=0;i<info->TopLevelPropertyCount;++i){auto name=text(info->EventPropertyInfoArray[i].NameOffset);a|=name=="NewThreadId";b|=name=="OldThreadId";ip|=name=="InstructionPointer";fields+=name+";";}
        s.context=a&&b;s.profile=ip;
        s.heap=s.provider.find("Heap")!=std::string::npos||s.task.find("Heap")!=std::string::npos||s.opcode.find("Alloc")!=std::string::npos;
        schemas<<k<<','<<clean(s.provider)<<','<<clean(s.task)<<','<<clean(s.opcode)<<','<<clean(fields)<<'\n';
    }
    return cache.emplace(k,s).first->second;
}
static std::string symbol(uint64_t ip){
    auto old=symbols.find(ip);if(old!=symbols.end())return old->second;
    alignas(SYMBOL_INFO) char data[sizeof(SYMBOL_INFO)+2048]{};auto* info=reinterpret_cast<SYMBOL_INFO*>(data);info->SizeOfStruct=sizeof(SYMBOL_INFO);info->MaxNameLen=2047;DWORD64 distance=0;
    std::string name;if(SymFromAddr(GetCurrentProcess(),ip,&distance,info))name=info->Name;
    return symbols.emplace(ip,clean(name)).first->second;
}
static void WINAPI event(EVENT_RECORD* r){
    ++allEvents;auto& s=schema(r);auto time=r->EventHeader.TimeStamp.QuadPart;ULONG tid=r->EventHeader.ThreadId;
    if(s.context){
        // Kernel CSwitch v2 begins with NewThreadId and OldThreadId. TDH is
        // still authoritative; no private offsets or undocumented casts.
        uint64_t next=0,old=0;if(!number(r,L"NewThreadId",next)||!number(r,L"OldThreadId",old))return;
        if(!tids.count(ULONG(next))&&!tids.count(ULONG(old)))return;
        uint64_t state=UINT64_MAX,reason=UINT64_MAX;number(r,L"OldThreadState",state);number(r,L"OldThreadWaitReason",reason);
        switches<<time<<','<<r->BufferContext.ProcessorNumber<<','<<old<<','<<next<<','<<state<<','<<reason<<'\n';++csEvents;
    }
    uint64_t payloadTid=tid;if(!tids.count(tid)){if(!number(r,L"ThreadId",payloadTid)||!tids.count(ULONG(payloadTid)))return;}
    if(s.profile){uint64_t ip=0;if(number(r,L"InstructionPointer",ip)){profiles<<time<<','<<payloadTid<<','<<r->BufferContext.ProcessorNumber<<','<<ip<<','<<symbol(ip)<<'\n';++profileEvents;}}
    if(s.heap){uint64_t size=0,address=0;bool sized=number(r,L"AllocationSize",size)||number(r,L"AllocSize",size)||number(r,L"NewSize",size)||number(r,L"Size",size);number(r,L"BaseAddress",address)||number(r,L"AllocationBase",address)||number(r,L"Address",address);
        heaps<<time<<','<<payloadTid<<','<<key(r)<<','<<clean(s.task)<<','<<clean(s.opcode)<<','<<sized<<','<<size<<','<<address<<'\n';++heapEvents;}
}
static std::vector<std::string> split(const std::string& s){std::vector<std::string> v;std::stringstream f(s);std::string p;while(std::getline(f,p,','))v.push_back(p);return v;}
int wmain(int argc,wchar_t** argv){
    if(argc!=5)return 2;fs::path etl=argv[1],rows=argv[2],modules=argv[3],out=argv[4];fs::create_directories(out);
    std::ifstream f(rows);std::string line;std::getline(f,line);while(std::getline(f,line)){auto v=split(line);if(v.size()>8)tids.insert(ULONG(std::stoul(v[8])));}
    switches.open(out/"cswitch.csv");switches<<"qpc,cpu,old_tid,new_tid,old_state,old_wait_reason\n";
    profiles.open(out/"samples.csv");profiles<<"qpc,tid,cpu,ip,symbol\n";
    heaps.open(out/"heap.csv");heaps<<"qpc,tid,event,task,opcode,size_valid,size,address\n";
    schemas.open(out/"schemas.csv");schemas<<"key,provider,task,opcode,fields\n";
    SymSetOptions(SYMOPT_DEFERRED_LOADS|SYMOPT_UNDNAME|SYMOPT_LOAD_LINES);SymInitialize(GetCurrentProcess(),nullptr,FALSE);
    std::ifstream mod(modules);std::getline(mod,line);std::set<uint64_t> bases;
    while(std::getline(mod,line)){auto v=split(line);if(v.size()<3)continue;auto base=std::stoull(v[0]);if(bases.insert(base).second)SymLoadModuleEx(GetCurrentProcess(),nullptr,v[2].c_str(),nullptr,base,DWORD(std::stoul(v[1])),nullptr,0);}
    EVENT_TRACE_LOGFILEW trace{};trace.LogFileName=const_cast<LPWSTR>(etl.c_str());trace.ProcessTraceMode=PROCESS_TRACE_MODE_EVENT_RECORD|PROCESS_TRACE_MODE_RAW_TIMESTAMP;trace.EventRecordCallback=event;
    TRACEHANDLE h=OpenTraceW(&trace);if(h==INVALID_PROCESSTRACE_HANDLE){std::cerr<<"OpenTrace error "<<GetLastError()<<'\n';return 1;}
    auto rc=ProcessTrace(&h,1,nullptr,nullptr);CloseTrace(h);SymCleanup(GetCurrentProcess());
    std::ofstream meta(out/"trace-meta.json");meta<<"{\"process_trace_result\":"<<rc<<",\"events_lost\":"<<trace.LogfileHeader.EventsLost<<",\"buffers_lost\":"<<trace.LogfileHeader.BuffersLost<<",\"perf_frequency\":"<<trace.LogfileHeader.PerfFreq.QuadPart<<",\"events\":"<<allEvents<<",\"target_cswitch\":"<<csEvents<<",\"target_samples\":"<<profileEvents<<",\"target_heap\":"<<heapEvents<<"}\n";
    std::cout<<"P135_ETW decoded="<<allEvents<<" target_cswitch="<<csEvents<<" target_samples="<<profileEvents<<" target_heap="<<heapEvents<<" result="<<rc<<'\n';return rc==ERROR_SUCCESS?0:1;
}
