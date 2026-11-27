# SolidWorks Threaded Hole Live Lessons

## 2026-08-29 Live Verification Findings

Previously, `CreateFeature(ThreadFeatureData)` returning `None` was not merely "COM instability", but incomplete creation data:

- After `InitializeThreadData()`, `Type` defaults to empty; internal metric threads must set `Type="Metric Tap"`.
- `Metric Tap.SLDLFP` must exist in the Thread Profiles directory. Official docs permit passing the profile name to `Type` without path or file extension.
- Select the planar circular edge with selection mark `1`, then assign `IThreadFeatureData.Edge`.
- When a planar circular edge is already supplied, do not also assign that same circular edge to `StartEntity`.
- `IThreadFeatureData` has no `LoadReferences(edge)` creation step; do not call it.
- The tap-drill cylindrical face already governs thread diameter; do not force `DiameterOverride=True` with the nominal major diameter.

Corrected M6×1 right-hand internal threads succeeded in live testing on SolidWorks 2026 SP01.1:

| Scenario | Tap Drill | Thread End Condition | Result |
|---|---|---|---|
| Blind hole in 16 mm block, 12 mm thread depth | Ø5.0, 13 mm blind Cut | `BlindDepth=12 mm` | `real-thread-verified`, review `pass/100` |
| Through-hole in 16 mm block | Ø5.0, `Through All` | `Revolutions=16` | `real-thread-verified`, review `pass/100` |

## Official API References

- [Thread Features and ThreadFeatureData Objects](https://help.solidworks.com/2026/English/api/sldworksapiprogguide/Overview/Thread_Features_and_ThreadFeatureData_Objects.htm)
- [IThreadFeatureData.Type](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IThreadFeatureData~Type.html)
- [IThreadFeatureData.Edge](https://help.solidworks.com/2026/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IThreadFeatureData~Edge.html)
- [swThreadEndCondition_e](https://help.solidworks.com/2026/English/api/swconst/SolidWorks.Interop.swconst~SolidWorks.Interop.swconst.swThreadEndCondition_e.html)
- [InsertCosmeticThread3](https://help.solidworks.com/2017/english/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IFeatureManager~InsertCosmeticThread3.html)
- [swCosmeticEndConditions_e](https://help.solidworks.com/2026/English/api/swconst/SolidWorks.Interop.swconst~SolidWorks.Interop.swconst.swCosmeticEndConditions_e.html)
- [BlankSketch](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IModelDoc2~BlankSketch.html)

## Correct End Conditions

Tap-drill Cuts, real `Thread` features, and `CosmeticThread` features use three distinct enumerations that must never be mixed:

```text
底孔 FeatureCut4:
  Blind      = swEndCondBlind (0)
  ThroughAll = swEndCondThroughAll (1)

ThreadFeatureData:
  Blind       = swThreadEndCondition_Blind (0)
  Revolutions = swThreadEndCondition_Revolutions (1)
  UpToSelect  = swThreadEndCondition_UpToSelection (2)

CosmeticThread:
  Blind   = swEndConditionBlind (0)
  Through = swEndConditionThrough (2)
```

Through tap-drill holes must use `FeatureCut4(..., T1=1, ...)`. A blind Cut of "thickness + 1 mm" appears to break through visually, but breaks feature semantics, parametric edits, and Engineering Drawing recognition.

## Parameter Validation Floor

Reject before calling COM:

- `NaN`/infinity or non-positive block dimensions, tap-drill diameter, depths, or Chamfer sizes.
- Tap-drill diameter greater than or equal to nominal diameter.
- Thread depth greater than blind tap-drill depth, or through-thread depth greater than plate thickness.
- Hole center outside the block, or insufficient edge margin for major thread diameter and hole-mouth Chamfer.
- Non-table metric pitch without an explicit `--tap-drill`. Tap-drill size depends on workpiece material, tap type, and percent thread engagement, so a generic `D-P` rule of thumb must never be treated as a confirmed value.

## Feature Persistence Evidence

A non-null COM object returned by `Thread`/`CosmeticThread` proves only an attempted creation, not final persistence. After `ForceRebuild3(False)`, the script traverses `FirstFeature`/`GetNextFeature` and recursively traverses `GetFirstSubFeature`/`GetNextSubFeature`, outputting:

- `thread_attempts`: attempt outcome and failure reason for each API.
- `thread_evidence`: whether the tap-drill Cut, Chamfer, real `Thread`, `CosmeticThread`, and 3D evidence Sketch remain in the FeatureManager tree.
- `thread_status`: `real-thread-verified` / `cosmetic-thread-verified` / `visible-helix-verified` derived from post-rebuild evidence. If only custom properties remain, the template blocks delivery.

Official SolidWorks examples document that `CosmeticThread` is a sub-feature of the hole or Cut. Traversing only top-level features falsely flags persisted `CosmeticThread` features as missing; current evidence collection includes sub-features.

## 3D Helix Is Visual Evidence Only

The legacy implementation rounded `thread_depth / pitch` to whole turns, distorting true pitch—for example, 16 mm depth at `P=1.25 mm` is 12.8 turns, not 13 turns. The current code uses fractional turns at 32 segments per turn to preserve exact pitch and stays within hole depth.

SolidWorks renders visible 3D Sketch curves through solid bodies, causing dashed lines across outer walls in standard isometric views. Therefore, the script exports `*_thread_evidence.bmp` first and then calls `BlankSketch()` to hide the evidence Sketch so standard previews stay clean.

A 3D Sketch is not a machinable thread form and must never be claimed as a CAM solid thread.

## Manufacturing Details Not Yet Covered

Blind tap-drill Cuts currently have flat bottoms without a standard drill-point cone, effective full-thread depth, incomplete lead/runout threads, tap-bottom clearance, or chip clearance. Thus "tap-drill Cut + `Thread`" provides sound CAD and drawing semantics, but must not be claimed as complete tapping process design without manufacturing review.

For detailed expansion ordering and acceptance gates, see [threaded-hole-roadmap.md](threaded-hole-roadmap.md).
