"""Build-only source mutations; never overwrite production translation units."""
from pathlib import Path
import sys

root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
mutations={
    'bank':('Synth.cpp','!selection.bankMsbTouched','selection.bankMsb == 0'),
    'amp':('Synth.cpp','shortenAttack(v.envvol,v.atkhldv,m_guiControls[0]);','/* test-only: attack overlay disconnected */'),
    'filter':('Synth.cpp','if(filterEdit>0.f && (v.pefe&0xFFu)==0)', 'if(false && filterEdit>0.f && (v.pefe&0xFFu)==0)'),
    'loop':('Synth.cpp','((bank && bank->version==SoundFont::Version::Sf2) ||', '((false) ||'),
    'end':('SoundFont.cpp','int64_t(s.end)+g.Get(Gen::EndAddrsOffset,0)+\n        int64_t(32768)*g.Get(Gen::EndAddrsCoarseOffset,0)', 'int64_t(s.end)'),
    'rom':('Synth.cpp','if (sampleInRom && ((drv', 'if (false && sampleInRom && ((drv'),
    'pedal':('Synth.cpp','if (m_channels[channel].sustain)\n        {', 'if (false && m_channels[channel].sustain)\n        {'),
    'headroom':('Synth.cpp','AWE125::FxSendLevel::Apply(originalReverb,m_guiControls[10])', 'AWE125::FxSendLevel::Apply(originalReverb,std::min(m_guiControls[10],0.5f))'),
}
for mutant,(file,old,new) in mutations.items():
    source=(root/'src/engine'/file).read_text()
    if source.count(old)!=1:raise RuntimeError('mutation anchor not unique: '+mutant)
    folder=out/mutant;folder.mkdir(exist_ok=True)
    (folder/file).write_text(source.replace(old,new))
