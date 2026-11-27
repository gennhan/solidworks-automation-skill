"""按真实副作用对已注册 MCP 工具分级；发现模式与原生直调共用这一份判据。

分级必须逐个工具人工确认，不能只看 annotations：例如
``solidworks_document_units`` 的注解是只读，但它可以在同一调用里改写文档单位；
``solidworks_review_active`` 看起来是"审视"，实际会落盘预览与报告。
未登记的工具一律 UNKNOWN 并拒绝，逼迫新增工具先补分级。
"""
from __future__ import annotations

import hashlib
import json
import re
from enum import Enum
from typing import Any, Iterable


class Effect(str, Enum):
    """工具调用对模型、文件或外部进程的真实影响。"""

    READ = "read"
    WRITE = "write"
    DESTRUCTIVE = "destructive"
    UNKNOWN = "unknown"


_READ: frozenset[str] = frozenset({
    "cadstudio_resolve_backend",
    "cadstudio_list_drc_rules",
    "cadstudio_routing_preflight",
    "cadstudio_fea_preflight",
    "cadstudio_read_artifact",
    "solidworks_addin_host_status",
    "solidworks_health_check",
    "solidworks_lookup_api",
    "solidworks_list_edges",
    "solidworks_mass_properties",
    "solidworks_bounding_box",
    "solidworks_interference_check",
    "solidworks_inspect_configurations",
    "solidworks_inspect_hole_features",
    "solidworks_inspect_motion_studies",
    "solidworks_validate_motion_study",
    "solidworks_inspect_native_geometry",
    "design_spec_validate",
})

_WRITE: frozenset[str] = frozenset({
    "solidworks_connect",
    "cadstudio_check_dfm",
    "cadstudio_check_drc",
    "cadstudio_check_routing",
    "cadstudio_review_advanced_geometry",
    "solidworks_inspect_drawing",
    "cadstudio_write_open_format",
    "cadstudio_build_dxf_preview_scene",
    "cadstudio_prepare_fea",
    "cadstudio_run_fea",
    "cadstudio_run_fea_convergence",
    "cadstudio_create_ocp_loft",
    "cadstudio_create_ocp_surface",
    "solidworks_recover",
    "solidworks_new_document",
    "solidworks_create_basic_part",
    "solidworks_sketch_and_extrude",
    "solidworks_revolve",
    "solidworks_fillet",
    "solidworks_chamfer",
    "solidworks_shell",
    "solidworks_pattern",
    "solidworks_mirror_feature",
    "solidworks_document_units",
    "design_spec_build",
    "solidworks_open_document",
    "solidworks_add_component",
    "solidworks_set_component_fixed",
    "solidworks_save_document",
    "solidworks_add_coincident_mate",
    "solidworks_add_distance_mate",
    "solidworks_add_concentric_mate",
    "solidworks_set_appearance",
    "solidworks_export_active",
    "solidworks_create_configuration",
    "solidworks_activate_configuration",
    "solidworks_update_dimension",
    "solidworks_set_custom_properties",
    "solidworks_export_assembly_bom",
    "solidworks_review_active",
    "solidworks_generate_drawing",
    "solidworks_review_drawing",
    "solidworks_create_hole_feature",
    "solidworks_add_rotary_motor",
    "solidworks_build_round_sweeps",
    "solidworks_import_step_part",
    "solidworks_replace_component_preserving_transform",
    "solidworks_exclude_reviewed_bodies",
})

# 覆盖或批量写入：一旦参数写错，损失是"已经覆盖的文件"而不是"多一个特征"。
_DESTRUCTIVE: frozenset[str] = frozenset({
    "solidworks_close_documents",
    "solidworks_pack_and_go",
    "solidworks_batch_export_files",
})

_NOTES: dict[str, str] = {
    "solidworks_health_check": "Launches or attaches to SolidWorks when start_solidworks=true; requires approval.",
    "solidworks_lookup_api": "Queries official docs and provisions dependencies by default; uses anonymous Parallel fallback with only public API identifiers and version when direct lookup and cache miss; set offline=true or auto_install=false to disable installation.",
    "cadstudio_check_dfm": "Writes the DFM check report to the output path.",
    "cadstudio_check_drc": "Writes the design rule check report to the output path.",
    "cadstudio_check_routing": "Writes the routing check report to the output path.",
    "cadstudio_review_advanced_geometry": "Writes the preflight review report to the output path.",
    "solidworks_inspect_drawing": "Generates drawing previews and a structure report.",
    "solidworks_document_units": "Annotated as read-only, but the same call can modify document units.",
    "solidworks_review_active": "Writes preview images and a review report to disk.",
    "solidworks_recover": "Dismisses blocking dialogs and resets session state.",
    "solidworks_connect": "May launch a new SolidWorks process.",
    "solidworks_close_documents": "Can close all open documents; unsaved changes will be lost.",
    "solidworks_pack_and_go": "Copies files in bulk to the target directory and may overwrite existing files.",
    "solidworks_batch_export_files": "Writes multiple exported files to disk and may overwrite existing outputs.",
    "solidworks_run_fea": "Launches a local solver process and writes result files.",
    "solidworks_run_fea_convergence": "Launches the solver repeatedly across mesh refinement levels.",
}

