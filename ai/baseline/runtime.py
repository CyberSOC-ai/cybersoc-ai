"""Explicit model loading/lifecycle; caller verifies configured artifact hashes."""

import http.client
from pathlib import Path
import socket
import subprocess
import time

from .runner import RunnerUnavailable


class LocalRuntime:
    def __init__(self, config, log_path):
        self.config, self.log_path = config, Path(log_path)
        self.process = None
        self.log = None

    def peak_memory_bytes(self):
        """Windows lifetime peak working set of this server, including loading.

        Not GPU allocation, not total machine memory, and not isolated per case.
        """
        if not self.process or not hasattr(subprocess, "CREATE_NO_WINDOW"):
            return None
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in ("PeakWorkingSetSize", "WorkingSetSize",
                "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.K32GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(0x0400 | 0x0010, False, self.process.pid)
        if not handle:
            return None
        try:
            counters = Counters()
            counters.cb = ctypes.sizeof(counters)
            if kernel.K32GetProcessMemoryInfo(handle, ctypes.byref(counters), counters.cb):
                return counters.PeakWorkingSetSize
            return None
        finally:
            kernel.CloseHandle(handle)

    def __enter__(self):
        c = self.config
        # Do not reuse or terminate an unrelated process already on this port.
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", c["port"])) == 0:
                raise RunnerUnavailable("Configured local port is already occupied")
        self.log = self.log_path.open("wb")
        command = [str(Path(c["runtime_executable"]).resolve()),
                   "--model", str(Path(c["model_file"]).resolve()),
                   "--host", "127.0.0.1", "--port", str(c["port"]),
                   "--ctx-size", str(c["context_tokens"]), "--parallel", "1",
                   "--threads", str(c["threads"]), "--n-gpu-layers", "0",
                   "--no-context-shift"]
        self.command = command
        try:
            self.process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                stdout=self.log, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            deadline = time.monotonic() + 120
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise RunnerUnavailable("Model server exited during loading; inspect local log")
                conn = http.client.HTTPConnection("127.0.0.1", c["port"], timeout=1)
                try:
                    conn.request("GET", "/health")
                    if conn.getresponse().status == 200:
                        return self
                except OSError:
                    pass
                finally:
                    conn.close()
                time.sleep(0.2)
            raise RunnerUnavailable("Model server did not become ready")
        except BaseException:
            self.__exit__(None, None, None)
            raise

    def __exit__(self, *args):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=5)
        if self.log:
            self.log.close()
