# Motion Study and Rotary Motor Automation

This document captures the Motion Study automation workflow verified on SolidWorks 2024 SP3.1 + Python 3.13 + `pywin32`. The goal is to create real motion studies and motor features rather than faking mechanical degrees of freedom with scripted animations.

## Applicable Scenarios

- User asks to "create a motion study," "set up Motion Study," "add a motor," or "rotate at a constant 60 RPM."
- The assembly already has real mates, with rotating components retaining rotational DOF via Concentric mates.
- A calculable, playable timeline animation is needed inside SolidWorks Motion Study.

Not applicable when:

- You only want to illustrate a pose angle change—use `sw_assembly.apply_component_transform_x()` to render frames.
- Complex contact, friction, collision, or force/torque dynamics are required—verify Motion / Simulation add-ins and licenses first and run dedicated validation.

## Recommended Workflow

1. Generate and save all parts first.
2. Create a new assembly and insert components.
3. Resolve components and use `GetCorresponding()` to select assembly-context entities.
4. Add a Concentric mate to the rotating component with `lock_rotation=False`.
5. Constrain axial float with a single planar Coincident or Distance mate; do not lock the rotating part with three reference plane mates.
6. Fix stationary parts; leave rotating parts floating.
7. Call `sw_motion.create_motion_study()` to create the study.
8. Call `add_constant_speed_rotary_motor_by_cylinders()` to add a constant-speed rotary motor.
9. Call `calculate_and_play()` to calculate and play the study.
10. Call `validate_motion_studies()`; proceed to delivery only when `validation.status == "pass"`.

## Minimal Example

```python
import sys
sys.path.insert(0, r"C:\Users\you\.codex\skills\solidworks-automation\scripts")

from sw_connect import mm
from sw_motion import (
    create_motion_study,
    add_constant_speed_rotary_motor_by_cylinders,
    calculate_and_play,
    validate_motion_studies,
)

# 前提：asm 是装配体文档；stand_comp 是静止轴/支架；impeller_comp 是叶轮。
# 前提：叶轮已用同心 Mate 装到轴上，且该同心 Mate 未锁定旋转。
study = create_motion_study(
    asm,
    name="叶轮_60RPM_循环转动",
    duration=4.0,
)

motor = add_constant_speed_rotary_motor_by_cylinders(
    study,
    shaft_component=stand_comp,
    rotor_component=impeller_comp,
    shaft_radius=(mm(4.5), mm(5.5)),
    rotor_radius=(mm(10.5), mm(11.5)),
    rpm=60.0,
    name="叶轮旋转马达_60RPM",
)

ok = calculate_and_play(study)
audit = validate_motion_studies(
    asm,
    study_name="叶轮_60RPM_循环转动",
    minimum_duration_seconds=4.0,
    minimum_motor_count=1,
    require_results=True,
)
print(ok, audit["validation"])
```

## Result Acceptance Gate

`validate_motion_studies()` verifies all of the following simultaneously:

- The target study exists and is readable.
- `swmotionstudy.tlb` is loaded.
- Study duration meets or exceeds the requirement.
- Motor count meets or exceeds the requirement.
- Optional `StudyType` matches the task.
- `GetResults()` returns a valid results object.
- `results_out_of_date` is explicitly `False`.

Seeing a timeline, motor icon, animation playback, or `Calculate=True` alone cannot substitute for this evidence set. If any check fails, the Reviewer Gate must block delivery and require recalculation or fixing assembly degrees of freedom.

## Type Library and Late-Bound COM Pitfalls

Motion Study's `IMotionStudyManager` resides in `swmotionstudy.tlb`, not in the main `SolidWorks.Interop.sldworks.dll` type library. Without generated `pywin32` wrappers, dynamic dispatch objects exhibit quirks:

