"""Own a benchmark process tree, including native launcher children, on Windows.

The first thread stays suspended until the process belongs to a kill-on-close
job. No process may escape between launch and assignment. This controls process
lifetime only; use an isolated host and account for unfamiliar executables.
"""
import ctypes
from ctypes import wintypes
import os
import subprocess


class BasicLimits(ctypes.Structure):
    _fields_ = [
        ("process_time", ctypes.c_longlong), ("job_time", ctypes.c_longlong),
        ("flags", wintypes.DWORD), ("min_working_set", ctypes.c_size_t),
        ("max_working_set", ctypes.c_size_t), ("active_processes", wintypes.DWORD),
        ("affinity", ctypes.c_size_t), ("priority", wintypes.DWORD),
        ("scheduling", wintypes.DWORD),
    ]


class ExtendedLimits(ctypes.Structure):
    _fields_ = [
        ("basic", BasicLimits), ("io_counters", ctypes.c_ulonglong * 6),
        ("process_memory", ctypes.c_size_t), ("job_memory", ctypes.c_size_t),
        ("peak_process_memory", ctypes.c_size_t), ("peak_job_memory", ctypes.c_size_t),
    ]


class WindowsJobProcess:
    def __init__(self, command, output):
        import _winapi
        import msvcrt

        self._api = _winapi
        self.args = command
        self.returncode = None
        self._process = None
        self._job = None
        self._kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self._kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self._kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self._kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
        self._kernel.SetInformationJobObject.restype = wintypes.BOOL
        self._kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self._kernel.AssignProcessToJobObject.restype = wintypes.BOOL
        self._kernel.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        self._kernel.TerminateJobObject.restype = wintypes.BOOL
        self._kernel.ResumeThread.argtypes = [wintypes.HANDLE]
        self._kernel.ResumeThread.restype = wintypes.DWORD
        thread = None
        try:
            self._job = self._kernel.CreateJobObjectW(None, None)
            if not self._job:
                raise ctypes.WinError(ctypes.get_last_error())
            limits = ExtendedLimits()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self._kernel.SetInformationJobObject(self._job, 9, ctypes.byref(limits), ctypes.sizeof(limits)):
                raise ctypes.WinError(ctypes.get_last_error())
            with open(os.devnull, "rb") as stdin:
                input_handle = msvcrt.get_osfhandle(stdin.fileno())
                output_handle = msvcrt.get_osfhandle(output.fileno())
                handles = [input_handle, output_handle]
                original = [os.get_handle_inheritable(handle) for handle in handles]
                startup = subprocess.STARTUPINFO()
                startup.dwFlags = subprocess.STARTF_USESTDHANDLES
                startup.hStdInput = input_handle
                startup.hStdOutput = output_handle
                startup.hStdError = output_handle
                startup.lpAttributeList = {"handle_list": handles}
                try:
                    for handle in handles:
                        os.set_handle_inheritable(handle, True)
                    self._process, thread, self.pid, _ = _winapi.CreateProcess(
                        command[0], subprocess.list2cmdline(command), None, None, True,
                        0x4 | subprocess.CREATE_NO_WINDOW, None, None, startup)
                finally:
                    for handle, inherited in zip(handles, original):
                        os.set_handle_inheritable(handle, inherited)
            if not self._kernel.AssignProcessToJobObject(self._job, self._process):
                raise ctypes.WinError(ctypes.get_last_error())
            if self._kernel.ResumeThread(thread) == 0xFFFFFFFF:
                raise ctypes.WinError(ctypes.get_last_error())
        except BaseException:
            if self._process is not None:
                _winapi.TerminateProcess(self._process, 1)
                _winapi.WaitForSingleObject(self._process, 5000)
            self.close()
            raise
        finally:
            if thread is not None:
                _winapi.CloseHandle(thread)

    def poll(self):
        if self.returncode is None and self._api.WaitForSingleObject(self._process, 0) == self._api.WAIT_OBJECT_0:
            self.returncode = self._api.GetExitCodeProcess(self._process)
        return self.returncode

    def wait(self, timeout=None):
        milliseconds = self._api.INFINITE if timeout is None else max(0, int(timeout * 1000))
        if self._api.WaitForSingleObject(self._process, milliseconds) == self._api.WAIT_TIMEOUT:
            raise subprocess.TimeoutExpired(self.args, timeout)
        self.returncode = self._api.GetExitCodeProcess(self._process)
        return self.returncode

    def terminate(self):
        if self._job is not None and not self._kernel.TerminateJobObject(self._job, 1):
            raise ctypes.WinError(ctypes.get_last_error())

    kill = terminate

    def close(self):
        if self._job is not None:
            self._api.CloseHandle(self._job)
            self._job = None
        if self._process is not None:
            self._api.CloseHandle(self._process)
            self._process = None
