# Assembly and Kinematic Mate Reference

## Official Documentation Links

- AddMate5: `https://help.solidworks.com/2023/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.iassemblydoc~addmate5.html`
- GetModelDoc2: `https://help.solidworks.com/2019/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.icomponent2~getmodeldoc2.html`
- GetCorresponding: `https://help.solidworks.com/2019/English/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.icomponent2~getcorresponding.html`
- IsCylinder / CylinderParams: `https://help.solidworks.com/2021/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISurface~IsCylinder.html`, `https://help.solidworks.com/2024/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISurface~CylinderParams.html`
- Gear Mates: `https://help.solidworks.com/2024/English/solidworks/sldworks/t_Gear_Mates_SWassy.htm`
- Hinge Mates: `https://help.solidworks.com/2023/english/SolidWorks/sldworks/t_hinge_mates.htm`
- Mate Controller: `https://help.solidworks.com/2024/english/SolidWorks/sldworks/c_assembly_mate_controller.htm`

## Adding Components

Prefer reusing `add_component()` from `scripts/sw_assembly.py`. Under SolidWorks 2024 Chinese Edition + pywin32, `AddComponent4()` can silently return `None` without raising an exception; the current wrapper tries the 8-parameter `AddComponent5()` signature first and falls back to `AddComponent4()` on failure. If both return `None`, the wrapper automatically opens the part silently in the SolidWorks session, reactivates the assembly, and retries `AddComponent5()`.

```python
from sw_assembly import add_component

component = add_component(asm_model, r"E:\parts\base.SLDPRT", x=0, y=0, z=0)
```

Stable low-level call:

```python
component = asm_model.AddComponent5(
    CompPath, 0, "", False, ConfigName, X, Y, Z
)
```

When `AddComponent4` / `AddComponent5` fails, verify that the part file actually exists, the assembly is the active document, and the part has been saved to disk; if needed, open the part first and then switch back to the assembly. Live regression test:

```powershell
py -3.13 tests\solidworks_add_component_regression.py --output-dir C:\CADAutomationWorkbench\solidworks_add_component_regression
```

## Kinematic Assembly Workflow

1. Generate and save each part first, closing part documents that are no longer being edited to avoid opening too many documents in SolidWorks.
2. Create a new assembly and insert components such as the base, bearing housings, shafts, gears, and top cover.
3. Call `resolve_component(component)` on every component whose features or faces need to be read; lightweight or suppressed components cause `GetModelDoc2()` to return `None`.
4. Use `IComponent2.GetCorresponding()` to map part-level reference planes, cylindrical faces, or sketch entities into the assembly context, then select them with `Select2()`.
5. Fixed components can be locked using three coincident reference plane mates or distance mates; do not fully lock rotating components with three reference plane mates.
6. Use a Concentric mate for shafts/holes with `lock_rotation=False` to preserve the rotational degree of freedom around the axis.
7. Use a Gear mate for gear transmission: select gear axes, bore cylindrical faces, outer cylindrical faces, or shaft entities, and pass the ratio according to tooth counts.
8. A top cover hinge can be represented with a Concentric mate plus a Coincident/Distance planar mate to leave one rotational degree of freedom; if Motion Analysis is required, prefer creating a native Hinge Mate in the GUI or using the higher-level `MateFeatureData` API.
9. After creation, traverse the `MateGroup` sub-features to verify that real mates are written into the FeatureManager design tree; preview animations only prove that a script can drive positions, not that the mechanism can be dragged interactively in SolidWorks.
10. Finally, run `sw_review.py` to export multi-view previews and manually drag a free component in SolidWorks to verify motion.

## Engineering Reference Summary

