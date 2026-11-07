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

# Original 1491x1055 board is sampled to 1000x708. Controls below the
# head retain their P165 geometry, only translated down by 55px.
CANVAS_H=708
def layout_y(y):
    return y+55 if y>=170 else y

def screen_pos(hwnd, x, y):
    sz = client_size(hwnd)
    pt = POINT(round(x*sz[0]/1000), round(layout_y(y)*sz[1]/CANVAS_H))
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
    scale_x,scale_y = w/1000,h/CANVAS_H
    x0,x1 = round(x0*scale_x),round(x1*scale_x)
    y0,y1 = round(layout_y(y0)*scale_y),round(layout_y(y1)*scale_y)
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
    for y in range(round(56*h/CANVAS_H),round(198*h/CANVAS_H)):
        for x in range(round(38*w/1000),round(310*w/1000)):
            i=(y*w+x)*4
            blue,green,red=raw[i],raw[i+1],raw[i+2]
            if red>=145 and green>=105 and red>=green and blue<green:
                count+=1
    return count

def gold_knob_pixels(frame, region):
    """Confirm that the actual VSTGUI drew the gold PNG frames, not the fallback."""
    w,h,raw=frame
    x0,y0,x1,y1=region
    scale_x,scale_y=w/1000.,h/CANVAS_H
    found=0
    for y in range(round(layout_y(y0)*scale_y),round(layout_y(y1)*scale_y)):
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
    for y in range(round(359*h/CANVAS_H),round(527*h/CANVAS_H),3):
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
            check(985<=w<=1045 and 698<=h<=745,
                  f"actual compact native editor {w}x{h} near 1000x708",results)
            check(gold_brand_pixels(first)>150,
                  "P165 actual gold logo sampled inside approved reduced 193x120 region",results)
            check(gold_knob_pixels(first,(74,278,132,336))>160,
                  "actual gold 58px filmstrip rendered, not fallback CDrawContext",results)
            check(gold_knob_pixels(first,(817,298,951,432))>800,
                  "actual gold 134px master filmstrip rendered, not fallback",results)
            # Inspect actual Windows pixels inside BOTH native-size button
            # assets and the gold-framed VSTGUI bank/preset/FX menus.
            for title,rect,minimum in (
                    ("ROM button",(819,177,896,218),25),
                    ("SF2 button",(904,177,979,218),25),
                    ("SYNTH page button",(610,179,703,218),28),
                    ("BROWSER page button",(712,179,811,218),28),
                    ("previous preset button",(212,179,252,218),12),
                    ("next preset button",(561,179,601,218),12),
                    ("RESET CONTROLS button",(808,513,960,549),35),
                    ("bank selector",(26,179,203,218),45),
                    ("preset selector",(261,179,552,218),80),
                    ("Reverb type selector",(32,382,174,405),45),
                    ("Chorus type selector",(216,382,358,405),45)):
                check(gold_knob_pixels(first,rect)>minimum,
                      "P152 actual gold " + title + " visible",results)
            # The new gold dropdowns are real custom-drawn hardware
            # selectors, with full-width metal bezels (not generic 1px frames).
            for label,rect in (
                ("bank",(26,179,203,218)),
                ("preset",(261,179,552,218)),
                ("Reverb",(32,382,174,405)),
                ("Chorus",(216,382,358,405))):
                check(gold_knob_pixels(first,rect)>45,
                      f"P155 custom hardware selector {label} visible",results)
            # P152: the empty amber screen artwork must really be drawn by
            # the VST3 editor; dark P152 rectangle and overlay text alone
            # are not sufficient. Count actual amber LCD background pixels.
            w,h,rgba=first
            amber=0
            for yy in range(round(105*h/CANVAS_H),round(180*h/CANVAS_H),2):
                for xx in range(round(355*w/1000),round(725*w/1000),2):
                    off=(yy*w+xx)*4
                    blue,green,red=rgba[off],rgba[off+1],rgba[off+2]
                    if red>=30 and green>=20 and red>=green and green>=blue+8:
                        amber+=1
            check(amber>4000,
                  "P152 blank photographic amber LCD visible beneath live text",results)
            # Pixel-fidelity acceptance: compare Windows editor pixels with
            # the actual user's ORIGINAL complete faceplate, on both pages.
            from PIL import Image
            fp=Path("src/vst3/resource/125A_P165_Original_Faceplate_1000x708.png")
            check(fp.is_file(), "P165 approved original faceplate staged",results)
            approved=Image.open(fp).convert("RGB")
            check(approved.size==(1000,708),"P165 original full aspect ratio",results)
            def patch_mae(frame,box):
                w,h,pixels=frame
                total=count=0
                x0,y0,x1,y1=box
                for py in range(y0,y1,3):
                    for px in range(x0,x1,3):
                        x=min(w-1,round(px*w/1000))
                        y=min(h-1,round(py*h/CANVAS_H))
                        k=(y*w+x)*4
                        b,g,r=pixels[k:k+3]
                        total+=sum(abs(a-b) for a,b in zip((r,g,b),approved.getpixel((px,py))))
                        count+=3
                return total/max(1,count)
            areas=(
                ("125A gold brand",(40,59,309,202)),
                ("complete EMU8000 chip",(799,67,945,225)),
                ("original LCD bezel upper",(314,55,767,81)),
                ("original LCD bezel lower",(314,199,767,219)),
                ("upper left screw",(6,6,65,65)),
                ("upper right screw",(934,6,993,65)))
            for name,area in areas:
                deviation=patch_mae(first,area)
                check(deviation<22.,
                      f"P165 {name}: photo-preserving MAE {deviation:.1f}",results)
            check(gold_knob_pixels(first,(20,608,980,633))>20,
                  "original gold bottom contacts visible",results)
            click(hwnd,751,198)
            browser=snap(hwnd,args.output/"02_browser.bmp")
            for name,area in areas:
                deviation=patch_mae(browser,area)
                check(deviation<22.,
                      f"P165 browser {name}: photo-preserving MAE {deviation:.1f}",results)

            check(different(first,browser,(17,235,983,591))>150,
                  "BROWSER switches to actual search/table",results)
            # P161 screenshot-based browser design acceptance: gold
            # enclosure and inset search are native VSTGUI views.
            check(gold_knob_pixels(browser,(580,243,974,289))>50,
                  "P161 recessed gold search field visible",results)
            check(gold_knob_pixels(browser,(24,295,974,581))>180,
                  "P161 gold preset list bezel visible",results)
            check(gold_knob_pixels(browser,(100,247,494,284))>100,
                  "P162 full-width 394px bank-filter field rendered",results)
            # Row selected highlight should reach the right-hand side of
            # the list; P161 used a fixed 892px column and left ~52px blank.
            def sample_rgba(frame,x,y):
                w,h,buf=frame
                px=round(x*w/1000.)
                py=round(layout_y(y)*h/CANVAS_H)
                j=(py*w+px)*4
                return tuple(buf[j:j+3])
            left=sample_rgba(browser,700,315)
            right=sample_rgba(browser,930,315)
            check(max(abs(left[j]-right[j]) for j in range(3))<35,
                  "P162 selected row fills the available list width",results)

            # P163: use the actual Windows screenshot pixels, not
            # just equal CRect limits. The SF2 atlas has ~5 px of
            # built-in right-hand shadow; its gold edge must line up
            # with both vector-painted gold inset surfaces.
            def visible_gold_right_edge(frame,from_y,to_y):
                w,h,pixels=frame
                observed=[]
                for y0 in range(from_y,to_y):
                    y=min(h-1,round(layout_y(y0)*h/CANVAS_H))
                    candidate=[]
                    for x0 in range(956,979):
                        x=min(w-1,round(x0*w/1000.))
                        off=(y*w+x)*4
                        blue,green,red=pixels[off:off+3]
                        # P165: browser recess has translucent antiqued-gold
                        # border (RGB ~120/85/41), not the brighter
                        # physical atlas gold of the SF2 button.
                        if red>105 and green>65 and red>green+25 and green>blue+20:
                            candidate.append(x0)
                    if candidate:
                        observed.append(max(candidate))
                if len(observed)<6:
                    return -1,len(observed)
                ordered=sorted(observed)
                return ordered[len(ordered)//2],len(observed)
            edges={}
            for name,ya,yb in (("SF2",192,207),("search",261,280),
                               ("list",320,540)):
                edge,count=visible_gold_right_edge(browser,ya,yb)
                edges[name]=edge
                check(count>=6 and abs(edge-974)<=2,
                      f"P163 {name} real visible gold right edge X={edge} near 974",results)
            check(max(edges.values())-min(edges.values())<=2,
                  f"P163 real visual right-hand alignment <=2px: {edges}",results)
            check(different(first,browser,(610,179,811,219))>35,
                  "P152 buttons show distinct on/off visual states",results)
            click(hwnd,652,198)
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
                click(hwnd,884,532)
                after_reset=snap(hwnd,args.output/"p152_mod_reset.bmp")
                check(different(before_reset,after_reset,(395,272,474,379))>15,
                      "MOD RESET resets modulation only",results)
            # Main program navigation is available from every page, even
            # if the browser is currently hidden.
            before_program=snap(hwnd,args.output/"p152_preset000.bmp")
            click(hwnd,579,198)
            next_program=snap(hwnd,args.output/"p152_preset012.bmp")
            check(different(before_program,next_program,(350,115,730,147))>10,
                  "NEXT switches sparse Bank 0 program 000 to 012",results)
            click(hwnd,230,198)
            prev_program=snap(hwnd,args.output/"p152_preset000_restored.bmp")
            check(different(next_program,prev_program,(350,115,730,147))>10,
                  "PREV switches program 012 back to 000",results)
            check(different(before_program,prev_program,(350,115,730,147))<24,
                  "PREV restores exact original bank/program",results)
            click(hwnd,751,198)
            click(hwnd,595,264)
            text_input("DRUM")
            filtered=snap(hwnd,args.output/"p152_browser_search.bmp")
            check(different(browser,filtered,(27,297,971,575))>15,
                  "separate BROWSER search filters actual SF2 rows",results)
            click(hwnd,140,323)
            selected=snap(hwnd,args.output/"p152_browser_selection.bmp")
            check(different(filtered,selected,(350,115,730,147))>10,
                  "BROWSER selection actually changes the host program",results)
            check(different(filtered,selected,(28,299,972,576))>15,
                  "P161 selected row visibly changes highlight",results)
            # File actions live outside page containers; cancellation must
            # never modify an already selected program.
            click(hwnd,852,198)
            key(0x1B)
            time.sleep(.35)
            after_rom=snap(hwnd,args.output/"p152_rom_cancel.bmp")
            check(different(selected,after_rom,(350,115,730,147))<24,
                  "ROM chooser cancel preserves current SF2 bank/program",results)
            click(hwnd,936,198)
            key(0x1B)
            time.sleep(.35)
            after_sf2=snap(hwnd,args.output/"p152_sf2_cancel.bmp")
            check(different(selected,after_sf2,(350,115,730,147))<24,
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
    print(f"P165 ORIGINAL-FACEPLATE REAL VSTGUI {'QUICK' if args.quick else 'FULL'} "
          f"{len(results)} NATIVE EDITOR INTERACTIONS PASS",flush=True)

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print(f"P18 FAIL: {type(exc).__name__}: {exc}",file=sys.stderr,flush=True)
        sys.exit(1)
