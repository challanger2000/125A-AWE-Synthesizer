#!/usr/bin/env python3
"""P18: actual VST3 editor open, Win32 input, screenshots and redraw smoke.

Run on an interactive Windows runner with Steinberg's pinned EditorHost.
This is a real plug-in view, NOT a synthetic C++ mock, source regex or OCR.
Do not label it PASS when no interactive desktop/screen capture is present.
"""
import argparse
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time

if os.name != "nt":
    raise SystemExit("P18 NOT RUN: Win32 interactive GUI required")

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi = ctypes.WinDLL("gdi32", use_last_error=True)

class RECT(ctypes.Structure):
    _fields_ = [(v, ctypes.c_long) for v in ("left", "top", "right", "bottom")]

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

u = user32
for name, restype, args in [
    ("EnumWindows", wintypes.BOOL, [ctypes.c_void_p, ctypes.c_void_p]),
    ("GetWindowThreadProcessId", wintypes.DWORD, [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]),
    ("IsWindowVisible", wintypes.BOOL, [wintypes.HWND]),
    ("GetClassNameW", ctypes.c_int, [wintypes.HWND, ctypes.c_wchar_p, ctypes.c_int]),
    ("GetClientRect", wintypes.BOOL, [wintypes.HWND, ctypes.POINTER(RECT)]),
    ("ClientToScreen", wintypes.BOOL, [wintypes.HWND, ctypes.POINTER(POINT)]),
    ("SetForegroundWindow", wintypes.BOOL, [wintypes.HWND]),
    ("SetCursorPos", wintypes.BOOL, [ctypes.c_int, ctypes.c_int]),
    ("mouse_event", None, [wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]),
    ("keybd_event", None, [wintypes.BYTE, wintypes.BYTE, wintypes.DWORD, ctypes.c_void_p]),
    ("PostMessageW", wintypes.BOOL, [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]),
    ("GetDC", wintypes.HDC, [wintypes.HWND]),
    ("ReleaseDC", ctypes.c_int, [wintypes.HWND, wintypes.HDC]),
]:
    f = getattr(u, name)
    f.restype, f.argtypes = restype, args
gdi.CreateCompatibleDC.restype = wintypes.HDC
gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
gdi.CreateCompatibleBitmap.restype = wintypes.HBITMAP
gdi.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
gdi.SelectObject.restype = wintypes.HANDLE
gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HANDLE]
gdi.BitBlt.restype = wintypes.BOOL
gdi.BitBlt.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int, ctypes.c_int,
                       ctypes.c_int, wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.DWORD]
gdi.GetDIBits.restype = ctypes.c_int
gdi.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT,
                         ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
gdi.DeleteObject.restype = wintypes.BOOL
gdi.DeleteObject.argtypes = [wintypes.HANDLE]
gdi.DeleteDC.restype = wintypes.BOOL
gdi.DeleteDC.argtypes = [wintypes.HDC]

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]

def chunk(name, value):
    return name.encode("ascii") + struct.pack("<I", len(value)) + value + bytes(len(value) % 2)

def phdr(name, bank, program):
    return name.encode("ascii")[:20].ljust(20, b"\0") + struct.pack("<HHHIII", program, bank, 0, 0, 0, 0)

def make_sf2(path):
    ph = b"".join([
        phdr("125A PIANO", 0, 0), phdr("RETRO LEAD", 2, 4),
        phdr("ROOM DRUM KIT", 128, 0), phdr("EOP", 0, 0),
    ])
    pdta = b"pdta" + chunk("phdr", ph)
    body = b"sfbk" + chunk("LIST", pdta)
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)

def get_editor(pid):
    found = []
    CB = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        proc = wintypes.DWORD(0)
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(proc))
        if proc.value == pid and u.IsWindowVisible(hwnd):
            buf = ctypes.create_unicode_buffer(128)
            u.GetClassNameW(hwnd, buf, 128)
            if buf.value == "VSTSDK WindowClass":
                found.append(hwnd)
        return True
    callback = CB(cb)
    u.EnumWindows(callback, 0)
    return found[0] if found else None

def client_size(hwnd):
    r = RECT()
    if not u.GetClientRect(hwnd, ctypes.byref(r)):
        raise RuntimeError("GetClientRect failed")
    return r.right-r.left, r.bottom-r.top

def screen_pos(hwnd, x, y):
    sz = client_size(hwnd)
    pt = POINT(round(x*sz[0]/1040), round(y*sz[1]/720))
    if not u.ClientToScreen(hwnd, ctypes.byref(pt)):
        raise RuntimeError("ClientToScreen failed")
    return pt.x, pt.y