- Official Mechanical Mates documentation emphasizes that a Gear Mate only enforces proportional relative rotation between two components around selected axes, and a Hinge Mate is equivalent to a Concentric mate plus a Coincident mate with optional angle limits.
- GoEngineer's Mate guide treats mates as geometric constraints between components; mechanical mates represent kinematic relationships such as gears, rack-and-pinion, screws, and universal joints, and are not equivalent to physical contact simulation: `https://www.goengineer.com/blog/introduction-to-solidworks-mates`
- CodeStack's lightweight component example shows that `GetModelDoc2()` returns `None` for lightweight or suppressed components, with a fallback of resolving the component or silently opening the referenced model: `https://www.codestack.net/solidworks-api/document/assembly/components/lightweight-get-model-doc/`
- CAD Booster's `GetCorresponding` guide emphasizes that part context and assembly context cannot be mixed; whenever an object reference is available, prefer `GetCorresponding()` + `Select2()` over coordinate-based clicking: `https://cadbooster.com/entities-and-getcorresponding-in-the-solidworks-api/`
- Lightweight components causing `GetModelDoc2()` to return `None` is a common pitfall; always resolve components before creating mates rather than mistaking `None` for "the part has no features."

## AddMate5 Parameters

`AddMate5` in SolidWorks 2015+ takes a 15-parameter signature; in Python COM, the by-ref error code must be wrapped in a `VARIANT`:

```python
errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
mate = asm_model.AddMate5(
    mate_type,          # swMateType_e
    align,              # swMateAlign_e，常用 0=Aligned
    flip,               # bool
    distance,           # 距离配合值，单位米
    distance_upper,     # 距离上限；无限制时等于 distance
    distance_lower,     # 距离下限；无限制时等于 distance
    gear_num,           # Gear Mate 分子
    gear_den,           # Gear Mate 分母
    angle,              # 角度，单位弧度
    angle_upper,        # 角度上限
    angle_lower,        # 角度下限
    for_positioning_only,
    lock_rotation,      # 同心配合是否锁定旋转
    width_mate_option,  # Width Mate 选项
    errors,
)
```

Prefer reusing `scripts/sw_assembly.py`:

```python
from sw_assembly import (
    add_concentric_mate_by_cylinders,
    add_gear_mate_by_cylinders,
    collect_mate_feature_summary,
)

add_concentric_mate_by_cylinders(
    asm,
    shaft_comp,
    bearing_comp,
    radius_a=(0.004, 0.006),
    radius_b=(0.004, 0.006),
    name="shaft_bearing_concentric",
    lock_rotation=False,
)

add_gear_mate_by_cylinders(
    asm,
    small_gear_comp,
    large_gear_comp,
    teeth_a=18,
    teeth_b=26,
    radius_a=(0.004, 0.008),
    radius_b=(0.004, 0.008),
    name="small_large_gear_ratio_18_26",
)

print(collect_mate_feature_summary(asm))
```

## Mate Type Enumeration

Common values verified against local SW 2024 `SolidWorks.Interop.swconst.dll`:

| Value | Name | Description |
|---:|---|---|
| 0 | `swMateCOINCIDENT` | Coincident |
| 1 | `swMateCONCENTRIC` | Concentric |
| 2 | `swMatePERPENDICULAR` | Perpendicular |
| 3 | `swMatePARALLEL` | Parallel |
| 4 | `swMateTANGENT` | Tangent |
| 5 | `swMateDISTANCE` | Distance |
| 6 | `swMateANGLE` | Angle |
| 10 | `swMateGEAR` | Gear |
| 11 | `swMateWIDTH` | Width |
| 16 | `swMateLOCK` | Lock |
| 22 | `swMateHINGE` | Hinge |

Common component suppression state values:

| Value | Name | Description |
|---:|---|---|
| 0 | `swComponentSuppressed` | Suppressed |
| 1 | `swComponentLightweight` | Lightweight |
| 2 | `swComponentFullyResolved` | Fully Resolved |
| 3 | `swComponentResolved` | Resolved |
| 4 | `swComponentFullyLightweight` | Fully Lightweight |

## Selection and Assembly Context

Reliable sequence:

