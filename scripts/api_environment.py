"""API 查证运行环境：按需安装缺失组件，保留离线与失败回退。"""
from __future__ import annotations

import hashlib
import importlib
import os
import platform
import site
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

_LOCK = threading.Lock()
_FAILED_UNTIL: dict[str, float] = {}
_OFF = {"off", "false", "0"}
_RELEASE = "https://github.com/ip7z/7zip/releases/download/26.05/"
_SEVENZIP_FILES = {
    "7zr.exe": "9bf582b894dfa665f852d7e9112b02290a1c303c2d95a21fcdc41ffcb03143b7",
    "7z2605-x64.exe": "fd99e86f57d8f429ef5ed045bf98315af962e2309b0f1ba87a147a44c71647d0",
    "7z.exe": "94205cfc054dd3bbeb978905bc619a65b3f04e9e73bb2717841110b6f46d962e",
    "7z.dll": "78bf6b668d75801e3aa180b4ccb16e6d8395fba80dec8a065055bb6f8dfabb82",
}


class SetupCancelled(Exception):
    """用户取消了自动配置。"""


@contextmanager
def _setup_lock(cancelled: Callable[[], bool] | None):
    """同时串行化同进程线程和不同客户端进程中的安装。"""
    deadline = time.monotonic() + 200
    while not _LOCK.acquire(timeout=0.2):
        if (cancelled and cancelled()) or time.monotonic() >= deadline:
            yield False
            return
    handle = None
    locked = False
    try:
        try:
            root = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache") / "solidworks-automation"
            root.mkdir(parents=True, exist_ok=True)
            handle = (root / "api-setup.lock").open("a+b")
            if handle.seek(0, os.SEEK_END) == 0:
                handle.write(b"0")
                handle.flush()
            while not locked:
                handle.seek(0)
                try:
                    if os.name == "nt":
                        import msvcrt
                        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    locked = True
                except OSError:
                    if (cancelled and cancelled()) or time.monotonic() >= deadline:
                        break
                    time.sleep(0.2)
        except OSError:
            locked = False
        yield locked
    finally:
        try:
            if handle is not None:
                try:
                    if locked:
                        handle.seek(0)
                        if os.name == "nt":
                            import msvcrt
                            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                        else:
                            import fcntl
                            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
                finally:
                    handle.close()
        finally:
            _LOCK.release()


def _run_setup(args: list[str], timeout: float, cancelled: Callable[[], bool] | None) -> None:
    process = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    deadline = time.monotonic() + timeout
    try:
        while process.poll() is None:
            if cancelled and cancelled():
                raise SetupCancelled()
            if time.monotonic() >= deadline:
                raise subprocess.TimeoutExpired(args, timeout)
            try:
                process.wait(timeout=0.2)
            except subprocess.TimeoutExpired:
                pass
        if process.returncode:
            raise subprocess.CalledProcessError(process.returncode, args)
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def setup_enabled(allow_network: bool) -> bool:
    return (allow_network and os.environ.get("SW_API_LOOKUP_NETWORK", "on").strip().lower() not in _OFF
            and os.environ.get("SW_API_LOOKUP_AUTO_INSTALL", "on").strip().lower() not in _OFF)


def _missing(modules: tuple[str, ...]) -> bool:
    for name in modules:
        try:
            importlib.import_module(name)
        except (ImportError, OSError):
            return True
    return False


