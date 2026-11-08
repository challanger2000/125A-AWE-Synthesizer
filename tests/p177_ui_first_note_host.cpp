// P177: actual exported Windows VST3, its real controller and native file dialog.
#define wmain p171_unused_entry
#include "p171_vst3_load_host.cpp"
#undef wmain
#include <ole2.h>
#include "base/source/fobject.h"
#include "pluginterfaces/gui/iplugview.h"
#include <cmath>
#include <iostream>
using namespace Steinberg;
using namespace Steinberg::Vst;
namespace {
constexpr wchar_t kClass[]=L"125A_P177_FirstNote_Host";
bool signaled=false;
LRESULT CALLBACK wndProc(HWND h,UINT m,WPARAM w,LPARAM l) {
    if(m==WM_APP+77){signaled=true;return 0;}
    return DefWindowProcW(h,m,w,l);
}
class Frame final:public FObject,public IPlugFrame {
public:
    explicit Frame(HWND hwnd):hwnd_(hwnd){}
    tresult PLUGIN_API resizeView(IPlugView* view,ViewRect* r) override {
        if(!view||!r||!hwnd_)return kResultFalse;
        RECT outer{0,0,r->getWidth(),r->getHeight()};
        const DWORD style=DWORD(GetWindowLongPtrW(hwnd_,GWL_STYLE));
        const DWORD ex=DWORD(GetWindowLongPtrW(hwnd_,GWL_EXSTYLE));
        if(!AdjustWindowRectEx(&outer,style,FALSE,ex))return kResultFalse;
        if(!SetWindowPos(hwnd_,nullptr,0,0,outer.right-outer.left,
                         outer.bottom-outer.top,SWP_NOMOVE|SWP_NOZORDER|SWP_NOACTIVATE))
            return kResultFalse;
        return view->onSize(r);
    }
    OBJ_METHODS(Frame,FObject)
    DEFINE_INTERFACES
        DEF_INTERFACE(IPlugFrame)
    END_DEFINE_INTERFACES(FObject)
    REFCOUNT_METHODS(FObject)
private:
    HWND hwnd_;
};
class Handler final:public FObject,public IComponentHandler {
public:
    tresult PLUGIN_API beginEdit(ParamID id) override {if(id==1000)++begins;return kResultOk;}
    tresult PLUGIN_API performEdit(ParamID id,ParamValue value) override {
        if(id==1000){++edits;program=value;}
        return kResultOk;
    }
    tresult PLUGIN_API endEdit(ParamID id) override {if(id==1000)++ends;return kResultOk;}
    tresult PLUGIN_API restartComponent(int32) override {return kResultOk;}
    bool selected() const {return begins&&edits&&ends&&std::abs(program-7./127.)<1e-6;}
    int begins=0,edits=0,ends=0;
    double program=-1.;
    OBJ_METHODS(Handler,FObject)
    DEFINE_INTERFACES
        DEF_INTERFACE(IComponentHandler)
    END_DEFINE_INTERFACES(FObject)
    REFCOUNT_METHODS(FObject)
};
void syncController(Instance& instance,const AWE125::AssetState::Data& stateData) {
    MemoryStream stream;
    require(AWE125::AssetState::Write([&](const void* ptr,size_t n) {
        int32 wrote=0;
        return stream.write(const_cast<void*>(ptr),int32(n),&wrote)==kResultOk&&wrote==int32(n);
    },stateData),"P177 initial state encode");
    stream.seek(0,IBStream::kIBSeekSet,nullptr);
    require(instance.controller->setComponentState(&stream)==kResultOk,"P177 controller state");
}
std::vector<float> editedFirstNote(IAudioProcessor* audio,double program) {
    std::vector<float> pcm;
    pcm.reserve(8*2048);
    for(int b=0;b<8;++b) {
        std::array<float,1024> l{},r{};
        float* channels[]{l.data(),r.data()};
        AudioBusBuffers output{};
        output.numChannels=2;output.channelBuffers32=channels;
        EventList events;
        ParameterChanges parameters(4);
        if(b==0) {
            int32 idx=0;
            auto* q=parameters.addParameterData(1000,idx);
            require(q&&q->addPoint(0,program,idx)==kResultOk,"P177 host-queued program");
            Event on{};on.type=Event::kNoteOnEvent;
            on.noteOn.channel=0;on.noteOn.pitch=60;on.noteOn.velocity=.85f;on.noteOn.noteId=1;
            require(events.addEvent(on)==kResultOk,"P177 MIDI NoteOn");
        }
        ProcessData data{};
        data.processMode=kRealtime;data.symbolicSampleSize=kSample32;
        data.numSamples=1024;data.numOutputs=1;data.outputs=&output;
        data.inputParameterChanges=&parameters;data.inputEvents=&events;
        require(audio->process(data)==kResultOk,"P177 actual DLL audio");
        pcm.insert(pcm.end(),l.begin(),l.end());
        pcm.insert(pcm.end(),r.begin(),r.end());
    }
    return pcm;
}
std::string savedSf2(IComponent* component) {
    MemoryStream stream;
    require(component->getState(&stream)==kResultOk,"P177 actual state save");
    stream.seek(0,IBStream::kIBSeekSet,nullptr);
    AWE125::AssetState::Data model{};
    require(AWE125::AssetState::Read([&](void* data,size_t n) {
        int32 got=0;
        return stream.read(data,int32(n),&got)==kResultOk&&got==int32(n);
    },model),"P177 actual state decode");
    return model.sf2Path;
}
} // namespace

