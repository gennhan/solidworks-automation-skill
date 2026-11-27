"""
@file design_rule_check.py
@brief 设计规则检查（DRC）引擎与标准规则集——面向设计审计的通用检查器。

定位：制造性由 dfm_review.py 负责；本模块是**设计意图层**的规则检查器，把几何健全性、
孔位规则、标准件（齿轮/弹簧/链轮）合理性、装配约束和工程图完整性等规则跑在一个
NeutralCadDocument 上，按严重度聚合成一份可审计报告。既有 DFM/几何/图纸审查可作为证据源，
本模块不重复实现它们。

设计哲学（与本仓库一致）：
- 规则逻辑是**纯函数**，消费中性文档，可离线单测；
- 规则集通过**声明式 Profile**（design_rule_profiles.py）配置与补充，代理可把自然语言
  翻译成 Profile JSON，无需写代码；
- 从活动 SolidWorks 模型抽取快照为 `pilot`，需真机验证；
- 报告始终 `reviewRequired=true`，不作为无人值守放行依据。

用法：
    report = build_drc_report("part.cadstudio.json", profiles=[profile_dict])
    write_drc_report("part.cadstudio.json", "out/drc.json", profiles=[...])
    rules = list_rules()  # 供代理了解可配置的内置规则
"""
from __future__ import annotations

import hashlib
import math
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

try:
    from .design_rule_profiles import DrcProfileError, list_rule_packs, load_profile, load_rule_pack, merge_profiles
    from .design_audit import assert_no_regression, summarize_audit
    from .fastener_audit import audit_fastener_holes, parse_fastener_hole
    from .drive_sizing import DEFAULT_LIMITS as DRIVE_DEFAULT_LIMITS, evaluate_drive
except ImportError:
    from design_rule_profiles import DrcProfileError, list_rule_packs, load_profile, load_rule_pack, merge_profiles
    from design_audit import assert_no_regression, summarize_audit
    from fastener_audit import audit_fastener_holes, parse_fastener_hole
    from drive_sizing import DEFAULT_LIMITS as DRIVE_DEFAULT_LIMITS, evaluate_drive

UNIT_TO_MM = {"mm": 1.0, "cm": 10.0, "m": 1000.0, "in": 25.4, "inch": 25.4}

DEFAULT_THRESHOLDS: dict[str, float] = {
    "minWallThicknessMm": 1.0,
    "minFeatureSizeMm": 0.5,
    "holeEdgeDistanceRatio": 0.5,       # 孔边到零件边 >= ratio * 孔径
    "holeEdgeDistanceMinMm": 1.5,
    "holeSpacingRatio": 2.0,            # 相邻孔中心距 >= ratio * 大孔半径
    "ligamentMinMm": 2.0,              # 相邻孔间腹板（边到边）最小厚度
    "threadEngagementRatio": 1.0,       # 螺纹啮合深度 >= ratio * 公称直径
    "sprocketMinTeeth": 17,
    "springIndexMin": 4.0,
    "springIndexMax": 12.0,
    "springIndexHardMin": 3.0,
    "springIndexHardMax": 16.0,
}

DEFAULT_THRESHOLDS.update(DRIVE_DEFAULT_LIMITS)  # 电机扭矩核验阈值（可经 Profile 覆盖）

_SEVERITY_TO_STATUS = {"critical": "fail", "major": "fail", "warning": "warning", "minor": "warning", "info": "info"}


