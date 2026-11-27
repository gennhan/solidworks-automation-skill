"""结构化工程图要求到原生尺寸/基准/GTol；不推测工程公差。"""
from __future__ import annotations

from copy import deepcopy
import math
import re
import json

from scripts.sw_connect import get_com_member
from scripts.sw_gdt_annotation import build_gtol_xmls, referenced_datums
from scripts.sw_gdt_copy import resolve_target, _persistent_id, _same_id, _resolve_plan, create_annotations

DIMENSION_TYPES = {"linear": {2, 11, 12}, "overall": {2, 11, 12}, "diameter": {6}, "radius": {5}, "angular": {3}}


def orientation(name):
    compact = re.sub(r"[^a-z\u4e00-\u9fff]", "", str(name).casefold())
    return {"front": "front", "frontview": "front", "前视": "front", "主视": "front",
            "top": "top", "topview": "top", "上视": "top", "俯视": "top",
            "right": "right", "rightview": "right", "右视": "right"}.get(compact)


def _number(value, *, positive=False):
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(value) and (value > 0 if positive else True)


def _position(value):
    return isinstance(value, list) and len(value) == 2 and all(_number(item) and item >= 0 for item in value)


def validate_dimensions(rows):
    from jsonschema import Draft202012Validator
    from scripts.sw_gdt_copy import SCHEMA
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    target_validator = Draft202012Validator({"$defs": schema["$defs"], "$ref": "#/$defs/target"})
    fields = {"id", "kind", "view", "valueMm", "valueDegrees", "axis", "positionMm", "target", "targets", "prefix", "basic"}
    for row in rows:
        if (not isinstance(row, dict) or set(row) - fields or not {"id", "kind", "view", "positionMm"} <= set(row)
                or row["kind"] not in DIMENSION_TYPES or not orientation(row["view"]) or not _position(row["positionMm"])):
            raise ValueError("Dimension must specify executable kind, standard view, explicit geometric target, value, and position")
        angular = row["kind"] == "angular"
        if not _number(row.get("valueDegrees" if angular else "valueMm"), positive=True):
            raise ValueError("Dimension must provide a positive valueMm or angular valueDegrees")
        if angular and "valueMm" in row or not angular and "valueDegrees" in row:
            raise ValueError("Conflicting dimension unit fields")
        if row["kind"] in {"linear", "overall"} and row.get("axis") not in {"horizontal", "vertical"}:
            raise ValueError("Linear dimension must specify horizontal or vertical axis")
        if ("target" in row) == ("targets" in row):
            raise ValueError("Dimension must provide either a single target or a pair of targets")
        targets = row.get("targets", [row.get("target")])
        if not isinstance(targets, list) or len(targets) not in (1, 2) or angular and len(targets) != 2:
            raise ValueError("Invalid dimension geometric target count")
        if row["kind"] in {"diameter", "radius"} and (len(targets) != 1 or targets[0].get("kind") != "circle"):
            raise ValueError("Radial dimension must reference a single circular edge")
        for target in targets:
            if not isinstance(target, dict) or target.get("kind") not in {"line", "circle"}:
                raise ValueError("New dimensions only accept explicit line or circular edges")
            errors = list(target_validator.iter_errors(target))
            if errors:
                raise ValueError("Invalid dimension geometry selector structure: " + errors[0].message)
        if "prefix" in row and (not isinstance(row["prefix"], str) or len(row["prefix"]) > 32):
            raise ValueError("Invalid dimension prefix")
        if "basic" in row and not isinstance(row["basic"], bool):
            raise ValueError("basic must be a boolean")