int wmain(int argc,wchar_t** argv) {
    if(argc!=3)return 2;
    if(FAILED(CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED)))return 2;
    HMODULE dll=nullptr;IPluginFactory* factory=nullptr;int rc=1;
    try {
        dll=LoadLibraryW(argv[1]);
        require(dll!=nullptr,"P177 LoadLibrary actual binary");
        using GetFactory=IPluginFactory*(*)();
        const auto get=reinterpret_cast<GetFactory>(GetProcAddress(dll,"GetPluginFactory"));
        require(get!=nullptr,"P177 factory export");
        factory=get();
        require(factory!=nullptr,"P177 factory");
        const auto assets=std::filesystem::path(argv[2]);
        AWE125::AssetState::Data wanted{};
        wanted.pathsSpecified=true;
        wanted.romPath=(assets/"zero.rom").string();
        wanted.sf2Path=(assets/"bank.sf2").string();
        wanted.program=7;wanted.bank=0;wanted.channelPrograms.fill(7);
        auto blank=wanted;blank.sf2Path.clear();blank.program=0;blank.channelPrograms.fill(0);
        Instance reference(factory,44100,wanted);
        const auto expected=render(reference.audio,0);
        require(std::any_of(expected.begin(),expected.end(),[](float x){return x!=0.f;}),
                "P177 reference sound missing");
        Instance actual(factory,44100,blank);
        syncController(actual,blank);
        auto* handler=new Handler;
        require(actual.controller->setComponentHandler(handler)==kResultOk,"P177 handler binding");
        auto* view=actual.controller->createView(ViewType::kEditor);
        require(view!=nullptr,"P177 actual VSTGUI view");
        Frame* frame=nullptr;HWND hwnd=nullptr;bool attached=false,frameSet=false;
        try {
            ViewRect size{};
            require(view->getSize(&size)==kResultTrue,"P177 editor size");
            require(view->isPlatformTypeSupported(kPlatformTypeHWND)==kResultTrue,
                    "P177 native HWND unsupported");
            WNDCLASSW wc{};wc.lpfnWndProc=wndProc;
            wc.hInstance=GetModuleHandleW(nullptr);wc.lpszClassName=kClass;
            wc.hCursor=LoadCursorW(nullptr,MAKEINTRESOURCEW(32512));
            require(RegisterClassW(&wc)||GetLastError()==ERROR_CLASS_ALREADY_EXISTS,
                    "P177 window class");
            RECT rect{0,0,size.getWidth(),size.getHeight()};
            require(AdjustWindowRectEx(&rect,WS_OVERLAPPEDWINDOW,FALSE,WS_EX_TOOLWINDOW),
                    "P177 window sizing");
            hwnd=CreateWindowExW(WS_EX_TOOLWINDOW,kClass,L"125A P177",
                WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,
                rect.right-rect.left,rect.bottom-rect.top,nullptr,nullptr,
                GetModuleHandleW(nullptr),nullptr);
            require(hwnd!=nullptr,"P177 create Win32 host");
            frame=new Frame(hwnd);
            require(view->setFrame(frame)==kResultTrue,"P177 native frame");
            frameSet=true;
            require(view->attached(hwnd,kPlatformTypeHWND)==kResultTrue,"P177 editor attach");
            attached=true;
            ShowWindow(hwnd,SW_SHOWNORMAL);UpdateWindow(hwnd);
            std::cout<<"P177_GUI_READY\n"<<std::flush;
            MSG message{};
            const auto until=GetTickCount64()+45000u;
            while(!signaled&&GetTickCount64()<until) {
                while(PeekMessageW(&message,nullptr,0,0,PM_REMOVE)){
                    TranslateMessage(&message);DispatchMessageW(&message);
                }
                Sleep(2);
            }
            require(signaled,"P177 SF2 file dialog/next click timed out");
            require(handler->selected(),"P177 actual host program begin/perform/endEdit missing");
            const double selected=actual.controller->getParamNormalized(1000);
            require(std::abs(selected-7./127.)<1e-6,"P177 wrong controller program");
            require(savedSf2(actual.component)==wanted.sf2Path,"P177 SF2 load via GUI not committed");
            const auto got=editedFirstNote(actual.audio,selected);
            require(got==expected&&std::any_of(got.begin(),got.end(),
                [](float x){return x!=0.f;}),"P177 first-note actual PCM differs");
            std::cout<<"P177_GUI_PCM_PASS real_dialog=1 host_program_gestures="
                     <<handler->edits<<" note0_pcm_identical=1\n"<<std::flush;
            rc=0;
        }catch(...) {
            if(attached)view->removed();
            if(frameSet)view->setFrame(nullptr);
            view->release();
            if(frame)frame->release();
            if(hwnd)DestroyWindow(hwnd);
            actual.controller->setComponentHandler(nullptr);
            handler->release();
            throw;
        }
        if(attached)view->removed();
        if(frameSet)view->setFrame(nullptr);
        view->release();
        if(frame)frame->release();
        if(hwnd)DestroyWindow(hwnd);
        actual.controller->setComponentHandler(nullptr);
        handler->release();
    }catch(const std::exception& e){
        std::cerr<<"P177_GUI_PCM_FAIL "<<e.what()<<'\n';
    }
    if(factory)factory->release();
    if(dll)FreeLibrary(dll);
    CoUninitialize();
    return rc;
}
