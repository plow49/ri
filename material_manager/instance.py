"""OS-held single instance lock; released even after a crash."""
import os
import time
from pathlib import Path
import storage

class InstanceLock:
    def __init__(self):self.file=None
    def acquire(self,timeout=0):
        directory=storage.data_directory();directory.mkdir(parents=True,exist_ok=True)
        self.file=open(directory/'instance.lock','a+b')
        self.file.seek(0,2)
        if self.file.tell()==0:self.file.write(b'0');self.file.flush()
        deadline=time.monotonic()+timeout
        while True:
            try:
                self.file.seek(0)
                if os.name=='nt':
                    import msvcrt
                    msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
                else:
                    import fcntl
                    fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
                return True
            except OSError:
                if time.monotonic()>=deadline:self.file.close();self.file=None;return False
                time.sleep(.1)
    def release(self):
        if self.file:self.file.close();self.file=None
