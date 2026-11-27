"""SolidWorks 中生成用于外观和几何验证的近似链轮，不保证链条啮合。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

try:
    from .standard_parts_geometry import roller_sprocket_profile
    from .sw_connect import get_com_member
except ImportError:
    from standard_parts_geometry import roller_sprocket_profile
    from sw_connect import get_com_member


@dataclass(frozen=True)
class SprocketSpec:
    chain_pitch_mm: float
    roller_diameter_mm: float
    teeth: int
    thickness_mm: float
    bore_diameter_mm: float = 0.0
    seat_samples: int = 8


def create_approximate_sprocket(model, spec: SprocketSpec, plane_name: str = "Front Plane"):
    """在空零件中创建近似链轮；不保存文件，不宣称符合链轮标准。"""
    if isinstance(spec.thickness_mm, bool) or not math.isfinite(float(spec.thickness_mm)) or float(spec.thickness_mm) <= 0:
        raise ValueError("Thickness must be a finite positive number")
    geometry = roller_sprocket_profile(spec.chain_pitch_mm, spec.roller_diameter_mm, spec.teeth,
                                      bore_diameter_mm=spec.bore_diameter_mm, seat_samples=spec.seat_samples)
    if len(geometry.profile_xy_mm) > 2500:
        raise ValueError("Too many discretized sprocket segments; refusing creation")
    if get_com_member(model, "GetType") != 1:
        raise ValueError("A SolidWorks part document is required")
    if tuple(get_com_member(model, "GetBodies2", 0, False) or ()):
        raise ValueError("Approximate sprocket can only be created in an empty part with no solid bodies")
    try:
        from .sw_part import extrude_boss, sketch, sketch_circle, sketch_line
    except ImportError:
        from sw_part import extrude_boss, sketch, sketch_circle, sketch_line

    manager = model.SketchManager
    old_add, old_display = None, None
    with sketch(model, plane_name) as sketch_name:
        try:
            old_add = bool(manager.AddToDB)
            old_display = bool(manager.DisplayWhenAdded)
            manager.AddToDB = True
            manager.DisplayWhenAdded = False
            points = geometry.profile_xy_mm
            for a, b in zip(points, points[1:] + points[:1]):
                if sketch_line(model, a[0] / 1000.0, a[1] / 1000.0, b[0] / 1000.0, b[1] / 1000.0) is None:
                    raise RuntimeError("Failed to create sprocket profile segment")
            if geometry.bore_diameter_mm > 0 and sketch_circle(model, 0, 0, geometry.bore_diameter_mm / 2000.0) is None:
                raise RuntimeError("Failed to create sprocket bore sketch")
        finally:
            try:
                if old_add is not None:
                    manager.AddToDB = old_add
            finally:
                if old_display is not None:
                    manager.DisplayWhenAdded = old_display

    feature = extrude_boss(model, sketch_name, float(spec.thickness_mm) / 1000.0)
    if feature is None:
        raise RuntimeError("Failed to extrude approximate sprocket profile")
    feature.Name = f"ApproxSprocket_z{spec.teeth}"
    model.ForceRebuild3(False)
    bodies = tuple(get_com_member(model, "GetBodies2", 0, False) or ())
    if len(bodies) != 1:
        raise RuntimeError(f"Unexpected sprocket solid body count: {len(bodies)}")
    evidence = {"status": "review_required", "input": asdict(spec), "feature_name": feature.Name,
                "profile": "polyline_approximation", "profile_segments": len(points),
                "pitch_diameter_mm": geometry.pitch_diameter_mm, "outside_diameter_mm": geometry.outside_diameter_mm,
                "nominal_root_diameter_mm": geometry.root_diameter_mm,
                "actual_profile_min_diameter_mm": geometry.profile_min_diameter_mm,
                "limitations": ["For visual and geometric verification only; chain meshing, strength, and manufacturing standards are not verified.", "Sketch profile is a discrete polyline approximation, not an exact curve.",
                                "Profile sketch is not fully parameterized or constrained; regenerate and re-verify after changing parameters."]}
    return feature, evidence
