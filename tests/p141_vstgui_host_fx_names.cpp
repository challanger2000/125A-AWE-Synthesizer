// P141: actual exported Windows VST3 controller, not a source-grep.
// The DAW must see all 16 Creative FX labels, the same discrete 0..7 IDs
// as our hardware COptionMenu and save/recall (old defaults untouched).
#include "pluginterfaces/base/ipluginbase.h"
#include "pluginterfaces/vst/ivsteditcontroller.h"
#include "pluginterfaces/vst/vsttypes.h"
#include <windows.h>
#include <array>
#include <cmath>
#include <cstring>
#include <iostream>
#include <string>
using namespace Steinberg;
using namespace Steinberg::Vst;
static bool check(bool cond,const char* why) {
    std::cout<<(cond?"PASS: ":"FAIL: ")<<why<<"\n";return cond;
}
int wmain(int argc,wchar_t** argv) {
    if(argc!=2)return 2;
    const HMODULE module=LoadLibraryW(argv[1]);
    if(!module)return 2;
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
            reinterpret_cast<void**>(&controller))==kResultOk)break;
    }
    bool ok=check(controller!=nullptr,"P141 actual VST3 FX edit controller exists");
    if(controller) {
        ok &=check(controller->initialize(nullptr)==kResultOk,
                  "P141 actual controller initialized");
        constexpr std::array<const char*,8> reverb={
            "Room 1","Room 2","Room 3","Hall 1","Hall 2",
            "Plate","Delay","Panning Delay"};
        constexpr std::array<const char*,8> chorus={
            "Chorus 1","Chorus 2","Chorus 3","Chorus 4",
            "Feedback","Flanger","Short Delay","Short Delay + FB"};
        for(unsigned fx=0;fx<2;++fx) {
            const ParamID id=fx==0?1200:1201;
            const auto& names=fx==0?reverb:chorus;
            bool metadata=false,allRoundTrips=true,autovalues=true;
            for(int32 n=0;n<controller->getParameterCount();++n) {
                ParameterInfo pi{};
                if(controller->getParameterInfo(n,pi)==kResultOk&&pi.id==id) {
                    metadata=pi.stepCount==7
                        && (pi.flags&ParameterInfo::kCanAutomate)!=0
                        && std::abs(pi.defaultNormalizedValue-
                            double(fx==0?4:2)/7.)<1e-8;
                    break;
                }
            }
            ok &=check(metadata,fx==0?
                "Reverb hardware selector keeps original Hall 2 default/automation":
                "Chorus hardware selector keeps original Chorus 3 default/automation");
            for(unsigned choice=0;choice<8;++choice) {
                String128 out{};
                const double norm=double(choice)/7.;
                if(controller->getParamStringByValue(id,norm,out)!=kResultOk) {
                    allRoundTrips=false;continue;
                }
                std::string text;
                for(int i=0;i<128&&out[i];++i) {
                    if(out[i]>127){allRoundTrips=false;break;}
                    text.push_back(static_cast<char>(out[i]));
                }
                ParamValue decoded=-1.;
                if(text!=names[choice] ||
                   controller->getParamValueByString(id,out,decoded)!=kResultOk ||
                   std::abs(decoded-norm)>1e-8)allRoundTrips=false;
                if(controller->setParamNormalized(id,norm)!=kResultOk ||
                   std::abs(controller->getParamNormalized(id)-norm)>1e-8)
                    autovalues=false;
            }
            ok &=check(allRoundTrips,fx==0?
                "P141 all eight Reverb names roundtrip UTF-16 host to normalized index":
                "P141 all eight Chorus names roundtrip UTF-16 host to normalized index");
            ok &=check(autovalues,fx==0?
                "P141 all eight Reverb host parameter values accepted":
                "P141 all eight Chorus host parameter values accepted");
            String128 invalid{};
            const char* fake="Missing FX";
            for(int i=0;fake[i];++i)invalid[i]=fake[i];
            ParamValue ignored=-1.;
            ok &=check(controller->getParamValueByString(id,invalid,ignored)!=kResultOk,
                "P141 invalid original Creative FX names rejected by host");
        }
        controller->terminate();
        controller->release();
    }
    factory->release();
    FreeLibrary(module);
    std::cout<<(ok?"P141_VSTGUI_HOST_FX_NAMES_PASS":"P141_VSTGUI_HOST_FX_NAMES_FAIL")<<"\n";
    return ok?0:1;
}