def validate_native_requests(spec):
    """返回可执行性问题；仅声明文字的历史要求继续阻断，不能伪造实体。"""
    issues = []
    dimensions = spec.get("requiredDimensions") or []
    try:
        validate_dimensions(dimensions)
    except (ValueError, TypeError, AttributeError) as error:
        issues.append({"code": "DRAWING_REQUIRED_DIMENSIONS_UNSUPPORTED", "path": "requiredDimensions", "message": str(error)})
    if dimensions and spec.get("insertModelDimensions") is True:
        issues.append({"code": "DRAWING_DIMENSION_MODE_CONFLICT", "path": "insertModelDimensions", "message": "Explicit dimensions and bulk model dimension import cannot be enabled simultaneously to avoid duplicate annotations"})
    requests = spec.get("professionalAnnotations") or {}
    if (dimensions or any(requests.get(key) for key in ("datums", "geometricTolerances"))) and spec.get("documentType") != "part":
        issues.append({"code": "DRAWING_NATIVE_PART_REQUIRED", "path": "documentType", "message": "Automated native dimension/GD&T placement currently supports single parts only; assemblies require a dedicated entrypoint"})
    sheet_mm = {"A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594), "A0": (1189, 841)}.get(spec.get("paperSize"))
    placed = list(dimensions) + [row for key in ("datums", "geometricTolerances") for row in requests.get(key) or []]
    placed += [row for row in (spec.get("views") or {}).values() if isinstance(row, dict)]
    if sheet_mm and any(isinstance(row, dict) and "positionMm" in row and
                        (not _position(row["positionMm"]) or any(v >= bound for v, bound in zip(row["positionMm"], sheet_mm))) for row in placed):
        issues.append({"code": "DRAWING_POSITION_OUTSIDE_SHEET", "path": "positionMm", "message": "Explicitly specified position must lie within the selected landscape sheet bounds"})
    for key in ("datums", "geometricTolerances"):
        rows = requests.get(key) or []
        if any(not isinstance(row, dict) or "target" not in row or not orientation(row.get("view")) for row in rows):
            issues.append({"code": "DRAWING_PROFESSIONAL_ANNOTATIONS_UNSUPPORTED", "path": "professionalAnnotations." + key, "message": "Structured geometric targets are required; plain text cannot substitute for native annotations"})
    ids = [row.get("id") for row in dimensions if isinstance(row, dict)]
    ids += [row.get("id") for key in ("datums", "geometricTolerances") for row in requests.get(key) or [] if isinstance(row, dict)]
    if ids and (any(not isinstance(item, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_.-]{0,63}", item) for item in ids) or len(set(ids)) != len(ids)):
        issues.append({"code": "DRAWING_BINDING_ID_INVALID", "path": "id", "message": "Executable annotation IDs must be unique 1..64 char identifiers starting with a letter and using letters, digits, '.', '-', or '_'"})
    available = {row["label"] for row in requests.get("datums") or [] if isinstance(row, dict) and "label" in row}
    if len(available) != len(requests.get("datums") or []) and requests.get("datums"):
        issues.append({"code": "DRAWING_DATUM_ID_INVALID", "path": "professionalAnnotations.datums", "message": "Unique datum labels are required"})
    for row in requests.get("geometricTolerances") or []:
        if not isinstance(row, dict) or "target" not in row:
            continue
        try:
            build_gtol_xmls(row)
            if not referenced_datums(row) <= available:
                raise ValueError("Tolerance references an undeclared datum")
            target = row["target"]
            if target.get("kind") == "dimension" and "dimensionId" in target:
                matches = [item for item in dimensions if item.get("id") == target["dimensionId"] and orientation(item.get("view")) == orientation(row.get("view"))]
                if len(matches) != 1:
                    raise ValueError("Tolerance dimensionId not found or belongs to another view")
            if (target.get("kind") == "dimension") == ("positionMm" in row):
                raise ValueError("Dimension-attached tolerances auto-position; edge-attached tolerances must specify positionMm")
        except (ValueError, TypeError, KeyError, AttributeError) as error:
            issues.append({"code": "DRAWING_GDT_SPEC_INVALID", "path": "professionalAnnotations.geometricTolerances", "message": str(error)})
    for hole in spec.get("holeRequirements") or []:
        matches = [row for row in dimensions if row.get("id") == hole.get("dimensionId") and row.get("kind") == "diameter"]
        match = re.fullmatch(r"[Ø⌀]\s*(\d+(?:\.\d+)?)(?:\s*(?:通孔|THRU))?", str(hole.get("specification") or ""), re.I)
        prefix = re.fullmatch(r"\s*(\d+)\s*[Xx×]\s*", str(matches[0].get("prefix") or "")) if len(matches) == 1 else None
        if (set(hole) - {"id", "specification", "count", "locationsMm", "view", "datum", "dimensionId"}
                or not match or len(matches) != 1 or not prefix or int(prefix[1]) != hole.get("count")
                or not math.isclose(float(match[1]), matches[0].get("valueMm", -1), abs_tol=1e-8)):
            issues.append({"code": "DRAWING_HOLE_REQUIREMENTS_UNSUPPORTED", "path": "holeRequirements", "message": "Automated hole callouts require matching diameter dimensionId, exact count prefix, and explicit diameter; hole tables/threads require a dedicated entrypoint"})
    return issues


def describe_target(owner):
    """从真实标注的唯一关联实体回读选择器；不明实体返回 unknown。"""
    try:
        ann = get_com_member(owner, "GetAnnotation")
        attached = get_com_member(ann, "GetAttachedEntities3") or ()
        if get_com_member(ann, "GetAttachedEntityCount3") != 1 or len(attached) != 1 or attached[0] is None:
            return {"kind": "unknown"}
        target = attached[0]
        try:
            curve = get_com_member(target, "GetCurve")
        except Exception:
            curve = None
        if curve is not None:
            if get_com_member(curve, "IsLine"):
                start, end = get_com_member(target, "GetStartVertex"), get_com_member(target, "GetEndVertex")
                return {"kind": "line", "startMm": [1000 * value for value in get_com_member(start, "GetPoint")],
                        "endMm": [1000 * value for value in get_com_member(end, "GetPoint")]}
            if get_com_member(curve, "IsCircle"):
                values = get_com_member(curve, "CircleParams")
                return {"kind": "circle", "centerMm": [1000 * value for value in values[:3]], "radiusMm": 1000 * values[6]}
        name = get_com_member(target, "GetNameForSelection")
        binding = dimension_binding(get_com_member(get_com_member(target, "GetAnnotation"), "GetName"), get_com_member(target, "Type2"))
        return {"kind": "dimension", "name": str(name), "dimensionId": binding.get("id"),
                "systemValue": get_com_member(get_com_member(target, "GetDimension2", 0), "SystemValue")}
    except Exception:
        return {"kind": "unknown"}


def target_matches(expected, actual):
    if not isinstance(actual, dict) or expected.get("kind") != actual.get("kind"):
        return False
    def near(a, b):
        return isinstance(b, (tuple, list)) and len(a) == len(b) and all(_number(value) and math.isclose(value, intended, abs_tol=1e-5, rel_tol=0) for intended, value in zip(a, b))
    kind = expected["kind"]
    if kind == "line":
        return (near(expected["startMm"], actual.get("startMm")) and near(expected["endMm"], actual.get("endMm"))) or (near(expected["startMm"], actual.get("endMm")) and near(expected["endMm"], actual.get("startMm")))
    if kind == "circle":
        return near(expected["centerMm"], actual.get("centerMm")) and near([expected["radiusMm"]], [actual.get("radiusMm")])
    if kind == "dimension":
        if "dimensionId" in expected:
            return expected["dimensionId"] == actual.get("dimensionId")
        return expected["name"] == actual.get("name") and near([expected["systemValue"]], [actual.get("systemValue")])
    return False


def map_views(drawing, creation):
    actual = get_com_member(get_com_member(drawing, "GetCurrentSheet"), "GetViews") or ()
    result = {}
    for record in creation["views"]:
        key = orientation(record["name"])
        candidates = [view for view in actual if get_com_member(view, "Name") == record["actual_name"]]
        if key and len(candidates) == 1:
            result[key] = candidates[0]
    if set(result) != {"front", "top", "right"}:
        raise ValueError("Unable to uniquely read back standard views")
    return result


def create_dimensions(drawing, rows, views):
    validate_dimensions(rows)
    resolved = []
    for row in rows:
        view = views[orientation(row["view"])]
        targets = row.get("targets", [row.get("target")])
        try:
            resolved.append((row, view, [resolve_target(view, target) for target in targets]))
        except ValueError as error:
            raise ValueError(f"Dimension {row['id']}: {error}") from error
    result = {}
    for row, view, targets in resolved:
        name = str(get_com_member(view, "Name"))
        if not get_com_member(drawing, "ActivateView", name):
            raise RuntimeError("Unable to activate dimension view")
        get_com_member(drawing, "ClearSelection2", True)
        manager = get_com_member(drawing, "SelectionManager")
        data = get_com_member(manager, "CreateSelectData")
        data.View = view
        for index, edge in enumerate(targets):
            if not get_com_member(edge, "Select4", bool(index), data):
                raise RuntimeError("Failed to select dimension edge")
        if get_com_member(manager, "GetSelectedObjectCount2", -1) != len(targets):
            raise RuntimeError("Dimension selection count does not match plan")
        kind = row["kind"]
        method = {"diameter": "AddDiameterDimension2", "radius": "AddRadialDimension2", "angular": "AddDimension2"}.get(kind)
        if kind in {"linear", "overall"}:
            method = "AddHorizontalDimension2" if row["axis"] == "horizontal" else "AddVerticalDimension2"
        x, y = (value / 1000 for value in row["positionMm"])
        display = get_com_member(drawing, method, x, y, 0.)
        if display is None:
            raise RuntimeError("Failed to create native dimension: " + row["id"])
        dimension = get_com_member(display, "GetDimension2", 0)
        expected = math.radians(row["valueDegrees"]) if kind == "angular" else row["valueMm"] / 1000
        if get_com_member(display, "Type2") not in DIMENSION_TYPES[kind] or not math.isclose(get_com_member(dimension, "SystemValue"), expected, rel_tol=0, abs_tol=1e-8):
            raise RuntimeError("Dimension type or actual value does not match request: " + row["id"])
        if "prefix" in row:
            get_com_member(display, "SetText", 1, row["prefix"])
            if get_com_member(display, "GetText", 1) != row["prefix"]:
                raise RuntimeError("Dimension prefix readback failed")
        if row.get("basic"):
            tolerance = get_com_member(dimension, "Tolerance")
            tolerance.Type = 1  # swTolBASIC，2026 类型库确认。
            if get_com_member(tolerance, "Type") != 1:
                raise RuntimeError("Basic dimension frame did not take effect")
        annotation = get_com_member(display, "GetAnnotation")
        if get_com_member(annotation, "IsDangling") is not False:
            raise RuntimeError("Created dimension attachment is dangling or cannot be confirmed")
        binding = "CAD_DIM__" + kind + "__" + row["id"]
        if not get_com_member(annotation, "SetName", binding) or get_com_member(annotation, "GetName") != binding:
            raise RuntimeError("Unable to persistently bind dimension ID")
        result[row["id"]] = {"object": display, "view": name, "request": row,
                              "persistent_id": _persistent_id(get_com_member(drawing, "Extension"), annotation)}
    return result


def create_professional_annotations(drawing, requests, creation, app, dimensions, sheet_size):
    views = map_views(drawing, creation)
    normalized = {key: deepcopy(requests.get(key) or []) for key in ("datums", "geometricTolerances")}
    for rows in normalized.values():
        for row in rows:
            row["view"] = str(get_com_member(views[orientation(row["view"])], "Name"))
    plan = {**normalized, "sheet": str(get_com_member(get_com_member(drawing, "GetCurrentSheet"), "GetName"))}
    resolved = _resolve_plan(drawing, plan, expected_sheet_size=sheet_size, dimensions=dimensions)
    return create_annotations(drawing, resolved, app, name_ids=True)


def dimension_binding(name, native_type):
    """只从实际原生名称还原绑定，且检查声明种类与原生类型相符。"""
    parts = str(name or "").split("__", 2)
    if len(parts) == 3 and parts[0] == "CAD_DIM" and native_type in DIMENSION_TYPES.get(parts[1], set()):
        return {"id": parts[2], "kind": parts[1]}
    return {}


def verify_dimensions(drawing, dimensions):
    extension = get_com_member(drawing, "Extension")
    views = get_com_member(get_com_member(drawing, "GetCurrentSheet"), "GetViews") or ()
    for identifier, record in dimensions.items():
        candidates = []
        for view in views:
            if get_com_member(view, "Name") == record["view"]:
                for display in get_com_member(view, "GetDisplayDimensions") or ():
                    ann = get_com_member(display, "GetAnnotation")
                    if _same_id(extension, record["persistent_id"], _persistent_id(extension, ann)):
                        candidates.append(display)
        if len(candidates) != 1:
            raise RuntimeError("Dimension persistent identity mismatch after reopen: " + identifier)
        display = candidates[0]
        row = record["request"]
        annotation = get_com_member(display, "GetAnnotation")
        if get_com_member(annotation, "IsDangling") is not False:
            raise RuntimeError("Dimension attachment is dangling or cannot be confirmed after reopen")
        if dimension_binding(get_com_member(annotation, "GetName"), get_com_member(display, "Type2")) != {"id": identifier, "kind": row["kind"]}:
            raise RuntimeError("Dimension ID or type mismatch after reopen")
        dimension = get_com_member(display, "GetDimension2", 0)
        expected = math.radians(row["valueDegrees"]) if row["kind"] == "angular" else row["valueMm"] / 1000
        if not math.isclose(get_com_member(dimension, "SystemValue"), expected, rel_tol=0, abs_tol=1e-8):
            raise RuntimeError("Dimension value mismatch after reopen")
        if row.get("basic") and get_com_member(get_com_member(dimension, "Tolerance"), "Type") != 1:
            raise RuntimeError("Basic dimension frame lost after reopen")
        if "prefix" in row and get_com_member(display, "GetText", 1) != row["prefix"]:
            raise RuntimeError("Dimension count prefix lost after reopen")
        if "saved_position" in record:
            actual = get_com_member(annotation, "GetPosition")
            if len(actual) != len(record["saved_position"]) or any(not math.isclose(a, b, abs_tol=1e-8, rel_tol=0) for a, b in zip(actual, record["saved_position"])):
                raise RuntimeError("Dimension position mismatch after reopen")
