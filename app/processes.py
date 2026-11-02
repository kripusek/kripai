"""Blokada pojedynczej instancji i Windows Job Object dla procesu modelu."""
import os
from . import config

class InstanceLock:
    def __enter__(self):
        config.DATA.mkdir(parents=True,exist_ok=True)
        self.file=(config.DATA/'instance.lock').open('a+b')
        self.file.seek(0,2)
        if self.file.tell()==0:self.file.write(b'0');self.file.flush()
        self.file.seek(0)
        try:
            if os.name=='nt':
                import msvcrt
                msvcrt.locking(self.file.fileno(),msvcrt.LK_NBLCK,1)
            else:
                import fcntl
                fcntl.flock(self.file,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except OSError:
            self.file.close();raise RuntimeError('KripAI jest uruchomione. Najpierw użyj WYLACZ.cmd.')
        return self
    def __exit__(self,*args):self.file.close()


class ModelJob:
    def __init__(self,memory_limit=None):
        self.handle=None
        if os.name!='nt':return
        import ctypes as c
        from ctypes import wintypes as w
        class BASIC(c.Structure):
            _fields_=[('ProcessTime',c.c_longlong),('JobTime',c.c_longlong),('Flags',w.DWORD),('MinWS',c.c_size_t),('MaxWS',c.c_size_t),('Active',w.DWORD),('Affinity',c.c_size_t),('Priority',w.DWORD),('Scheduling',w.DWORD)]
        class IO(c.Structure):_fields_=[(n,c.c_ulonglong) for n in ('ReadOps','WriteOps','OtherOps','ReadBytes','WriteBytes','OtherBytes')]
        class LIMIT(c.Structure):_fields_=[('Basic',BASIC),('IO',IO),('ProcessMemory',c.c_size_t),('JobMemory',c.c_size_t),('PeakProcess',c.c_size_t),('PeakJob',c.c_size_t)]
        self.kernel=c.WinDLL('kernel32',use_last_error=True)
        self.kernel.CreateJobObjectW.argtypes=[c.c_void_p,w.LPCWSTR];self.kernel.CreateJobObjectW.restype=w.HANDLE
        self.kernel.SetInformationJobObject.argtypes=[w.HANDLE,c.c_int,c.c_void_p,w.DWORD];self.kernel.SetInformationJobObject.restype=w.BOOL
        self.kernel.AssignProcessToJobObject.argtypes=[w.HANDLE,w.HANDLE];self.kernel.AssignProcessToJobObject.restype=w.BOOL
        self.kernel.CloseHandle.argtypes=[w.HANDLE];self.kernel.CloseHandle.restype=w.BOOL
        handle=self.kernel.CreateJobObjectW(None,None)
        if not handle:raise c.WinError(c.get_last_error())
        limit=LIMIT();limit.Basic.Flags=0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if memory_limit:
            limit.Basic.Flags |= 0x100  # JOB_OBJECT_LIMIT_PROCESS_MEMORY
            limit.ProcessMemory=memory_limit
        if not self.kernel.SetInformationJobObject(handle,9,c.byref(limit),c.sizeof(limit)):
            self.kernel.CloseHandle(handle);raise c.WinError(c.get_last_error())
        self.handle=handle
    def attach(self,process):
        if self.handle and not self.kernel.AssignProcessToJobObject(self.handle,int(process._handle)):
            import ctypes
            process.kill();process.wait();raise ctypes.WinError(ctypes.get_last_error())
    def close(self):
        if self.handle:self.kernel.CloseHandle(self.handle);self.handle=None
