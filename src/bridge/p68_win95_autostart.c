/*
 * P68: Windows 95 native startup diagnostic and Creative bridge launcher.
 * CRT-free: imports kernel32.dll only. WIN.INI [windows] run= invokes it.
 * Creates a short diagnostic file BEFORE attempting the MIDI agent.
 * This avoids the GUI scancode race observed in P67.
 */
#define WINVER 0x0400
#define _WIN32_WINNT 0x0400
#define WIN32_LEAN_AND_MEAN
#include <windows.h>

static HANDLE log_file = INVALID_HANDLE_VALUE;
static void emit(const char *str) {
    DWORD len=0,written=0;
    if(log_file==INVALID_HANDLE_VALUE)return;
    while(str[len])++len;
    if(len)WriteFile(log_file,str,len,&written,NULL);
}
static void hex32(DWORD n) {
    char buf[11]="0x00000000";
    static const char abc[]="0123456789ABCDEF";
    int shift;
    for(shift=0;shift<8;shift++)
        buf[2+shift]=abc[(n>>(28-4*shift))&15u];
    emit(buf);
}
void WINAPI p68_entry(void) {
    const char *exe="C:\\AWE32\\P63MIDI.EXE";
    STARTUPINFOA si={0};
    PROCESS_INFORMATION pi={0};
    DWORD err=0;
    /* Independent, short-name root marker: proves the Win95 PE entrypoint
     * has actually executed even when the AWE32 directory log is absent. */
    HANDLE root=CreateFileA("C:\\P71ROOT.TXT",GENERIC_WRITE,
                  FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(root!=INVALID_HANDLE_VALUE) {
        static const char marker[]="P71 ENTRYPOINT EXECUTED\r\n";
        DWORD written=0;
        WriteFile(root,marker,sizeof(marker)-1,&written,NULL);
        FlushFileBuffers(root);
        CloseHandle(root);
    }
    log_file=CreateFileA("C:\\AWE32\\P68BOOT.LOG",GENERIC_WRITE,
                  FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    emit("P68 WIN95 AUTOSTART LOADED\r\n");
    si.cb=sizeof(si);
    if(CreateProcessA(exe,NULL,NULL,NULL,FALSE,CREATE_NEW_CONSOLE,
                      NULL,NULL,&si,&pi)) {
        emit("P63 CREATEPROCESS SUCCESS pid=");
        hex32(pi.dwProcessId);emit("\r\n");
        {
            DWORD wait=WaitForSingleObject(pi.hProcess,1000);
            DWORD status=0;
            if(wait==WAIT_TIMEOUT) emit("P63 STILL RUNNING AFTER 1 SEC\r\n");
            else if(wait==WAIT_OBJECT_0) {
                emit("P63 EXITED BEFORE 1 SEC status=");
                if(GetExitCodeProcess(pi.hProcess,&status)) hex32(status);
                else emit("unknown");
                emit("\r\n");
            } else {
                emit("P63 WAIT ERROR=");hex32(GetLastError());emit("\r\n");
            }
        }
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
    } else {
        err=GetLastError();
        emit("P63 CREATEPROCESS ERROR=");
        hex32(err);emit("\r\n");
    }
    if(log_file!=INVALID_HANDLE_VALUE) {
        FlushFileBuffers(log_file);
        CloseHandle(log_file);
    }
    /* 71 is a deliberate Win95 COMMAND.COM exit-code probe.  It must be
     * visible in the Startup .BAT independently of any FAT writeback. */
    ExitProcess(71);
}
