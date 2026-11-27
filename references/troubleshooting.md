# Troubleshooting Guide

## Connection Issues

### Cannot Connect to SolidWorks

```
错误: pywintypes.com_error: (-2147221005, '无效的类字符串', None, None)
```

**Cause**: SolidWorks is not installed or COM is not registered.
**Resolution**: Confirm SolidWorks is installed and try connecting with an explicit version ProgID:
```python
sw = win32com.client.Dispatch("SldWorks.Application.32")  # SW 2024
```

### GetActiveObject Failure

```
错误: pywintypes.com_error: (-2147221021, '操作不可用', None, None)
```

**Cause**: SolidWorks may not be running, or a responsive instance already exists that the current session cannot retrieve from the Running Object Table (ROT). Check running processes, version, and desktop session state first rather than repeatedly spawning new instances.

When a single target instance with a known version is running and versioned `Dispatch` on the local machine is confirmed to return that same instance, you may explicitly set `SW_ATTACH_EXISTING_DISPATCH=1` in the execution environment and call `connect_solidworks(version=2024)` (substitute the actual version year). MCP clients must pass this variable to the server process and reconnect; if unset or not equal to `1`, the default behavior blocking duplicate construction remains active.

The fallback still waits on the ROT first, then verifies the returned PID, actual version, and before/after process lists; on any mismatch, it halts without modeling and does not assume ownership to terminate an existing instance. **This does not guarantee the constructor will never launch a new instance**: different versions or installations may return another process. On identity mismatch, never force-close that process—inspect the running instance list and any unsaved documents before deciding how to proceed, and do not auto-retry. This option does not repair Windows ROT mechanics; ambiguous targets, unknown versions, or changing process lists still reject attachment.

