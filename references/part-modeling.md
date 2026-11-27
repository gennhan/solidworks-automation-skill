# Part Modeling API Reference

## Sketch Operations

### Reference Plane Selection

```python
# 英文版
model.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0)
# 中文版
model.Extension.SelectByID2("前视基准面", "PLANE", 0, 0, 0, False, 0, None, 0)
```

Reference plane mapping:
| English | Chinese | Normal Direction |
|---|---|---|
| Front Plane | 前视基准面 | Z-axis |
| Top Plane | 上视基准面 | Y-axis |
| Right Plane | 右视基准面 | X-axis |

### Sketch Geometry Methods Quick Reference

| Method | Parameters | Description |
|---|---|---|
| `CreateLine(x1,y1,z1, x2,y2,z2)` | Start and end coordinates (meters) | Line |
| `CreateCircleByRadius(cx,cy,cz, r)` | Center + radius | Circle |
| `CreateCenterRectangle(cx,cy,cz, rx,ry,rz)` | Center + corner point | Center rectangle |
| `CreateCornerRectangle(x1,y1,z1, x2,y2,z2)` | Opposite corner points | Corner rectangle |
| `CreateArc(cx,cy,cz, x1,y1,z1, x2,y2,z2, dir)` | Center + start/end points + direction | Arc |
| `CreatePolygon(cx,cy,cz, sx,sy,sz, sides, inscr)` | Center + vertex + number of sides | Regular polygon |
| `CreateEllipse(cx,cy,cz, mx,my,mz, r)` | Center + major axis endpoint + minor radius | Ellipse |
| `CreateSpline2(pointArray, closed)` | Point array + closed flag | Spline |
| `CreateSketchSlot(type, w, w, ...)` | Type + width + endpoints | Slot |

### Sketch Relations (Constraints)

```python
# 选中实体后添加约束
model.SketchAddConstraints("sgHORIZONTAL")
```

Common constraint types: `sgHORIZONTAL`, `sgVERTICAL`, `sgCOLINEAR`, `sgPARALLEL`, `sgPERPENDICULAR`, `sgTANGENT`, `sgCONCENTRIC`, `sgEQUAL`, `sgSYMMETRIC`, `sgMIDPOINT`, `sgCOINCIDENT`. `sgFIXED` must only be used for explicitly fixed references and must not be applied in bulk to fake a fully defined parametric sketch.

Coordinates only define initial geometric positions and are not equivalent to driving dimensions and geometric relations. For basic circular/rectangular sketches, call `sw_sketch_quality.fully_define_sketch(model)` while in sketch edit mode; this adds dimensions and relations relative to the actual origin and reads back the constraint status, dimension count, and Fix count. For complex sketches, manually define the design parameters first, then call `inspect_model_sketches(model)` to inspect them; any missing dimensions, dangling entities, or insufficient evidence require review.

### Native Patterns

`sw_part.linear_pattern()` delegates to `sw_pattern`, selecting the exact seed feature and a real straight edge parallel to the direction vector, and invokes the 20-parameter `FeatureLinearPattern4`. The direction vector is dimensionless while spacing is passed in meters; stop immediately if selection fails. Circular patterns use an explicit axis name or entity; do not treat `InsertAxis2` as a `FeatureManager` member. Verified on live SolidWorks 2026: after saving and reopening, changing plate thickness preserves hole count and hole center positions.

### Reliable Sketch Selection Strategy

Prefer using the `sw_part.sketch()` context manager or the return value of `end_sketch()`, rather than relying solely on hardcoded `SelectByID2("Sketch1", "SKETCH", ...)`. Chinese SolidWorks 2024 has reported cases where selecting by SKETCH name persistently returns `False`.

Recommended:

```python
with sketch(model, "Front Plane") as sketch_name:
    sketch_circle(model, 0, 0, mm(25))
feature = extrude_boss(model, sketch_name, mm(50))
```

Manual workflow:

```python
start_sketch(model, "Front Plane")
sketch_circle(model, 0, 0, mm(25))
sketch_ref = end_sketch(model)
feature = extrude_boss(model, sketch_ref, mm(50))
```

Internal rule: `extrude_boss()` / `extrude_cut()` select the sketch in the following order: active sketch reference -> cached reference from creation -> `FeatureByName` -> `SelectByID2("SKETCH")`. Residual selections are no longer treated as evidence that the sketch is selected.

## Feature Operations

### FeatureExtrusion3 Parameter Details