def snap(hwnd, filename):
    w,h = client_size(hwnd)
    x,y = screen_pos(hwnd, 0, 0)
    if w < 1020 or h < 700:
        raise RuntimeError(f"Editor window wrong dimensions {w}x{h}")
    src = u.GetDC(None)
    mem = gdi.CreateCompatibleDC(src)
    bmp = gdi.CreateCompatibleBitmap(src, w, h)
    prev = gdi.SelectObject(mem, bmp)
    try:
        if not gdi.BitBlt(mem,0,0,w,h,src,x,y,0x00CC0020):
            raise RuntimeError("Screen capture unavailable (no interactive desktop?)")
        info = BITMAPINFOHEADER()
        info.biSize = ctypes.sizeof(info)
        info.biWidth, info.biHeight = w, -h   # top-down 32-bit pixels
        info.biPlanes, info.biBitCount = 1,32
        pixels = (ctypes.c_ubyte*(w*h*4))()
        if not gdi.GetDIBits(mem,bmp,0,h,ctypes.byref(pixels),ctypes.byref(info),0):
            raise RuntimeError("GetDIBits failed")
        raw = bytes(pixels)
        # BMP byte array is bottom-up while screen pixel array is top-down.
        path = Path(filename)
        file_size = 54 + len(raw)
        header = (b"BM" + struct.pack("<IHHI", file_size, 0, 0, 54)
                  + struct.pack("<IiiHHIIiiII", 40,w,-h,1,32,0,len(raw),0,0,0,0))
        path.write_bytes(header+raw)
        return (w,h,raw)
    finally:
        gdi.SelectObject(mem,prev)
        gdi.DeleteObject(bmp)
        gdi.DeleteDC(mem)
        u.ReleaseDC(None,src)

def different(before,after,region):
    w,h,a = before
    w2,h2,b = after
    if (w,h)!=(w2,h2):
        raise RuntimeError("Editor size changed unexpectedly")
    x0,y0,x1,y1 = region
    scale_x,scale_y = w/1040,h/720
    x0,x1 = round(x0*scale_x),round(x1*scale_x)
    y0,y1 = round(y0*scale_y),round(y1*scale_y)
    changed = 0
    for y in range(y0,y1,2):
        for x in range(x0,x1,2):
            off = (y*w+x)*4
            if any(abs(a[off+c]-b[off+c])>16 for c in range(3)):
                changed+=1
    return changed

def red_logo_pixels(frame):
    w,h,raw=frame
    count=0
    # Logo view occupies header x18..150 / y8..53. Pixel array is BGRA.
    for y in range(round(8*h/720),round(54*h/720)):
        for x in range(round(17*w/1040),round(151*w/1040)):
            i=(y*w+x)*4
            blue,green,red=raw[i],raw[i+1],raw[i+2]
            if red>=125 and red>=green*2 and red>=blue*1.6:
                count+=1
    return count

def click(hwnd,x,y):
    sx,sy=screen_pos(hwnd,x,y)
    if not u.SetForegroundWindow(hwnd):
        # Windows focus is best effort; SetCursorPos failure is fatal.
        pass
    if not u.SetCursorPos(sx,sy):
        raise RuntimeError("Cannot position mouse: no interactive desktop")
    time.sleep(.15)
    u.mouse_event(0x0002,0,0,0,None)
    time.sleep(.08)
    u.mouse_event(0x0004,0,0,0,None)
    time.sleep(.65)

def key(v):
    u.keybd_event(v,0,0,None)
    time.sleep(.05)
    u.keybd_event(v,0,2,None)

def choose_menu(hwnd,x,y,last=False,debug=None):
    # VSTGUI COptionMenu::onKeyboardEvent handles VK_UP/VK_DOWN, *not*
    # VK_HOME/VK_END. Its mouse-down opens a native OS popup, so first
    # dismiss it with ESC while retaining focus on the menu control.
    click(hwnd,x,y)
    if debug is not None:
        snap(hwnd,debug)
    key(0x1B)  # escape from native popup; focus returns to COptionMenu
    time.sleep(.15)
    for _ in range(2):
        key(0x28 if last else 0x26)  # VK_DOWN/VK_UP
        time.sleep(.22)
    time.sleep(.65)

def text_input(s):
    # Send unicode via KEYEVENTF_UNICODE, works even without US keyboard layout.
    class MOUSEINPUT(ctypes.Structure):
        _fields_=[("dx",wintypes.LONG),("dy",wintypes.LONG),("mouseData",wintypes.DWORD),
                  ("dwFlags",wintypes.DWORD),("time",wintypes.DWORD),("dwExtraInfo",ctypes.c_void_p)]
    class KEYBDINPUT(ctypes.Structure):
        _fields_=[("wVk",wintypes.WORD),("wScan",wintypes.WORD),
                  ("dwFlags",wintypes.DWORD),("time",wintypes.DWORD),
                  ("dwExtraInfo",ctypes.c_void_p)]
    class HARDWAREINPUT(ctypes.Structure):
        _fields_=[("uMsg",wintypes.DWORD),("wParamL",wintypes.WORD),("wParamH",wintypes.WORD)]
    class Union(ctypes.Union):
        _fields_=[("mi",MOUSEINPUT),("ki",KEYBDINPUT),("hi",HARDWAREINPUT)]
    class INPUT(ctypes.Structure):
        _fields_=[("type",wintypes.DWORD),("u",Union)]
    u.SendInput.argtypes=[wintypes.UINT,ctypes.POINTER(INPUT),ctypes.c_int]
    u.SendInput.restype=wintypes.UINT
    for c in s:
        for down in (True,False):
            item=INPUT()
            item.type=1
            item.u.ki=KEYBDINPUT(0,ord(c),4 if down else 6,0,None)
            if u.SendInput(1,ctypes.byref(item),ctypes.sizeof(INPUT))!=1:
                raise RuntimeError("SendInput unavailable")
    time.sleep(.75)

