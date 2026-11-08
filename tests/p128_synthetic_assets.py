# Synthetic sine samples and a zero ROM only. No proprietary data.
from pathlib import Path
import struct,math,sys
D=Path(sys.argv[1]);D.mkdir(parents=True,exist_ok=True)
def u16(*x):return struct.pack('<'+'H'*len(x),*(a&65535 for a in x))
def u32(*x):return struct.pack('<'+'I'*len(x),*x)
def name(s):return s.encode()[:20].ljust(20,b'\0')
def chunk(k,b):return k.encode()+u32(len(b))+b+(b'\0' if len(b)%2 else b'')
def lst(k,b):return chunk('LIST',k.encode()+b)
N=4096;keys=[(b,p) for b in (0,5,128) for p in (0,7,9)]
for stress in (False,True):
 smpl=b'';phdr=b'';pbag=b'';pgen=b'';inst=b'';ibag=b'';igen=b'';shdr=b''
 for i,(b,p) in enumerate(keys):
  start=len(smpl)//2
  period=[64,53,37,83,43,29,97,67,41][i]
  smpl+=b''.join(u16(int(11000*math.sin(2*math.pi*(n%period)/period))) for n in range(N))+u16(*([0]*46))
  phdr+=name(f'B{b}P{p}')+u16(p,b,i)+u32(0,0,0)
  pbag+=u16(i,0);pgen+=u16(41,i)
  inst+=name(f'I{i}')+u16(i)
  ibag+=u16(i*(12 if stress else 6),0)
  if stress:igen+=u16(25,-12000,26,4300,27,-12000,28,4300,29,1000,30,4300)
  igen+=u16(34,-11959,38,-3600,54,1,58,60,17,0,53,i)
  shdr+=name(f'S{i}')+u32(start,start+N,start+64,start+N-64,44100)+bytes([60,0])+u16(0,1)
 phdr+=name('EOP')+u16(0,0,len(keys))+u32(0,0,0)
 pbag+=u16(len(keys),0);inst+=name('EOI')+u16(len(keys));ibag+=u16(len(keys)*(12 if stress else 6),0)
 shdr+=name('EOS')+u32(0,0,0,0,0)+bytes([0,0])+u16(0,1)
 info=chunk('ifil',u16(2,1))+chunk('INAM',b'Independent synthetic P128\0')
 pdta=b''.join(chunk(k,v) for k,v in [('phdr',phdr),('pbag',pbag),('pmod',bytes(10)),('pgen',pgen),('inst',inst),('ibag',ibag),('imod',bytes(10)),('igen',igen),('shdr',shdr)])
 b=b'sfbk'+lst('INFO',info)+lst('sdta',chunk('smpl',smpl))+lst('pdta',pdta)
 (D/('bank-filter-stress.sf2' if stress else 'bank.sf2')).write_bytes(chunk('RIFF',b))
(D/'zero.rom').write_bytes(bytes(1048576))
print('9 distinct bank/program waves (including GM drum channel); generated from sine formula; zero-filled synthetic ROM')

# P176: independent 86Box/VST3 loop-mode fixtures with a 16-word
# post-loop tail. Reuse the already falsified P170 sample-mode oracle.
# All tones are generated, public-domain-equivalent mathematical signals;
# no original Wave-ROM, SBK or user SF2 data leaves the local machine.
from p170_audio_oracles import DRY, sf2
for loop_mode in (0, 1, 3):
    generators = [pair for pair in DRY if pair[0] not in (38, 54)]
    generators += [(38, 0), (54, loop_mode)]
    sf2(D / f'loop-{loop_mode}.sf2', generators, loop_end=4080)