def ensure_python_packages(requirements: tuple[str, ...], modules: tuple[str, ...], *,
                           allow_network: bool, cancelled: Callable[[], bool] | None = None) -> str | None:
    """缺失时只安装指定依赖；失败返回可见错误，避免重复安装。"""
    if not _missing(modules):
        return None
    if not setup_enabled(allow_network):
        return "Missing Python dependencies and auto-install is disabled: " + ", ".join(requirements)
    key = "pip:" + ",".join(requirements)
    with _setup_lock(cancelled) as acquired:
        if not acquired:
            return "Auto-setup lock unavailable or task cancelled; Python dependencies were not installed."
        if not _missing(modules):
            return None
        if time.monotonic() < _FAILED_UNTIL.get(key, 0):
            return "Python dependency installation failed recently; check network or Python environment: " + ", ".join(requirements)
        if cancelled and cancelled():
            return "Task cancelled; Python dependencies were not installed."
        args = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "--no-input",
                "--only-binary=:all:"]
        install_to_user = sys.prefix == getattr(sys, "base_prefix", sys.prefix)
        if install_to_user:
            args.append("--user")
        args.extend(requirements)
        try:
            _run_setup(args, 180, cancelled)
            importlib.invalidate_caches()
            if install_to_user and not sys.flags.no_user_site:
                site.addsitedir(site.getusersitepackages())
            if not _missing(modules):
                return None
        except SetupCancelled:
            return "Task cancelled; stopped Python dependency installation."
        except (OSError, subprocess.SubprocessError):
            pass
        _FAILED_UNTIL[key] = time.monotonic() + 300
        return "Python dependency auto-install failed; check network, pip, and write permissions: " + ", ".join(requirements)


def _portable_root() -> Path:
    return Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".cache") / "solidworks-automation" / "tools" / "7zip-26.05-x64"


def _valid_portable(root: Path) -> bool:
    try:
        return all((root / name).stat().st_size <= 10_000_000 and
                   hashlib.sha256((root / name).read_bytes()).hexdigest() == _SEVENZIP_FILES[name]
                   for name in ("7z.exe", "7z.dll"))
    except OSError:
        return False


def _download(url: str, expected: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "SolidWorks-API-Lookup/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        data = response.read(5_000_001)
    if len(data) > 5_000_000 or hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("7-Zip download hash mismatch against official release")
    destination.write_bytes(data)


def ensure_sevenzip(*, allow_network: bool, cancelled: Callable[[], bool] | None = None) -> tuple[str | None, str | None]:
    """仅安装经过固定官方哈希验证的 x64 便携版，不更改系统安装或 PATH。"""
    root = _portable_root()
    if _valid_portable(root):
        return str(root / "7z.exe"), None
    if os.name != "nt" or platform.machine().lower() not in {"amd64", "x86_64"}:
        return None, "Usable 7-Zip not found; auto-setup of the local help parser is unsupported on this platform."
    if not setup_enabled(allow_network):
        return None, "7-Zip not found, and offline mode or settings disallow auto-install."
    with _setup_lock(cancelled) as acquired:
        if not acquired:
            return None, "Auto-setup lock unavailable or task cancelled; 7-Zip was not installed."
        if _valid_portable(root):
            return str(root / "7z.exe"), None
        if root.exists():
            return None, "Existing portable 7-Zip verification failed; directory was not overwritten."
        if time.monotonic() < _FAILED_UNTIL.get("7zip", 0):
            return None, "7-Zip auto-setup failed recently; check network and retry."
        try:
            root.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(prefix="7zip-setup-", dir=root.parent) as temp:
                work = Path(temp)
                for name in ("7zr.exe", "7z2605-x64.exe"):
                    if cancelled and cancelled():
                        return None, "Task cancelled; 7-Zip was not installed."
                    _download(_RELEASE + name, _SEVENZIP_FILES[name], work / name)
                out = work / "portable"
                out.mkdir()
                _run_setup([str(work / "7zr.exe"), "e", "-y", "-o" + str(out),
                            str(work / "7z2605-x64.exe"), "7z.exe", "7z.dll"], 30, cancelled)
                if not _valid_portable(out):
                    raise ValueError("Extracted 7-Zip file verification failed")
                try:
                    out.rename(root)
                except OSError:
                    if not _valid_portable(root):
                        raise
            return str(root / "7z.exe"), None
        except SetupCancelled:
            return None, "Task cancelled; stopped 7-Zip auto-setup."
        except (OSError, ValueError, subprocess.SubprocessError):
            _FAILED_UNTIL["7zip"] = time.monotonic() + 300
            return None, "7-Zip auto-setup failed; check network and install official 7-Zip manually."
