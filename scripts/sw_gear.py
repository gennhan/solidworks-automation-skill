"""标准外啮合直齿圆柱齿轮的渐开线几何与 SolidWorks 建模工具。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class SpurGearSpec:
    """@brief 标准全齿高外啮合直齿轮输入，尺寸单位均为毫米。"""

    module_mm: float
    teeth: int
    face_width_mm: float
    pressure_angle_deg: float = 20.0
    bore_diameter_mm: float = 0.0
    involute_segments: int = 12
    tip_arc_segments: int = 4
    root_arc_segments: int = 5


@dataclass(frozen=True)
class SpurGearGeometry:
    """@brief 经过校验的齿轮解析尺寸和闭合外轮廓。"""

    spec: SpurGearSpec
    pitch_diameter_mm: float
    base_diameter_mm: float
    outside_diameter_mm: float
    root_diameter_mm: float
    circular_pitch_mm: float
    tooth_thickness_at_pitch_mm: float
    minimum_teeth_without_undercut: int
    undercut_risk: bool
    outline_points_m: tuple[tuple[float, float], ...]
    warnings: tuple[str, ...]

    def evidence(self) -> dict:
        """@brief 返回可序列化的输入、解析尺寸和近似精度证据。"""
        return {
            "gear_type": "standard_external_spur_involute",
            "input": asdict(self.spec),
            "dimensions_mm": {
                "pitch_diameter": self.pitch_diameter_mm,
                "base_diameter": self.base_diameter_mm,
                "outside_diameter": self.outside_diameter_mm,
                "root_diameter": self.root_diameter_mm,
                "circular_pitch": self.circular_pitch_mm,
                "tooth_thickness_at_pitch": self.tooth_thickness_at_pitch_mm,
                "face_width": self.spec.face_width_mm,
                "bore_diameter": self.spec.bore_diameter_mm,
            },
            "profile": {
                "curve": "involute_of_base_circle",
                "addendum_coefficient": 1.0,
                "dedendum_coefficient": 1.25,
                "profile_shift_coefficient": 0.0,
                "root_form": "radial_transition_plus_root_arc",
                "involute_segments_per_flank": self.spec.involute_segments,
                "outline_segment_count": len(self.outline_points_m),
            },
            "minimum_teeth_without_undercut": self.minimum_teeth_without_undercut,
            "undercut_risk": self.undercut_risk,
            "warnings": list(self.warnings),
        }


def _finite_positive(value: float, name: str) -> float:
    """@brief 校验有限正数并返回浮点值。"""
    number = float(value)
    if not math.isfinite(number) or number <= 0.0:
        raise ValueError(f"{name} must be a finite positive number")
    return number


def _involute_angle(t: float) -> float:
    """@brief 返回 inv(alpha)=tan(alpha)-alpha 的参数形式。"""
    return float(t) - math.atan(float(t))


def _polar(radius_m: float, angle_rad: float) -> tuple[float, float]:
    """@brief 把极坐标转换为草图平面笛卡尔坐标。"""
    return radius_m * math.cos(angle_rad), radius_m * math.sin(angle_rad)


def _append_unique(points: list[tuple[float, float]], point: tuple[float, float]) -> None:
    """@brief 避免相邻重复点产生零长度草图线。"""
    if points and math.dist(points[-1], point) <= 1e-12:
        return
    points.append(point)


def _sample_angles(start: float, end: float, segments: int) -> Iterable[float]:
    """@brief 返回圆弧内部采样角；端点由相邻轮廓负责。"""
    for index in range(1, segments):
        yield start + (end - start) * index / segments


def calculate_external_spur_gear(spec: SpurGearSpec) -> SpurGearGeometry:
    """@brief 计算标准全齿高外啮合直齿轮的离散渐开线闭合轮廓。

    采用 ``d=m*z``、``db=d*cos(alpha)``、``da=d+2m``、
    ``df=d-2.5m``。齿廓从基圆或齿根圆中较大者开始，齿根低于基圆时使用
    径向过渡；这不是滚刀生成的精确齿根过渡曲线，因此结果必须保持 reviewed。
    """
    module_mm = _finite_positive(spec.module_mm, "module")
    face_width_mm = _finite_positive(spec.face_width_mm, "face width")
    if isinstance(spec.teeth, bool) or int(spec.teeth) != spec.teeth:
        raise ValueError("Teeth count must be an integer")
    teeth = int(spec.teeth)
    if teeth < 6 or teeth > 300:
        raise ValueError("Teeth count must be in 6..300; larger profiles require dedicated gear software or native add-ins")
    pressure_angle_deg = float(spec.pressure_angle_deg)
    if not math.isfinite(pressure_angle_deg) or not 10.0 <= pressure_angle_deg <= 35.0:
        raise ValueError("Pressure angle must be within 10..35 degrees")
    bore_diameter_mm = float(spec.bore_diameter_mm)
    if not math.isfinite(bore_diameter_mm) or bore_diameter_mm < 0.0:
        raise ValueError("Bore diameter cannot be negative")
    for value, name, lower, upper in (
        (spec.involute_segments, "involute segments per flank", 4, 64),
        (spec.tip_arc_segments, "tip arc segments", 2, 32),
        (spec.root_arc_segments, "root arc segments", 2, 32),
    ):
        if isinstance(value, bool) or int(value) != value or not lower <= int(value) <= upper:
            raise ValueError(f"{name} must be in {lower}..{upper}")

    alpha = math.radians(pressure_angle_deg)
    pitch_radius_mm = module_mm * teeth / 2.0
    base_radius_mm = pitch_radius_mm * math.cos(alpha)
    outside_radius_mm = pitch_radius_mm + module_mm
    root_radius_mm = pitch_radius_mm - 1.25 * module_mm
    if root_radius_mm <= 0.0:
        raise ValueError("Root circle radius is non-positive; increase teeth count or adjust tooth system")
    if bore_diameter_mm >= 2.0 * root_radius_mm:
        raise ValueError("Bore diameter must be smaller than root circle diameter")

    pitch = 2.0 * math.pi / teeth
    pitch_involute = _involute_angle(math.tan(alpha))
    base_half_angle = math.pi / (2.0 * teeth) + pitch_involute
    start_radius_mm = max(root_radius_mm, base_radius_mm)
    start_t = math.sqrt(max(0.0, (start_radius_mm / base_radius_mm) ** 2 - 1.0))
    tip_t = math.sqrt(max(0.0, (outside_radius_mm / base_radius_mm) ** 2 - 1.0))
    start_half_angle = base_half_angle - _involute_angle(start_t)
    tip_half_angle = base_half_angle - _involute_angle(tip_t)
    if tip_half_angle <= 0.0:
        raise ValueError("Tip thickness degenerates to zero; this parameter combination requires profile shift or another tooth system")
    if pitch - 2.0 * start_half_angle <= 0.0:
        raise ValueError("Adjacent root profiles intersect; this parameter combination is invalid for standard tooth form")

    estimated_segments = teeth * (
        2 * (int(spec.involute_segments) + 1)
        + int(spec.tip_arc_segments)
        + int(spec.root_arc_segments)
        + 2
    )
    if estimated_segments > 12_000:
        raise ValueError("Discretized tooth profile exceeds 12000 segments; reduce teeth count or sampling density")

    points: list[tuple[float, float]] = []
    scale = 0.001
    for tooth_index in range(teeth):
        center = tooth_index * pitch
        left_start_angle = center - start_half_angle
        right_start_angle = center + start_half_angle

        if root_radius_mm < start_radius_mm:
            _append_unique(points, _polar(root_radius_mm * scale, left_start_angle))

        for index in range(int(spec.involute_segments) + 1):
            ratio = index / int(spec.involute_segments)
            parameter = start_t + (tip_t - start_t) * ratio
            radius_mm = base_radius_mm * math.sqrt(1.0 + parameter * parameter)
            half_angle = base_half_angle - _involute_angle(parameter)
            _append_unique(points, _polar(radius_mm * scale, center - half_angle))

        for angle in _sample_angles(
            center - tip_half_angle,
            center + tip_half_angle,
            int(spec.tip_arc_segments),
        ):
            _append_unique(points, _polar(outside_radius_mm * scale, angle))

        for index in range(int(spec.involute_segments), -1, -1):
            ratio = index / int(spec.involute_segments)
            parameter = start_t + (tip_t - start_t) * ratio
            radius_mm = base_radius_mm * math.sqrt(1.0 + parameter * parameter)
            half_angle = base_half_angle - _involute_angle(parameter)
            _append_unique(points, _polar(radius_mm * scale, center + half_angle))

        if root_radius_mm < start_radius_mm:
            _append_unique(points, _polar(root_radius_mm * scale, right_start_angle))

        next_left_angle = center + pitch - start_half_angle
        for angle in _sample_angles(
            right_start_angle,
            next_left_angle,
            int(spec.root_arc_segments),
        ):
            _append_unique(points, _polar(root_radius_mm * scale, angle))

    if len(points) < teeth * 8:
        raise RuntimeError("Generated tooth profile point count is invalid")
    area = 0.5 * sum(
        x1 * y2 - x2 * y1
        for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1])
    )
    if area <= 0.0:
        raise RuntimeError("Tooth profile orientation or closure order is invalid")

    minimum_teeth = math.ceil(2.0 / (math.sin(alpha) ** 2))
    undercut_risk = teeth < minimum_teeth
    warnings: list[str] = [
        "Root uses radial transitions and root arcs, which is not equivalent to an exact hob-generated trochoid root fillet.",
        "Profile shift, backlash, tip relief, lead crowning, tolerances, material, and strength checks are not included.",
    ]
    if undercut_risk:
        warnings.append(
            f"Teeth count {teeth} is below the theoretical undercut minimum {minimum_teeth} for this pressure angle; undercut risk exists."
        )

    return SpurGearGeometry(
        spec=spec,
        pitch_diameter_mm=2.0 * pitch_radius_mm,
        base_diameter_mm=2.0 * base_radius_mm,
        outside_diameter_mm=2.0 * outside_radius_mm,
        root_diameter_mm=2.0 * root_radius_mm,
        circular_pitch_mm=math.pi * module_mm,
        tooth_thickness_at_pitch_mm=math.pi * module_mm / 2.0,
        minimum_teeth_without_undercut=minimum_teeth,
        undercut_risk=undercut_risk,
        outline_points_m=tuple(points),
        warnings=tuple(warnings),
    )


def create_external_spur_gear(model, spec: SpurGearSpec, plane_name: str = "Front Plane"):
    """@brief 在活动零件中绘制完整渐开线齿廓并一次拉伸成直齿轮。

    @param model SolidWorks IModelDoc2/IPartDoc。
    @param spec 标准外啮合直齿轮规格。
    @param plane_name 建模基准面，中英文名称由 ``sw_part`` 兼容。
    @return ``(feature, evidence)``；feature 为空时抛出异常。
    """
    geometry = calculate_external_spur_gear(spec)
    try:
        from .sw_part import extrude_boss, sketch, sketch_circle, sketch_line
    except ImportError:
        from sw_part import extrude_boss, sketch, sketch_circle, sketch_line

    sketch_manager = model.SketchManager
    old_add_to_db = None
    old_display = None
    with sketch(model, plane_name) as sketch_name:
        try:
            old_add_to_db = bool(sketch_manager.AddToDB)
            old_display = bool(sketch_manager.DisplayWhenAdded)
            sketch_manager.AddToDB = True
            sketch_manager.DisplayWhenAdded = False
        except Exception:
            old_add_to_db = None
            old_display = None
        try:
            points = geometry.outline_points_m
            profile_entity_count = 0
            for start, end in zip(points, points[1:] + points[:1]):
                if sketch_line(model, *start, *end) is None:
                    raise RuntimeError("Failed to create discretized gear profile segment")
                profile_entity_count += 1
            if spec.bore_diameter_mm > 0.0:
                if sketch_circle(model, 0.0, 0.0, spec.bore_diameter_mm / 2000.0) is None:
                    raise RuntimeError("Failed to create gear bore sketch circle")
                profile_entity_count += 1
        finally:
            try:
                if old_add_to_db is not None:
                    sketch_manager.AddToDB = old_add_to_db
                if old_display is not None:
                    sketch_manager.DisplayWhenAdded = old_display
            except Exception:
                pass

    feature = extrude_boss(model, sketch_name, spec.face_width_mm / 1000.0)
    if feature is None:
        raise RuntimeError("Failed to extrude gear profile")
    feature_name = f"SpurGear_m{spec.module_mm:g}_z{spec.teeth}"
    try:
        feature.Name = feature_name
    except Exception:
        pass
    model.ForceRebuild3(False)
    evidence = geometry.evidence()
    evidence.update({
        "status": "review_required",
        "feature_name": feature_name,
        "plane_name": plane_name,
        "solidworks_profile_entity_count": profile_entity_count,
        "solidworks_flank_entity": "polyline_chord_approximation",
        "solidworks_tip_root_entities": "polyline_chord_approximation",
    })
    return feature, evidence