- `model.Extension.GetMotionStudyManager` behaves as a property rather than a method.
- `motion_mgr.CreateMotionStudy` behaves as a property—reading it creates the study, whereas calling `CreateMotionStudy()` raises "Member not found."
- `study.Activate`, `study.Calculate`, and `study.Play` may behave as boolean properties rather than methods.
- `study.SetDuration()`, `study.CreateDefinition()`, and `study.CreateFeature()` typically remain methods.

Reliable pattern: reuse `sw_motion.motion_member()` and `sw_motion.ensure_motion_type_library()`.

```python
from sw_motion import ensure_motion_type_library, motion_member

ensure_motion_type_library()
motion_mgr = motion_member(asm.Extension, "GetMotionStudyManager")
study = motion_member(motion_mgr, "CreateMotionStudy")
motion_member(study, "SetDuration", 4.0)
calculated = motion_member(study, "Calculate")
```

## Key Rotary Motor API

Create a rotary motor via `MotionStudy.CreateDefinition(swFmAEMRotationalMotor)`:

```python
SW_FM_AEM_ROTATIONAL_MOTOR = 78
motor_data = study.CreateDefinition(SW_FM_AEM_ROTATIONAL_MOTOR)
motor_data.DirectionReference = shaft_axis_face
motor_data.ConstantSpeedMotor(60.0)  # 单位：RPM
motor_data.RelativeComponent = stand_comp
motor_data.Location = rotor_face
motor_data.LoadReferences = (rotor_face,)
motor_feature = study.CreateFeature(motor_data)
```

Live-tested notes:

- Choosing the stationary shaft's assembly-context cylindrical face for `DirectionReference` is most reliable.
- `LoadReferences` accepts a tuple/list; some environments require `VARIANT(VT_ARRAY | VT_VARIANT, [...])` or `VT_DISPATCH`.
- `ConstantSpeedMotor(60.0)` takes RPM directly; do not convert to rad/s.
- If `CreateFeature()` returns `None`, verify that both direction and load references are assembly-context entities.

## Relationship to Mate Degrees of Freedom

A Motion Motor can only drive components that still have a rotational degree of freedom. Common failure causes:

- The rotor/impeller component is fixed via `FixComponent()`.
- The Concentric mate was created with `lock_rotation=True`.
- Additional coincident reference plane mates locked rotational DOF.
- Part-context faces were selected instead of assembly-context faces mapped via `component.GetCorresponding()`.

Recommended constraints:

- Stationary parts: fix the base, center post, and protective cover.
- Rotating part: apply only a Concentric mate + one axial locating mate; keep the component floating.
- Concentric mate: `lock_rotation=False`.

## Session Cleanup and Same-Title Documents

During repeated automated part generation runs, leftover documents with identical titles in the SolidWorks session can cause:

```text
OpenDoc6 errors=65536
swFileWithSameTitleAlreadyOpen
AddComponent4 返回 None
```

Reliable approach:

1. Before running a batch script, check whether open documents can be closed; unattended pipelines can call `sw.CloseAllDocuments(True)`.
2. Close each part via `sw.CloseDoc(title)` right after saving, then insert by path during assembly.
3. Do not treat `OpenDoc6` returning `65536` as file corruption—it usually indicates a document with the same title is already open.

## Verification Record

Environment:

- SolidWorks Premium 2024 SP3.1
- Python 3.13
- `pywin32` dynamic COM

Verified benchmark case:

- 4-part desktop mini cooling fan: base, center post, bladed impeller, circular front guard.
- Assembly mates: base/post concentric + coincident; impeller/shaft concentric (rotation unlocked) + axial coincident; front guard concentric + angular alignment.
- Fix states: base/post/front guard fixed; impeller floating.
- Motion Study: created `叶轮_60RPM_循环转动`, added `叶轮旋转马达_60RPM`, `Calculate=True`.

`examples/08_mini_fan_motion_assembly.py` in the repository is a repeatable benchmark example. It validates automated modeling, assembly, real mates, Motion Study, and review export; fillets/chamfers are not used as success criteria, and blades use reliable rectangular geometry rather than complex curved surfaces.
