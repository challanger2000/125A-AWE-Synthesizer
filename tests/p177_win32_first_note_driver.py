#!/usr/bin/env python3
"""P177: real Win32 GetOpenFileName UI → host gesture → first exported-DLL PCM."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
if os.name!="nt":
    raise SystemExit("P177 NOT RUN: interactive Windows required")
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"tools"))
import p165_original_faceplate_editor_acceptance as gui
u=gui.u
u.GetClassNameW.restype=ctypes.c_int
u.GetClassNameW.argtypes=[wintypes.HWND,ctypes.c_wchar_p,ctypes.c_int]
def windows(pid,name):
    found=[]
    CB=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    def visit(hwnd,_):
        p=wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd,ctypes.byref(p))
        if p.value!=pid or not u.IsWindowVisible(hwnd):return True
        buf=ctypes.create_unicode_buffer(128)
        u.GetClassNameW(hwnd,buf,128)
        if buf.value==name:found.append(hwnd)
        return True
    cb=CB(visit)
    u.EnumWindows(cb,0)
    return found
def wait(predicate,seconds,what):
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        value=predicate()
        if value:return value
        time.sleep(.15)
    raise RuntimeError(f"P177 {what} timed out")
def alt_n():
    u.keybd_event(0x12,0,0,None)
    try:gui.key(ord("N"))
    finally:u.keybd_event(0x12,0,2,None)
def main():
    if len(sys.argv)!=4:raise ValueError("Usage: driver HOST.exe VST3.dll ASSET_DIR")
    host,plugin,assets=[Path(x).resolve() for x in sys.argv[1:]]
    sf2=assets/"bank.sf2"
    if not host.is_file() or not plugin.is_file() or not sf2.is_file():
        raise RuntimeError("P177 real host/plugin/synthetic SF2 missing")
    gui.ensure_full_desktop()
    with tempfile.TemporaryDirectory(prefix="125a_p177_") as temp:
        env=os.environ.copy()
        appdata=Path(temp)/"APPDATA"
        appdata.mkdir()
        env["APPDATA"]=str(appdata)
        proc=subprocess.Popen([str(host),str(plugin),str(assets)],
                              env=env,stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,text=True)
        try:
            hwnd=wait(lambda:(windows(proc.pid,"125A_P177_FirstNote_Host") or [None])[0],
                      15,"real native VST3 editor")
            time.sleep(.5)
            gui.click(hwnd,936,198) # actual VSTGUI SF2 button
            dlg=wait(lambda:(windows(proc.pid,"#32770") or [None])[0],8,
                     "native GetOpenFileName dialog")
            u.SetForegroundWindow(dlg)
            time.sleep(.2)
            alt_n() # File Name accelerator in Windows Common File Open dialog
            gui.text_input(str(sf2))
            gui.key(0x0D)
            wait(lambda:not windows(proc.pid,"#32770"),12,
                 "file chooser close after genuine SF2 selection")
            time.sleep(1.0)
            gui.click(hwnd,579,198) # real preset NEXT: 0->7 (sparse bank)
            time.sleep(.45)
            if not u.PostMessageW(hwnd,0x8000+77,0,0):
                raise RuntimeError("P177 native host signal failed")
            stdout,_=proc.communicate(timeout=20)
            print(stdout,flush=True)
            if proc.returncode!=0 or "P177_GUI_PCM_PASS" not in stdout:
                raise RuntimeError(f"P177 real end-to-end PCM FAIL: {proc.returncode}")
            print("P177_PASS native_file_picker/controller/host_edit/first_PCM",flush=True)
        finally:
            if proc.poll() is None:
                proc.terminate()
                try:proc.wait(timeout=5)
                except subprocess.TimeoutExpired:proc.kill()
if __name__=="__main__":
    try:main()
    except Exception as e:
        print(f"P177_NATIVE_UI_FAIL: {type(e).__name__}: {e}",
              file=sys.stderr,flush=True)
        sys.exit(1)