```python
from sw_assembly import (
    get_component_feature,
    get_assembly_entity,
    find_component_by_name,
    resolve_component,
    select_entities_for_mate,
)

component_a = find_component_by_name(asm, "shaft")
component_b = find_component_by_name(asm, "bearing")
resolve_component(component_a)
resolve_component(component_b)

feature_a = get_component_feature(component_a, ["前视基准面", "Front Plane"])
feature_b = get_component_feature(component_b, ["前视基准面", "Front Plane"])
entity_a = get_assembly_entity(component_a, feature_a)
entity_b = get_assembly_entity(component_b, feature_b)

select_entities_for_mate(asm, entity_a, entity_b, mark=1)
```

Notes:

- Resolve components before selecting entities; `SetSuppression2()` can clear the active selection set.
- Select the first entity with `Select2(False, 1)` and append the second entity with `Select2(True, 1)`.
- Verify `SelectionManager.GetSelectedObjectCount2(-1) == 2` before creating the mate.
- Gear mates and standard mates typically use selection mark `1`; Width Mate uses `16`, and Cam-Follower uses `8`.

## Cylindrical Face Identification

Shafts, holes, and gear axes are typically identified via their largest cylindrical face:

```python
from sw_assembly import find_largest_cylinder_face

face = find_largest_cylinder_face(
    gear_component,
    min_radius=0.004,
    max_radius=0.008,
)
```

Underlying logic:

```python
bodies = part.GetBodies2(0, False)
for body in bodies:
    for face in body.GetFaces():
        surface = face.GetSurface()
        if surface.IsCylinder:
            params = surface.CylinderParams
            radius = params[6]  # 单位米
```

## Can the Assembly Be Manipulated Interactively in SolidWorks?

Yes, provided the assembly contains real mates and is not over-constrained:

- Open the `.SLDASM` file in SolidWorks.
- Use `Move Component` (`移动零部件` / `Move Component`) to drag shafts, gears, or covers.
- If the Gear Mate is properly configured, rotating one gear about its axis drives the mating gear proportionally in the opposite or same direction.
- If a component cannot be dragged, check whether the part is Fixed, whether Lock Rotation is checked on a Concentric mate, whether additional planar mates lock the rotating part, or whether mates have errors or are over-defined.

Script-generated GIFs or preview videos only demonstrate that components can be driven to multiple poses; true interactive motion depends on the SolidWorks Mate solver and remaining degrees of freedom.

## Interference and Motion Limits

A Gear Mate does not prevent solid gear bodies from penetrating each other; it only enforces a rotational ratio. When geometric clearance must be verified:

- Run `InterferenceDetection` or GUI Interference Detection to verify clearances.
- Use Limit Angle / Limit Distance mates to restrict travel.
- Use Mate Controller to save key positions and generate a Motion Study animation.

```python
from scripts.sw_measure import inspect_interference

result = inspect_interference(asm)
print(result["status"], result["interference_count"], result["items"])
# status=blocked 或 count=None 是证据未知，不能解释为零干涉。
```

The native object is `IAssemblyDoc.InterferenceDetectionManager`; `GetInterferences()` performs the calculation, and `Done()` must be called only after reading the count, interference volumes, and interfering components. Zero interference alone does not prove an assembly is correct. For multi-part structural Golden acceptance criteria covering mates, constraint status, degrees of freedom, and delivery verification, see [P0-2 Parallel Gripper Acceptance](../docs/architecture/real-golden-parallel-gripper-acceptance.md).

## Large Assembly Recommendations

- When building more than 20 parts, generate parts in batches, save and close each document, and then assemble them together.
- Verify that all file paths exist before inserting components, and log a list of any failed components.
- Disable unnecessary graphics redraws during automation scripts; re-enable graphics, rebuild, and export previews at the end.
- If too many documents are open or COM throws internal errors, call `CloseAllDocuments(False)` first; if instability persists, restart the main SolidWorks process.
