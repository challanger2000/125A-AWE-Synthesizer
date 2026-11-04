#include "pluginterfaces/base/ipluginbase.h"
#include "pluginterfaces/vst/ivsteditcontroller.h"
#include "pluginterfaces/vst/ivstunits.h"
#include "pluginterfaces/vst/ivsttypes.h"
#include <windows.h>
#include <cmath>
#include <cstring>
#include <iostream>
using namespace Steinberg;
using namespace Steinberg::Vst;

static bool check(bool pass,const char* what) {
    std::cout<<(pass?"PASS: ":"FAIL: ")<<what<<"\n";return pass;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 2;
    const HMODULE module=LoadLibraryW(argv[1]);
    if(!module){std::cerr<<"P120 VST3 DLL could not be loaded\n";return 2;}
    using FactoryFn=IPluginFactory*(*)();
    auto getFactory=reinterpret_cast<FactoryFn>(
        GetProcAddress(module,"GetPluginFactory"));
    if(!getFactory){FreeLibrary(module);return 2;}
    IPluginFactory* factory=getFactory();
    if(!factory){FreeLibrary(module);return 2;}
    IEditController* controller=nullptr;
    for(int32 i=0;i<factory->countClasses();++i) {
        PClassInfo info{};
        if(factory->getClassInfo(i,&info)!=kResultOk)continue;
        if(std::strcmp(info.category,kVstComponentControllerClass)!=0)continue;
        if(factory->createInstance(info.cid,IEditController::iid,
                reinterpret_cast<void**>(&controller))==kResultOk)
            break;
    }
    bool ok=check(controller!=nullptr,
        "real VST3 controller instantiates through exported factory");
    if(controller) {
        const tresult init=controller->initialize(nullptr);
        ok &=check(init==kResultOk,
            "controller initializes with real SDK");
        IUnitInfo* units=nullptr;
        ok &=check(controller->queryInterface(IUnitInfo::iid,
            reinterpret_cast<void**>(&units))==kResultOk && units,
            "IUnitInfo is exposed");
        if(units) {
            ok &=check(units->getUnitCount()==17,
                "one root Unit plus 16 MIDI channel Units");
            ok &=check(units->getProgramListCount()==16,
                "16 program lists are exported");
            bool unitOk=true,listsOk=true;
            for(int ch=0;ch<16;++ch) {
                UnitID unit=-1;
                if(units->getUnitByBus(kEvent,kInput,0,ch,unit)!=kResultOk
                    ||unit!=ch+1)unitOk=false;
                ProgramListInfo list{};
                if(units->getProgramListInfo(ch,list)!=kResultOk ||
                   list.programCount!=128 || list.id!=ch+1)
                    listsOk=false;
            }
            ok &=check(unitOk,
                "getUnitByBus maps all 16 actual event channels to distinct Units");
            ok &=check(listsOk,
                "ProgramList metadata contains 128 programs per channel");
            units->release();
        }
        bool paramsOk=true;
        for(int ch=0;ch<16;++ch) {
            ParameterInfo pi{};
            bool found=false;
            for(int32 i=0;i<controller->getParameterCount();++i) {
                if(controller->getParameterInfo(i,pi)==kResultOk
                    && pi.id==static_cast<ParamID>(3000+ch)) {
                    found=true;break;
                }
            }
            if(!found||pi.unitId!=ch+1||pi.stepCount!=127||
               !(pi.flags&ParameterInfo::kIsProgramChange)||
               !(pi.flags&ParameterInfo::kCanAutomate))
                paramsOk=false;
        }
        ok &=check(paramsOk,
            "all 16 channel Program parameters are automatable, discrete and kIsProgramChange");
        const auto global=42./127.;
        ok &=check(controller->setParamNormalized(1000,global)==kResultOk,
            "legacy GUI Program parameter remains operational");
        bool globalSync=true;
        for(int ch=0;ch<16;++ch)
            if(std::abs(controller->getParamNormalized(
                static_cast<ParamID>(3000+ch))-global)>1e-8)
                globalSync=false;
        ok &=check(globalSync,
            "legacy GUI-wide program selection updates every controller channel");
        ok &=check(controller->setParamNormalized(3001,7./127.)==kResultOk &&
                  std::abs(controller->getParamNormalized(3000)-global)<1e-8 &&
                  std::abs(controller->getParamNormalized(3001)-7./127.)<1e-8,
                  "channel 2 Program Change does not alter channel 1");
        controller->terminate();
        controller->release();
    }
    factory->release();
    FreeLibrary(module);
    std::cout<<(ok?"P120_VST3_PROGRAM_HOST_PASS":"P120_VST3_PROGRAM_HOST_FAIL")<<"\n";
    return ok?0:1;
}
