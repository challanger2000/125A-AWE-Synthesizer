#pragma once
// P119: Windows-only hidden message window owned by the Controller's UI
// thread. It persists when VSTGUI editor windows are closed. Non-UI VST3
// connection callbacks only POST a notification; host APIs are called by
// the receiving window's own thread, never directly by the audio callback.
#if defined(_WIN32)
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <mutex>

namespace AWE125 {
class WinUiDispatch {
public:
    using Handler=bool(*)(void*); // return true when delivery needs a retry
    WinUiDispatch()=default;
    WinUiDispatch(const WinUiDispatch&)=delete;
    WinUiDispatch& operator=(const WinUiDispatch&)=delete;
    ~WinUiDispatch(){Stop();}
    bool Start(void* ctx,Handler callback,HINSTANCE module) {
        if(hwnd_||!callback||!module)return false;
        context_=ctx;handler_=callback;module_=module;
        {
            std::lock_guard<std::mutex> guard(classMutex_);
            if(classRefs_==0) {
                WNDCLASSEXW wc{};
                wc.cbSize=sizeof(wc);
                wc.lpfnWndProc=&WindowProc;
                wc.hInstance=module_;
                wc.lpszClassName=kClassName;
                if(!RegisterClassExW(&wc) &&
                   GetLastError()!=ERROR_CLASS_ALREADY_EXISTS)return false;
            }
            ++classRefs_;
        }
        hwnd_=CreateWindowExW(0,kClassName,L"",0,0,0,0,0,
                              HWND_MESSAGE,nullptr,module_,this);
        if(!hwnd_){
            ReleaseClass();
            return false;
        }
        return true;
    }
    void Post() const noexcept {
        if(hwnd_)PostMessageW(hwnd_,kNotify,0,0);
    }
    bool Active() const noexcept {return hwnd_!=nullptr;}
private:
    static constexpr UINT kNotify=WM_APP+0x5A;
    static constexpr UINT_PTR kTimer=1;
    static inline constexpr wchar_t kClassName[]=L"125A_AWE_VST3_HostDispatch_P119";
    static inline std::mutex classMutex_{};
    static inline unsigned classRefs_=0;
    HWND hwnd_=nullptr;
    HINSTANCE module_=nullptr;
    void* context_=nullptr;
    Handler handler_=nullptr;
    void Stop() {
        if(hwnd_) {
            KillTimer(hwnd_,kTimer);
            SetWindowLongPtrW(hwnd_,GWLP_USERDATA,0);
            DestroyWindow(hwnd_); // controller is created/destroyed on UI thread
            hwnd_=nullptr;
            ReleaseClass();
        }
    }
    void ReleaseClass() {
        std::lock_guard<std::mutex> guard(classMutex_);
        if(classRefs_ && --classRefs_==0)
            UnregisterClassW(kClassName,module_);
    }
    static LRESULT CALLBACK WindowProc(HWND hwnd,UINT msg,WPARAM wp,LPARAM lp) {
        if(msg==WM_NCCREATE) {
            auto* cs=reinterpret_cast<CREATESTRUCTW*>(lp);
            auto* self=static_cast<WinUiDispatch*>(cs->lpCreateParams);
            SetWindowLongPtrW(hwnd,GWLP_USERDATA,reinterpret_cast<LONG_PTR>(self));
            return TRUE;
        }
        auto* self=reinterpret_cast<WinUiDispatch*>(
            GetWindowLongPtrW(hwnd,GWLP_USERDATA));
        if(self && (msg==kNotify || (msg==WM_TIMER&&wp==kTimer))) {
            const bool retry=self->handler_&&self->handler_(self->context_);
            if(retry)SetTimer(hwnd,kTimer,250,nullptr);
            else KillTimer(hwnd,kTimer);
            return 0;
        }
        return DefWindowProcW(hwnd,msg,wp,lp);
    }
};
} // namespace AWE125
#else
namespace AWE125 {
class WinUiDispatch {
public:
    using Handler=bool(*)(void*);
    bool Start(void*,Handler,void*){return false;}
    void Post() const noexcept {}
    bool Active() const noexcept {return false;}
};
}
#endif
