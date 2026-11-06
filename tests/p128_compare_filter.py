"""Compare actual chip PCM, retaining both runs as evidence outside the checkout."""
from pathlib import Path
import hashlib
import subprocess
import sys
cached, uncached, assets, output = sys.argv[1:]
output = Path(output)
output.mkdir(parents=True, exist_ok=True)
paths = [output / 'cached.pcm', output / 'uncached.pcm']
for executable, path in zip((cached, uncached), paths):
    path.unlink(missing_ok=True)
    subprocess.run([executable, assets, str(path)], check=True)
a, b = (p.read_bytes() for p in paths)
assert a and a == b, 'coefficient cache changed actual PCM'
print(f'PASS {len(a)} bytes bit-exact PCM, SHA256={hashlib.sha256(a).hexdigest()}')
