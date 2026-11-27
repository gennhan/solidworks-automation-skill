"""@brief CAD Studio/SolidWorks Skill 的能力真源读取与门禁工具。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


MANIFEST_PATH = Path(__file__).resolve().parents[1] / "capabilities.yaml"
VALID_LEVELS = {"verified", "pilot", "reference_only", "not_implemented"}
VALID_ROUTE_SEMANTICS = {
    "automation_equivalent",
    "exact_automation",
    "exact_managed_addin",
    "exact_managed_plugin",
    "exact_native",
    "exact_native_addin",
    "open_format",
    "solver_native",
}


def manifest_path(path: str | Path | None = None) -> Path:
    """@brief 返回能力清单路径。"""
    return Path(path).expanduser().resolve() if path else MANIFEST_PATH


def load_capabilities(path: str | Path | None = None) -> dict[str, Any]:
    """@brief 读取 JSON-compatible YAML 能力清单并校验能力与多语言路由。"""
    source = manifest_path(path)
    payload = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("capabilities"), list):
        raise ValueError(f"Invalid capability manifest format: {source}")
    for item in payload["capabilities"]:
        if not isinstance(item, dict) or not item.get("id") or item.get("level") not in VALID_LEVELS:
            raise ValueError(f"Invalid capability manifest entry: {item!r}")
    backends = payload.get("backend_catalog", {})
    routes = payload.get("operation_routes", [])
    if not isinstance(backends, dict) or not all(isinstance(item, dict) for item in backends.values()):
        raise ValueError("backend_catalog must be an object mapping")
    if not isinstance(routes, list):
        raise ValueError("operation_routes must be a list")
    route_ids: set[str] = set()
    capability_ids = {str(item["id"]) for item in payload["capabilities"]}
    for route in routes:
        if not isinstance(route, dict) or not route.get("id") or route["id"] in route_ids:
            raise ValueError(f"Invalid or duplicate operation route ID: {route!r}")
        route_ids.add(str(route["id"]))
        unknown_capabilities = set(route.get("capability_ids", [])) - capability_ids
        if unknown_capabilities:
            raise ValueError(f"Route {route['id']} references unknown capabilities: {sorted(unknown_capabilities)}")
        candidates = route.get("candidates", [])
        if not isinstance(candidates, list):
            raise ValueError(f"Route {route['id']} candidates must be a list")
        for candidate in candidates:
            backend_id = candidate.get("backend") if isinstance(candidate, dict) else None
            semantics = candidate.get("semantics") if isinstance(candidate, dict) else None
            if backend_id not in backends:
                raise ValueError(f"Route {route['id']} references unknown backend: {backend_id!r}")
            if semantics not in VALID_ROUTE_SEMANTICS:
                raise ValueError(f"Route {route['id']} has invalid semantics type: {semantics!r}")
            if not isinstance(candidate.get("priority"), int):
                raise ValueError(f"Route {route['id']} priority must be an integer")
        unknown_diagnostics = set(route.get("diagnostic_backends", [])) - set(backends)
        if unknown_diagnostics:
            raise ValueError(f"Route {route['id']} references unknown diagnostic backends: {sorted(unknown_diagnostics)}")
    return payload


def capability_index(payload: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """@brief 返回能力 ID 到条目的索引。"""
    source = payload or load_capabilities()
    return {str(item["id"]): dict(item) for item in source.get("capabilities", [])}


def backend_index(payload: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """@brief 返回执行后端 ID 到定义的索引。"""
    source = payload or load_capabilities()
    return {str(key): dict(value) for key, value in source.get("backend_catalog", {}).items()}


def operation_route_index(payload: Mapping[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    """@brief 返回原子操作 ID 到多语言后端路由的索引。"""
    source = payload or load_capabilities()
    return {str(item["id"]): dict(item) for item in source.get("operation_routes", [])}


def resolve_operation_backend(
    operation_id: str,
    *,
    available_backends: Iterable[str] | None = None,
    available_requirements: Iterable[str] | None = None,
    solidworks_revision: str | None = None,
    exact_api: bool = False,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """@brief 按语义、版本、依赖和可用运行时选择最合适的语言后端。

    ``exact_api=False`` 允许优先选择官方 Automation 等价接口；只有调用者明确
    要求原始 ``I*`` 指针语义时，才会跳过 ``automation_equivalent`` 候选。
    """
    source = payload or load_capabilities()
    backends = backend_index(source)
    route = operation_route_index(source).get(operation_id)
    if route is None:
        return {
            "status": "blocked",
            "operation_id": operation_id,
            "error_code": "UNKNOWN_OPERATION_ROUTE",
            "reason": "Operation route does not exist in capability matrix",
        }

    revision = str(solidworks_revision or "").strip()
    blocked_revisions = route.get("blocked_revisions", {})
    if revision and revision in blocked_revisions:
        return {
            "status": "blocked",
            "operation_id": operation_id,
            "error_code": "KNOWN_HOST_REVISION_BLOCKER",
            "reason": str(blocked_revisions[revision]),
            "solidworks_revision": revision,
            "diagnostic_backends": list(route.get("diagnostic_backends", [])),
            "review_required": True,
        }

    supplied_requirements = {str(item) for item in (available_requirements or [])}
    missing_requirements = [
        str(item) for item in route.get("requires", []) if str(item) not in supplied_requirements
    ]
    if missing_requirements:
        return {
            "status": "blocked",
            "operation_id": operation_id,
            "error_code": "MISSING_RUNTIME_REQUIREMENT",
            "reason": "Missing language-independent runtime prerequisites; switching languages cannot unblock this operation",
            "missing_requirements": missing_requirements,
            "review_required": True,
        }

    candidates = sorted(route.get("candidates", []), key=lambda item: item["priority"])
    if not candidates:
        return {
            "status": "blocked",
            "operation_id": operation_id,
            "error_code": "NO_LANGUAGE_SUBSTITUTION",
            "reason": str(route.get("blocked_reason") or "No execution backend is available for this operation"),
            "review_required": bool(route.get("review_required", True)),
        }

    available = {str(item) for item in (available_backends or [])}
    considered: list[dict[str, Any]] = []
    for candidate in candidates:
        backend_id = str(candidate["backend"])
        semantics = str(candidate["semantics"])
        if exact_api and semantics == "automation_equivalent":
            considered.append({
                "backend": backend_id,
                "accepted": False,
                "reason": "Caller requires exact interface semantics; Automation-equivalent interface cannot be used",
            })
            continue
        if backend_id not in available:
            considered.append({"backend": backend_id, "accepted": False, "reason": "Runtime unavailable"})
            continue
        backend = backends[backend_id]
        considered.append({"backend": backend_id, "accepted": True, "reason": "Selected by priority"})
        return {
            "status": "ready",
            "operation_id": operation_id,
            "backend": backend_id,
            "language": backend.get("language"),
            "runtime": backend.get("runtime"),
            "semantics": semantics,
            "exact_api_requested": exact_api,
            "review_required": bool(route.get("review_required", True)),
            "considered": considered,
            "notes": list(route.get("notes", [])),
        }

    return {
        "status": "unavailable",
        "operation_id": operation_id,
        "error_code": "NO_COMPATIBLE_BACKEND_AVAILABLE",
        "reason": "No known backend is available or satisfies the requested interface semantics",
        "exact_api_requested": exact_api,
        "considered": considered,
        "diagnostic_backends": list(route.get("diagnostic_backends", [])),
        "review_required": bool(route.get("review_required", True)),
    }


def backend_route_snapshot(payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """@brief 生成技能矩阵的语言、运行时与操作路由摘要。"""
    source = payload or load_capabilities()
    backends = backend_index(source)
    routes = operation_route_index(source)
    return {
        "schema_version": source.get("backend_schema_version", "1.0"),
        "backend_count": len(backends),
        "route_count": len(routes),
        "languages": sorted({str(item.get("language", "")) for item in backends.values()}),
        "backend_ids": sorted(backends),
        "operation_ids": sorted(routes),
    }


def capability_level(capability_id: str, payload: Mapping[str, Any] | None = None) -> str:
    """@brief 返回能力等级，未知能力按未实现处理。"""
    return capability_index(payload).get(capability_id, {}).get("level", "not_implemented")


def unattended_allowed(capability_ids: Iterable[str], payload: Mapping[str, Any] | None = None) -> bool:
    """@brief 判断一组能力是否允许无人值守执行。"""
    return all(capability_level(capability_id, payload) == "verified" for capability_id in capability_ids)


def capability_snapshot(capability_ids: Iterable[str] | None = None, payload: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """@brief 生成可写入任务证据的能力快照。"""
    index = capability_index(payload)
    selected = list(capability_ids) if capability_ids is not None else list(index)
    return [dict(index.get(capability_id, {"id": capability_id, "level": "not_implemented"})) for capability_id in selected]
