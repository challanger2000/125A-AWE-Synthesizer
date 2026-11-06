# Test-only translation-unit extraction: no production source or header is modified.
# Keep the Processor implementation, remove GUI/controller/plugin entry code,
# expose fields for deterministic scheduling, and add no-op-by-default pause hooks.
from pathlib import Path
import sys
import hashlib
s=Path(sys.argv[1]).read_text()
p=s[:s.index('class Controller final')]
p=p.replace('#include "PresetBrowserView.h"','').replace('#include "vstgui/plugin-bindings/vst3editor.h"','')
p=p.replace('namespace AWE125 {','extern void auditHook(const char*);\nnamespace AWE125 {',1)
p=p.replace('private:', 'public:')
hooks={
'        std::unique_ptr<Synth> prepared;\n        bool loadedSf2=false,loadedGm=false;':'        auditHook("recall_prepared_epoch");\n        std::unique_ptr<Synth> prepared;\n        bool loadedSf2=false,loadedGm=false;',
'            const auto latestBank=bankOrder_.Latest();':'            const auto latestBank=bankOrder_.Latest();\n            auditHook("recall_bank_snapshot");',
'        ApplyPendingGlobalBank(synth_);\n        ApplyPendingProgramIntents(synth_);':'        auditHook("block_pin");\n        ApplyPendingGlobalBank(synth_);\n        ApplyPendingProgramIntents(synth_);',
'            RealtimeStateVersion::Writer write(\n                rtStateVersion_, RealtimeStateVersion::Domain::Audio,persisted);':'            auditHook("parameter_before_writer");\n            RealtimeStateVersion::Writer write(\n                rtStateVersion_, RealtimeStateVersion::Domain::Audio,persisted);',
'        if(bankOrder_.Latest().sequence<=lastGlobalBankSequence_)return;':'        if(bankOrder_.Latest().sequence<=lastGlobalBankSequence_)return;\n        auditHook("pending_bank_before_writer");',
'        if(!pending)return;':'        if(!pending)return;\n        auditHook("pending_program_before_writer");',
'        if(!consistent) {':'        if(!consistent) {\n            auditHook("save_fallback");',
'                    if(AllowEmuNoteOn(entry&&':'                    auditHook("note_before_dispatch");\n                    if(AllowEmuNoteOn(entry&&'
}
for a,b in hooks.items():
 assert a in p,a
 p=p.replace(a,b)
p+='\n} // namespace AWE125\n'
Path(sys.argv[2]).write_text(p)
print('Factory.cpp sha256',hashlib.sha256(s.encode()).hexdigest())
