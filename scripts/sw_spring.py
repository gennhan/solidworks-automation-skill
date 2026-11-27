"""SolidWorks 等螺距、开放端圆线弹簧的受限几何试点。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

try:
    from .sw_connect import get_com_member
except ImportError:
    from sw_connect import get_com_member


@dataclass(frozen=True)
class OpenHelicalSpringSpec:
    wire_diameter_mm: float
    mean_diameter_mm: float
    helix_height_mm: float
    turns: float
    clockwise: bool = False


def validate_spring_spec(spec: OpenHelicalSpringSpec) -> dict[str, float]:
    """校验受限几何；高度是中心线轴向行程，不是弹簧自由高度。"""
    values = []
    for name in ("wire_diameter_mm", "mean_diameter_mm", "helix_height_mm", "turns"):
        raw = getattr(spec, name)
        if isinstance(raw, bool):
            raise ValueError(f"{name} must be a finite positive number")
        value = float(raw)
        if not math.isfinite(value) or value <= 0:
            raise ValueError(f"{name} must be a finite positive number")
        values.append(value)
    wire, mean, height, turns = values
    if not isinstance(spec.clockwise, bool):
        raise ValueError("clockwise must be a boolean")
    if not 1 <= turns <= 20 or mean < wire * 4 or not .1 <= wire <= 50 or mean > 500 or height > 2000:
        raise ValueError("Pilot requires turns in 1..20, wire diameter in 0.1..50 mm, mean diameter <= 500 mm and >= 4x wire diameter, and height <= 2000 mm")
    pitch = height / turns
    if pitch < wire * 1.25 or pitch > mean * 0.5:
        raise ValueError("Pilot requires centerline pitch >= 1.25x wire diameter and <= 0.5x mean diameter")
    centerline_length = math.hypot(math.pi * mean * turns, height)
    return {"pitch_mm": pitch, "centerline_length_mm": centerline_length,
            "ideal_volume_mm3": math.pi * (wire / 2) ** 2 * centerline_length}


def exact_body_bounds_mm(body) -> list[float]:
    """用 B-Rep 极值点读取三轴长度，避免 GetPartBox 的近似包围盒。"""
    import pythoncom
    from win32com.client import VARIANT, dynamic

    ole = getattr(body, "_oleobj_", None)
    dispatch = dynamic.DumbDispatch(ole, "Body") if ole is not None else body
    bounds = []
    for axis in range(3):
        limits = []
        for direction in (-1.0, 1.0):
            vector = [0.0, 0.0, 0.0]
            vector[axis] = direction
            values = [VARIANT(pythoncom.VT_BYREF | pythoncom.VT_R8, 0.0) for _ in range(3)]
            if not dispatch.GetExtremePoint(*vector, *values):
                raise RuntimeError("Unable to read spring body extreme point")
            coordinate = float(values[axis].value)
            if not math.isfinite(coordinate):
                raise RuntimeError("Spring body extreme point is not a finite number")
            limits.append(coordinate * 1000)
        bounds.append(limits[1] - limits[0])
    return bounds


def expected_body_bounds_mm(spec: OpenHelicalSpringSpec, pitch: float) -> list[float]:
    """圆形截面垂直中心线时的径向与轴向尺寸；顺序与建模平面无关。"""
    circumference = math.pi * float(spec.mean_diameter_mm)
    end_axial_extent = float(spec.wire_diameter_mm) * circumference / math.hypot(circumference, pitch)
    return sorted([float(spec.mean_diameter_mm) + float(spec.wire_diameter_mm)] * 2
                  + [float(spec.helix_height_mm) + end_axial_extent])


def verify_helix_definition(helix, spec: OpenHelicalSpringSpec, pitch: float) -> dict[str, object]:
    """回读旋向、圈数和尺寸，不能仅凭扫描体积判断旋向。"""
    definition = get_com_member(helix, "GetDefinition")
    direction = get_com_member(definition, "Clockwise")
    by = get_com_member(definition, "DefinedBy")
    height = float(get_com_member(definition, "Height")) * 1000
    actual_pitch = float(get_com_member(definition, "Pitch")) * 1000
    turns = float(get_com_member(definition, "Revolution"))
    if direction not in (True, False) or bool(direction) != spec.clockwise or by != 1 or any(
            not math.isclose(actual, wanted, rel_tol=1e-8, abs_tol=1e-8)
            for actual, wanted in ((height, float(spec.helix_height_mm)), (actual_pitch, pitch), (turns, float(spec.turns)))):
        raise RuntimeError("Helix direction, definition mode, or dimensions readback mismatch")
    return {"clockwise": bool(direction), "defined_by": by, "height_mm": height, "pitch_mm": actual_pitch, "turns": turns}


def create_open_helical_spring(model, spec: OpenHelicalSpringSpec, plane_name: str = "Front Plane"):
    """在空零件中创建真实螺旋线和圆形截面扫描；不保存文件。"""
    calculated = validate_spring_spec(spec)
    kind = get_com_member(model, "GetType")
    if isinstance(kind, bool) or kind != 1:
        raise ValueError("A SolidWorks part document is required")
    if tuple(get_com_member(model, "GetBodies2", 0, False) or ()):
        raise ValueError("Spring can only be created in an empty part with no solid bodies")
    try:
        from .sw_part import sketch, sketch_circle, _ensure_sketch_selected
        from .sw_review import collect_model_summary
        from .sw_sketch_quality import fully_define_sketch
        from .sw_measure import collect_mass_properties
    except ImportError:
        from sw_part import sketch, sketch_circle, _ensure_sketch_selected
        from sw_review import collect_model_summary
        from sw_sketch_quality import fully_define_sketch
        from sw_measure import collect_mass_properties

    before = {item.get("name") for item in collect_model_summary(model).get("features", [])}
    with sketch(model, plane_name) as ref:
        if sketch_circle(model, 0, 0, float(spec.mean_diameter_mm) / 2000) is None:
            raise RuntimeError("Failed to create helix base circle")
        sketch_quality = fully_define_sketch(model)
    _ensure_sketch_selected(model, ref)
    # swHelixDefinedByHeightAndRevolution=1。InsertHelix 返回 void，需回读特征树。
    model.InsertHelix(False, spec.clockwise, False, False, 1, float(spec.helix_height_mm) / 1000,
                      calculated["pitch_mm"] / 1000, float(spec.turns), 0.0, 0.0)
    features = collect_model_summary(model).get("features", [])
    helixes = [item for item in features if item.get("type") == "Helix" and item.get("name") not in before]
    if len(helixes) != 1:
        raise RuntimeError("Unable to uniquely identify newly created helix")
    helix = get_com_member(model, "FeatureByName", helixes[0]["name"])
    helix_data = verify_helix_definition(helix, spec, calculated["pitch_mm"])
    model.ClearSelection2(True)
    if not get_com_member(helix, "Select2", False, 4):  # 4 = sweep path
        raise RuntimeError("Unable to select helix sweep path")
    # SW2026 类型库确认 20 个输入参数；CircularProfile=True，直径为米。
    feature = model.FeatureManager.InsertProtrusionSwept4(
        False, False, 0, False, False, 0, 0, False, 0.0, 0.0, 0, 0,
        True, False, True, 0.0, False, True, float(spec.wire_diameter_mm) / 1000, 0)
    model.ClearSelection2(True)
    if feature is None:
        raise RuntimeError("Circular profile sweep failed")
    feature.Name = "OpenHelicalSpring"
    if not model.ForceRebuild3(False):
        raise RuntimeError("Spring rebuild failed")
    bodies = tuple(get_com_member(model, "GetBodies2", 0, False) or ())
    mass = collect_mass_properties(model)
    volume = mass.get("volume_mm3")
    if len(bodies) != 1 or mass.get("errors") or not isinstance(volume, (int, float)) or not math.isfinite(volume):
        raise RuntimeError("Unable to confirm single solid body and volume")
    if not math.isclose(volume, calculated["ideal_volume_mm3"], rel_tol=0.005):
        raise RuntimeError("Actual swept volume does not match theoretical non-self-intersecting circular-wire helix volume")
    actual_bounds = exact_body_bounds_mm(bodies[0])
    expected_bounds = expected_body_bounds_mm(spec, calculated["pitch_mm"])
    if any(not math.isclose(actual, expected, rel_tol=.002, abs_tol=.03)
           for actual, expected in zip(sorted(actual_bounds), expected_bounds)):
        raise RuntimeError("Actual body extreme bounds do not match specified helix and section")
    return feature, {"status": "review_required", "input": asdict(spec), "calculated": calculated,
                     "actual_volume_mm3": volume, "actual_extreme_bounds_mm": actual_bounds,
                     "helix_feature": helixes[0]["name"], "helix_readback": helix_data,
                     "sweep_feature": str(get_com_member(feature, "Name")), "sketch_quality": sketch_quality,
                     "limitations": ["Open-end, constant-pitch helix; end coils are not closed or ground.", "Centerline height does not equal solid free length.",
                                     "Material, stiffness, fatigue, solid height, and manufacturing standards are not verified.", "Verified only on limited sizes and SW2026 examples."]}