_EFFECTS: dict[str, Effect] = {
    **{name: Effect.READ for name in _READ},
    **{name: Effect.WRITE for name in _WRITE},
    **{name: Effect.DESTRUCTIVE for name in _DESTRUCTIVE},
}

# 这些工具在执行时读取活动文档，现有审批记录无法绑定该文档身份。
# 服务端审批模式下在可靠的文档身份快照和持锁复核实现前必须拒绝执行。
_ACTIVE_DOCUMENT_WRITES: frozenset[str] = frozenset({
    "solidworks_sketch_and_extrude", "solidworks_revolve", "solidworks_fillet",
    "solidworks_chamfer", "solidworks_shell", "solidworks_pattern", "solidworks_mirror_feature",
    "solidworks_document_units", "solidworks_add_component", "solidworks_set_component_fixed",
    "solidworks_save_document", "solidworks_close_documents", "solidworks_add_coincident_mate",
    "solidworks_add_distance_mate", "solidworks_add_concentric_mate", "solidworks_set_appearance",
    "solidworks_export_active", "solidworks_create_configuration", "solidworks_activate_configuration",
    "solidworks_update_dimension", "solidworks_set_custom_properties", "solidworks_export_assembly_bom",
    "solidworks_pack_and_go", "solidworks_review_active", "solidworks_create_hole_feature",
    "solidworks_add_rotary_motor", "solidworks_build_round_sweeps", "solidworks_import_step_part",
    "solidworks_replace_component_preserving_transform", "solidworks_exclude_reviewed_bodies",
})


def needs_active_document_identity(tool_name: str) -> bool:
    return tool_name in _ACTIVE_DOCUMENT_WRITES


_UNSUPPORTED_DOCUMENT_WRITES: frozenset[str] = frozenset({
    # 关闭全部文档需要绑定完整文档集合。原生子进程还需独立绑定 PID 与输入文件状态。
    "solidworks_close_documents", "solidworks_build_round_sweeps", "solidworks_import_step_part",
    "solidworks_replace_component_preserving_transform", "solidworks_exclude_reviewed_bodies",
    "solidworks_document_units", "solidworks_add_component", "solidworks_review_active",
    "solidworks_pack_and_go",
})


def supports_document_identity(tool_name: str) -> bool:
    return needs_active_document_identity(tool_name) and tool_name not in _UNSUPPORTED_DOCUMENT_WRITES

# 参数名里带这些片段的字符串值视为"落盘目标"，审批范围按它绑定。
_PATH_HINT = re.compile(r"path|file|dir|output|target|destination", re.IGNORECASE)


def classify(tool_name: str, arguments: Any = None) -> tuple[Effect, str]:
    """返回工具副作用等级和可展示的原因。"""
    # 健康检查默认不启动 SolidWorks，但可通过参数要求启动；不能仅凭工具名放行。
    if tool_name == "solidworks_health_check" and isinstance(arguments, dict):
        params = arguments.get("params", {})
        if isinstance(params, dict) and params.get("start_solidworks") not in (None, False, 0):
            return Effect.WRITE, "Requested launching or connecting to SolidWorks for health check."
    if tool_name == "solidworks_lookup_api":
        params = arguments.get("params", {}) if isinstance(arguments, dict) else {}
        if not isinstance(params, dict):
            return Effect.UNKNOWN, "Invalid API lookup arguments."
        if params.get("offline") is True or params.get("auto_install") is False:
            return Effect.READ, "Auto-install disabled for this call; lookup reads local docs and cache only."
        return Effect.WRITE, _NOTES[tool_name]
    effect = _EFFECTS.get(tool_name, Effect.UNKNOWN)
    if effect is Effect.UNKNOWN:
        return effect, "Unregistered side-effect tool: denied by default (not allowed); add classification in policy.py first."
    return effect, _NOTES.get(tool_name, "")


def registered_names() -> frozenset[str]:
    """策略表覆盖的全部工具名，用于测试断言注册表没有漏登记。"""
    return frozenset(_EFFECTS)


def requires_approval(effect: Effect) -> bool:
    """只有写和破坏性操作需要人工批准；只读与未知分别放行/拒绝。"""
    return effect in (Effect.WRITE, Effect.DESTRUCTIVE)


def targets(arguments: Any) -> list[str]:
    """提取参数里的落盘目标，供审批展示和范围匹配。"""
    found: list[str] = []
    for key, value in _walk(arguments):
        if not _PATH_HINT.search(key):
            continue
        for item in _strings(value):
            if item not in found:
                found.append(item)
    return found


def canonical_digest(tool_name: str, arguments: Any) -> str:
    """把一次具体调用压成摘要；任何参数变化都会得到不同摘要。"""
    payload = json.dumps(
        {"tool": tool_name, "arguments": arguments},
        sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def summarize(tool_name: str, arguments: Any, limit: int = 1200) -> str:
    """给审批界面看的参数摘要，避免把超长数组整段塞进终端。"""
    text = json.dumps(arguments, ensure_ascii=False, sort_keys=True, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


def _walk(value: Any, key: str = "") -> Iterable[tuple[str, Any]]:
    if isinstance(value, dict):
        for name, item in value.items():
            yield from _walk(item, str(name))
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _walk(item, key)
    else:
        yield key, value


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str) and value.strip():
        yield value.strip()
