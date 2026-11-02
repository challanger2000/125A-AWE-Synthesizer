import errno
import importlib.util
import os
from pathlib import Path
import tempfile
import threading
import time
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "tools" / "p64_original_win95_midi_trial.py"
# imports local sibling tools as this is also a standalone script module
import sys
sys.path.insert(0,str(SOURCE.parent))
spec=importlib.util.spec_from_file_location("p64",SOURCE)
p64=importlib.util.module_from_spec(spec)
spec.loader.exec_module(p64)


@unittest.skipUnless(hasattr(os,"mkfifo"),"Linux FIFO is required")
class P64Fifo(unittest.TestCase):
    def test_guest_receive_pipe(self):
        with tempfile.TemporaryDirectory() as temp:
            base=Path(temp)/"awe-midi"
            receiver=Path(str(base)+".in")
            os.mkfifo(receiver)
            observed=[]
            ready=threading.Event()
            def reader():
                fd=os.open(receiver,os.O_RDONLY|os.O_NONBLOCK)
                ready.set()
                try:
                    deadline=time.monotonic()+3
                    while time.monotonic()<deadline and not observed:
                        try:
                            b=os.read(fd,6)
                            if b:observed.append(b)
                        except BlockingIOError:
                            pass
                        time.sleep(.01)
                finally:
                    os.close(fd)
            th=threading.Thread(target=reader)
            th.start()
            self.assertTrue(ready.wait(2))
            fd=p64.connect_linux_86box_fifo(base,3)
            try:
                os.write(fd,bytes([0xA5,0x5A,0x90,48,100,0x90^48^100^0x5A]))
            finally:
                os.close(fd)
            th.join(5)
            self.assertEqual(len(observed),1)
            self.assertEqual(len(observed[0]),6)


if __name__=="__main__":
    unittest.main()
