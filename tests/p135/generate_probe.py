"""Generate a separately linked diagnostic DLL; never edit production files."""
from pathlib import Path
import hashlib,json,shutil,sys
root,out=map(Path,sys.argv[1:]);out.mkdir(parents=True,exist_ok=True)
engine=out/'engine'
shutil.copytree(root/'src/engine',engine,dirs_exist_ok=True)
# Visibility only; same members, layout and production function bodies.
for name in ['Synth.h','Emu8000.h']:
 p=engine/name;p.write_text(p.read_text().replace('private:','public:'))
p=engine/'Emu8000Box.h';p.write_text((root/'upstream/AWE32Emu/AWE32Emu/src/Emu8000Box.h').read_text().replace('private:','public:'))
p=engine/'Emu8000Box.cpp'
p.write_text(p.read_text()+r'''
#include "probe_api.h"
extern "C" void p135PeekChip(void* impl,P135Voices* out) {
    if(!impl||!out)return;
    const auto& i=*static_cast<Emu8000Box::Impl*>(impl);
    for(const auto& v:i.emu.voice) {
        out->nonzero+=v.cvcf_curr_volume!=0;
        out->envelopes+=v.env_engine_on!=0;
    }
    out->pending=static_cast<uint32_t>(i.pendingCount);
    out->frameInBlock=static_cast<uint32_t>(i.frameInBlock);
    out->chipPosition=static_cast<uint32_t>(i.emu.pos);
}
''')
s=(root/'src/vst3/Factory.cpp').read_text().replace('private:','public:')
s+=r'''
#include "probe_api.h"
extern "C" void p135PeekChip(void*,P135Voices*);
extern "C" __declspec(dllexport) int p135ReadVoices(void* audio,P135Voices* out) {
    if(!audio||!out)return 0;
    auto* p=dynamic_cast<AWE125::Processor*>(static_cast<Steinberg::Vst::IAudioProcessor*>(audio));
    if(!p)return 0;
    *out={};out->generation=p->engines_.PublishedVersion();
    auto pin=p->engines_.Read();
    if(!pin||!pin->synth)return 1;
    const auto& s=*pin->synth;
    for(const auto& v:s.m_alloc)out->allocated+=v.inUse||v.heldBySustain;
    for(const auto& n:s.CaptureHeldNotes())out->held+=n.sequence!=0;
    p135PeekChip(s.m_core.m_box.m_impl,out);
    return 1;
}
static void* volatile p135AllocationEscape=nullptr;
extern "C" __declspec(dllexport) void p135HeapControl() {
    // ETW positive controls: all outside process(), clearly marked in CSV.
    void* p=std::malloc(37);p135AllocationEscape=p;
    p=std::realloc(p,73);p135AllocationEscape=p;std::free(p);
    void* q=HeapAlloc(GetProcessHeap(),0,91);p135AllocationEscape=q;
    q=HeapReAlloc(GetProcessHeap(),0,q,131);p135AllocationEscape=q;
    HeapFree(GetProcessHeap(),0,q);p135AllocationEscape=nullptr;
}
'''
(out/'Factory.cpp').write_text(s)
files=['src/vst3/Factory.cpp','src/engine/Emu8000.cpp','src/engine/Emu8000Box.cpp','src/engine/Synth.cpp','src/engine/snd_emu8k.c']
(out/'source-hashes.json').write_text(json.dumps({x:hashlib.sha256((root/x).read_bytes()).hexdigest() for x in files},indent=2))
