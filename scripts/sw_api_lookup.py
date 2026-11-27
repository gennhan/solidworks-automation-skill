"""按目标 SolidWorks 版本只读查证类型库与可选官方 API 文档。

默认不启动 CAD、不修改文档；已知版本时可查询官方文档，支持显式离线。接口声明、官方说明和真机行为分别记录，
类型库中存在某个方法并不意味着它已在当前文档、许可证或服务包上验证通过。
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from collections import OrderedDict
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable

try:
    from .cad_installation import discover_installations
    from .sw_process import solidworks_processes
    from .local_api_evidence import load_document, read_local_help, save_document
    from .parallel_api_lookup import ParallelLookupCancelled, retrieve_parallel_document
    from .api_environment import ensure_python_packages
except ImportError:
    from cad_installation import discover_installations
    from sw_process import solidworks_processes
    from local_api_evidence import load_document, read_local_help, save_document
    from parallel_api_lookup import ParallelLookupCancelled, retrieve_parallel_document
    from api_environment import ensure_python_packages

_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,127}$")
_MAX_RESPONSE = 2 * 1024 * 1024
_CACHE_TTL_SECONDS = 3600.0
_OFFICIAL_CACHE: OrderedDict[tuple[int, str, str], tuple[float, dict[str, Any]]] = OrderedDict()
_CACHE_LOCK = threading.Lock()


class LookupCancelled(Exception):
    """用户在查证期间取消任务。"""


def _identifier(value: str, label: str) -> str:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ValueError(f"{label} must be a 1-128 character ASCII interface/member identifier")
    return value


def official_api_url(version: int, interface: str, member: str) -> str:
    """为指定版本构造候选官方页面；URL 不是接口存在的证据。"""
    interface, member = _identifier(interface, "interface"), _identifier(member, "member")
    if isinstance(version, bool) or not isinstance(version, int) or not 2010 <= version <= 2035:
        raise ValueError("version must be a year between 2010 and 2035")
    if interface.casefold().startswith("sw") and not interface.startswith("I"):
        return (f"https://help.solidworks.com/{version}/english/api/swconst/"
                f"SolidWorks.Interop.swconst~SolidWorks.Interop.swconst.{interface}.html?format=P&value=")
    return (f"https://help.solidworks.com/{version}/english/api/sldworksapi/"
            f"SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.{interface}~{member}.html?format=P&value=")


def _process_executable(pid: int) -> Path:
    """只读取指定进程的可执行文件路径，不启动、关闭或切换 SolidWorks。"""
    import win32api  # type: ignore
    import win32con  # type: ignore
    import win32process  # type: ignore

    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
    try:
        path = Path(win32process.GetModuleFileNameEx(handle, 0)).resolve()
    finally:
        win32api.CloseHandle(handle)
    if path.name.casefold() != "sldworks.exe":
        raise RuntimeError("Target process is not SLDWORKS.exe")
    return path


def _executable_version(path: Path) -> tuple[int | None, str | None]:
    """读取可执行文件自身的版本；不能识别时不根据文件夹名称猜测。"""
    try:
        import win32api  # type: ignore
        info = win32api.GetFileVersionInfo(str(path), "\\")
        ms, ls = int(info["FileVersionMS"]), int(info["FileVersionLS"])
        major = ms >> 16
        year = major if 2010 <= major <= 2035 else major + 1992 if 18 <= major <= 43 else None
        return year, f"{major}.{ms & 0xffff}.{ls >> 16}.{ls & 0xffff}"
    except Exception:
        return None, None


def _executable_year(path: Path) -> int | None:
    return _executable_version(path)[0]


def _running_target(version: int | None, process_id: int | None) -> dict[str, Any] | None:
    """只核验运行进程的 PID、可执行文件和文件版本，不向 CAD 发 COM 调用。"""
    if os.name != "nt":
        return None
    processes = solidworks_processes()
    if processes is None:
        raise RuntimeError("Unable to enumerate SolidWorks processes to determine target version")
    if not processes:
        return None
    if process_id is not None and process_id not in processes:
        raise RuntimeError("Specified SolidWorks process not found")
    candidates = [pid for pid, year in processes.items() if version is None or year in (None, version)]
    if process_id is None and len(candidates) > 1:
        raise RuntimeError("Multiple candidate SolidWorks instances found; specify process ID and version explicitly")
    if not candidates and process_id is None:
        return None
    try:
        pid = process_id if process_id is not None else candidates[0]
        executable = _process_executable(pid)
        year = _executable_year(executable)
        if year is None or (processes[pid] is not None and processes[pid] != year):
            raise RuntimeError("SolidWorks process file version does not match process enumeration or cannot be confirmed")
        if version is not None and year != version:
            raise RuntimeError(f"Requested version is {version}, but target process version is {year}")
        return {"year": year, "revision": None, "file_version": _executable_version(executable)[1], "process_id": pid,
                "executable": executable, "source": "running_process"}
    except RuntimeError:
        raise
    except Exception as exc:
        raise RuntimeError(f"Unable to reliably identify running SolidWorks instance: {type(exc).__name__}") from exc


def _installed_target(version: int | None) -> dict[str, Any] | None:
    """没有运行实例时只从已识别安装中选择，不把安装版本冒充运行版本。"""
    items = discover_installations("solidworks") if os.name == "nt" else []
    matches = []
    for item in items:
        exe, raw_year = item.get("executable"), item.get("version")
        if not exe or not str(raw_year or "").isdigit():
            continue
        reported_year = int(raw_year)
        path = Path(str(exe)).resolve()
        if not path.is_file() or path.name.casefold() != "sldworks.exe":
            continue
        year = _executable_year(path)
        if year is None or year != reported_year:
            continue
        if version is not None and year != version:
            continue
        matches.append({"year": year, "revision": None, "file_version": _executable_version(path)[1], "process_id": None,
                        "executable": path, "source": "installed_version"})
    if len(matches) > 1:
        raise RuntimeError("Multiple matching installations found; connect to the target SolidWorks instance first")
    return matches[0] if matches else None


def _type_text(info: Any, value: Any, depth: int = 0) -> str:
    """将 COM 类型描述转换为可读名称；无法解码的部分明确保留原始值。"""
    if depth > 5:
        return "unknown"
    import pythoncom  # type: ignore
    names = {getattr(pythoncom, key): key[3:] for key in dir(pythoncom)
             if key.startswith("VT_") and isinstance(getattr(pythoncom, key), int)}
    if isinstance(value, int):
        return names.get(value, f"VT_{value}")
    if isinstance(value, (list, tuple)) and value:
        kind = value[0]
        if kind == getattr(pythoncom, "VT_PTR", 26) and len(value) > 1:
            return f"pointer<{_type_text(info, value[1], depth + 1)}>"
        if kind == getattr(pythoncom, "VT_SAFEARRAY", 27) and len(value) > 1:
            return f"SAFEARRAY<{_type_text(info, value[1], depth + 1)}>"
        if kind == getattr(pythoncom, "VT_USERDEFINED", 29) and len(value) > 1:
            try:
                return str(info.GetRefTypeInfo(value[1]).GetDocumentation(-1)[0])
            except Exception:
                return "user_defined_unknown"
        return _type_text(info, kind, depth + 1) if isinstance(kind, int) else "unknown"
    return "unknown"


def _lookup_typelib(path: Path, interface: str, member: str) -> dict[str, Any]:
    import pythoncom  # type: ignore
    pythoncom.CoInitialize()
    try:
        return _lookup_typelib_initialized(path, interface, member)
    finally:
        pythoncom.CoUninitialize()


def _lookup_typelib_initialized(path: Path, interface: str, member: str) -> dict[str, Any]:
    import pythoncom  # type: ignore
    library = pythoncom.LoadTypeLib(str(path))
    for index in range(library.GetTypeInfoCount()):
        name = str(library.GetDocumentation(index)[0] or "")
        if name.casefold() != interface.casefold():
            continue
        info = library.GetTypeInfo(index)
        attr = info.GetTypeAttr()
        matches: list[dict[str, Any]] = []
        for i in range(attr.cFuncs):
            desc = info.GetFuncDesc(i)
            names = info.GetNames(desc.memid)
            if not names or str(names[0]).casefold() != member.casefold():
                continue
            params = []
            for position, arg in enumerate(desc.args):
                flags = int(arg[1]) if len(arg) > 1 else 0
                params.append({"name": str(names[position + 1]) if len(names) > position + 1 else None,
                               "type": _type_text(info, arg[0]), "in": bool(flags & 1),
                               "out": bool(flags & 2), "optional": bool(flags & 16)})
            matches.append({"name": str(names[0]), "parameters": params,
                            "return_type": _type_text(info, desc.rettype[0]),
                            "optional_parameter_count": int(desc.cParamsOpt),
                            "invocation_kind": int(desc.invkind)})
        for i in range(attr.cVars):
            desc = info.GetVarDesc(i)
            names = info.GetNames(desc.memid)
            if names and str(names[0]).casefold() == member.casefold():
                matches.append({"name": str(names[0]), "value": desc.value, "kind": "constant"})
        return {"interface_found": True, "member_found": bool(matches), "declarations": matches}
    return {"interface_found": False, "member_found": False, "declarations": []}


class _NextDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.capture = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("id") == "__NEXT_DATA__":
            self.capture = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.capture = False

    def handle_data(self, data: str) -> None:
        if self.capture:
            self.parts.append(data)


class _PlainText(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.hidden = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.hidden += 1
        elif tag in {"p", "br", "div", "tr", "li", "h1", "h2", "h3", "pre"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data: str) -> None:
        if not self.hidden:
            self.parts.append(data)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ANN201
        return None


class _SemanticPage(HTMLParser):
    """备用解析：仅接受同时明确包含年份和 API 产品元数据的正文。"""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.in_title = False
        self.depth = 0
        self.hidden = 0
        self.title: list[str] = []
        self.body: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta" and values.get("name") and values.get("content"):
            self.meta[values["name"].casefold()] = values["content"]
        if tag == "title": self.in_title = True
        if tag in {"script", "style"}: self.hidden += 1
        if tag in {"main", "article"} and not self.depth: self.depth = 1
        elif self.depth and tag not in {"br", "img", "meta", "input", "hr"}: self.depth += 1
        if self.depth and tag in {"p", "br", "div", "tr", "li", "h1", "h2", "pre"}: self.body.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag == "title": self.in_title = False
        if tag in {"script", "style"} and self.hidden: self.hidden -= 1
        if self.depth and tag not in {"br", "img", "meta", "input", "hr"}: self.depth -= 1

    def handle_data(self, data: str) -> None:
        if self.in_title: self.title.append(data)
        if self.depth and not self.hidden: self.body.append(data)


def retrieve_official_document(version: int, interface: str, member: str, *,
                               timeout: float = 15.0,
                               cancelled: Callable[[], bool] | None = None) -> dict[str, Any]:
    """明确授权后只访问固定官方域名；不发送任务描述、路径或凭据。"""
    url = official_api_url(version, interface, member)
    if cancelled and cancelled():
        raise LookupCancelled("API lookup cancelled by user")
    request = urllib.request.Request(url, headers={"User-Agent": "SolidWorks-API-Lookup/1.0", "Accept": "text/html"})
    try:
        deadline = time.monotonic() + timeout
        opener = urllib.request.build_opener(_NoRedirect())
        with opener.open(request, timeout=timeout) as response:
            if response.geturl() != url:
                raise RuntimeError("Official documentation URL changed; read stopped")
            chunks, size = [], 0
            while True:
                if cancelled and cancelled():
                    raise LookupCancelled("API lookup cancelled by user")
                if time.monotonic() > deadline:
                    raise TimeoutError("Official documentation read timeout")
                chunk = response.read(min(65536, _MAX_RESPONSE + 1 - size))
                if not chunk:
                    break
                chunks.append(chunk)
                size += len(chunk)
                if size > _MAX_RESPONSE:
                    raise RuntimeError("Official documentation response exceeded size limit")
        html = b"".join(chunks).decode("utf-8")
        parser = _NextDataParser()
        parser.feed(html)
        try:
            data = json.loads("".join(parser.parts)) if parser.parts else None
        except (ValueError, RecursionError):
            data = None
        outer_props = data.get("props") if isinstance(data, dict) else None
        props = outer_props.get("pageProps") if isinstance(outer_props, dict) else None
        help_data = None
        if isinstance(props, dict):
            if str(props.get("version")) != str(version) or props.get("product") != "api":
                raise RuntimeError("Official page version or product does not match request")
            help_data = props.get("helpContentData")
        if isinstance(help_data, dict) and isinstance(help_data.get("helpText"), str):
            title = str(help_data.get("title") or "")[:200]
            content = _PlainText()
            content.feed(help_data["helpText"])
            body = "".join(content.parts)
        else:
            semantic = _SemanticPage()
            semantic.feed(html)
            if semantic.meta.get("solidworks-version") != str(version) or semantic.meta.get("solidworks-product") != "api":
                raise RuntimeError("Official page version or product does not match request")
            title = "".join(semantic.title).strip()[:200]
            body = "".join(semantic.body)
        enum_page = interface.casefold().startswith("sw") and not interface.startswith("I")
        if interface.casefold() not in title.casefold() or (not enum_page and member.casefold() not in title.casefold()):
            raise RuntimeError("Official page title does not match requested interface")
        text = re.sub(r"\n{3,}", "\n\n", body).strip()
        match_at = text.casefold().find(member.casefold())
        if match_at < 0:
            raise RuntimeError("Official page body is missing the requested method")
        if match_at > 5000:
            text = text[max(0, match_at - 800):]
        text = text[:6000]
        return {"status": "found", "source": url, "version": version, "title": title,
                "text": text, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "provider": "solidworks-direct", "trust": "untrusted_reference", "runtime_verified": False}
    except LookupCancelled:
        raise
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Failed to read official documentation: HTTP {exc.code}") from exc
    except (urllib.error.URLError, TimeoutError, OSError, UnicodeError, ValueError, RecursionError) as exc:
        raise RuntimeError(f"Failed to read official documentation: {type(exc).__name__}") from exc


def _cached_official_document(version: int, interface: str, member: str, *,
                              cancelled: Callable[[], bool] | None = None) -> dict[str, Any]:
    """仅缓存公开官方片段；进程内有界缓存不包含任务内容或会话标识。"""
    if cancelled and cancelled():
        raise LookupCancelled("API lookup cancelled by user")
    key = (version, interface.casefold(), member.casefold())
    now = time.monotonic()
    with _CACHE_LOCK:
        entry = _OFFICIAL_CACHE.get(key)
        if entry and now - entry[0] < _CACHE_TTL_SECONDS:
            _OFFICIAL_CACHE.move_to_end(key)
            return copy.deepcopy(entry[1])
        _OFFICIAL_CACHE.pop(key, None)
    result = retrieve_official_document(version, interface, member, cancelled=cancelled)
    with _CACHE_LOCK:
        _OFFICIAL_CACHE[key] = (time.monotonic(), copy.deepcopy(result))
        _OFFICIAL_CACHE.move_to_end(key)
        while len(_OFFICIAL_CACHE) > 32:
            _OFFICIAL_CACHE.popitem(last=False)
    return result


def lookup_api(interface: str, member: str, version: int | None = None, *,
               process_id: int | None = None, online: bool = True,
               parallel_fallback: bool = True, auto_install: bool = True,
               cancelled: Callable[[], bool] | None = None) -> dict[str, Any]:
    """默认查官方文档；直读失败时可使用匿名 Parallel 备用提取。"""
    interface, member = _identifier(interface, "interface"), _identifier(member, "member")
    if version is not None:
        official_api_url(version, interface, member)
    if process_id is not None and (isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0):
        raise ValueError("process_id must be a positive integer")
    if cancelled and cancelled():
        raise LookupCancelled("API lookup cancelled by user")
    result: dict[str, Any] = {"interface": interface, "member": member, "status": "unknown",
                              "target": None, "typelib": None, "local_help": None, "official": None, "warnings": [],
                              "runtime_verified": False}
    network_enabled = online and os.environ.get("SW_API_LOOKUP_NETWORK", "on").strip().lower() not in {"off", "false", "0"}
    setup_allowed = network_enabled and auto_install
    if os.name == "nt":
        setup_warning = ensure_python_packages(("pywin32>=305",), ("pythoncom", "win32api"),
                                               allow_network=setup_allowed, cancelled=cancelled)
        if setup_warning:
            result["warnings"].append(setup_warning)
        if cancelled and cancelled():
            raise LookupCancelled("API lookup cancelled by user")
    try:
        target = _running_target(version, process_id)
        if target is None and process_id is not None:
            raise RuntimeError("Specified SolidWorks process is not running or cannot be attached")
        if target is None:
            target = _installed_target(version)
        if target is None:
            result["warnings"].append("No SolidWorks installation with a confirmed version was found; software was not launched.")
        else:
            result["target"] = {key: target.get(key) for key in ("year", "revision", "file_version", "process_id", "source")}
            version = int(target["year"])
            result["local_help"] = read_local_help(target["executable"], version, interface, member,
                                                    official_api_url(version, interface, member),
                                                    allow_install=setup_allowed, warnings=result["warnings"],
                                                    cancelled=cancelled)
            if cancelled and cancelled():
                raise LookupCancelled("API lookup cancelled by user")
            if result["local_help"]:
                if result["local_help"].get("version_evidence") == "signed_installer_product_and_file_hash":
                    result["warnings"].append("Local API Help was restored using signed installer, product version, and file hash; this does not represent runtime verification.")
                else:
                    result["warnings"].append("Local API Help comes from the target installation directory; internal file version has not been independently verified.")
            library_names = ("swconst.tlb",) if interface.lower().startswith("sw") and not interface.startswith("I") else (
                "sldworks.tlb", "swmotionstudy.tlb", "SWRoutingLib.tlb", "cmotionswapi.tlb")
            libraries = []
            for library_name in library_names:
                if cancelled and cancelled():
                    raise LookupCancelled("API lookup cancelled by user")
                path = target["executable"].parent / library_name
                if not path.is_file():
                    continue
                try:
                    declaration = _lookup_typelib(path, interface, member)
                    libraries.append({"file": library_name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                                      **declaration})
                except Exception as exc:
                    result["warnings"].append(f"Unable to read {library_name}: {type(exc).__name__}")
            matching = [item for item in libraries if item["interface_found"]]
            if target.get("process_id") and (_process_executable(target["process_id"]) != target["executable"] or
                                              _executable_year(target["executable"]) != version):
                raise RuntimeError("Target process changed during lookup; type library results discarded")
            if len(matching) > 1:
                result["status"] = "conflict"
                result["warnings"].append("Multiple type libraries define the same interface name; unable to determine which to use.")
            elif matching:
                result["typelib"] = matching[0]
                result["status"] = "found" if matching[0]["member_found"] else "not_found"
            elif libraries:
                result["typelib"] = {"file": libraries[0]["file"], "sha256": libraries[0]["sha256"],
                                     "interface_found": False, "member_found": False, "declarations": [],
                                     "searched_libraries": [item["file"] for item in libraries]}
                result["status"] = "not_found"
            else:
                result["warnings"].append("No readable matching type library found for target version.")
    except LookupCancelled:
        raise
    except (ImportError, OSError, RuntimeError, ValueError) as exc:
        result["target"] = None
        result["local_help"] = None
        result["warnings"].append(str(exc))
    if result["local_help"]:
        if result["typelib"] is None and result["status"] != "conflict":
            result["status"] = "documented"
        elif result["typelib"] is not None and result["typelib"]["member_found"] is False:
            result["status"] = "conflict"
            result["warnings"].append("Local API Help conflicts with type library; verify installation and documentation versions.")
    if version is not None:
        result["official_url"] = official_api_url(version, interface, member)
        if network_enabled:
            try:
                result["official"] = _cached_official_document(version, interface, member, cancelled=cancelled)
            except RuntimeError as exc:
                result["warnings"].append(str(exc))
                result["official"] = load_document(version, interface, member)
                if result["official"]:
                    result["warnings"].append("Official web page unavailable; using last fetched local cache (may not be up to date).")
                elif parallel_fallback and os.environ.get("SW_API_LOOKUP_PARALLEL", "on").strip().lower() not in {"off", "false", "0"}:
                    try:
                        setup_warning = ensure_python_packages(("mcp>=1.27,<2", "httpx>=0.27.1,<1"), ("mcp", "httpx"),
                                                               allow_network=setup_allowed, cancelled=cancelled)
                        if cancelled and cancelled():
                            raise LookupCancelled("API lookup cancelled by user")
                        if setup_warning:
                            raise RuntimeError(setup_warning)
                        result["official"] = retrieve_parallel_document(version, interface, member,
                                                                          result["official_url"], cancelled=cancelled)
                        result["warnings"].append("Direct official web read failed; extracted official page via anonymous Parallel fallback (version inferred only from URL and title; verify further).")
                    except ParallelLookupCancelled as cancel:
                        raise LookupCancelled(str(cancel)) from cancel
                    except RuntimeError as fallback_error:
                        result["warnings"].append(str(fallback_error))
            if result["official"]:
                if not result["official"].get("cache_status"):
                    save_document(version, interface, member, result["official"])
                if result["typelib"] is None and result["status"] != "conflict":
                    result["status"] = "documented"
                elif result["typelib"] is not None and result["typelib"]["member_found"] is False:
                    result["status"] = "conflict"
                    result["warnings"].append("Official page conflicts with local type library; cannot claim runtime availability.")
        else:
            result["official"] = load_document(version, interface, member)
            if result["official"]:
                result["warnings"].append("Using last fetched local cache offline (may not be up to date).")
                if result["typelib"] is None and result["status"] != "conflict": result["status"] = "documented"
                elif result["typelib"] is not None and result["typelib"]["member_found"] is False:
                    result["status"] = "conflict"
                    result["warnings"].append("Cached documentation conflicts with local type library; cannot claim runtime availability.")
            if online:
                result["warnings"].append("Environment configuration disables online official documentation lookup for this tool.")
    elif online:
        result["warnings"].append("Version unknown; official web page was not queried.")
    return result


def lookup_task(task: str, version: int | None = None, *, process_id: int | None = None,
                online: bool = True, parallel_fallback: bool = True, auto_install: bool = True,
                cancelled: Callable[[], bool] | None = None) -> dict[str, Any]:
    """本地识别自然语言候选；只向外部发送候选 API 标识。"""
    if not isinstance(task, str) or not task.strip() or len(task) > 10000:
        raise ValueError("task must be a description of 1 to 10000 characters")
    if version is not None and (isinstance(version, bool) or not isinstance(version, int) or not 2010 <= version <= 2035):
        raise ValueError("version must be a year between 2010 and 2035")
    if process_id is not None and (isinstance(process_id, bool) or not isinstance(process_id, int) or process_id <= 0):
        raise ValueError("process_id must be a positive integer")
    try:
        from .api_intent import task_candidates, task_years
    except ImportError:
        from api_intent import task_candidates, task_years
    candidates, _ = task_candidates(task)
    years = task_years(task)
    if len(years) > 1 or (version is not None and years and version not in years):
        raise ValueError("Task references multiple or conflicting SolidWorks versions; specify target version explicitly")
    year = version if version is not None else next(iter(years), None)
    results = [lookup_api(interface, member, year, process_id=process_id, online=online,
                          parallel_fallback=parallel_fallback, auto_install=auto_install, cancelled=cancelled)
               for interface, member in candidates]
    return {"status": "candidates" if results else "no_candidate", "results": results,
            "warning": "Candidates are for lookup only; actual methods must be confirmed by task planning and target-version evidence."}


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only lookup of SolidWorks API interfaces for a target version")
    parser.add_argument("interface", nargs="?", help="Interface name, e.g. ISketchManager")
    parser.add_argument("member", nargs="?", help="Member name, e.g. CreateCircleByRadius")
    parser.add_argument("--task", help="Identify up to two candidate APIs from natural language; full task text is never sent to online lookup services")
    parser.add_argument("--version", type=int, help="Target SolidWorks release year")
    parser.add_argument("--process-id", type=int, help="Target running SolidWorks process ID")
    parser.add_argument("--offline", action="store_true", help="Do not access the network; use local docs and cached history")
    parser.add_argument("--no-parallel", action="store_true", help="Query official web docs only; disable Parallel fallback")
    parser.add_argument("--no-auto-install", action="store_true", help="Do not automatically install dependencies or restore local API help")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        if args.task:
            if args.interface or args.member:
                raise ValueError("--task cannot be used together with positional interface/member arguments")
            output = lookup_task(args.task, args.version, process_id=args.process_id, online=not args.offline,
                                 parallel_fallback=not args.no_parallel, auto_install=not args.no_auto_install)
        else:
            if not args.interface or not args.member:
                raise ValueError("Provide interface and member, or use --task for a natural-language task")
            output = lookup_api(args.interface, args.member, args.version, process_id=args.process_id,
                                online=not args.offline, parallel_fallback=not args.no_parallel,
                                auto_install=not args.no_auto_install)
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, LookupCancelled) as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
