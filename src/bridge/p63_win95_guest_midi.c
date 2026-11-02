/*
 * 125A P63 — native Windows 95 x86 bridge. Runs INSIDE the 86Box guest.
 * COM1 comes from 86Box's host-local serial Named Pipe device.
 * Crucially: MIDI goes through the ORIGINAL Creative Windows 95 WinMM
 * endpoint, NOT the 125A P26 SoundFont interpreter and NOT FluidSynth.
 * AWECP32 must first load the user's bank into the original driver.
 */
#ifndef WINVER
#define WINVER 0x0400
#endif
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0400
#endif
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <mmsystem.h>
#include <stdio.h>
#include <string.h>
#include "P63MidiWire.h"

static int is_awe_synth(const char *source) {
    char name[MAXPNAMELEN + 1];
    size_t i;
    for(i=0;i<MAXPNAMELEN && source[i];++i) {
        unsigned char c=(unsigned char)source[i];
        name[i]=(char)((c>='a' && c<='z')?(c-'a'+'A'):c);
    }
    name[i]=0;
    /* Never silently route to Microsoft's GM synth or an external FM port. */
    return strstr(name,"AWE")!=NULL && strstr(name,"SYNTH")!=NULL;
}

static int open_original_creative(HMIDIOUT *midi) {
    UINT i,n=midiOutGetNumDevs();
    MIDIOUTCAPSA caps;
    for(i=0;i<n;++i) {
        memset(&caps,0,sizeof(caps));
        if(midiOutGetDevCapsA(i,&caps,sizeof(caps))!=MMSYSERR_NOERROR)
            continue;
        printf("MIDI device %u: %s\n",i,caps.szPname);
        if(is_awe_synth(caps.szPname)) {
            MMRESULT result=midiOutOpen(midi,i,0,0,CALLBACK_NULL);
            if(result==MMSYSERR_NOERROR) {
                printf("Selected original Creative AWE synthesizer: %s\n",caps.szPname);
                return 1;
            }
            fprintf(stderr,"Creative AWE device found but midiOutOpen failed: %u\n",result);
            return 0;
        }
    }
    fprintf(stderr,"No original Creative AWE MIDI Synth device is installed.\n");
    return 0;
}

static HANDLE open_com1(void) {
    HANDLE h=CreateFileA("COM1",GENERIC_READ,0,NULL,OPEN_EXISTING,0,NULL);
    DCB dcb;
    COMMTIMEOUTS timeouts;
    if(h==INVALID_HANDLE_VALUE)return h;
    memset(&dcb,0,sizeof(dcb));
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
    memset(&timeouts,0,sizeof(timeouts));
    timeouts.ReadIntervalTimeout=MAXDWORD;
    timeouts.ReadTotalTimeoutConstant=50;
    if(!SetCommTimeouts(h,&timeouts))goto fail;
    PurgeComm(h,PURGE_RXCLEAR);
    return h;
fail:
    CloseHandle(h);
    return INVALID_HANDLE_VALUE;
}

int main(int argc,char **argv) {
    HMIDIOUT midi=0;
    HANDLE com;
    P63MidiDecoder decoder;
    uint32_t message=0;
    unsigned long received=0;
    DWORD count;
    unsigned char byte;
    int rc;
    (void)argc;(void)argv;
    printf("125A P63 Win95 original-Creative MIDI bridge; COM1 115200 8N1\n");
    if(!open_original_creative(&midi))return 2;
    com=open_com1();
    if(com==INVALID_HANDLE_VALUE) {
        fprintf(stderr,"Cannot open COM1 (86Box serial Named Pipe required).\n");
        midiOutClose(midi);
        return 3;
    }
    p63_midi_reset(&decoder);
    printf("Ready; MIDI bytes are forwarded to the Creative driver.\n");
    fflush(stdout);
    while(1) {
        count=0;
        if(!ReadFile(com,&byte,1,&count,NULL)) {
            fprintf(stderr,"COM1 read failed.\n");
            break;
        }
        if(count!=1) {Sleep(1);continue;}
        rc=p63_midi_feed(&decoder,byte,&message);
        if(rc==1) {
            MMRESULT m=midiOutShortMsg(midi,(DWORD)message);
            if(m!=MMSYSERR_NOERROR) {
                fprintf(stderr,"Creative driver rejected MIDI message (%u).\n",m);
                break;
            }
            ++received;
            if((received&63ul)==0)fflush(stdout);
        }
    }
    midiOutReset(midi);
    CloseHandle(com);
    midiOutClose(midi);
    return 4;
}