```python
feature_mgr.FeatureExtrusion3(
    Sd,           # bool: 单方向（True）或双方向（False）
    Flip,         # bool: 翻转切割方向
    Dir,          # bool: 翻转挤出方向
    T1,           # int: 终止条件1 (见下表)
    T2,           # int: 终止条件2（双方向时使用）
    D1,           # float: 深度1（米）
    D2,           # float: 深度2
    Dchk1,        # bool: 拔模1
    Dchk2,        # bool: 拔模2
    Ddir1,        # bool: 拔模方向1向外
    Ddir2,        # bool: 拔模方向2向外
    Dang1,        # float: 拔模角度1（弧度）
    Dang2,        # float: 拔模角度2
    OffsetReverse1, # bool: 偏移反转1
    OffsetReverse2, # bool: 偏移反转2
    TranslateSurface, # bool: 平移曲面
    Merge,        # bool: 合并结果
    UseFeatScope, # bool: 自动选择实体范围
    UseAutoSelect, # bool: 自动选择
    T0,           # bool:
    StartOffset   # float: 起始偏移
)
```

End condition enumeration:
| Value | Name | Description |
|---|---|---|
| 0 | swEndCondBlind | Blind |
| 1 | swEndCondThroughAll | Through All |
| 2 | swEndCondThroughAllBoth | Through All - Both |
| 5 | swEndCondUpToSurface | Up To Surface |
| 6 | swEndCondMidPlane | Mid Plane |
| 7 | swEndCondUpToBody | Up To Body |

### FeatureCut4 Parameter Details

Similar to `FeatureExtrusion3`, but used for cut operations. Additional parameters:
- `NormalCut`: Normal cut
- `FlipSide`: Flip side to cut

### FeatureRevolve2 Parameters

```python
feature_mgr.FeatureRevolve2(
    SingleDir,     # bool: 单方向
    IsSolid,       # bool: 实体旋转（True）
    IsThin,        # bool: 薄壁旋转
    IsCut,         # bool: 切除旋转
    ReverseDir,    # bool: 反转方向
    BothDirectionUpToSameEntity, # bool
    Dir1Type,      # int: 终止条件（0=Blind）
    Dir2Type,      # int
    Dir1Angle,     # float: 旋转角度（弧度）
    Dir2Angle,     # float
    OffsetReverse1, # bool
    OffsetReverse2, # bool
    OffsetDistance1, # float
    OffsetDistance2, # float
    ThinType,      # int: 薄壁类型
    ThinThickness1, # float
    ThinThickness2, # float
    Merge,         # bool
    UseFeatScope,  # bool
    UseAutoSelect  # bool
)
```

### Recommended Stepped Shaft Modeling Workflow

For shaft components, prefer generating the main body in a single operation using a half-section profile + centerline + Revolved Boss/Base instead of extruding and merging cylinders segment by segment. This keeps the FeatureManager design tree shorter and makes shoulder positions and overall length easier to control from a parameter table.

Recommended approach:

1. Define shaft segments in millimeters using a parameter table: `start_mm`, `end_mm`, `diameter_mm`.
2. Draw a centerline on `Front Plane` as the axis of revolution.
3. Generate a closed half-section profile based on the segment radii.
4. Immediately verify that the returned feature from `FeatureRevolve2(..., 2*pi, ...)` is not `None`.
5. Record dimensional tolerances, GD&T, and surface roughness as engineering requirements in custom properties or delivery notes; do not directly perturb nominal solid dimensions.

Minimal pattern:

```python
segments = [
    {"start": 0, "end": 43, "diameter": 56},
    {"start": 43, "end": 113, "diameter": 65},
]

with sketch(model, "Front Plane") as sketch_name:
    model.SketchManager.CreateCenterLine(mm(-5), 0, 0, mm(120), 0, 0)
    points = [(0, 0), (0, 28), (43, 28), (43, 32.5), (113, 32.5), (113, 0), (0, 0)]
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        model.SketchManager.CreateLine(mm(x1), mm(y1), 0, mm(x2), mm(y2), 0)

model.ClearSelection2(True)
model.Extension.SelectByID2(sketch_name, "SKETCH", 0, 0, 0, False, 0, create_empty_dispatch_variant(), 0)
feature = model.FeatureManager.FeatureRevolve2(
    True, True, False, False, False, False,
    0, 0, 2 * math.pi, 0,
    False, False, 0, 0, 0, 0, 0,
    True, True, True,
)
if feature is None:
    raise RuntimeError("阶梯轴旋转主体创建失败")
```

