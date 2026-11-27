"""@brief 复杂曲面与模具中性计划的结构校验和执行前置门禁。

本模块不把参数计划冒充真实几何。只有具体后端实现、生成并重新读取了几何产物后，
后续专项执行器才可升级状态；当前输出固定为 pilot 或 blocked，并保留黄金失败证据。
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_]{0,63}$")
_OPERATIONS = {"loft", "sweep", "knit", "thicken", "continuity_check", "draft", "parting", "core_cavity"}
_ENTITY_TYPES = {"profile", "path", "surface", "face", "edge", "solid", "direction"}
_TOP_FIELDS = {"schemaVersion", "planId", "units", "entities", "operations"}
_OP_FIELDS = {
    "id", "type", "profiles", "path", "surfaces", "surface", "faces", "edges", "solid", "direction",
    "continuity", "toleranceMm", "thicknessMm", "angleDeg", "partingSurfaces", "partingEdges", "output",
    "allowOpenShell", "checkSelfIntersection", "referenceSurface", "moldBlocks", "shrinkagePercent",
}


def _now_iso() -> str:
    """@brief 返回 UTC 秒级时间戳。"""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _versioned_target(path: Path) -> Path:
    """@brief 返回不覆盖旧产物的版本化路径。"""
    if not path.exists():
        return path
    index = 2
    while True:
        candidate = path.with_name(f"{path.stem}_v{index}{path.suffix}")
        if not candidate.exists():
            return candidate
        index += 1


def _sha256(path: Path) -> str:
    """@brief 计算文件 SHA-256。"""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _id(value: Any, field: str) -> str:
    """@brief 校验稳定实体或操作 ID。"""
    token = str(value or "")
    if not _ID.fullmatch(token):
        raise ValueError(f"{field} must start with a letter and use 1-64 letters, digits, or underscores.")
    return token


def _positive(value: Any, field: str, *, maximum: float | None = None) -> float:
    """@brief 校验有限正数及可选上限。"""
    if isinstance(value, bool):
        raise ValueError(f"{field} must be a finite positive number.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be a finite positive number.") from exc
    if not math.isfinite(number) or number <= 0 or (maximum is not None and number > maximum):
        raise ValueError(f"{field} must be greater than zero" + (f" and at most {maximum:g}" if maximum is not None else "") + ".")
    return number


def _load_plan(value: str | Path | dict[str, Any]) -> dict[str, Any]:
    """@brief 从字典或最大 4 MiB JSON 文件读取中性计划。"""
    if isinstance(value, dict):
        return dict(value)
    path = Path(value).expanduser().resolve()
    if path.suffix.lower() != ".json" or not path.is_file():
        raise ValueError("Advanced geometry plan must be an existing JSON file.")
    if path.stat().st_size > 4 * 1024 * 1024:
        raise ValueError("Advanced geometry plan exceeds the 4 MiB safety limit.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Advanced geometry plan must be a JSON object.")
    return payload


def _refs(operation: dict[str, Any], field: str) -> list[str]:
    """@brief 将单个或数组引用归一为字符串数组。"""
    value = operation.get(field)
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [_id(item, f"{operation['id']}.{field}") for item in values]


def validate_geometry_plan(value: str | Path | dict[str, Any]) -> dict[str, Any]:
    """@brief 严格校验 loft/sweep/knit/thicken、连续性和模具计划。"""
    plan = _load_plan(value)
    unknown = set(plan) - _TOP_FIELDS
    if unknown:
        raise ValueError(f"Plan contains disallowed fields: {', '.join(sorted(unknown))}")
    if plan.get("schemaVersion") != "1.0" or plan.get("units") != "mm":
        raise ValueError("schemaVersion must be 1.0 and units must be mm.")
    _id(plan.get("planId"), "planId")
    entities = plan.get("entities")
    operations = plan.get("operations")
    if not isinstance(entities, list) or not entities:
        raise ValueError("entities requires at least one item.")
    if not isinstance(operations, list) or not operations:
        raise ValueError("operations requires at least one item.")
    entity_types: dict[str, str] = {}
    for index, entity in enumerate(entities):
        if not isinstance(entity, dict) or set(entity) != {"id", "type", "source"}:
            raise ValueError(f"entities[{index}] must contain only id, type, and source.")
        entity_id = _id(entity["id"], f"entities[{index}].id")
        if entity_id in entity_types:
            raise ValueError(f"Duplicate entity ID: {entity_id}")
        if entity.get("type") not in _ENTITY_TYPES or not str(entity.get("source") or "").strip():
            raise ValueError(f"entities[{index}] has invalid type or source.")
        entity_types[entity_id] = entity["type"]
    known = dict(entity_types)
    operation_ids: set[str] = set()
    for index, operation in enumerate(operations):
        if not isinstance(operation, dict) or set(operation) - _OP_FIELDS:
            raise ValueError(f"operations[{index}] has invalid structure or disallowed fields.")
        operation_id = _id(operation.get("id"), f"operations[{index}].id")
        if operation_id in operation_ids or operation_id in known:
            raise ValueError(f"Duplicate operation or entity ID: {operation_id}")
        operation_ids.add(operation_id)
        kind = operation.get("type")
        if kind not in _OPERATIONS:
            raise ValueError(f"operations[{index}].type is unsupported.")
        _validate_operation(operation, known)
        output = operation.get("output")
        if output is not None:
            output_id = _id(output, f"{operation_id}.output")
            if output_id in known or output_id in operation_ids:
                raise ValueError(f"Duplicate output ID: {output_id}")
            known[output_id] = "solid" if kind in {"thicken", "core_cavity"} else "surface"
    return plan


def _require_types(operation: dict[str, Any], field: str, known: dict[str, str], allowed: set[str], *, minimum: int = 1) -> list[str]:
    """@brief 校验引用存在、数量和实体类型。"""
    refs = _refs(operation, field)
    if len(refs) < minimum:
        raise ValueError(f"{operation['id']}.{field} requires at least {minimum} reference(s).")
    invalid = [ref for ref in refs if known.get(ref) not in allowed]
    if invalid:
        raise ValueError(f"{operation['id']}.{field} references missing or wrong-type entities: {', '.join(invalid)}")
    return refs


def _validate_operation(operation: dict[str, Any], known: dict[str, str]) -> None:
    """@brief 校验单项复杂曲面或模具操作的工程必需字段。"""
    kind = operation["type"]
    if kind == "loft":
        _require_types(operation, "profiles", known, {"profile", "edge"}, minimum=2)
        if operation.get("continuity") not in {"G0", "G1", "G2"}:
            raise ValueError(f"{operation['id']}.continuity must declare G0/G1/G2.")
    elif kind == "sweep":
        _require_types(operation, "profiles", known, {"profile"})
        _require_types(operation, "path", known, {"path", "edge"})
        if operation.get("checkSelfIntersection") is not True:
            raise ValueError(f"{operation['id']} must enable checkSelfIntersection.")
    elif kind == "knit":
        _require_types(operation, "surfaces", known, {"surface"}, minimum=2)
        _positive(operation.get("toleranceMm"), f"{operation['id']}.toleranceMm", maximum=1.0)
        if operation.get("allowOpenShell") not in {True, False}:
            raise ValueError(f"{operation['id']}.allowOpenShell must be explicitly declared.")
    elif kind == "thicken":
        _require_types(operation, "surface", known, {"surface"})
        _positive(operation.get("thicknessMm"), f"{operation['id']}.thicknessMm")
        _require_types(operation, "direction", known, {"direction"})
    elif kind == "continuity_check":
        _require_types(operation, "edges", known, {"edge"})
        if operation.get("continuity") not in {"G0", "G1", "G2"}:
            raise ValueError(f"{operation['id']}.continuity must declare G0/G1/G2.")
        _positive(operation.get("toleranceMm"), f"{operation['id']}.toleranceMm", maximum=1.0)
    elif kind == "draft":
        _require_types(operation, "faces", known, {"face", "surface"})
        _require_types(operation, "direction", known, {"direction"})
        _positive(operation.get("angleDeg"), f"{operation['id']}.angleDeg", maximum=30.0)
    elif kind == "parting":
        _require_types(operation, "solid", known, {"solid"})
        _require_types(operation, "direction", known, {"direction"})
        _require_types(operation, "partingEdges", known, {"edge"})
    elif kind == "core_cavity":
        _require_types(operation, "solid", known, {"solid"})
        _require_types(operation, "partingSurfaces", known, {"surface"})
        blocks = _refs(operation, "moldBlocks")
        if len(blocks) != 2 or any(known.get(item) != "solid" for item in blocks):
            raise ValueError(f"{operation['id']}.moldBlocks must reference two valid solid mold blocks.")
        shrinkage = _positive(operation.get("shrinkagePercent"), f"{operation['id']}.shrinkagePercent", maximum=10.0)
        if shrinkage <= 0:
            raise ValueError("Shrinkage rate must be greater than zero.")


def geometry_preflight(value: str | Path | dict[str, Any]) -> dict[str, Any]:
    """@brief 生成复杂几何执行门禁报告，不声称已生成几何。"""
    try:
        plan = validate_geometry_plan(value)
    except (ValueError, json.JSONDecodeError) as exc:
        return {
            "schemaVersion": "1.0", "status": "blocked", "stage": "validate", "checks": [], "artifacts": [],
            "manual_review_required": True, "retryable": False, "error_code": "advanced_geometry_invalid_plan",
            "message": str(exc), "generatedAt": _now_iso(), "geometryProduced": False,
        }
    ocp_available = importlib.util.find_spec("OCP") is not None
    kinds = sorted({item["type"] for item in plan["operations"]})
    checks = [
        {"id": "plan_valid", "status": "pass", "message": "Advanced geometry references, units, and required engineering parameters passed structural validation."},
        {"id": "ocp_runtime", "status": "pass" if ocp_available else "warning", "message": "OCP runtime found." if ocp_available else "OCP runtime not found."},
        {"id": "backend_implementation", "status": "fail", "message": "No loft/sweep/knit/thicken/mold execution adapter with golden-sample and failure-evidence regression exists yet."},
    ]
    return {
        "schemaVersion": "1.0", "status": "pilot" if ocp_available else "blocked", "stage": "preflight",
        "checks": checks, "artifacts": [], "manual_review_required": True, "retryable": False,
        "error_code": "advanced_geometry_backend_unverified" if ocp_available else "advanced_geometry_runtime_missing",
        "planId": plan["planId"], "operationTypes": kinds, "backend": "headless_ocp" if ocp_available else None,
        "geometryProduced": False, "generatedAt": _now_iso(),
        "limitations": ["A structured plan is not a B-Rep artifact; geometry must be generated, reopened, inspected for topology/continuity, and verified against golden samples before claiming completion."],
    }


def write_preflight_report(value: str | Path | dict[str, Any], output_path: str | Path) -> dict[str, Any]:
    """@brief 不覆盖旧报告地写出复杂几何前置证据。"""
    report = geometry_preflight(value)
    target = _versioned_target(Path(output_path).expanduser().resolve())
    if target.suffix.lower() != ".json":
        raise ValueError("Advanced geometry report extension must be .json.")
    target.parent.mkdir(parents=True, exist_ok=True)
    report["reportPath"] = str(target)
    report["artifacts"] = [{"kind": "advanced_geometry_preflight", "path": str(target), "producedThisRun": True}]
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["artifacts"][0].update({"sha256": _sha256(target), "sizeBytes": target.stat().st_size})
    return report


def main(argv: list[str] | None = None) -> int:
    """@brief 命令行入口。"""
    parser = argparse.ArgumentParser(description="CAD Studio preflight check for complex surface and mold neutral plans")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    result = write_preflight_report(args.input, args.output) if args.output else geometry_preflight(args.input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