`visible` controls only instances newly launched in the current run; attaching never alters an existing window state. For the SW2024 contributor record, see [Original ROT Fallback Verification](https://github.com/wzyn20051216/solidworks-automation-skill/blob/main/docs/rot-sw2024-regression.md); for independent SW2026 direct API, MCP stdio, visible/hidden window, and unsaved document verification, see [SW2026 Acceptance](https://github.com/wzyn20051216/solidworks-automation-skill/blob/main/docs/rot-sw2026-regression.md). Acceptance docs and manual tests live in the source repository; runtime packages exclude `docs/` and `tests/`.

### Through-Hole Cut Returns None (Issue #82)

When circular hole `FeatureCut4` returns `None`, the direct API preserves the `SolidWorks 未创建特征` error prefix and attaches read-only diagnostics; MCP returns `error_code=SW_HOLE_NOT_CREATED`, `diagnostics`, and `retryable=false`. Diagnostics capture post-failure state: selection count, whether a sketch is still being edited, solid body count, sketch entity/contour counts, requested plane, and depth; unreadable fields are `null` and must not be interpreted as absent.

Keep the failed sketch intact and inspect selections, sketch plane, cut direction, and intersection with the solid body; do not auto-retry or automatically flip cut direction. Regressions pass on SW2026 SP1.1 for new parts, reopened parts, standalone MCP, and pre-existing holed plates; the SW2024 build 32.5.0 scenario originally reported in #82 has not yet been verified and must not be claimed fixed. See [Through-Hole Regression and Diagnostics](https://github.com/wzyn20051216/solidworks-automation-skill/blob/main/docs/hole-reopen-regression.md) for raw reports, source regression scripts, and collection methods.

### Python 32-bit / 64-bit Mismatch

**Cause**: Python architecture must match SolidWorks (typically 64-bit).
**Resolution**: Install 64-bit Python.

## Type and COM Marshaling Errors

### Pseudo-Callable COM Properties Raise "Member Not Found"

Scenario: When traversing the FeatureManager tree or reading model summaries, members such as `FirstFeature`, `GetNextFeature`, or `GetTitle` report `callable=True` in `pywin32`, yet calling them raises:

```text
(-2147352573, '找不到成员。', None, None)
```

Cause: Under dynamic dispatch, certain SolidWorks COM members can appear as either properties or methods; `callable(member)` is not a reliable test.

Reliable approach: Prefer `sw_connect.get_com_member()` or `sw_assembly.safe_get_com_member()`.

```python
from sw_connect import get_com_member

feature = get_com_member(model, "FirstFeature")
while feature:
    print(get_com_member(feature, "Name"), get_com_member(feature, "GetTypeName2"))
    feature = get_com_member(feature, "GetNextFeature")
```

### Motion Study Members Raise "Member Not Found"

Scenario: `model.Extension.GetMotionStudyManager()` or `motion_mgr.CreateMotionStudy()` raises:

```text
(-2147352573, '找不到成员。', None, None)
```

Common causes:

1. Strongly typed Motion Study interfaces live in `swmotionstudy.tlb`, not in the main `sldworks` type library.
2. Under `pywin32` dynamic dispatch, `GetMotionStudyManager`, `CreateMotionStudy`, `Activate`, `Calculate`, and `Play` may behave as properties rather than methods.

Reliable approach: Prefer `sw_motion.py`.

```python
from sw_motion import create_motion_study, motion_member

study = create_motion_study(asm, name="Motion_60RPM", duration=4.0)
calculated = motion_member(study, "Calculate")
```

If low-level calls are unavoidable, load the type library first:

```python
from sw_motion import ensure_motion_type_library

ensure_motion_type_library(raise_on_error=True)
motion_mgr = asm.Extension.GetMotionStudyManager
study = motion_mgr.CreateMotionStudy
```

### SelectByID2 Type Mismatch

```
错误: TypeError: Objects of type 'NoneType' can not be converted to a COM VARIANT
```

**Resolution**: Pass an explicit `VARIANT` for the `Callout` parameter:
```python
from win32com.client import VARIANT
import pythoncom
callout = VARIANT(pythoncom.VT_DISPATCH, None)
model.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, callout, 0)
```

### By-Ref Parameter Errors

**Resolution**: Wrap output parameters in `VARIANT`:
```python
errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
warnings = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
```

### Pack and Go Raises "Parameter Not Optional"

Scenario: `model.Extension.GetPackAndGo()` or strongly typed `IModelDocExtension.GetPackAndGo()` raises a missing required parameter error, even though official API docs and Interop reflection confirm it takes zero arguments and returns `IPackAndGo`.

Cause: Local SW2024/2026 + `pywin32` runtime objects mis-marshal `[out, retval] IPackAndGo**`. Testing shows both zero-argument dynamic calls and explicit `VT_BYREF | VT_DISPATCH` can fail to return the pointer.

Reliable approach: Prefer `sw_delivery.pack_and_go()`. It tries the official `pywin32` zero-argument call first; if `pywin32` raises a signature error, it falls back to `comtypes` early binding for native `IModelDocExtension.GetPackAndGo()` / `SavePackAndGo()`.

```python
from sw_delivery import pack_and_go

report = pack_and_go(assembly, r"E:\\delivery\\pack_and_go", flatten=True)
assert report["success"], report
```

### Pack and Go Outputs Only the Top-Level Assembly

Scenario: `IModelDoc2.GetDependencies2()` returns the referenced `.SLDPRT` files, yet `IPackAndGo.GetDocumentNames()` lists only the top-level `.SLDASM`, and the saved package contains only the assembly file.

Remediation: Never treat pre-save enumeration as the final deliverable, and never use `AddExternalDocuments` to patch missing native assembly parts. `sw_delivery.pack_and_go()` runs native `SavePackAndGo()` first and then audits dependencies against actual files written in the current run; a basic two-part assembly on SW2026 SP01.1 has output the complete 1 assembly + 2 parts across three consecutive runs. If actual disk output still misses dependencies, the default policy generates a clearly marked `pilot` staged package, while strict policy returns `status=blocked` and `SW_PACK_AND_GO_DEPENDENCY_ENUMERATION_INCOMPLETE`; both preserve missing-dependency evidence and require manual review.

### STL Exported the Active Assembly Instead of the Target Part

Scenario: `IModelDocExtension.SaveAs()` returns success, but the expected target part STL is missing while multiple files like `<PartName> - <AssemblyComponentName>.STL` appear in the directory.

Cause: SW2024 STL export may read from `ActiveDoc`; holding a reference to the target part's `IModelDoc2` alone does not guarantee the right document is exported.

Remediation: Use `sw_export.batch_export_formats()`. It calls `ActivateDoc3()` before exporting each format and strictly verifies the active document path, stopping on mismatch rather than trusting the API's nominal success flag.

## Operation Failures

### `run_review` Captures Only One Part or Subassembly

Scenario: Component counts, visibility, and color readbacks in the assembly all look normal, yet previews exported by `run_review()` show only a single wheel hub or small part while everything else is missing or shadowed.

Common causes:

1. SolidWorks `SaveBMP()` captures the active graphics window, and the target `model` is not the active document.
2. After batch-opening parts/subassemblies, the active document remained on the last opened component.
3. Rule-based review checks only that previews are non-blank and cannot detect capturing the wrong document.

Reliable approach: Use the updated `sw_review.save_preview()` / `run_review()`, which activates the target document by `GetTitle()` prior to capture. In custom capture code, always call `ActivateDoc3()`, `ClearSelection2(True)`, `ViewZoomtofit2()`, and then `SaveBMP()`.

```python
errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
sw.ActivateDoc3(model.GetTitle(), False, 0, errors)
model.ClearSelection2(True)
model.ViewZoomtofit2()
model.SaveBMP(r"E:\review\assembly.bmp", 1600, 1000)
```

Always visually inspect all four views afterward; `evaluation.status=pass` cannot replace geometric judgment.

### Split-STEP Sub-Parts All Stack at the Origin After Assembly

Scenario: A multi-color STEP/assembly is split into multiple STEP files, imported individually as native SolidWorks parts, and assembled into a new top-level assembly; component counts match, yet previews show only a single wheel or a pile of overlapping shadows.

Cause: Some CAD exporters preserve original world coordinates when exporting individual bodies, while SolidWorks `AddComponent5(path, ..., x, y, z)` may position components by their bounding-box center—passing `(0,0,0)` stacks every sub-part centered at the origin.

Reliable approach:

1. Record each body's pre-export global bounding-box center in the split manifest.
2. Pass that center coordinate (in meters) when inserting each component instead of `(0,0,0)`.
3. After insertion, read back `Transform2.ArrayData[9:12]` and `GetBox()` to confirm the overall assembly envelope approximates the original model.
4. Recursively inspect components inside `.SLDASM` subassemblies rather than checking top-level component counts alone.

```python
center_m = [value / 1000.0 for value in bbox_center_mm]
component = add_component(asm, native_path, x=center_m[0], y=center_m[1], z=center_m[2])
```

### `GetModelDoc2` Returns `None`

Scenario: A component clearly exists in the assembly, yet `component.GetModelDoc2()` returns `None`, preventing access to its reference planes, faces, or features.

Common causes:

1. The component is suppressed or lightweight.
2. The referenced file is not loaded in memory.
3. The assembly has not resolved the component immediately after insertion.

Reliable approach: Resolve the component before reading its model; prefer `sw_assembly.get_component_model()`.

```python
from sw_assembly import get_component_model, resolve_component

resolve_component(component)  # 默认 swComponentFullyResolved=2，失败时回退 swComponentResolved=3
part = get_component_model(component)
```

### `AddComponent4` Returns `None`

Scenario: Under SolidWorks 2024 Chinese Edition + `pywin32`, `asm.AddComponent4(path, "", x, y, z)` raises no exception but persistently returns `None`, preventing parts from being inserted into the assembly.

Reliable approach: Prefer `sw_assembly.add_component()`. The wrapper checks the file path first, calls `AddComponent5(path, 0, "", False, config, x, y, z)`, falls back to `AddComponent4()` on failure, and if still `None`, silently opens the part, reactivates the assembly, and retries `AddComponent5()`.

```python
from sw_assembly import add_component, get_components

component = add_component(asm, r"E:\parts\probe_block.SLDPRT", x=0, y=0, z=0)
if component is None:
    raise RuntimeError("添加组件失败")
print(get_components(asm))
```

Live SolidWorks regression test:

```powershell
py -3.13 tests\solidworks_add_component_regression.py --output-dir C:\CADAutomationWorkbench\solidworks_add_component_regression
```

Pass criteria: `component_count >= 1`, non-empty `component_name`, `.SLDASM` saved successfully, and `review_evaluation.status == "pass"` (or at minimum `review_checks.expected_outputs_exist=true`).

### No Real Mates in Feature Tree After Mate Creation

Scenario: The script reports "success," but SolidWorks shows no Gear Mate / Concentric Mate and dragging components produces no linked motion.

Checklist:

1. Did `AddMate5()` return `None`?
2. Is the by-ref `ErrorStatus` a success code? (`swAddMateError_NoError=1`; some versions also return `0` on success.)
3. Did the selection set contain exactly 2 objects right before mate creation?
4. Are the selected objects assembly-context entities rather than part-document entities?
5. Was the mate actually written as a sub-feature under `MateGroup`?

Reliable approach:

```python
from sw_assembly import add_mate5_checked, collect_mate_feature_summary

mate = add_mate5_checked(asm, 1, lock_rotation=False, name="shaft_concentric")
print(collect_mate_feature_summary(asm))
```

### `AddMate5` Returns a Mate With `error_status=1`

Scenario: `AddMate5()` returns a non-null Mate and the mate appears in the SolidWorks FeatureManager tree, yet the script reports failure:

```text
AddMate5 失败: type=1, error_status=1
```

Cause: In `swAddMateError_e`, `1 = swAddMateError_NoError`—it is not an error. Do not treat only `0` as success.

Verification command:

```powershell
Add-Type -Path 'E:\Solidworks\SOLIDWORKS\SolidWorks.Interop.swconst.dll'
[int][SolidWorks.Interop.swconst.swAddMateError_e]::swAddMateError_NoError
```

Reliable approach: Use the updated `sw_assembly.add_mate5_checked()`, which accepts both `0` and `1` as success codes while still checking that the returned mate is not `None`.

### Selection Set Gets Cleared

Scenario: Selecting the first face succeeds, then resolving a component or switching documents occurs; selecting the second face succeeds, but `AddMate5()` fails.

Cause: `SetSuppression2()`, activating a document, and certain rebuild operations clear or mutate the active selection set.

Reliable sequence:

1. Resolve all participating components first.
2. Map all entities to assembly context with `GetCorresponding()`.
3. Clear the selection set, then select both entities back-to-back.
4. Immediately invoke `AddMate5()`.

```python
from sw_assembly import select_entities_for_mate

select_entities_for_mate(asm, entity_a, entity_b, mark=1)
```

### `GetCorresponding` Returns `None`

Scenario: A reference plane or face exists inside the part, yet `component.GetCorresponding(face_or_feature)` returns `None`.

Common causes:

1. The passed object does not belong to the document referenced by that component.
2. The component is not resolved.
3. The wrong component instance was used; when a part is inserted multiple times, `GetCorresponding()` must be called on the target component instance.
4. The object is temporary geometry or has become stale.

Reliable approach: Look up features/faces inside the model returned by `get_component_model(component)`, then map them through that exact same `component`.

### Component Cannot Rotate After Concentric Mate

The cause is usually locked rotational degrees of freedom rather than a missing hinge:

1. `lock_rotation=True` or Lock Rotation is checked in the GUI.
2. The rotating part was also locked down with three coincident reference plane mates.
3. The component itself is Fixed.
4. Excessive axial locating mates over-defined the component.

For kinematic assemblies, default Concentric mates to:

```python
add_concentric_mate_by_cylinders(..., lock_rotation=False)
```

For a cover hinge, use a Concentric mate to preserve rotation plus a single planar Coincident/Distance mate to prevent axial float.

### Feature Creation Fails (Returns `None`)

Common causes:
1. **Wrong entity selected** — verify entity name and type passed to `SelectByID2`.
2. **Under-defined sketch** — add sufficient geometric relations and dimensions.
3. **Open sketch contour** — standard extrusions require closed profiles.
4. **Wrong units** — the API expects meters, not millimeters.

### `SelectByID2("SKETCH")` Persistently Returns `False`

Scenario: In SolidWorks 2024 Chinese Edition, both `SelectByID2("草图1", "SKETCH", ...)` and `SelectByID2("Sketch1", "SKETCH", ...)` return `False`, followed by `FeatureExtrusion3()` returning `None`.

Root cause: Sketch selection by name is unstable in certain versions/locales; older `sw_part._ensure_sketch_selected()` also treated `selection_count > 0` as success, so early parts succeeded accidentally via leftover selections and failed completely once the selection set was cleared.

Reliable approach:

1. Prefer `with sketch(model, "...") as sketch_name:`, letting `sw_part.py` cache the real sketch object reference at creation time.
2. Never rely on leftover selections before feature creation; switching documents, rebuilding, resolving components, and failed API calls can all clear the selection set.
3. Prefer object-level `Select2()` on the sketch `Feature` / `Sketch`; fall back to `SelectByID2("SKETCH")` only as a last resort.
4. When using manual low-level calls, pass the return value of `end_sketch(model)` directly to `extrude_boss()` / `extrude_cut()`.

```python
from sw_part import end_sketch, extrude_boss, sketch_circle, start_sketch

start_sketch(model, "Front Plane")
sketch_circle(model, 0, 0, 0.025)
sketch_ref = end_sketch(model)
feature = extrude_boss(model, sketch_ref, 0.05)
if feature is None:
    raise RuntimeError("拉伸失败：检查草图闭合、方向和对象选择")
```

Live SolidWorks regression test:

```powershell
py -3.13 tests\solidworks_sketch_selection_regression.py --output-dir C:\CADAutomationWorkbench\solidworks_skill_regression
```

Pass criteria: After two `ClearSelection2(True)` calls both report `selection_count=0`, the script still creates `凸台-拉伸1` (Boss-Extrude1) and `切除-拉伸1` (Cut-Extrude1), saves `.SLDPRT`, exports `.step`, and achieves `review_evaluation.status == "pass"`.

### `FeatureCut4` Long Parameter List Instability

Scenario: Hand-written `FeatureCut4(...)` calls return `None`, even though the same sketch cuts cleanly in the GUI or via wrapper helpers.

Cause: `FeatureCut4` has a large argument list where any mismatch in end condition, flip direction, `FlipSide`, `NormalCut`, or selection state fails silently. Never assemble its parameters from memory.

Reliable approach:

1. Prefer `sw_part.extrude_cut()`.
2. If low-level calls are unavoidable, test directions and end conditions on a minimal cylinder/block first.
3. Check the returned feature object after every cut; never save deliverables if it failed.

```python
from sw_part import extrude_cut

feature = extrude_cut(model, sketch_name, 0, direction=True, flip=False)
if feature is None:
    feature = extrude_cut(model, sketch_name, 0, direction=True, flip=True)
if feature is None:
    raise RuntimeError("切除失败，需检查草图、方向或终止条件")
```

### Cutting a Slot From the Center Reference Plane Splits the Shaft Open

Scenario: To create an oblong slot or keyway on a shaft, the script sketches the slot on `Front Plane` and runs a blind cut, resulting in a large planar cut splitting the cylinder open along the axis.

Cause: `Front Plane` typically passes through the shaft centerline rather than the outer cylindrical surface, so cutting from it produces a cross-sectional cut instead of a surface pocket.

Reliable approach: Create a tangent offset reference plane first, then sketch and blind-cut the slot depth from that plane; see "Oblong Slots on Cylindrical Surfaces" in `references/part-modeling.md`.

### Slot Feature Succeeds in Feature Tree but Is Invisible in Previews

Scenario: `Cut_*_Slot` appears in the FeatureManager tree and `run_review()` passes, yet no slot is visible in isometric or front views.

Checklist:

1. Was the slot cut on the back side? Try toggling `flip` or exporting the opposite view.
2. Was it cut from the center plane and hidden by current shading? Check top/right views.
3. Did the cut only remove hidden internal volume? Inspect with a section view or adjust the tangent reference plane.
4. Is a selected reference plane obscuring the slot contour in the preview?

Remediation: Never rely solely on `feature is not None`. Export `isometric/front/top/right` views and visually verify that key features actually appear.

### Reference Plane Selection Failure

**Cause**: English and Chinese UI editions use different default plane names.
**Resolution**:
```python
# 尝试英文名称
success = model.Extension.SelectByID2("Front Plane", "PLANE", 0, 0, 0, False, 0, None, 0)
if not success:
    # 尝试中文名称
    model.Extension.SelectByID2("前视基准面", "PLANE", 0, 0, 0, False, 0, None, 0)
```

### Save / Export Failure

Inspect error and warning codes:
```python
errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
warnings = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
success = model.Extension.SaveAs(path, 0, 1, None, errors, warnings)
print(f"错误码: {errors.value}, 警告码: {warnings.value}")
# 查看 references/export.md 中的错误码对照表
```

### STEP/IGES Crashes or Pops Up Template Dialog With `OpenDoc6`

Scenario: Opening `.step/.stp/.igs/.iges` via `OpenDoc6()` crashes SolidWorks or drops RPC; or `LoadFile4(path, "", importData, errors)` blocks on the "New SOLIDWORKS Document" (`"新建 SOLIDWORKS 文件"`) template dialog.

Cause: Foreign CAD files (other than DXF/DWG and Pro/E) should be imported as new SolidWorks documents via `LoadFile4` with `ArgString` set to `"r"`. An empty string can trigger the template picker UI in SW2024, breaking unattended automation.

Reliable approach: Prefer `sw_connect.open_document()` / `SolidWorksSession.open()`, which automatically calls `LoadFile4(file_path, "r", sw.GetImportFileData(file_path), errors)` for STEP/STP/IGES/IGS. Before importing, it also invokes `ensure_default_templates()` to configure default part/assembly/drawing templates and enables `swAlwaysUseDefaultTemplates=111` to suppress the "New SOLIDWORKS Document" (`"新建 SOLIDWORKS 文件"`) prompt.

```python
from sw_session import SolidWorksSession

session = SolidWorksSession(version=2024, visible=True)
model = session.open(r"E:\parts\body.step", silent=True, raise_on_error=True)
session.save(model, r"E:\parts\body.SLDPRT")
```

Live SolidWorks regression test:

```powershell
py -3.13 tests\solidworks_loadfile4_import_regression.py --output-dir C:\CADAutomationWorkbench\solidworks_loadfile4_import_regression
```

Pass criteria: `status=pass`, `body_count >= 1`, imported `.SLDPRT` saved successfully, and four-view review report generated.

Note: String user-preference enum values for default template paths are `swDefaultTemplatePart=8`, `swDefaultTemplateAssembly=9`, and `swDefaultTemplateDrawing=10`. Do not substitute file-location enums or legacy values, or `NewDocument()` / `LoadFile4()` may still display the template dialog.

If a large monolithic STEP repeatedly triggers `pywintypes.com_error: (-2147023170, 'The remote procedure call failed.')` (`'远程过程调用失败。'`), do not keep blindly retrying against the same SolidWorks process; save logs, restart SolidWorks, and switch to smaller split sub-parts, Parasolid intermediate format, or manual template dialog confirmation. `ensure_default_templates()` reduces dialog frequency but cannot guarantee silent import under every local SW2024 template configuration.

### OBJ/STL Fails in `OpenDoc6` or Hits Type Mismatch in `LoadFile4`

Scenario: Opening a public mesh reference model, car styling mesh, or test cube `.obj/.stl` via `OpenDoc6(path, swDocPART, ...)` fails with error `2097152` (`swFileRequiresRepairError`), while `LoadFile4(path, "r", None, errors)` raises `com_error(-2147352571, 'Type mismatch.')` (`'类型不匹配。'`).

Cause: In some SolidWorks 2024 COM environments, OBJ/STL cannot be opened through the normal part path, and `LoadFile4()` rejects Python `None` as its 3rd argument. This does not necessarily indicate a corrupt mesh—even a 684-byte test STL cube reproduces the issue.

Reliable approach: Prefer `scripts/sw_import_mesh_reference.py`, or use this minimal import sequence:

```python
from sw_connect import connect_solidworks, create_empty_dispatch_variant, save_document
from win32com.client import VARIANT
import pythoncom

sw, _ = connect_solidworks(visible=True)
sw.SetUserPreferenceIntegerValue(208, 0)   # swImportStlVrmlModelType_Graphics
sw.SetUserPreferenceIntegerValue(210, 2)   # swMETER
sw.SetUserPreferenceToggle(303, True)      # swImportStlVrmlTextureInformation
sw.SetUserPreferenceToggle(679, True)      # swVrmlStlImportAsPSMesh

errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
model = sw.LoadFile4(
    r"E:\work\reference_scaled_m.obj",
    "r",
    create_empty_dispatch_variant(),
    errors,
)
assert model is not None, errors.value
save_document(model, r"E:\work\reference.SLDPRT")
```

Note: Neutral CAD files (STEP/STP/IGES/IGS) and mesh reference files (OBJ/STL) require different import-data arguments. Keep using `sw.GetImportFileData(path)` for neutral CAD files and an empty Dispatch variant for OBJ/STL meshes—do not mix the two paths.

### `SaveAs` Error Code 1 or Overwrite Failure

Scenario: `session.save(model, path)` or `model.Extension.SaveAs(...)` fails with error code `1` even though the target file and path are valid.

Common cause: A document with the same filename is already open in the SolidWorks session, or the target file is locked by the running SolidWorks process, blocking overwrite.

Reliable approach:

```python
session = SolidWorksSession()
session.sw.CloseDoc("Drawing_Stepped_Shaft.SLDPRT")
model = session.new_part()
```

Note: Close only the specific output document that the script intends to overwrite; never blindly call `CloseAllDocuments()` unless the user confirms clearing the entire session.

### Cannot Delete Temporary `.SLDPRT` File

Scenario: PowerShell `Remove-Item` reports:

```text
The process cannot access the file ... because it is being used by another process.
```

Cause: The scratch/debug part is still open inside SolidWorks.

Resolution sequence:

1. Close the document with `sw.CloseDoc("<filename>.SLDPRT")`.
2. Delete the temporary file with `Remove-Item -LiteralPath <path> -Force`.
3. Verify the path matches only expected temporary files (e.g., `debug_*.SLDPRT`) before deleting.

### Reference Planes or Sketches Clutter Preview Images

Scenario: BMP previews exported by `run_review()` display large orange reference planes, sketches, or selection highlights that obscure the solid geometry.

Reliable approach:

```python
for plane_name in created_plane_names:
    model.ClearSelection2(True)
    selected = model.Extension.SelectByID2(
        plane_name, "PLANE", 0, 0, 0, False, 0,
        create_empty_dispatch_variant(), 0,
    )
    if selected:
        model.BlankRefGeom()

model.BlankSketch()
model.ClearSelection2(True)
model.ForceRebuild3(False)
```

`BlankRefGeom()` generally requires selecting the reference geometry first; calling it alone may not hide newly created reference planes.

### Multi-Color Assembly Turns Almost Entirely Green

Scenario: The script assigns red, blue, silver, black, and other colors, yet the assembly or BMP preview renders almost completely green.

Two distinct causes must be checked separately:

1. Passing a plain Python `list` directly to `MaterialPropertyValues`, causing misaligned COM array marshaling.
2. Leaving components, faces, or edges selected before capture so SolidWorks' green selection highlight masks true appearances.

Reliable approach:

```python
from sw_appearance import set_component_appearance, verify_appearance

assert set_component_appearance(component, "signal_red")
assert verify_appearance(component, "signal_red")["ok"]

model.ClearSelection2(True)
model.GraphicsRedraw2()
```

Do not simply swap `list` for `tuple` and retry; always use `material_variant()` to construct `VT_ARRAY | VT_R8`. Do not check `bool(SetMaterialPropertyValues2(...))` since the method returns `void`. Verification command:

```powershell
python tests\solidworks_appearance_regression.py
```

### `MathUtility.CreateTransform` Instability

Scenario: Calling `sw.GetMathUtility().CreateTransform(data)` or `math_utility.CreateTransform()` raises a COM error, returns `None`, or fails to solve after moving a component.

Reliable approach: Read the component's existing `Transform2`, update `ArrayData`, and call `SetTransformAndSolve2()`, falling back to `component.Transform2 = transform` on failure.

```python
from sw_assembly import apply_component_transform_x
from sw_connect import deg

ok = apply_component_transform_x(component, 0.1, 0.0, 0.0, deg(30))
```

Note: Directly modifying transforms is suitable for rendering demo frames or initial placement; if the component must be interactively draggable in SolidWorks, rely on real mates that leave the required degrees of freedom open.

### SolidWorks Internal Errors or Degrading COM Performance

Scenario: After batch-generating many parts or assemblies, `AddComponent4`, save, export, or feature operations fail intermittently.

Common causes: Too many open documents, accumulated graphics/FeatureManager redraw overhead, or long-running session degradation.

Resolution sequence:

1. Save critical outputs.
2. Call `sw.CloseAllDocuments(False)` to clean up the session.
3. Reopen required parts in batches and assemble.
4. If instability persists, ask the user before restarting `SLDWORKS.exe`.
5. Log failed components and failed API calls in the script—never merely print "Done."

### `FeatureFillet` Raises "Parameter Not Optional"

Scenario: `model.FeatureManager.FeatureFillet(195, radius, 0, 0, None, None, None)` raises:

```text
com_error: (-2147352561, '非选择性的参数。', None, None)
```

Cause: `IFeatureManager::FeatureFillet` **accepts only 4 parameters**: `(Options, Radius, R1, R2)`. Passing 7 parameters (padding three trailing `None` values) fails on both SolidWorks 2024 and 2026. Older documentation and early wrappers contained this bug, confirmed on live hosts.

Reliable approach:

```python
from sw_edge_select import select_edges
from sw_part import fillet
from sw_connect import mm

# 必须先建立非空的边线选择集
selection = select_edges(model, {"axis": "z", "convex_only": True})
if selection["status"] != "ok":
    raise RuntimeError(f"未选中边线: {selection['errors']}")
feature = fillet(model, mm(4))
```

`sw_part.fillet()` raises `ValueError` on an empty selection set rather than continuing—otherwise SolidWorks applies the fillet to the active contour/residual selection and produces hard-to-trace geometry errors.

### Fillet / Chamfer Picks the Wrong Edges

Scenario: The script succeeds without errors, yet fillets appear on unintended edges—or all fillet locations break after changing model dimensions.

Cause: `SelectByID2("Edge1", "EDGE", x, y, z, ...)` relies on hardcoded magic coordinates that break whenever dimensions change, and fails silently (returning `False` while subsequent features do not throw).

Reliable approach: Switch to `sw_edge_select.select_edges()` to select edges by B-Rep geometric criteria. See [references/edge-selection.md](edge-selection.md).

```python
from sw_edge_select import select_edges

# 先预览选中了哪些边，以及每条被排除的边的原因
preview = select_edges(model, {"axis": "z", "convex_only": True})
print(preview["selected_count"], preview["selected"])
print(preview["rejected_sample"])
```

### `IEdge.Select4` Raises "Type Mismatch"

Scenario: `edge.Select4(True, None, False)` raises:

```text
com_error: (-2147352571, '类型不匹配。', None, None)
```

Cause: The second parameter of `Select4(Append, Callout)` is a **Callout object**, which must be a Dispatch VARIANT rather than Python `None`.

Reliable approach: Prefer `Select2(Append, Mark)`, which avoids this issue; when `Select4` is required, pass `create_empty_dispatch_variant()`.

```python
from sw_connect import create_empty_dispatch_variant

edge.Select2(True, 0)                                    # 首选
edge.Select4(True, create_empty_dispatch_variant())      # 回退
```

### Hole "Succeeded" Yet No Hole Appears on the Model

Scenario: `create_through_hole()` returns feature evidence, yet no cut feature appears in the tree or `SolidWorks 未创建特征` is reported.

Checklist:

1. **Units**: `center`, `diameter`, and `depth` in `sw_hole_features` all expect **meters**. Passing millimeters (e.g., `10` for 10 mm) produces a 1000x oversized sketch that falls completely outside the solid body and is silently rejected. Live testing observed a 100x60x6 mm plate expanding to a 13,300 mm bounding box for this exact reason.
   ```python
   from sw_connect import mm
   create_through_hole(model, center=(mm(10), mm(10)), diameter=mm(6.6))
   ```
2. **Hole within solid bounds**: When a cut sketch lies completely outside the solid, SolidWorks raises no error and simply returns `None`. Validate bounds via `build_from_spec.validate_holes_inside_base()` or manual checks.
3. **Reading the wrong return key**: `HoleFeatureEvidence.to_dict()` uses `feature_names` (a tuple) and has no `status` or `feature_name` key. Calling `result.get("status")` misclassifies a succeeded hole as failed.

### Check Feature Return Values Against `None`, Not Truthiness Alone

Most SolidWorks feature APIs return `None` on failure. **Never** rely loosely on `if feature:` or ignore return values. Check every feature immediately after creation, and abort or degrade cleanly on failure:

```python
feature = extrude_boss(model, sketch_ref, mm(8))
if feature is None:
    raise RuntimeError("拉伸失败：检查草图是否闭合、方向是否正确、深度是否非零")
```

### Bounding Box Readback Is Off by 1000x or 0.001x

Scenario: Values returned by `model.GetPartBox(True)` are misinterpreted between millimeters and meters.

Cause: `GetPartBox` has two modes with different units:

| Call | Return Units |
|---|---|
| `GetPartBox(True)` | **Meters** (system units) |
| `GetPartBox(False)` | **Millimeters** (document units, dependent on document unit settings) |

`sw_measure.collect_bounding_box()` consistently uses `True` and converts to millimeters—use the wrapper directly.

```python
from sw_measure import collect_bounding_box
box = collect_bounding_box(model)
print(box["size_mm"])   # [长, 宽, 高]，毫米
```

### Mass Properties Warns "No Material Assigned"

Scenario: `warnings` from `collect_mass_properties()` includes `"文档未分配材料"` ("no material assigned to document").

Cause: SolidWorks calculates unassigned parts using a default density (1000 kg/m³). Although numeric values are produced, they **must not be used directly for engineering decisions** (motor sizing, shipping weight, and cost estimates will all be off).

Remediation: Assign a material in the document, or pass an explicit density override:

```python
result = collect_mass_properties(model, density_kg_m3=7850.0)   # 45 钢
```

In addition, `IMassProperty.Status` is unavailable in some versions (observed on SW2024 SP5), so returning `status: null` is normal and does not invalidate mass values.

### MCP Calls Hang Indefinitely

Scenario: Any SolidWorks MCP tool call never returns, and all subsequent tool calls queue up indefinitely.

Cause: When SolidWorks displays a modal dialog (template picker, license prompt, overwrite confirmation), it stops responding to Automation calls and never times out, leaving the lock-holding operation wedged.

Remediation:

1. Run `solidworks_recover` to diagnose—it enumerates SolidWorks windows and reports any detected modal dialogs plus the operation currently holding the lock.
2. Switch to the SolidWorks window and **manually** dismiss the dialog. For automated dismissal, pass `{"dismiss_dialogs": true}`, noting that `WM_CLOSE` may discard unsaved changes (disabled by default).
3. If the window is completely frozen, terminate `SLDWORKS.exe` via Task Manager and call `solidworks_connect`.

The lock timeout cap is 300 seconds; after that, tools return a structured error rather than blocking permanently.

## Calling Unwrapped APIs

When a task requires a SolidWorks API not yet wrapped by this skill:

1. Check official SolidWorks API docs or local SDK documentation first to confirm signatures and enumerations.
2. Validate the interface with a minimal standalone script—never embed unverified calls straight into a large workflow.
3. Check COM return values for `None` / `False` and print error/warning codes.
4. Once proven, promote the stable wrapper into `scripts/` and record pitfalls in this file or the corresponding `references/*.md`.

Documentation template:

```text
### <API 或错误现象>

场景:
错误/症状:
原因:
稳定写法:
  # 最小可运行示例
验证方式:
```

## Performance Optimization

### Slow Operations on Large Assemblies

```python
# 开启后台处理模式
model.FeatureManager.EnableFeatureTree = False
model.ActiveView.EnableGraphicsUpdate = False

# ... 执行操作 ...

# 恢复并刷新
model.FeatureManager.EnableFeatureTree = True
model.ActiveView.EnableGraphicsUpdate = True
model.GraphicsRedraw2()
```

### Batch Operation Optimization

```python
# 禁用自动重建
sw.UserControl = False

# 执行批量操作...

# 手动重建
model.EditRebuild3()
sw.UserControl = True
```

## Version Number Mapping

| SolidWorks | Revision | ProgID |
|---|---|---|
| 2020 | 28 | SldWorks.Application.28 |
| 2021 | 29 | SldWorks.Application.29 |
| 2022 | 30 | SldWorks.Application.30 |
| 2023 | 31 | SldWorks.Application.31 |
| 2024 | 32 | SldWorks.Application.32 |
| 2025 | 33 | SldWorks.Application.33 |
| 2026 | 34 | SldWorks.Application.34 |

Formula: `Revision = (Year - 2000) + 8`

## Licensing and Add-in Boundaries

Connecting to base SolidWorks COM does not prove that Simulation, Routing, Motion, or Mold add-ins have usable licenses. Capability probing must separately record add-in registration, load state, and minimal live operation results; when valid authorization is missing, return `blocked` with the specific dependency rather than misreporting license issues as generic script errors.

This project never patches licenses, bypasses activation, modifies licensing services, or fabricates capabilities for unlicensed installations. In such cases, legal headless backends such as OCP, CalculiX, and `ezdxf` can still be used for open-format tasks.