### Oblong Slots on Cylindrical Surfaces

When keyways, oblong slots, or local pockets in a drawing are located on an outer cylindrical surface, do not cut directly from the center reference plane. Cutting from the center plane can split the shaft open, making the preview look like a large planar opening rather than a surface pocket.

Reliable approach:

1. Create an offset reference plane parallel to `Front Plane` with an offset distance approximately equal to the target cylinder radius.
2. Sketch the oblong slot on that tangent reference plane using `sketch_slot()`.
3. Express slot depth with a blind cut; try one direction first, and toggle `flip` if it fails.
4. Hide the temporary reference plane after creation so the orange plane does not clutter preview renders.

```python
plane = model.FeatureManager.InsertRefPlane(8, mm(radius_mm), 0, 0, 0, 0)
plane.Name = "Plane_Keyway_Tangent"

model.Extension.SelectByID2(plane.Name, "PLANE", 0, 0, 0, False, 0, create_empty_dispatch_variant(), 0)
model.SketchManager.InsertSketch(True)
sketch_name = model.SketchManager.ActiveSketch.Name
sketch_slot(model, mm(x1), 0, mm(x2), 0, mm(slot_width_mm / 2))
model.SketchManager.InsertSketch(True)

feature = extrude_cut(model, sketch_name, mm(depth_mm), direction=True, flip=True)
if feature is None:
    feature = extrude_cut(model, sketch_name, mm(depth_mm), direction=True, flip=False)
if feature is None:
    raise RuntimeError("圆柱表面长圆槽创建失败")
```

Note: In `CreateSketchSlot`, the `radius` parameter relates to the slot width; verify actual behavior with a local test. When manufacturing-grade slot width accuracy is critical, verify after export using measurement tools or a 2D drawing.

### Fillet / Chamfer

```python
# 圆角 FeatureFillet 参数
feature_mgr.FeatureFillet(
    Options,   # int: 195 = 常用默认值
    R1,        # float: 半径（米）
    R2,        # float: 第二半径
    R3,        # float: 第三半径
    Rarray1,   # variant: 半径数组1
    Rarray2,   # variant: 半径数组2
    Rarray3    # variant: 半径数组3
)

# 倒角 InsertFeatureChamfer
feature_mgr.InsertFeatureChamfer(
    Options,     # int: 4 = 角度距离
    ChamferType, # int: 1 = 等距离
    Width,       # float: 距离（米）
    Angle,       # float: 角度（弧度）
    OtherDist,   # float: 另一距离
    VertexDist1, # float
    VertexDist2, # float
    VertexDist3  # float
)
```

### Current Reliability Boundary for Fillets and Chamfers

The main difficulty with fillets and chamfers is not the API parameters themselves, but **reliably selecting the target edges or faces**. Different SolidWorks versions, UI languages, feature orders, and sketch contours all change auto-generated `Edge`/`Face` names, so do not treat "arbitrary coordinate `SelectByID2` edge picking + `FeatureFillet`" as a high-reliability workflow.

Recommended strategy:

1. Do not treat cosmetic fillets/chamfers as hard success criteria for baseline demos or unattended batch scripts.
2. When fillets are needed, prefer approximating them at the modeling stage with more stable sketch contours such as arcs, slots, or filleted rectangles.
3. When feature-level fillets or chamfers are mandatory, enumerate bodies/faces/edges and filter target edges by geometric criteria before selecting entity objects for the feature; never rely on transient `Edge1` names.
4. If a fillet fails, fall back to preserving the sharp-edged model and note "cosmetic fillet not applied" in the review report or final summary rather than failing the entire model generation workflow.

## SelectByID2 Entity Types

| Type String | Description |
|---|---|
| `"PLANE"` | Reference Plane |
| `"FACE"` | Face |
| `"EDGE"` | Edge |
| `"VERTEX"` | Vertex |
| `"SKETCH"` | Sketch |
| `"BODYFEATURE"` | Solid Body Feature |
| `"COMPONENT"` | Component |
| `"AXIS"` | Axis |
| `"SKETCHSEGMENT"` | Sketch Segment |
| `"SKETCHPOINT"` | Sketch Point |
| `"EXTSKETCHSEGMENT"` | External Sketch Segment |
| `"REFERENCECURVES"` | Reference Curves |
