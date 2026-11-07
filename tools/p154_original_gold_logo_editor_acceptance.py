#!/usr/bin/env python3
"""P152: actual VST3 editor open, Win32 input, screenshots and redraw smoke.

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
    # A tiny, genuinely playable and redistributable SF2 with three banks:
    # synthetic sine-family samples only, no Creative copyrighted assets.
    import math
    def u16(n): return struct.pack("<H",n&65535)
    def u32(n): return struct.pack("<I",n)
    def name(s): return s.encode("ascii")[:20].ljust(20,b"\0")
    def listchunk(kind,children): return chunk("LIST",kind.encode("ascii")+children)
    info=chunk("ifil",u16(2)+u16(1))+chunk("INAM",b"125A P106 GUI fixture\0")
    sample_words=2048
    periods=(64,37,83)
    pcm=b"".join(u16(round(math.sin(2*math.pi*(n%k)/k)*11000))
                 for k in periods for n in range(sample_words))
    pcm+=b"\0"*(46*2)
    sdta=chunk("smpl",pcm)
    phdrdata=b""
    for display,bank,program,index in (
        ("125A PIANO",0,0,0),("SYNTH BRASS",0,12,0),
        ("RETRO LEAD",2,4,1),("ROOM DRUM KIT",128,0,2)):
        phdrdata+=name(display)+u16(program)+u16(bank)+u16(index)+u32(0)*3
    phdrdata+=name("EOP")+u16(0)+u16(0)+u16(4)+u32(0)*3
    pbag=b"".join(u16(i)+u16(0) for i in range(5))
    pgen=b"".join(u16(41)+u16(i) for i in (0,0,1,2))
    instdata=b"".join(name(v)+u16(i) for i,v in enumerate(
        ("125A Wave","125A Wave B","125A Wave C","EOI")))
    ibag=b"".join(u16(i*2)+u16(0) for i in range(4))
    igen=b"".join(u16(54)+u16(1)+u16(53)+u16(i) for i in range(3))
    shdr=b""
    for i,title in enumerate(("125A Wave","125A Wave B","125A Wave C")):
        start=i*sample_words
        end=(i+1)*sample_words
        shdr+=(name(title)+u32(start)+u32(end)+u32(start+16)+
               u32(end-16)+u32(44100)+bytes((69,0))+u16(0)+u16(1))
    shdr+=name("EOS")+u32(0)*5+b"\0\0"+u16(0)+u16(1)
    pdta=b"".join((
        chunk("phdr",phdrdata),chunk("pbag",pbag),
        chunk("pmod",bytes(10)),chunk("pgen",pgen),
        chunk("inst",instdata),chunk("ibag",ibag),
        chunk("imod",bytes(10)),chunk("igen",igen),chunk("shdr",shdr)
    ))
    body=(b"sfbk"+listchunk("INFO",info)+listchunk("sdta",sdta)+
          listchunk("pdta",pdta))
    path.write_bytes(b"RIFF"+u32(len(body))+body)


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

# The Github hosted Windows desktop can start at only 1024x768. A 1200x780
# plugin view is then clipped by EditorHost before any VSTGUI screenshot
# or mouse test. Enumerate supported display modes and temporarily switch
# to a real larger mode; never mark a cropped screen as a GUI PASS.
class DEVMODEW(ctypes.Structure):
    _fields_=[
        ("dmDeviceName",wintypes.WCHAR*32),
        ("dmSpecVersion",wintypes.WORD),
        ("dmDriverVersion",wintypes.WORD),
        ("dmSize",wintypes.WORD),
        ("dmDriverExtra",wintypes.WORD),
        ("dmFields",wintypes.DWORD),
        ("dmPositionX",wintypes.LONG),
        ("dmPositionY",wintypes.LONG),
        ("dmDisplayOrientation",wintypes.DWORD),
        ("dmDisplayFixedOutput",wintypes.DWORD),
        ("dmColor",wintypes.SHORT),
        ("dmDuplex",wintypes.SHORT),
        ("dmYResolution",wintypes.SHORT),
        ("dmTTOption",wintypes.SHORT),
        ("dmCollate",wintypes.SHORT),
        ("dmFormName",wintypes.WCHAR*32),
        ("dmLogPixels",wintypes.WORD),
        ("dmBitsPerPel",wintypes.DWORD),
        ("dmPelsWidth",wintypes.DWORD),
        ("dmPelsHeight",wintypes.DWORD),
        ("dmDisplayFlags",wintypes.DWORD),
        ("dmDisplayFrequency",wintypes.DWORD),
        ("dmICMMethod",wintypes.DWORD),
        ("dmICMIntent",wintypes.DWORD),
        ("dmMediaType",wintypes.DWORD),
        ("dmDitherType",wintypes.DWORD),
        ("dmReserved1",wintypes.DWORD),
        ("dmReserved2",wintypes.DWORD),
        ("dmPanningWidth",wintypes.DWORD),
        ("dmPanningHeight",wintypes.DWORD),
    ]

u.EnumDisplaySettingsW.restype=wintypes.BOOL
u.EnumDisplaySettingsW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,ctypes.POINTER(DEVMODEW)]
u.ChangeDisplaySettingsW.restype=wintypes.LONG
u.ChangeDisplaySettingsW.argtypes=[ctypes.POINTER(DEVMODEW),wintypes.DWORD]
u.GetSystemMetrics.restype=ctypes.c_int
u.GetSystemMetrics.argtypes=[ctypes.c_int]

def ensure_full_desktop():
    before=(u.GetSystemMetrics(0),u.GetSystemMetrics(1))
    print(f"P117 desktop before resolution change: {before}",flush=True)
    if before[0]>=1400 and before[1]>=900:return before
    supported=[]
    for index in range(1000):
        mode=DEVMODEW()
        mode.dmSize=ctypes.sizeof(DEVMODEW)
        if not u.EnumDisplaySettingsW(None,index,ctypes.byref(mode)):break
        if mode.dmPelsWidth>=1400 and mode.dmPelsHeight>=900:
            supported.append((mode.dmPelsWidth,mode.dmPelsHeight,mode.dmDisplayFrequency,mode))
    supported.sort(key=lambda x:(abs(x[0]-1600)+abs(x[1]-900),x[0]*x[1]))
    for width,height,hz,mode in supported:
        mode.dmFields=0x00080000|0x00100000 # DM_PELSWIDTH | DM_PELSHEIGHT
        status=u.ChangeDisplaySettingsW(ctypes.byref(mode),0)
        after=(u.GetSystemMetrics(0),u.GetSystemMetrics(1))
        print(f"P117 desktop try {width}x{height} @ {hz}Hz: code={status}, got={after}",flush=True)
        if status==0 and after[0]>=1400 and after[1]>=900:
            time.sleep(.5)
            return after
    raise RuntimeError(
        f"P117 GUI test BLOCKED: CI desktop {before} cannot fit 1200x780 window; "
        f"no supported 1400x900 display mode. Available qualifying modes: {len(supported)}. "
        "Do not approve a cropped editor image.")

def client_size(hwnd):
    r = RECT()
    if not u.GetClientRect(hwnd, ctypes.byref(r)):
        raise RuntimeError("GetClientRect failed")
    return r.right-r.left, r.bottom-r.top

def screen_pos(hwnd, x, y):
    sz = client_size(hwnd)
    pt = POINT(round(x*sz[0]/1000), round(y*sz[1]/640))
    if not u.ClientToScreen(hwnd, ctypes.byref(pt)):
        raise RuntimeError("ClientToScreen failed")
    return pt.x, pt.y

def snap(hwnd, filename):
    w,h = client_size(hwnd)
    x,y = screen_pos(hwnd, 0, 0)
    if w < 980 or h < 625:
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
    scale_x,scale_y = w/1000,h/640
    x0,x1 = round(x0*scale_x),round(x1*scale_x)
    y0,y1 = round(y0*scale_y),round(y1*scale_y)
    changed = 0
    for y in range(y0,y1,2):
        for x in range(x0,x1,2):
            off = (y*w+x)*4
            if any(abs(a[off+c]-b[off+c])>16 for c in range(3)):
                changed+=1
    return changed

def gold_brand_pixels(frame):
    """P117: the owner-approved gold 125A typography is in the raster faceplate."""
    w,h,raw=frame
    count=0
    for y in range(round(14*h/640),round(50*h/640)):
        for x in range(round(27*w/1000),round(156*w/1000)):
            i=(y*w+x)*4
            blue,green,red=raw[i],raw[i+1],raw[i+2]
            if red>=145 and green>=105 and red>=green and blue<green:
                count+=1
    return count

def gold_knob_pixels(frame, region):
    """Confirm that the actual VSTGUI drew the gold PNG frames, not the fallback."""
    w,h,raw=frame
    x0,y0,x1,y1=region
    scale_x,scale_y=w/1000.,h/640.
    found=0
    for y in range(round(y0*scale_y),round(y1*scale_y)):
        for x in range(round(x0*scale_x),round(x1*scale_x)):
            i=(y*w+x)*4
            blue,green,red=raw[i],raw[i+1],raw[i+2]
            if red>140 and green>80 and red>green+30 and green>blue+30:
                found+=1
    return found


def chip_pin_pixels(frame):
    """Count distinct gold pin pixels from the MAIN-only EMU8000 art."""
    w,h,raw=frame
    found=0
    for y in range(round(359*h/640),round(527*h/640),3):
        for x in range(round(32*w/1000),round(225*w/1000),3):
            i=(y*w+x)*4
            blue,green,red=raw[i],raw[i+1],raw[i+2]
            if red>=115 and green>=75 and red>blue+35 and green>blue+22:
                found+=1
    return found


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

def ctrl_click(hwnd,x,y):
    u.keybd_event(0x11,0,0,None)
    try:
        click(hwnd,x,y)
    finally:
        u.keybd_event(0x11,0,2,None)
    time.sleep(.35)

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
    p.add_argument("--quick",action="store_true",
                   help="One of three independent quick real EditorHost opens")
    args=p.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    if not args.editorhost.is_file() or not args.plugin.is_dir():
        raise RuntimeError("EditorHost or real VST3 bundle absent")
    results=[]
    ensure_full_desktop()
    with tempfile.TemporaryDirectory(prefix="125a_p152_") as temp:
        root=Path(temp)
        sf2=root/"p152_synthetic.sf2"
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
            check(hwnd is not None,"real P152 compact VST3 editor opened",results)
            time.sleep(.8)
            first=snap(hwnd,args.output/"01_main.bmp")
            w,h,_=first
            check(985<=w<=1045 and 630<=h<=690,
                  f"actual compact native editor {w}x{h} near 1000x640",results)
            check(gold_brand_pixels(first)>150,
                  "P154 actual extracted gold lettering visible",results)
            check(gold_knob_pixels(first,(74,278,132,336))>160,
                  "actual gold 58px filmstrip rendered, not fallback CDrawContext",results)
            check(gold_knob_pixels(first,(817,298,951,432))>800,
                  "actual gold 134px master filmstrip rendered, not fallback",results)
            # Inspect actual Windows pixels inside BOTH native-size button
            # assets and the gold-framed VSTGUI bank/preset/FX menus.
            for title,rect,minimum in (
                    ("ROM button",(808,177,885,218),25),
                    ("SF2 button",(893,177,968,218),25),
                    ("SYNTH page button",(597,179,690,218),28),
                    ("BROWSER page button",(698,179,797,218),28),
                    ("previous preset button",(202,179,242,218),12),
                    ("next preset button",(545,179,587,218),12),
                    ("RESET CONTROLS button",(808,535,960,571),35),
                    ("bank selector",(67,179,193,218),15),
                    ("preset selector",(250,179,537,218),20),
                    ("Reverb type selector",(32,382,174,405),12),
                    ("Chorus type selector",(216,382,358,405),12)):
                check(gold_knob_pixels(first,rect)>minimum,
                      "P152 actual gold " + title + " visible",results)
            # P152: the empty amber screen artwork must really be drawn by
            # the VST3 editor; dark P152 rectangle and overlay text alone
            # are not sufficient. Count actual amber LCD background pixels.
            w,h,rgba=first
            amber=0
            for yy in range(round(60*h/640),round(118*h/640),2):
                for xx in range(round(320*w/1000),round(714*w/1000),2):
                    off=(yy*w+xx)*4
                    blue,green,red=rgba[off],rgba[off+1],rgba[off+2]
                    if red>=30 and green>=20 and red>=green and green>=blue+8:
                        amber+=1
            check(amber>4000,
                  "P152 blank photographic amber LCD visible beneath live text",results)
            check(gold_knob_pixels(first,(808,78,963,146))<10,
                  "P152 top-right EMU8000 zone is free of live gold controls",results)
            check(gold_knob_pixels(first,(30,608,965,633))<10,
                  "P152 bottom connector strip contains no live controls",results)
            # All sound controls stay visible on SYNTH; BROWSER is separate.
            click(hwnd,747,198)
            browser=snap(hwnd,args.output/"02_browser.bmp")
            check(different(first,browser,(17,235,983,591))>150,
                  "BROWSER switches to actual search/table",results)
            check(different(first,browser,(597,179,797,219))>35,
                  "P152 buttons show distinct on/off visual states",results)
            click(hwnd,641,198)
            mainagain=snap(hwnd,args.output/"03_synth_again.bmp")
            check(different(browser,mainagain,(17,235,983,591))>150,
                  "SYNTH is immediately available again",results)
            check(different(first,mainagain,(18,237,981,590))<120,
                  "SYNTH controls maintain unchanged values",results)
            if not args.quick:
                # New compact MAIN: same host-owned three controls and two
                # separate Creative-DSP mode dropdowns.
                drag(hwnd,885,352,885,398)
                master_down=snap(hwnd,args.output/"05_master_down.bmp")
                check(different(mainagain,master_down,(801,289,965,485))>15,
                      "SYNTH master volume is a functional independent control",results)
                ctrl_click(hwnd,884,364)
                master_reset=snap(hwnd,args.output/"06_master_unity.bmp")
                check(different(master_down,master_reset,(801,289,965,485))>15,
                      "SYNTH master Ctrl-click restores unity",results)
                check(different(mainagain,master_reset,(801,289,965,485))<20,
                      "SYNTH master is genuinely back at 100 percent",results)
                for index,x,y in ((10,74,278),(11,258,278)):
                    before=snap(hwnd,args.output/f"p152_send_{index}_before.bmp")
                    drag(hwnd,x+29,y+34,x+29,y+7)
                    after=snap(hwnd,args.output/f"p152_send_{index}_drag.bmp")
                    region=(x-15,y-5,x+100,y+104)
                    check(different(before,after,region)>15,
                          f"MAIN SEND {index} accepts actual drag",results)
                    ctrl_click(hwnd,x+29,y+29)
                    zero=snap(hwnd,args.output/f"p152_send_{index}_reset.bmp")
                    check(different(after,zero,region)>15,
                          f"MAIN SEND {index} Ctrl-click returns to neutral",results)
                    check(different(before,zero,region)<20,
                          f"MAIN SEND {index} returns to original pixels",results)
                for title,x,area in (("Reverb",103,(29,379,178,409)),
                                     ("Chorus",287,(211,379,362,409))):
                    before=snap(hwnd,args.output/f"p152_{title}_type_before.bmp")
                    choose_menu(hwnd,x,394,last=True,
                                debug=args.output/f"p152_{title}_popup.bmp")
                    after=snap(hwnd,args.output/f"p152_{title}_type_after.bmp")
                    check(different(before,after,area)>15,
                          f"MAIN {title} selects actual hardware FX mode",results)
                # All ten AMP/FILTER knobs permanently on SYNTH.
                positions=((0,408,278),(1,502,278),(2,596,278),(3,690,278),
                           (4,48,464),(5,169,464),(6,290,464),
                           (7,411,464),(8,563,464),(9,687,464))
                for index,x,y in positions:
                    before=snap(hwnd,args.output/f"p152_edit_{index}_zero.bmp")
                    drag(hwnd,x+29,y+34,x+29,y+6)
                    moved=snap(hwnd,args.output/f"p152_edit_{index}_changed.bmp")
                    rect=(x-14,y-7,x+103,y+104)
                    check(different(before,moved,rect)>15,
                          f"permanent SYNTH overlay {index} physical drag responds",results)
                    ctrl_click(hwnd,x+29,y+29)
                    zero=snap(hwnd,args.output/f"p152_edit_{index}_reset.bmp")
                    check(different(moved,zero,rect)>15,
                          f"permanent SYNTH overlay {index} Ctrl-click restores zero",results)
                    check(different(before,zero,rect)<20,
                          f"permanent SYNTH overlay {index} returned to original display",results)
                # MOD RESET must cover editing offsets but not bank/master/FX.
                drag(hwnd,437,312,437,287)
                before_reset=snap(hwnd,args.output/"p152_mod_changed.bmp")
                click(hwnd,884,554)
                after_reset=snap(hwnd,args.output/"p152_mod_reset.bmp")
                check(different(before_reset,after_reset,(395,272,474,379))>15,
                      "MOD RESET resets modulation only",results)
            # Main program navigation is available from every page, even
            # if the browser is currently hidden.
            before_program=snap(hwnd,args.output/"p152_preset000.bmp")
            click(hwnd,566,198)
            next_program=snap(hwnd,args.output/"p152_preset012.bmp")
            check(different(before_program,next_program,(282,63,759,109))>10,
                  "NEXT switches sparse Bank 0 program 000 to 012",results)
            click(hwnd,221,198)
            prev_program=snap(hwnd,args.output/"p152_preset000_restored.bmp")
            check(different(next_program,prev_program,(282,63,759,109))>10,
                  "PREV switches program 012 back to 000",results)
            check(different(before_program,prev_program,(282,63,759,109))<24,
                  "PREV restores exact original bank/program",results)
            click(hwnd,747,198)
            click(hwnd,595,264)
            text_input("DRUM")
            filtered=snap(hwnd,args.output/"p152_browser_search.bmp")
            check(different(browser,filtered,(27,297,971,575))>15,
                  "separate BROWSER search filters actual SF2 rows",results)
            click(hwnd,140,323)
            selected=snap(hwnd,args.output/"p152_browser_selection.bmp")
            check(different(filtered,selected,(282,63,759,109))>10,
                  "BROWSER selection actually changes the host program",results)
            # File actions live outside page containers; cancellation must
            # never modify an already selected program.
            click(hwnd,847,198)
            key(0x1B)
            time.sleep(.35)
            after_rom=snap(hwnd,args.output/"p152_rom_cancel.bmp")
            check(different(selected,after_rom,(282,63,759,109))<24,
                  "ROM chooser cancel preserves current SF2 bank/program",results)
            click(hwnd,930,198)
            key(0x1B)
            time.sleep(.35)
            after_sf2=snap(hwnd,args.output/"p152_sf2_cancel.bmp")
            check(different(selected,after_sf2,(282,63,759,109))<24,
                  "SF2 chooser cancel preserves current bank/program",results)
            u.PostMessageW(hwnd,0x0010,0,0)
            proc.wait(timeout=10)
            check(proc.returncode==0,
                  f"native P152 EditorHost closes cleanly ({proc.returncode})",results)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill()
            (args.output/"result.json").write_text(
                json.dumps({"results":results,"passed":all(x["pass"] for x in results)},
                           indent=2),encoding="utf-8")
    print(f"P154 REAL COMPACT VSTGUI {'QUICK' if args.quick else 'FULL'} "
          f"{len(results)} NATIVE EDITOR INTERACTIONS PASS",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print(f"P18 FAIL: {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)
