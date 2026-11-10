/*
 * P66: CRT-free 32-bit Windows 95 Creative WinMM MIDI bridge.
 * Important: stock Windows 95 does not include MSVCRT.DLL. A conventional
 * MinGW executable therefore did not start on the actual 86Box guest.
 * This implementation imports ONLY KERNEL32.DLL and WINMM.DLL.
 * Do not add printf, malloc, stdio, strlen, memcpy or the CRT startup.
 */
#define WINVER 0x0400
#define _WIN32_WINNT 0x0400
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mmsystem.h>
#include "P63MidiWire.h"

static HANDLE logfd=INVALID_HANDLE_VALUE;

static void logline(const char *msg) {
    DWORD n=0,written=0;
    if(logfd==INVALID_HANDLE_VALUE)return;
    while(msg[n])++n;
    if(n) { WriteFile(logfd,msg,n,&written,NULL); FlushFileBuffers(logfd); }
}
/*
 * P220: opt-in forensic evidence, compiled ONLY into a disposable guest
 * helper for real private 77-SF2 acceptance. Original WinMM MIDI routing
 * is unchanged. Every *successfully delivered* message includes its
 * original status/data bytes in the guest's local P63LOG.TXT.
 * The ordinary P63 helper still logs only the historical generic line.
 * Do not add printf/CRT or ship this guest executable as a product.
 */
static void log_delivered_message(DWORD m) {
#ifdef AWE125_P220_MIDI_EVIDENCE
    static const char hex[]="0123456789ABCDEF";
    char line[]="MIDI DELIVERED 0x00 0x00 0x00\r\n";
    unsigned char a=(unsigned char)(m&255u);
    unsigned char b=(unsigned char)((m>>8)&255u);
    unsigned char c=(unsigned char)((m>>16)&255u);
    line[17]=hex[a>>4];line[18]=hex[a&15u];
    line[22]=hex[b>>4];line[23]=hex[b&15u];
    line[27]=hex[c>>4];line[28]=hex[c&15u];
    logline(line);
#else
    (void)m;
    logline("MIDI DELIVERED\r\n");
#endif
}

static DWORD p74_uart_debug_bytes=0;
static void log_byte(unsigned char b) {
    static const char hex[]="0123456789ABCDEF";
    char line[]="P74 UART RX 0x00\r\n";
    if(p74_uart_debug_bytes>=32)return;
    line[14]=hex[b>>4];
    line[15]=hex[b&15u];
    logline(line);
}
static char uppercase(char c) {
    if(c>='a' && c<='z')return (char)(c-'a'+'A');
    return c;
}
static int name_contains(const char *haystack,const char *needle) {
    int i,j;
    for(i=0;haystack[i];++i) {
        for(j=0;needle[j] && haystack[i+j] && uppercase(haystack[i+j])==needle[j];++j){}
        if(!needle[j])return 1;
    }
    return 0;
}
static int open_original_creative(HMIDIOUT *midi) {
    UINT i,n=midiOutGetNumDevs();
    for(i=0;i<n;++i) {
        MIDIOUTCAPSA caps={0};
        MMRESULT result;
        if(midiOutGetDevCapsA(i,&caps,sizeof(caps))!=MMSYSERR_NOERROR)
            continue;
        logline("MIDI device: ");logline(caps.szPname);logline("\r\n");
        if(!name_contains(caps.szPname,"AWE") ||
           !name_contains(caps.szPname,"SYNTH"))continue;
        result=midiOutOpen(midi,i,0,0,CALLBACK_NULL);
        if(result!=MMSYSERR_NOERROR) {
            logline("ERROR Creative midiOutOpen\r\n");
            return 0;
        }
        logline("SELECTED original Creative AWE Synth\r\n");
        return 1;
    }
    logline("ERROR No original Creative AWE MIDI Synth device\r\n");
    return 0;
}
static HANDLE open_com1(void) {
    HANDLE h=CreateFileA("COM1",GENERIC_READ,0,NULL,OPEN_EXISTING,0,NULL);
    DCB dcb={0};
    COMMTIMEOUTS t={0};
    if(h==INVALID_HANDLE_VALUE)return h;
    dcb.DCBlength=sizeof(dcb);
    if(!GetCommState(h,&dcb))goto fail;
    dcb.BaudRate=CBR_115200;
    dcb.ByteSize=8;
    dcb.Parity=NOPARITY;
    dcb.StopBits=ONESTOPBIT;
    dcb.fBinary=TRUE;
    dcb.fOutxCtsFlow=FALSE;
    dcb.fOutxDsrFlow=FALSE;
    dcb.fOutX=FALSE;
    dcb.fInX=FALSE;
    if(!SetCommState(h,&dcb))goto fail;
    t.ReadIntervalTimeout=MAXDWORD;
    t.ReadTotalTimeoutConstant=50;
    if(!SetCommTimeouts(h,&t))goto fail;
    PurgeComm(h,PURGE_RXCLEAR);
    return h;
fail:
    CloseHandle(h);
    return INVALID_HANDLE_VALUE;
}
static void run(void) {
    HMIDIOUT midi=0;
    HANDLE com;
    P63MidiDecoder decoder;
    uint32_t message=0;
    DWORD count=0;
    unsigned char b=0;
    logfd=CreateFileA("C:\\AWE32\\P63LOG.TXT",GENERIC_WRITE,
                      FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    logline("P66 CRT-free original Creative Win95 bridge startup\r\n");
    if(!open_original_creative(&midi))goto done;
    com=open_com1();
    if(com==INVALID_HANDLE_VALUE) {
        logline("ERROR Cannot open COM1\r\n");
        midiOutClose(midi);
        goto done;
    }
    p63_midi_reset(&decoder);
    logline("READY COM1 115200 8N1\r\n");
    while(1) {
        int decoded;
        count=0;
        if(!ReadFile(com,&b,1,&count,NULL)) {
            logline("ERROR COM1 read\r\n");
            break;
        }
        if(count!=1){Sleep(1);continue;}
        ++p74_uart_debug_bytes;
        log_byte(b);
        decoded=p63_midi_feed(&decoder,b,&message);
        if(decoded<0)logline("P74 UART FRAME REJECTED\r\n");
        if(decoded==1) {
            if(midiOutShortMsg(midi,(DWORD)message)!=MMSYSERR_NOERROR) {
                logline("ERROR Original Creative midiOutShortMsg\r\n");
                break;
            }
            log_delivered_message((DWORD)message);
        }
    }
    midiOutReset(midi);
    CloseHandle(com);
    midiOutClose(midi);
done:
    if(logfd!=INVALID_HANDLE_VALUE){FlushFileBuffers(logfd);CloseHandle(logfd);}
}
void WINAPI p63_entry(void) {
    /* P73 independent entrypoint witness: leave a durable FAT root marker
     * before opening WinMM, COM1 or waiting for inbound MIDI. */
    HANDLE mark=CreateFileA("C:\\P73MIDI.TXT",GENERIC_WRITE,
                         FILE_SHARE_READ,NULL,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,NULL);
    if(mark!=INVALID_HANDLE_VALUE) {
        static const char literal[]="P73 WIN95 MIDI ENTRYPOINT EXECUTED\r\n";
        DWORD written=0;
        WriteFile(mark,literal,sizeof(literal)-1,&written,NULL);
        FlushFileBuffers(mark);
        CloseHandle(mark);
    }
    run();
    ExitProcess(0);
}
