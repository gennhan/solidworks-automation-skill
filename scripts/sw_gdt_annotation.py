"""SolidWorks 2026 原生基准和形位公差标注试点；调用者必须提供精确对象。"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
import math
import re
import xml.etree.ElementTree as ET

try:
    from .sw_connect import get_com_member, create_empty_dispatch_variant
    from .sw_gdt_options import datum_references, datum_labels, append_datum_xml, append_options_before_material, append_flag
except ImportError:
    from sw_connect import get_com_member, create_empty_dispatch_variant
    from sw_gdt_options import datum_references, datum_labels, append_datum_xml, append_options_before_material, append_flag

# 官方 Gtol Frame XML Schema 及 SW2026 gtol.sym 的 ISO 符号名。
_SYMBOLS = {
    "straightness": "IGTOL-STRAIGHT", "flatness": "IGTOL-FLAT",
    "circularity": "IGTOL-CIRC", "cylindricity": "IGTOL-CYL",
    "line_profile": "IGTOL-LPROF", "surface_profile": "IGTOL-SPROF",
    "parallelism": "IGTOL-PARA", "perpendicularity": "IGTOL-PERP",
    "angularity": "IGTOL-ANGULAR", "position": "IGTOL-POSI",
    "concentricity": "IGTOL-CONC", "symmetry": "IGTOL-SYMMETRY",
    "circular_runout": "IGTOL-SRUN", "total_runout": "IGTOL-TRUN",
}
_FORM = {"straightness", "flatness", "circularity", "cylindricity"}
_DATUM_REQUIRED = set(_SYMBOLS) - _FORM - {"line_profile", "surface_profile"}
_DIAMETER_ALLOWED = {"straightness", "position", "parallelism", "perpendicularity", "angularity", "concentricity"}
_DATUM = re.compile(r"^[A-Z]{1,2}$")


def build_frame_xml(characteristic: str, tolerance: str, diameter: bool, datums: list, *, material_condition=None, composite=False, options=None) -> str:
    """输入公差字符串以当前图纸显示单位解释；禁止猜测默认值。"""
    if not isinstance(characteristic, str) or characteristic not in _SYMBOLS:
        raise ValueError("Unsupported GD&T characteristic")
    if not isinstance(tolerance, str) or len(tolerance) > 32 or not re.fullmatch(r"\d+(?:\.\d+)?", tolerance):
        raise ValueError("Tolerance must be an explicit non-exponential decimal string")
    try:
        value = Decimal(tolerance)
    except InvalidOperation as error:
        raise ValueError("Invalid tolerance value") from error
    if not value.is_finite() or value <= 0:
        raise ValueError("Tolerance must be greater than zero")
    if not isinstance(diameter, bool) or not isinstance(composite, bool):
        raise ValueError("Invalid tolerance zone or datum input")
    references = datum_references(datums)
    if characteristic in _FORM and datums:
        raise ValueError("Form tolerances cannot reference datums")
    if characteristic in _DATUM_REQUIRED and not datums and not composite:
        raise ValueError("This tolerance requires explicit datums")
    if diameter and characteristic not in _DIAMETER_ALLOWED:
        raise ValueError("Cylindrical tolerance zone is unsupported for this characteristic")
    if material_condition not in (None, "M", "L", "S"):
        raise ValueError("Material condition must be M, L, S, or null")
    if material_condition is not None and (characteristic not in {"position", "straightness"} or not diameter):
        raise ValueError("Material condition is supported only for cylindrical position and axis straightness")
    root = ET.Element("GtolFrame")
    ET.SubElement(root, "ToleranceSymbol").text = "" if composite else _SYMBOLS[characteristic]
    limits = ET.SubElement(root, "ToleranceRangeInfo")
    ET.SubElement(limits, "PrimaryToleranceValue").text = tolerance
    ET.SubElement(limits, "PrimaryRangeSymbol").text = "phi" if diameter else ""
    options = append_options_before_material(root, limits, options, characteristic=characteristic, tolerance=tolerance,
                                             diameter=diameter, material_condition=material_condition)
    if material_condition:
        names = {"M": "MaximumMaterialCondition", "L": "LeastMaterialCondition", "S": "RegardlessToFeatureSize"}
        material = ET.SubElement(root, "MaterialCondition")
        ET.SubElement(material, names[material_condition]).text = "true"
        if options.get("reciprocity"):
            ET.SubElement(material, "ReciprocityRequirement").text = "true"
    for key, name in (("freeState", "StateSymbol"), ("statistical", "StatisticalSymbol")):
        if key in options:
            append_flag(root, name, options[key])
    for index in range(3):
        compartment = ET.SubElement(root, "DatumCompartment")
        if index < len(references):
            append_datum_xml(compartment, references[index])
    return ET.tostring(root, encoding="unicode", short_empty_elements=False)


def build_gtol_xmls(request):
    """构建有序单框、独立多框或复合框；所有层都在写入前校验。"""
    fields = {"characteristic", "tolerance", "diameter", "datums", "materialCondition", "composite", "options"}
    if "frames" in request:
        if fields & set(request):
            raise ValueError("Multi-frame and legacy single-frame fields cannot be provided together")
        frames = request["frames"]
    else:
        frames = [{key: value for key, value in request.items() if key in fields}]
    if not isinstance(frames, list) or not 1 <= len(frames) <= 8:
        raise ValueError("Tolerance frames must contain 1..8 rows")
    xmls = []
    previous = None
    for frame in frames:
        if not isinstance(frame, dict) or set(frame) - fields or not {"characteristic", "tolerance", "diameter", "datums"} <= set(frame):
            raise ValueError("Tolerance frame fields are incomplete or contain unknown fields")
        if frame.get("options") is not None and not isinstance(frame["options"], dict):
            raise ValueError("Tolerance options must be a structured object")
        composite = frame.get("composite", False)
        if composite:
            if previous is None:
                raise ValueError("First frame cannot be a composite lower tier")
            if frame["characteristic"] != previous["characteristic"] or frame["diameter"] != previous["diameter"]:
                raise ValueError("Composite lower tier must retain the previous tier's characteristic and zone type")
            for key, default in (("symbolLibrary", "iso"), ("zoneShape", "diameter" if frame["diameter"] else "none")):
                if (frame.get("options") or {}).get(key, default) != (previous.get("options") or {}).get(key, default):
                    raise ValueError("Composite lower tier must retain the previous tier's symbol library and zone shape")
        xml = build_frame_xml(frame["characteristic"], frame["tolerance"], frame["diameter"], frame["datums"],
                              material_condition=frame.get("materialCondition"), composite=composite, options=frame.get("options"))
        if composite:
            if Decimal(frame["tolerance"]) > Decimal(previous["tolerance"]):
                raise ValueError("Composite lower tier tolerance cannot exceed the previous tier")
            old_refs, new_refs = datum_references(previous["datums"]), datum_references(frame["datums"])
            if new_refs != old_refs[:len(new_refs)]:
                raise ValueError("Composite lower tier may only keep a prefix of the previous tier's datums and modifiers in order")
        xmls.append(xml)
        previous = frame
    return xmls


def referenced_datums(request):
    frames = request.get("frames") or [request]
    return set().union(*(datum_labels(frame["datums"]) for frame in frames))


def verify_gtol_xml(actual, expected):
    """严格核对全部 XML，并指出首个不一致路径，便于查证版本/API 格式差异。"""
    if not isinstance(actual, str) or not actual or len(actual) > 65536 or "<!" in actual:
        raise RuntimeError("Invalid GTol XML readback")
    try:
        before, after = ET.fromstring(expected), ET.fromstring(actual)
    except ET.ParseError as error:
        raise RuntimeError("Unable to parse GTol XML readback") from error

    def compare(wanted, found, path):
        if wanted.tag != found.tag or wanted.attrib != found.attrib:
            return path + f" (actual tag {found.tag})"
        if (wanted.text or "") != (found.text or "") or (wanted.tail or "") != (found.tail or ""):
            return path + f" (expected {wanted.text!r}, actual {found.text!r})"
        if len(wanted) != len(found):
            return path + " (child count differs: " + ",".join(child.tag for child in found) + ")"
        return next((difference for index, (a, b) in enumerate(zip(wanted, found), 1)
                     if (difference := compare(a, b, path + f"/{a.tag}[{index}]"))), None)

    difference = compare(before, after, "GtolFrame")
    if difference:
        raise RuntimeError("GTol content readback mismatch: " + difference)


def verify_gtol_frames(symbol, expected):
    if get_com_member(symbol, "GetFormat") != 2 or get_com_member(symbol, "GetFrameCount") != len(expected):
        raise RuntimeError("GTol format or frame count mismatch")
    for index, xml in enumerate(expected, 1):
        actual = get_com_member(get_com_member(symbol, "GetFrame", index), "GetSymbolXml")
        try:
            verify_gtol_xml(actual, xml)
        except RuntimeError as error:
            raise RuntimeError(f"GTol frame {index}: {error}") from error


def _select_target(drawing, view, edge):
    if get_com_member(drawing, "GetType") != 3 or view is None or edge is None:
        raise ValueError("Drawing, owning view, and real edge must be provided")
    name = str(get_com_member(view, "Name") or "")
    if not name or not get_com_member(drawing, "ActivateView", name):
        raise RuntimeError("Unable to activate target view")
    get_com_member(drawing, "ClearSelection2", True)
    selection = get_com_member(drawing, "SelectionManager")
    data = get_com_member(selection, "CreateSelectData")
    data.View = view
    if not get_com_member(edge, "Select4", False, data) or get_com_member(selection, "GetSelectedObjectCount2", -1) != 1:
        raise RuntimeError("Unable to uniquely select target edge")


def _select_dimension(drawing, view, dimension, app):
    if get_com_member(drawing, "GetType") != 3 or view is None or dimension is None:
        raise ValueError("Drawing, owning view, and dimension object must be provided")
    view_name = str(get_com_member(view, "Name") or "")
    name = str(get_com_member(dimension, "GetNameForSelection") or "")
    members = get_com_member(view, "GetDisplayDimensions") or ()
    if sum(get_com_member(app, "IsSame", dimension, item) == 1 for item in members) != 1:
        raise ValueError("Dimension does not belong to the specified view or is not unique within it")
    if not view_name or not name or not get_com_member(drawing, "ActivateView", view_name):
        raise RuntimeError("Unable to confirm owning view of dimension")
    get_com_member(drawing, "ClearSelection2", True)
    extension = get_com_member(drawing, "Extension")
    if not get_com_member(extension, "SelectByID2", name, "DIMENSION", 0.0, 0.0, 0.0, False, 0, create_empty_dispatch_variant(), 0):
        raise RuntimeError("Unable to select dimension object")
    selection = get_com_member(drawing, "SelectionManager")
    selected = get_com_member(selection, "GetSelectedObject6", 1, -1)
    if get_com_member(selection, "GetSelectedObjectCount2", -1) != 1 or selected is None or get_com_member(app, "IsSame", dimension, selected) != 1:
        raise RuntimeError("Selected object does not match target dimension")


def _check_position(position):
    if not isinstance(position, (list, tuple)) or len(position) != 2:
        raise ValueError("Sheet coordinates (in meters) must be specified")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0 for v in position):
        raise ValueError("Sheet coordinates must be finite non-negative numbers")
    return tuple(float(v) for v in position)


def _confirm_attachment(app, annotation, edge):
    attached = get_com_member(annotation, "GetAttachedEntities3")
    if (get_com_member(annotation, "GetAttachedEntityCount3") != 1 or not isinstance(attached, (list, tuple))
            or len(attached) != 1 or attached[0] is None or get_com_member(app, "IsSame", edge, attached[0]) != 1):
        raise RuntimeError("Annotation is not attached to the target entity")


def _set_position(annotation, x, y):
    if not get_com_member(annotation, "SetPosition", x, y, 0.0):
        raise RuntimeError("Failed to set annotation position")
    actual = get_com_member(annotation, "GetPosition")
    if (not isinstance(actual, (tuple, list)) or len(actual) < 2
            or not math.isclose(float(actual[0]), x, abs_tol=1e-6)
            or not math.isclose(float(actual[1]), y, abs_tol=1e-6)):
        raise RuntimeError(f"Actual annotation position differs from requested position: requested {(x, y)}, actual {actual}")


def insert_datum(drawing, view, edge, app, label, position, *, display_style="square"):
    """插入关联指定边线的基准；失败时调用方必须丢弃本次测试图纸。"""
    if not isinstance(label, str) or not _DATUM.fullmatch(label):
        raise ValueError("Invalid datum label")
    if display_style not in ("square", "round_gb"):
        raise ValueError("Datum display_style must be explicitly set to 'square' or 'round_gb'")
    x, y = _check_position(position)
    _select_target(drawing, view, edge)
    datum = get_com_member(drawing, "InsertDatumTag2")
    if datum is None or not get_com_member(datum, "SetLabel", label) or get_com_member(datum, "GetLabel") != label:
        raise RuntimeError("Failed to create or read back datum tag")
    style = 1 if display_style == "square" else 2  # swDatumDisplayType_e，2026 类型库确认。
    if not get_com_member(datum, "SetDisplayStyle", False, style) or get_com_member(datum, "GetDisplayStyle") != style:
        raise RuntimeError("Failed to read back datum display style")
    annotation = get_com_member(datum, "GetAnnotation")
    _confirm_attachment(app, annotation, edge)
    _set_position(annotation, x, y)
    return datum


def insert_gtol(drawing, view, target, app, *, characteristic=None, tolerance=None, diameter=None, datums=None, position=None, target_kind="edge", material_condition=None, frames=None, options=None):
    """创建 2022+ XML 格式公差框；尺寸目标使用 SW 自动定位。"""
    if frames is not None:
        if any(value is not None for value in (characteristic, tolerance, diameter, datums, material_condition, options)):
            raise ValueError("Multi-frame and legacy single-frame fields cannot be provided together")
        xmls = build_gtol_xmls({"frames": frames})
    else:
        xmls = build_gtol_xmls({"characteristic": characteristic, "tolerance": tolerance, "diameter": diameter, "datums": datums, "materialCondition": material_condition, "options": options})
    xml = xmls[0]
    if target_kind == "edge":
        x, y = _check_position(position)
        _select_target(drawing, view, target)
    elif target_kind == "dimension":
        if position is not None:
            raise ValueError("SolidWorks auto-positions dimension-attached tolerances; position must not be specified")
        _select_dimension(drawing, view, target, app)
    else:
        raise ValueError("Only edge or dimension targets are supported")
    symbol = get_com_member(drawing, "InsertGtol")
    if symbol is None or not get_com_member(symbol, "CanConvertFormat") or get_com_member(symbol, "ConvertFormat") != 0:
        raise RuntimeError("Unable to create modern GTol symbol")
    if get_com_member(symbol, "GetFormat") != 2 or not get_com_member(symbol, "AddFrame"):
        raise RuntimeError("Unable to create GTol frame")
    count = get_com_member(symbol, "GetFrameCount")
    frame = get_com_member(symbol, "GetFrame", count)
    if frame is None or not get_com_member(frame, "SetSymbolXml", xml):
        raise RuntimeError("Unable to write GTol content")
    actual = get_com_member(frame, "GetSymbolXml")
    verify_gtol_xml(actual, xml)
    # 新建并转换的符号可能留下空白占位框，不能将其当成用户要求的第二框。
    for index in range(count - 1, 0, -1):
        previous = get_com_member(symbol, "GetFrame", index)
        if previous is None or get_com_member(previous, "GetSymbolXml") != "" or not get_com_member(symbol, "DeleteFrame", index):
            raise RuntimeError("Unable to remove unexpected GTol placeholder frame")
    if get_com_member(symbol, "GetFrameCount") != 1:
        raise RuntimeError("Unexpected frame count on single-frame GTol")
    for index, next_xml in enumerate(xmls[1:], 2):
        if not get_com_member(symbol, "AddFrame") or get_com_member(symbol, "GetFrameCount") != index:
            raise RuntimeError("Unable to create subsequent GTol frame")
        if not get_com_member(get_com_member(symbol, "GetFrame", index), "SetSymbolXml", next_xml):
            raise RuntimeError(f"Unable to write GTol frame {index}")
    verify_gtol_frames(symbol, xmls)
    annotation = get_com_member(symbol, "GetAnnotation")
    _confirm_attachment(app, annotation, target)
    if target_kind == "edge":
        _set_position(annotation, x, y)
    else:
        actual = get_com_member(annotation, "GetPosition")
        if not isinstance(actual, (tuple, list)) or len(actual) < 2 or not all(math.isfinite(float(v)) for v in actual[:2]):
            raise RuntimeError("Unable to confirm position of dimension-attached tolerance frame")
    return symbol