def check(condition, label, results):
    results.append({"test":label,"pass":bool(condition)})
    print(("PASS: " if condition else "FAIL: ")+label, flush=True)
    if not condition: raise AssertionError(label)

def drag(hwnd,x0,y0,x1,y1):
    sx,sy=screen_pos(hwnd,x0,y0)
    ex,ey=screen_pos(hwnd,x1,y1)
    u.SetForegroundWindow(hwnd)
    if not u.SetCursorPos(sx,sy):
        raise RuntimeError("P18 cannot position pointer")
    time.sleep(.15)
    u.mouse_event(0x0002,0,0,0,None)
    for step in range(1,9):
        px=round(sx+(ex-sx)*step/8)
        py=round(sy+(ey-sy)*step/8)
        u.SetCursorPos(px,py)
        time.sleep(.06)
    u.mouse_event(0x0004,0,0,0,None)
    time.sleep(.45)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--editorhost",type=Path,required=True)
    p.add_argument("--plugin",type=Path,required=True)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if not args.editorhost.is_file() or not args.plugin.is_dir():
        raise RuntimeError("EditorHost executable / VST3 bundle not found")
    results=[]
    with tempfile.TemporaryDirectory(prefix="125a_p18_") as temp:
        root=Path(temp)
        sf2=root/"ui_fixture.sf2"
        make_sf2(sf2)
        appdata=root/"AppData"
        cfg=appdata/"125A"/"AWE Synthesizer"/"assets.cfg"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(f'SF2 = "{sf2}"\n',encoding="utf-8")
        env=os.environ.copy()
        env["APPDATA"]=str(appdata)
        proc=subprocess.Popen([str(args.editorhost),"--componentHandler",str(args.plugin)],
                              cwd=str(args.editorhost.parent),env=env,
                              stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        try:
            hwnd=None
            for _ in range(90):
                if proc.poll() is not None:
                    raise RuntimeError(f"EditorHost exited early: {proc.returncode}")
                hwnd=get_editor(proc.pid)
                if hwnd:break
                time.sleep(.2)
            check(hwnd is not None,"real AWE-only VST3 window opened",results)
            time.sleep(1.0)
            first=snap(hwnd,args.output/"01_initial.bmp")
            w,h,_=first
            check(w>=1020 and h>=700,
                  f"real hardware editor dimensions {w}x{h}",results)
            distinct=len(set(first[2][0::384]))
            check(distinct>3,"editor painted nonflat hardware faceplate",results)
            check(red_logo_pixels(first)>15,
                  "authentic 125A red-vector logo painted",results)
            click(hwnd,917,178)
            closed=snap(hwnd,args.output/"02_browser_closed.bmp")
            check(different(first,closed,(650,285,1015,652))>35,
                  "browser toggle hides preset table and filter",results)
            click(hwnd,917,178)
            reopened=snap(hwnd,args.output/"03_browser_reopened.bmp")
            check(different(closed,reopened,(650,285,1015,652))>35,
                  "browser toggle reopens searchable preset list",results)
            drag(hwnd,116,286,116,251)
            moved=snap(hwnd,args.output/"04_knob_dragged.bmp")
            check(different(reopened,moved,(85,262,175,365))>15,
                  "amp attack knob responds to physical mouse drag",results)
            click(hwnd,88,645)
            reset=snap(hwnd,args.output/"05_reset_original.bmp")
            check(different(moved,reset,(85,262,175,365))>15,
                  "reset restores 0-percent original SoundFont value",results)
            click(hwnd,796,323)
            text_input("DRUM")
            searched=snap(hwnd,args.output/"07_search_drum.bmp")
            check(different(reset,searched,(654,346,1013,650))>10,
                  "preset search filters SF2 bank 128 rows",results)
            click(hwnd,723,359)
            selected=snap(hwnd,args.output/"08_bank128_selected.bmp")
            check(different(searched,selected,(214,157,753,198))>8,
                  "bank 128 sound selection updates instrument label",results)
            # Canceling the Windows file chooser is safe, without changing bank.
            click(hwnd,915,103)
            key(0x1B)
            time.sleep(.65)
            after_cancel=snap(hwnd,args.output/"09_sf2_dialog_cancelled.bmp")
            check(different(selected,after_cancel,(10,10,1027,210))<20,
                  "native SF2 chooser cancels without mutating current preset",results)
            u.PostMessageW(hwnd,0x0010,0,0)
            proc.wait(timeout=10)
            check(proc.returncode==0,"EditorHost closes normally",results)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill()
            (args.output/"result.json").write_text(
                json.dumps({"results":results,"passed":all(x["pass"] for x in results)},
                           indent=2),encoding="utf-8")
    print("P106 WIN32 AWE-ONLY EDITORHOST GUI SMOKE PASS",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print(f"P18 FAIL: {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)