# ---------------------------------------------------------------------------
# 通用
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _num(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _check(check_id: str, category: str, status: str, severity: str, message: str, **extra: Any) -> dict[str, Any]:
    """@brief 构造稳定检查项。"""
    payload: dict[str, Any] = {
        "id": check_id,
        "category": category,
        "status": status,
        "severity": severity,
        "message": message,
    }
    payload.update({key: value for key, value in extra.items() if value is not None})
    return payload


# ---------------------------------------------------------------------------
# 中性文档解析
# ---------------------------------------------------------------------------


def _load_document(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(source, Mapping):
        document = dict(source)
    else:
        path = Path(source)
        if path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("Neutral document exceeds 4 MiB limit")
        document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise ValueError("NeutralCadDocument must be a JSON object")
    if not str(document.get("documentId") or "").strip():
        raise ValueError("NeutralCadDocument is missing documentId")
    if not isinstance(document.get("features", []), list):
        raise ValueError("features must be a list")
    if len(document.get("features", [])) > 1000:
        raise ValueError("features exceeds 1000-item limit; split checks")
    return document


def _extract_context(document: Mapping[str, Any]) -> dict[str, Any]:
    """@brief 从中性文档抽取 DRC 需要的规范化上下文（长度统一 mm）。"""
    units = str(document.get("units") or "mm").strip().lower()
    factor = UNIT_TO_MM.get(units)
    if factor is None:
        raise ValueError(f"Unsupported DRC units: {units}")
    metadata = document.get("metadata") if isinstance(document.get("metadata"), Mapping) else {}
    design = metadata.get("design") if isinstance(metadata.get("design"), Mapping) else {}
    manufacturing = metadata.get("manufacturing") if isinstance(metadata.get("manufacturing"), Mapping) else {}
    assembly = metadata.get("assembly") if isinstance(metadata.get("assembly"), Mapping) else {}
    drawing = metadata.get("drawing") if isinstance(metadata.get("drawing"), Mapping) else {}

    features = [f for f in document.get("features", []) if isinstance(f, Mapping)]
    holes: list[dict[str, Any]] = []
    for feature in features:
        if str(feature.get("type") or "").lower() != "hole":
            continue
        params = feature.get("parameters") if isinstance(feature.get("parameters"), Mapping) else {}
        diameter = _num(params.get("diameter"))
        if diameter is None and _num(params.get("radius")) is not None:
            diameter = _num(params.get("radius")) * 2.0
        holes.append(
            {
                "id": str(feature.get("id") or ""),
                "diameter_mm": diameter * factor if diameter is not None else None,
                "depth_mm": _num(params.get("depth")) * factor if _num(params.get("depth")) is not None else None,
                "edge_distance_mm": _num(params.get("edgeDistance")) * factor
                if _num(params.get("edgeDistance")) is not None
                else None,
                "engagement_mm": _num(params.get("threadEngagement")) * factor
                if _num(params.get("threadEngagement")) is not None
                else None,
                "thread": str(params.get("thread") or "") or None,
                "thread_nominal_mm": _num(params.get("threadNominal")) * factor
                if _num(params.get("threadNominal")) is not None
                else None,
                "x_mm": _num(params.get("x")) * factor if _num(params.get("x")) is not None else None,
                "y_mm": _num(params.get("y")) * factor if _num(params.get("y")) is not None else None,
            }
        )

    min_wall = _num(design.get("minWallThicknessMm"))
    if min_wall is None:
        raw_wall = _num(manufacturing.get("wallThickness"))
        min_wall = raw_wall * factor if raw_wall is not None else None
    else:
        min_wall = min_wall  # design 块默认已是 mm

    standard_parts = document.get("standardParts")
    if not isinstance(standard_parts, list):
        standard_parts = metadata.get("standardParts") if isinstance(metadata.get("standardParts"), list) else []
    standard_parts = [p for p in standard_parts if isinstance(p, Mapping)]

    plate = metadata.get("plate") if isinstance(metadata.get("plate"), Mapping) else {}
    plate_thickness = _num(plate.get("thicknessMm"))
    gdt = metadata.get("gdt") if isinstance(metadata.get("gdt"), list) else []
    gdt = [g for g in gdt if isinstance(g, Mapping)]
    datums_declared = metadata.get("datums") if isinstance(metadata.get("datums"), list) else []
    bom = metadata.get("bom") if isinstance(metadata.get("bom"), list) else []
    bom = [b for b in bom if isinstance(b, Mapping)]
    hole_callouts = drawing.get("holeCallouts") if isinstance(drawing.get("holeCallouts"), list) else None

    fastener_holes = [parsed for f in features if (parsed := parse_fastener_hole(f)) is not None]
    for fastener in fastener_holes:
        for key in ("main_diameter_mm", "sink_diameter_mm", "sink_depth_mm"):
            if fastener.get(key) is not None:
                fastener[key] *= factor
    fastener_stacks = metadata.get("fastenerStacks") if isinstance(metadata.get("fastenerStacks"), list) else []
    fastener_stacks = [s for s in fastener_stacks if isinstance(s, Mapping)]
    drives = metadata.get("drives") if isinstance(metadata.get("drives"), list) else []

    return {
        "documentId": str(document.get("documentId")),
        "units": units,
        "factor": factor,
        "features": features,
        "holes": holes,
        "min_wall_mm": min_wall,
        "plate_thickness_mm": plate_thickness,
        "standard_parts": standard_parts,
        "assembly": dict(assembly),
        "drawing": dict(drawing),
        "gdt": gdt,
        "datums_declared": [str(d.get("id") if isinstance(d, Mapping) else d) for d in datums_declared],
        "bom": bom,
        "hole_callouts": hole_callouts,
        "fastener_holes": fastener_holes,
        "fastener_stacks": fastener_stacks,
        "drives": drives,
    }


# ---------------------------------------------------------------------------
# 内置标准规则
# ---------------------------------------------------------------------------


def rule_geometry(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    min_wall = ctx.get("min_wall_mm")
    limit = th["minWallThicknessMm"]
    if min_wall is None:
        checks.append(_check("DRC-GEO-001", "geometry", "info", "info", "Minimum wall thickness not provided; skipping wall thickness check", threshold_mm=limit))
    elif min_wall < limit:
        checks.append(
            _check("DRC-GEO-001", "geometry", "fail", "major", f"Minimum wall thickness {min_wall:g}mm is below threshold {limit:g}mm", value_mm=min_wall, threshold_mm=limit)
        )
    elif min_wall < limit * 1.5:
        checks.append(
            _check("DRC-GEO-001", "geometry", "warning", "minor", f"Minimum wall thickness {min_wall:g}mm is close to threshold {limit:g}mm", value_mm=min_wall, threshold_mm=limit)
        )
    else:
        checks.append(_check("DRC-GEO-001", "geometry", "pass", "info", f"Minimum wall thickness {min_wall:g}mm is acceptable", value_mm=min_wall, threshold_mm=limit))
    return checks


def rule_holes(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    holes = ctx.get("holes", [])
    if not holes:
        return [_check("DRC-HOLE-000", "holes", "info", "info", "Document has no hole features; skipping hole rules")]
    for hole in holes:
        hid = hole.get("id") or "hole"
        diameter = hole.get("diameter_mm")
        if diameter is not None and diameter <= 0:
            checks.append(_check("DRC-HOLE-004", "holes", "fail", "critical", f"Hole {hid} diameter is non-positive", target=hid))
            continue
        # 孔边距
        edge = hole.get("edge_distance_mm")
        if edge is not None and diameter is not None:
            required = max(th["holeEdgeDistanceMinMm"], th["holeEdgeDistanceRatio"] * diameter)
            if edge < required:
                checks.append(
                    _check("DRC-HOLE-001", "holes", "fail", "major", f"Hole {hid} edge distance {edge:g}mm is below required {required:g}mm", target=hid, value_mm=edge, required_mm=required)
                )
        # 螺纹啮合深度
        engagement = hole.get("engagement_mm")
        nominal = hole.get("thread_nominal_mm")
        if hole.get("thread") and engagement is not None and nominal:
            required = th["threadEngagementRatio"] * nominal
            if engagement < required:
                checks.append(
                    _check("DRC-HOLE-003", "holes", "warning", "warning", f"Hole {hid} thread engagement {engagement:g}mm is below recommended {required:g}mm", target=hid, value_mm=engagement, required_mm=required)
                )
    # 孔间距
    positioned = [h for h in holes if h.get("x_mm") is not None and h.get("y_mm") is not None and h.get("diameter_mm")]
    for i in range(len(positioned)):
        for j in range(i + 1, len(positioned)):
            a, b = positioned[i], positioned[j]
            distance = ((a["x_mm"] - b["x_mm"]) ** 2 + (a["y_mm"] - b["y_mm"]) ** 2) ** 0.5
            required = th["holeSpacingRatio"] * max(a["diameter_mm"], b["diameter_mm"]) / 2.0
            if distance < required:
                checks.append(
                    _check("DRC-HOLE-002", "holes", "warning", "warning", f"Hole {a['id']} to {b['id']} center distance {distance:g}mm is below recommended {required:g}mm", value_mm=distance, required_mm=required)
                )
    incomplete = any(h.get("diameter_mm") is None or h.get("edge_distance_mm") is None or
                     (h.get("thread") and (h.get("engagement_mm") is None or h.get("thread_nominal_mm") is None))
                     for h in holes) or (len(holes) > 1 and len(positioned) != len(holes))
    if incomplete:
        checks.append(_check("DRC-HOLE-EVIDENCE", "holes", "info", "info", "Hole diameter, edge distance, position, or thread engagement evidence is incomplete; cannot confirm all holes pass"))
    elif not checks:
        checks.append(_check("DRC-HOLE-OK", "holes", "pass", "info", f"Provided data for {len(holes)} hole(s) triggered no hole rules"))
    return checks


def gear_min_teeth_without_undercut(
    pressure_angle_deg: float = 20.0,
    addendum_coeff: float = 1.0,
    profile_shift_coeff: float = 0.0,
    *,
    override: float | None = None,
) -> int:
    """@brief 外啮合渐开线直齿轮理论最小无根切齿数 z_min = 2(ha* - x) / sin²(α)，向上取整。

    20°、ha*=1、x=0 时为 17.097 -> 18（与上游 sw_gear 真机路径一致）；14.5° 约 32；正变位 x>0 可降低下限。
    override 非空（用户在 Profile 里显式设了 gearMinTeeth）时直接采用，保持向后兼容。
    """
    if override is not None:
        return int(math.ceil(float(override)))
    alpha = math.radians(pressure_angle_deg)
    sin2 = math.sin(alpha) ** 2
    if sin2 <= 0.0:
        return 0
    return max(0, int(math.ceil(2.0 * (addendum_coeff - profile_shift_coeff) / sin2 - 1e-9)))


def rule_standard_parts(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []
    parts = ctx.get("standard_parts", [])
    if not parts:
        return [_check("DRC-STD-000", "standard_parts", "info", "info", "Document has no standard parts; skipping standard-part rules")]
    for part in parts:
        ptype = str(part.get("type") or "").lower()
        pid = str(part.get("id") or ptype or "part")
        if ptype in {"spur_gear", "gear"}:
            if part.get("is_pointed") is True:
                checks.append(_check("DRC-STD-001", "standard_parts", "fail", "major", f"Gear {pid} has pointed teeth (zero tip width)", target=pid))
            teeth = _num(part.get("teeth"))
            shift = _num(part.get("profile_shift_coeff")) or 0.0
            z_min = gear_min_teeth_without_undercut(
                _num(part.get("pressure_angle_deg")) or 20.0,
                _num(part.get("addendum_coeff")) or 1.0,
                shift,
                override=th.get("gearMinTeeth"),
            )
            if teeth is not None and teeth < z_min:
                checks.append(
                    _check(
                        "DRC-STD-002", "standard_parts", "warning", "warning",
                        f"Gear {pid} tooth count {teeth:g} is below non-undercut minimum {z_min} "
                        f"(pressure angle {_num(part.get('pressure_angle_deg')) or 20.0:g}°, shift x={shift:g}); undercut risk",
                        target=pid, required=z_min,
                    )
                )
        elif ptype in {"compression_spring", "spring"}:
            index = _num(part.get("spring_index"))
            if index is not None:
                if index < th["springIndexHardMin"] or index > th["springIndexHardMax"]:
                    checks.append(_check("DRC-STD-003", "standard_parts", "fail", "major", f"Spring {pid} index C={index:g} is outside manufacturable range [{th['springIndexHardMin']:g}, {th['springIndexHardMax']:g}]", target=pid))
                elif index < th["springIndexMin"] or index > th["springIndexMax"]:
                    checks.append(_check("DRC-STD-003", "standard_parts", "warning", "warning", f"Spring {pid} index C={index:g} is outside recommended range [{th['springIndexMin']:g}, {th['springIndexMax']:g}]", target=pid))
            solid = _num(part.get("solid_length_mm"))
            free = _num(part.get("free_length_mm"))
            if solid is not None and free is not None and solid >= free:
                checks.append(_check("DRC-STD-004", "standard_parts", "fail", "critical", f"Spring {pid} solid length {solid:g}mm is not less than free length {free:g}mm", target=pid))
        elif ptype in {"roller_sprocket", "sprocket"}:
            teeth = _num(part.get("teeth"))
            if teeth is not None and teeth < th["sprocketMinTeeth"]:
                checks.append(_check("DRC-STD-005", "standard_parts", "warning", "warning", f"Sprocket {pid} tooth count {teeth:g} is below {th['sprocketMinTeeth']:g}; wear/polygonal-effect risk", target=pid))
    if not checks:
        checks.append(_check("DRC-STD-EVIDENCE", "standard_parts", "info", "info", f"Provided data for {len(parts)} standard part(s) triggered no rules; full design parameters still require review"))
    return checks


def rule_assembly(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    assembly = ctx.get("assembly", {})
    if not assembly:
        return [_check("DRC-ASM-000", "assembly", "info", "info", "No assembly metadata; skipping assembly rules")]
    checks: list[dict[str, Any]] = []
    interferences = assembly.get("interferences")
    count = len(interferences) if isinstance(interferences, list) else _num(assembly.get("interferenceCount"))
    if count and count > 0:
        checks.append(_check("DRC-ASM-001", "assembly", "fail", "critical", f"Detected {int(count)} assembly interference(s)", value=int(count)))
    components = _num(assembly.get("componentCount"))
    mates = _num(assembly.get("mateCount"))
    if components is not None and mates is not None and components >= 2 and mates == 0:
        checks.append(_check("DRC-ASM-002", "assembly", "warning", "warning", f"{int(components)} components with no mates; assembly is under-constrained", value=int(components)))
    if count is None or components is None or mates is None:
        checks.append(_check("DRC-ASM-EVIDENCE", "assembly", "info", "info", "Assembly component, mate, or interference data is incomplete"))
    elif not checks:
        checks.append(_check("DRC-ASM-EVIDENCE", "assembly", "info", "info", "Provided counts show no rule violations; mate count alone cannot prove full constraint"))
    return checks


def rule_drawing(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    drawing = ctx.get("drawing", {})
    if not drawing:
        return [_check("DRC-DRW-000", "drawing", "info", "info", "No drawing metadata; skipping drawing rules")]
    checks: list[dict[str, Any]] = []
    missing = drawing.get("requiredDimensionsMissing")
    if isinstance(missing, list) and missing:
        checks.append(_check("DRC-DRW-001", "drawing", "fail", "major", f"Drawing is missing required dimensions: {', '.join(str(m) for m in missing[:8])}", value=len(missing)))
    without_tol = _num(drawing.get("dimensionsWithoutTolerance"))
    if without_tol is not None and without_tol > 0:
        checks.append(_check("DRC-DRW-002", "drawing", "warning", "minor", f"{int(without_tol)} dimension(s) missing tolerance callouts", value=int(without_tol)))
    if not isinstance(missing, list) or without_tol is None:
        checks.append(_check("DRC-DRW-EVIDENCE", "drawing", "info", "info", "Missing dimension completeness or tolerance evidence; cannot confirm drawing completeness"))
    elif not checks:
        checks.append(_check("DRC-DRW-OK", "drawing", "pass", "info", "Provided dimension and tolerance evidence triggered no rules"))
    return checks


def rule_ligament(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    """@brief B-Rep 实测：相邻孔间腹板（边到边）最小厚度。

    腹板 = 中心距 − 半径a − 半径b；由真实孔位/孔径计算，反映钻孔面板最薄弱的材料桥。
    """
    holes = [h for h in ctx.get("holes", []) if h.get("x_mm") is not None and h.get("y_mm") is not None and h.get("diameter_mm")]
    if len(holes) < 2:
        return [_check("DRC-HOLE-005", "holes", "info", "info", "Fewer than 2 positioned holes; skipping hole-to-hole ligament check")]
    limit = th["ligamentMinMm"]
    checks: list[dict[str, Any]] = []
    worst = None
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            a, b = holes[i], holes[j]
            distance = ((a["x_mm"] - b["x_mm"]) ** 2 + (a["y_mm"] - b["y_mm"]) ** 2) ** 0.5
            ligament = distance - a["diameter_mm"] / 2.0 - b["diameter_mm"] / 2.0
            if worst is None or ligament < worst:
                worst = ligament
            if ligament < limit:
                checks.append(
                    _check("DRC-HOLE-005", "holes", "fail", "major", f"Ligament between hole {a['id']} and {b['id']} is {ligament:.3g}mm, below minimum {limit:g}mm", value_mm=round(ligament, 4), required_mm=limit)
                )
            elif ligament < limit * 1.5:
                checks.append(
                    _check("DRC-HOLE-005", "holes", "warning", "minor", f"Ligament between hole {a['id']} and {b['id']} is {ligament:.3g}mm, close to minimum {limit:g}mm", value_mm=round(ligament, 4), required_mm=limit)
                )
    if not checks:
        checks.append(_check("DRC-HOLE-005", "holes", "pass", "info", f"Minimum hole-to-hole ligament {worst:.3g}mm is acceptable", value_mm=round(worst, 4), required_mm=limit))
    return checks


def rule_thread_vs_thickness(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    """@brief 螺纹啮合 vs 实际板厚：贯穿攻丝孔在薄板上啮合圈数不足。"""
    thickness = ctx.get("plate_thickness_mm") or ctx.get("min_wall_mm")
    tapped = [h for h in ctx.get("holes", []) if h.get("thread") and h.get("thread_nominal_mm")]
    if not tapped:
        return [_check("DRC-HOLE-006", "holes", "info", "info", "No tapped holes; skipping thread-engagement vs plate-thickness check")]
    if thickness is None:
        return [_check("DRC-HOLE-006", "holes", "info", "info", "Plate thickness not provided; skipping thread-engagement vs plate-thickness check")]
    checks: list[dict[str, Any]] = []
    for hole in tapped:
        nominal = hole["thread_nominal_mm"]
        available = hole.get("depth_mm") if hole.get("depth_mm") else thickness
        required = th["threadEngagementRatio"] * nominal
        if available < required:
            checks.append(
                _check("DRC-HOLE-006", "holes", "warning", "warning", f"Hole {hole['id']} available engagement {available:g}mm is below recommended {required:g}mm (plate thickness {thickness:g})", target=hole["id"], value_mm=available, required_mm=required)
            )
    if not checks:
        checks.append(_check("DRC-HOLE-006", "holes", "pass", "info", f"Thread engagement matches plate thickness for {len(tapped)} tapped hole(s)"))
    return checks


def rule_relations(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    """@brief 关系型/跨特征：GD&T 基准存在性、孔表覆盖度、BOM 与特征数一致性。"""
    checks: list[dict[str, Any]] = []

    # DRC-REL-001 GD&T 基准存在性
    gdt = ctx.get("gdt", [])
    if not gdt:
        checks.append(_check("DRC-REL-001", "relations", "info", "info", "No GD&T metadata; skipping datum existence check"))
    else:
        declared = set(ctx.get("datums_declared", []))
        referenced: set[str] = set()
        for frame in gdt:
            for datum in frame.get("datums", []) or []:
                referenced.add(str(datum))
        missing = sorted(referenced - declared)
        if missing:
            checks.append(_check("DRC-REL-001", "relations", "fail", "major", f"GD&T references undeclared datums: {', '.join(missing)}", value=missing))
        else:
            checks.append(_check("DRC-REL-001", "relations", "pass", "info", "All datums referenced by GD&T are declared"))

    # DRC-REL-002 孔表/孔标注覆盖度
    callouts = ctx.get("hole_callouts")
    holes = ctx.get("holes", [])
    if callouts is None or not holes:
        checks.append(_check("DRC-REL-002", "relations", "info", "info", "No hole callout metadata or no holes; skipping hole-table coverage check"))
    else:
        specs = {f"{round(h['diameter_mm'], 1)}" for h in holes if h.get("diameter_mm")}
        covered = {str(c).replace("⌀", "").replace("φ", "").strip() for c in callouts}
        uncovered = sorted(s for s in specs if not any(s in c or c in s for c in covered))
        if uncovered:
            checks.append(_check("DRC-REL-002", "relations", "warning", "warning", f"Hole sizes not covered by hole table/callouts: ⌀{', ⌀'.join(uncovered)}", value=uncovered))
        else:
            checks.append(_check("DRC-REL-002", "relations", "pass", "info", "All hole sizes are covered by hole table/callouts"))

    # DRC-REL-003 BOM 与特征数一致性
    bom = ctx.get("bom", [])
    if not bom:
        checks.append(_check("DRC-REL-003", "relations", "info", "info", "No BOM metadata; skipping consistency check"))
    else:
        features = ctx.get("features", [])
        type_counts: dict[str, int] = {}
        for feature in features:
            ftype = str(feature.get("type") or "").lower()
            type_counts[ftype] = type_counts.get(ftype, 0) + 1
        mismatched = []
        for item in bom:
            ftype = str(item.get("featureType") or "").lower()
            quantity = _num(item.get("quantity"))
            if ftype and quantity is not None and type_counts.get(ftype, 0) != int(quantity):
                mismatched.append(f"{ftype}: BOM {int(quantity)} vs features {type_counts.get(ftype, 0)}")
        if mismatched:
            checks.append(_check("DRC-REL-003", "relations", "warning", "warning", f"BOM quantity mismatches feature count: {'; '.join(mismatched)}", value=mismatched))
        else:
            checks.append(_check("DRC-REL-003", "relations", "pass", "info", "BOM quantities match feature counts"))
    return checks


def rule_fastener(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    """@brief 3D 配合：沉头有效性/头部容纳/朝向 + 跨零件避让(pilot)。"""
    return audit_fastener_holes(ctx.get("fastener_holes", []), stacks=ctx.get("fastener_stacks", []))


def rule_drives(ctx: Mapping[str, Any], th: Mapping[str, float]) -> list[dict[str, Any]]:
    """@brief 电机扭矩核验（drive_sizing）：峰值/RMS 转矩、转速、惯量比、垂直轴抱闸。

    输入取自 metadata.drives[]（drive-spec）。非法 spec 给出 DRC-DRV-900 而不是静默跳过。
    """
    drives = ctx.get("drives", [])
    if not drives:
        return [_check("DRC-DRV-000", "drive", "info", "info", "No drive (drive-spec) metadata; skipping motor torque sizing")]
    limits = {k: th[k] for k in DRIVE_DEFAULT_LIMITS if k in th}
    checks: list[dict[str, Any]] = []
    for index, spec in enumerate(drives):
        if not isinstance(spec, Mapping):
            checks.append(_check("DRC-DRV-900", "drive", "fail", "major", f"Drive {index} must be an object", target=str(index)))
            continue
        try:
            checks.extend(evaluate_drive(spec, limits)["checks"])
        except ValueError as exc:
            checks.append(_check("DRC-DRV-900", "drive", "fail", "major", f"Drive {spec.get('id') or index} has invalid drive-spec: {exc}", target=str(spec.get("id") or index)))
    return checks


BUILTIN_RULES: list[Callable[[Mapping[str, Any], Mapping[str, float]], list[dict[str, Any]]]] = [
    rule_geometry,
    rule_holes,
    rule_ligament,
    rule_thread_vs_thickness,
    rule_standard_parts,
    rule_assembly,
    rule_drawing,
    rule_relations,
    rule_fastener,
    rule_drives,
]

RULE_CATALOG = [
    {"id": "DRC-GEO-001", "category": "geometry", "title": "Minimum wall thickness", "thresholds": ["minWallThicknessMm"], "severity": "major"},
    {"id": "DRC-HOLE-001", "category": "holes", "title": "Hole edge distance", "thresholds": ["holeEdgeDistanceRatio", "holeEdgeDistanceMinMm"], "severity": "major"},
    {"id": "DRC-HOLE-002", "category": "holes", "title": "Hole spacing", "thresholds": ["holeSpacingRatio"], "severity": "warning"},
    {"id": "DRC-HOLE-003", "category": "holes", "title": "Thread engagement depth", "thresholds": ["threadEngagementRatio"], "severity": "warning"},
    {"id": "DRC-HOLE-004", "category": "holes", "title": "Hole dimension validity", "thresholds": [], "severity": "critical"},
    {"id": "DRC-HOLE-005", "category": "holes", "title": "Hole-to-hole ligament thickness (measured)", "thresholds": ["ligamentMinMm"], "severity": "major"},
    {"id": "DRC-HOLE-006", "category": "holes", "title": "Thread engagement vs plate thickness", "thresholds": ["threadEngagementRatio"], "severity": "warning"},
    {"id": "DRC-STD-001", "category": "standard_parts", "title": "Gear pointed teeth", "thresholds": [], "severity": "major"},
    {"id": "DRC-STD-002", "category": "standard_parts", "title": "Gear minimum teeth without undercut", "thresholds": ["gearMinTeeth"], "severity": "warning"},
    {"id": "DRC-STD-003", "category": "standard_parts", "title": "Spring index range", "thresholds": ["springIndexMin", "springIndexMax", "springIndexHardMin", "springIndexHardMax"], "severity": "major"},
    {"id": "DRC-STD-004", "category": "standard_parts", "title": "Spring solid vs free length", "thresholds": [], "severity": "critical"},
    {"id": "DRC-STD-005", "category": "standard_parts", "title": "Sprocket minimum teeth", "thresholds": ["sprocketMinTeeth"], "severity": "warning"},
    {"id": "DRC-ASM-001", "category": "assembly", "title": "Assembly interference", "thresholds": [], "severity": "critical"},
    {"id": "DRC-ASM-002", "category": "assembly", "title": "Assembly under-constrained", "thresholds": [], "severity": "warning"},
    {"id": "DRC-DRW-001", "category": "drawing", "title": "Missing required dimensions", "thresholds": [], "severity": "major"},
    {"id": "DRC-DRW-002", "category": "drawing", "title": "Dimensions missing tolerances", "thresholds": [], "severity": "minor"},
    {"id": "DRC-REL-001", "category": "relations", "title": "GD&T datum existence", "thresholds": [], "severity": "major"},
    {"id": "DRC-REL-002", "category": "relations", "title": "Hole table / callout coverage", "thresholds": [], "severity": "warning"},
    {"id": "DRC-REL-003", "category": "relations", "title": "BOM vs feature count consistency", "thresholds": [], "severity": "warning"},
    {"id": "DRC-CSK-001", "category": "fastener", "title": "Countersink/counterbore geometry validity", "thresholds": [], "severity": "major"},
    {"id": "DRC-CSK-002", "category": "fastener", "title": "Counterbore diameter accommodates bolt head", "thresholds": [], "severity": "major"},
    {"id": "DRC-CSK-003", "category": "fastener", "title": "Counterbore depth accommodates head height", "thresholds": [], "severity": "warning"},
    {"id": "DRC-CSK-004", "category": "fastener", "title": "Countersink facing mating surface", "thresholds": [], "severity": "critical"},
    {"id": "DRC-CSK-005", "category": "fastener", "title": "Group countersink orientation consistency", "thresholds": [], "severity": "warning"},
    {"id": "DRC-DRV-001", "category": "drive", "title": "Motor peak torque (with safety factor)", "thresholds": ["driveTorqueSafetyFactor"], "severity": "major"},
    {"id": "DRC-DRV-002", "category": "drive", "title": "Motor RMS torque vs rated", "thresholds": ["driveRmsUtilizationMax"], "severity": "major"},
    {"id": "DRC-DRV-003", "category": "drive", "title": "Required speed vs motor speed", "thresholds": [], "severity": "major"},
    {"id": "DRC-DRV-004", "category": "drive", "title": "Load-to-rotor inertia ratio", "thresholds": ["driveInertiaRatioWarn", "driveInertiaRatioMax"], "severity": "major"},
    {"id": "DRC-DRV-005", "category": "drive", "title": "Vertical/inclined axis brake", "thresholds": [], "severity": "critical"},
    {"id": "DRC-FIT-001", "category": "fastener", "title": "Cross-part head clearance (pilot)", "thresholds": [], "severity": "major"},
]

# 每条规则的标准/条款出处，便于审计时追溯依据（非强制法规，供工程复核参考）。
RULE_CLAUSES = {
    "DRC-GEO-001": {"standard": "Mechanical Design Practice", "clause": "Minimum wall thickness guideline"},
    "DRC-HOLE-001": {"standard": "Mechanical Design Handbook", "clause": "Hole edge distance guideline"},
    "DRC-HOLE-002": {"standard": "Mechanical Design Handbook", "clause": "Hole spacing guideline"},
    "DRC-HOLE-003": {"standard": "GB/T 196 / GB/T 197", "clause": "Thread engagement length"},
    "DRC-HOLE-004": {"standard": "Geometric Validity", "clause": "Positive diameter"},
    "DRC-HOLE-005": {"standard": "Mechanical Design Practice", "clause": "Minimum hole-to-hole ligament thickness"},
    "DRC-HOLE-006": {"standard": "GB/T 196 / GB/T 197", "clause": "Effective thread engagement length"},
    "DRC-STD-001": {"standard": "GB/T 1356", "clause": "Pointed tooth tip"},
    "DRC-STD-002": {"standard": "GB/T 1356", "clause": "Minimum teeth / undercut"},
    "DRC-STD-003": {"standard": "GB/T 1239 / GB/T 2089", "clause": "Spring index range"},
    "DRC-STD-004": {"standard": "GB/T 2089", "clause": "Solid height"},
    "DRC-STD-005": {"standard": "GB/T 1243", "clause": "Sprocket minimum teeth"},
    "DRC-ASM-001": {"standard": "Assembly Design", "clause": "Zero interference"},
    "DRC-ASM-002": {"standard": "Assembly Design", "clause": "Full constraint"},
    "DRC-DRW-001": {"standard": "GB/T 4458.4", "clause": "Required dimensions completeness"},
    "DRC-DRW-002": {"standard": "GB/T 1800", "clause": "Fit and tolerance callouts"},
    "DRC-REL-001": {"standard": "GB/T 1182", "clause": "Datum feature references"},
    "DRC-REL-002": {"standard": "GB/T 4458.4", "clause": "Hole table / callout completeness"},
    "DRC-REL-003": {"standard": "GB/T 10609.2", "clause": "BOM consistency with parts"},
    "DRC-CSK-001": {"standard": "GB/T 152.2/152.3/152.4", "clause": "Countersink/counterbore dimensions"},
    "DRC-CSK-002": {"standard": "GB/T 70.1 / GB/T 70.3", "clause": "Bolt head diameter accommodation"},
    "DRC-CSK-003": {"standard": "GB/T 70.1", "clause": "Counterbore depth vs head height"},
    "DRC-CSK-004": {"standard": "Assembly Design", "clause": "Countersink facing mating surface"},
    "DRC-CSK-005": {"standard": "Assembly Design", "clause": "Fastening direction consistency"},
    "DRC-FIT-001": {"standard": "Assembly Design", "clause": "Fastener head clearance"},
    "DRC-DRV-001": {"standard": "Servo Sizing Practice (Vendor Manuals)", "clause": "Peak torque check and safety factor"},
    "DRC-DRV-002": {"standard": "Servo Sizing Practice (Vendor Manuals)", "clause": "Continuous (RMS) torque check"},
    "DRC-DRV-003": {"standard": "Servo Sizing Practice (Vendor Manuals)", "clause": "Speed and torque-speed curve"},
    "DRC-DRV-004": {"standard": "Servo Sizing Practice (Vendor Manuals)", "clause": "Inertia ratio (varies by vendor/dynamics)"},
    "DRC-DRV-005": {"standard": "Machine Safety Design Practice", "clause": "Vertical-axis power-off holding / brake"},
}


def _rule_clause(check_id: str) -> dict[str, str] | None:
    """@brief 由规则 id（去掉 -OK/-000 等后缀前的主 id）查条款出处。"""
    base = str(check_id)
    if base in RULE_CLAUSES:
        return RULE_CLAUSES[base]
    # DRC-HOLE-OK / DRC-STD-000 等汇总项归到其类别的代表规则不强求出处。
    return None


def list_rules() -> dict[str, Any]:
    """@brief 返回内置规则目录与默认阈值，供代理据此用自然语言配置 Profile。"""
    return {
        "schema": "cadstudio.drc-rule-catalog",
        "version": "1.0",
        "rules": [dict(rule, referenceHint=RULE_CLAUSES.get(rule["id"]), referenceVerified=False) for rule in RULE_CATALOG],
        "defaultThresholds": dict(DEFAULT_THRESHOLDS),
        "customRule": {
            "categories": sorted({"geometry", "holes", "standard_parts", "assembly", "drawing", "relations", "fastener", "drive", "custom"}),
            "severities": ["info", "minor", "warning", "major", "critical"],
            "operators": ["lt", "lte", "gt", "gte", "eq", "ne"],
            "appliesTo": ["hole", "feature", "standard_part", "document"],
        },
    }


# ---------------------------------------------------------------------------
# 声明式自定义规则
# ---------------------------------------------------------------------------


_HOLE_FIELD_ALIASES = {"diameter": "diameter_mm", "depth": "depth_mm", "edgeDistance": "edge_distance_mm", "engagement": "engagement_mm"}


def _document_scalars(ctx: Mapping[str, Any]) -> dict[str, Any]:
    assembly = ctx.get("assembly", {})
    interferences = assembly.get("interferences")
    return {
        "minWallThicknessMm": ctx.get("min_wall_mm"),
        "holeCount": len(ctx.get("holes", [])),
        "standardPartCount": len(ctx.get("standard_parts", [])),
        "componentCount": _num(assembly.get("componentCount")),
        "mateCount": _num(assembly.get("mateCount")),
        "interferenceCount": len(interferences) if isinstance(interferences, list) else _num(assembly.get("interferenceCount")),
    }


def _compare(left: Any, operator: str, right: Any) -> bool:
    left_num, right_num = _num(left), _num(right if not isinstance(right, str) else None)
    if isinstance(right, str) and not isinstance(left, (int, float)):
        left_s, right_s = str(left), right
        if operator == "eq":
            return left_s == right_s
        if operator == "ne":
            return left_s != right_s
        return False
    if left_num is None or right_num is None:
        return False
    return {
        "lt": left_num < right_num,
        "lte": left_num <= right_num,
        "gt": left_num > right_num,
        "gte": left_num >= right_num,
        "eq": left_num == right_num,
        "ne": left_num != right_num,
    }[operator]


def _apply_custom_rule(ctx: Mapping[str, Any], rule: Mapping[str, Any]) -> list[dict[str, Any]]:
    applies = rule["appliesTo"]
    field = rule["field"]
    status = _SEVERITY_TO_STATUS[rule["severity"]]
    checks: list[dict[str, Any]] = []

    def emit(target: str, actual: Any) -> None:
        checks.append(
            _check(rule["id"], rule.get("category", "custom"), status, rule["severity"], rule["message"], target=target, field=field, actual=actual, operator=rule["operator"], value=rule["value"])
        )

    if applies == "hole":
        key = _HOLE_FIELD_ALIASES.get(field, field)
        for hole in ctx.get("holes", []):
            actual = hole.get(key)
            if actual is not None and _compare(actual, rule["operator"], rule["value"]):
                emit(hole.get("id") or "hole", actual)
    elif applies == "feature":
        for feature in ctx.get("features", []):
            params = feature.get("parameters") if isinstance(feature.get("parameters"), Mapping) else {}
            actual = params.get(field)
            if actual is not None and _compare(actual, rule["operator"], rule["value"]):
                emit(str(feature.get("id") or "feature"), actual)
    elif applies == "standard_part":
        for part in ctx.get("standard_parts", []):
            actual = part.get(field)
            if actual is not None and _compare(actual, rule["operator"], rule["value"]):
                emit(str(part.get("id") or part.get("type") or "part"), actual)
    else:  # document
        actual = _document_scalars(ctx).get(field)
        if actual is not None and _compare(actual, rule["operator"], rule["value"]):
            emit(ctx.get("documentId", "document"), actual)

    if not checks:
        checks.append(_check(rule["id"], rule.get("category", "custom"), "pass", "info", f"Custom rule {rule['id']} found no violations"))
    return checks


# ---------------------------------------------------------------------------
# 报告构建
# ---------------------------------------------------------------------------


def _resolve_profile(profiles: Sequence[str | Path | Mapping[str, Any]] | None) -> dict[str, Any]:
    if not profiles:
        return {"schema": "cadstudio.drc-profile", "version": "1.0", "id": "default", "thresholds": {}, "disabledRules": [], "customRules": []}
    return merge_profiles([load_profile(item) for item in profiles])


def _aggregate_status(checks: Sequence[Mapping[str, Any]]) -> str:
    statuses = {check.get("status") for check in checks}
    if "fail" in statuses:
        return "fail"
    if "warning" in statuses:
        return "warning"
    if not statuses or "info" in statuses:
        return "review_required"
    return "pass"


def _resolve_rule_packs(rule_packs: Sequence[str] | None) -> list[dict[str, Any]]:
    """@brief 把行业规则包名解析为 profile 列表。"""
    return [load_rule_pack(name) for name in (rule_packs or [])]


def build_drc_report(
    source: str | Path | Mapping[str, Any],
    *,
    profiles: Sequence[str | Path | Mapping[str, Any]] | None = None,
    rule_packs: Sequence[str] | None = None,
    baseline: str | Path | Mapping[str, Any] | None = None,
    waivers: Sequence[Mapping[str, Any]] | None = None,
    risk_weights: Mapping[str, float] | None = None,
    as_of_date: str | None = None,
    regression_gate: bool = False,
    regression_tolerance: float = 0.0,
) -> dict[str, Any]:
    """@brief 在中性文档上运行 DRC 并返回报告（不写盘）。

    深化能力（均可选，不传时行为向后兼容）：
    - rule_packs：叠加行业规则包（机加工支架/注塑外壳/钣金面板/钻孔面板）。
    - baseline：上一版报告（路径/对象），用于 new/fixed/persisting 增量 diff。
    - waivers：让步单列表（理由/责任人/有效期），命中且未过期的 finding 退出门禁。
    - risk_weights：风险评分权重覆盖。
    - as_of_date：让步单过期判定的当前日期（ISO）。
    - regression_gate：回归门禁（需 baseline）。候选风险分高于基线或新增 critical 即 regressionGate.passed=False。
    每条内置 finding 附带 fingerprint 与标准条款出处；报告含 audit 块与加权风险评分。
    """
    try:
        document = _load_document(source)
        context = _extract_context(document)
        merged_profiles = _resolve_rule_packs(rule_packs) + list(profiles or [])
        profile = _resolve_profile(merged_profiles or None)
        baseline_report = _load_document_json(baseline) if baseline is not None else None
    except (ValueError, DrcProfileError) as exc:
        return {
            "schema": "cadstudio.drc-report",
            "version": "1.0",
            "status": "blocked",
            "reviewRequired": True,
            "checks": [_check("DRC-INPUT", "input", "fail", "critical", str(exc))],
            "summary": {"fail": 1, "warning": 0, "pass": 0, "info": 0, "total": 1},
            "generatedAt": _now_iso(),
        }

    thresholds = dict(DEFAULT_THRESHOLDS)
    thresholds.update(profile.get("thresholds", {}))
    disabled = set(profile.get("disabledRules", []))

    checks: list[dict[str, Any]] = []
    for rule_fn in BUILTIN_RULES:
        for check in rule_fn(context, thresholds):
            if check["id"] in disabled:
                continue
            clause = _rule_clause(check["id"])
            if clause:
                check["referenceHint"] = clause
                check["referenceVerified"] = False
            checks.append(check)
    for custom_rule in profile.get("customRules", []):
        if custom_rule["id"] in disabled:
            continue
        checks.extend(_apply_custom_rule(context, custom_rule))

    audit = summarize_audit(
        checks,
        baseline_checks=baseline_report.get("checks") if isinstance(baseline_report, Mapping) else None,
        waivers=waivers,
        as_of_date=as_of_date,
        risk_weights=risk_weights,
    )
    checks = audit.pop("checks")

    regression = None
    if regression_gate:
        if not isinstance(baseline_report, Mapping):
            regression = {"passed": False, "reasons": ["Regression gate requires a baseline (previous DRC report)"], "error": "baseline_required"}
        else:
            regression = assert_no_regression(
                baseline_report.get("checks", []), checks, weights=risk_weights, tolerance=regression_tolerance
            )

    summary = {
        "fail": sum(1 for c in checks if c["status"] == "fail"),
        "warning": sum(1 for c in checks if c["status"] == "warning"),
        "pass": sum(1 for c in checks if c["status"] == "pass"),
        "info": sum(1 for c in checks if c["status"] == "info"),
        "total": len(checks),
        "waived": sum(1 for c in checks if c.get("waived")),
    }
    return {
        "schema": "cadstudio.drc-report",
        "version": "1.1",
        "documentId": context["documentId"],
        "units": "mm",
        "status": audit["gatedStatus"],
        "rawStatus": _aggregate_status(checks),
        "reviewRequired": True,
        "riskScore": audit["risk"],
        "summary": summary,
        "checks": checks,
        "audit": audit,
        **({"regressionGate": regression} if regression is not None else {}),
        "profileApplied": {
            "id": profile.get("id", "default"),
            "rulePacks": list(rule_packs or []),
            "thresholds": thresholds,
            "disabledRules": sorted(disabled),
            "customRuleCount": len(profile.get("customRules", [])),
        },
        "limitations": [
            "DRC only inspects evidence present in the neutral document; missing sections are skipped as info and do not indicate compliance.",
            "Reports always set reviewRequired=true and must not be used for unattended sign-off; risk scores and waivers do not replace engineering approval.",
            "Extracting snapshots from an active SolidWorks model is pilot functionality and requires live machine and engineering review.",
        ],
        "generatedAt": _now_iso(),
    }


def _load_document_json(source: str | Path | Mapping[str, Any]) -> dict[str, Any]:
    """@brief 读取基线报告（对象或 JSON 路径）。"""
    if isinstance(source, Mapping):
        return dict(source)
    return json.loads(Path(source).read_text(encoding="utf-8"))


def write_drc_report(
    source: str | Path | Mapping[str, Any],
    output_path: str | Path,
    *,
    profiles: Sequence[str | Path | Mapping[str, Any]] | None = None,
    rule_packs: Sequence[str] | None = None,
    baseline: str | Path | Mapping[str, Any] | None = None,
    waivers: Sequence[Mapping[str, Any]] | None = None,
    risk_weights: Mapping[str, float] | None = None,
    as_of_date: str | None = None,
    regression_gate: bool = False,
    regression_tolerance: float = 0.0,
) -> dict[str, Any]:
    """@brief 运行 DRC 并写出版本化报告，返回值附带 SHA-256 产物证据。"""
    report = build_drc_report(
        source,
        profiles=profiles,
        rule_packs=rule_packs,
        baseline=baseline,
        waivers=waivers,
        risk_weights=risk_weights,
        as_of_date=as_of_date,
        regression_gate=regression_gate,
        regression_tolerance=regression_tolerance,
    )
    requested = Path(output_path).expanduser().absolute()
    requested.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    # 独占创建避免并发检查时覆盖其他任务或用户已有报告。
    for index in range(1000):
        target = requested if index == 0 else requested.with_name(f"{requested.stem}.v{index}{requested.suffix}")
        try:
            with target.open("x", encoding="utf-8") as handle:
                handle.write(payload)
            break
        except FileExistsError:
            continue
    else:
        raise FileExistsError("Unable to allocate an unused DRC report filename")
    report["reportPath"] = str(target)
    report["artifacts"] = [
        {
            "kind": "drc_report",
            "type": "artifact",
            "format": "json",
            "path": str(target),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "sizeBytes": target.stat().st_size,
            "producedThisRun": True,
        }
    ]
    return report


def main(argv: Sequence[str] | None = None) -> int:
    """@brief 命令行入口。"""
    import argparse

    parser = argparse.ArgumentParser(description="Run Design Rule Checks (DRC) on a NeutralCadDocument.")
    parser.add_argument("input", nargs="?", help="Path to NeutralCadDocument (.cadstudio.json).")
    parser.add_argument("--output", help="Output path for the DRC report JSON.")
    parser.add_argument("--profile", action="append", default=[], help="Path to a DRC Profile JSON (repeatable).")
    parser.add_argument("--rule-pack", action="append", default=[], help="Industry rule pack name (machined_bracket/injection_shell/sheet_metal_panel/drilling_panel), repeatable.")
    parser.add_argument("--baseline", help="Previous DRC report JSON path for incremental diff.")
    parser.add_argument("--waivers", help="Waivers JSON array file (containing fingerprint or ruleId, reason, owner, optional expiresOn).")
    parser.add_argument("--as-of", help="Current ISO date for waiver expiration checks, e.g. 2026-09-08.")
    parser.add_argument("--fail-on-regression", action="store_true", help="Regression gate: exit non-zero if risk score worsens or new critical findings appear vs --baseline.")
    parser.add_argument("--regression-tolerance", type=float, default=0.0, help="Allowed risk score increase tolerance for regression gate (default: 0).")
    parser.add_argument("--list-rules", action="store_true", help="Print built-in rule catalog and default thresholds, then exit.")
    parser.add_argument("--list-rule-packs", action="store_true", help="Print built-in industry rule packs, then exit.")
    args = parser.parse_args(argv)

    if args.list_rules:
        print(json.dumps(list_rules(), ensure_ascii=False, indent=2))
        return 0
    if args.list_rule_packs:
        print(json.dumps({"rulePacks": list_rule_packs()}, ensure_ascii=False, indent=2))
        return 0
    if not args.input:
        parser.error("Provide a NeutralCadDocument path, or use --list-rules / --list-rule-packs")
    waivers = json.loads(Path(args.waivers).read_text(encoding="utf-8")) if args.waivers else None
    kwargs = dict(
        profiles=args.profile or None,
        rule_packs=args.rule_pack or None,
        baseline=args.baseline,
        waivers=waivers,
        as_of_date=args.as_of,
        regression_gate=args.fail_on_regression,
        regression_tolerance=args.regression_tolerance,
    )
    if args.output:
        report = write_drc_report(args.input, args.output, **kwargs)
    else:
        report = build_drc_report(args.input, **kwargs)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    gate_failed = isinstance(report.get("regressionGate"), dict) and not report["regressionGate"].get("passed", True)
    if report.get("status") in {"blocked", "fail"} or gate_failed:
        return 1
    return 2 if report.get("status") == "review_required" else 0


if __name__ == "__main__":
    raise SystemExit(main())
