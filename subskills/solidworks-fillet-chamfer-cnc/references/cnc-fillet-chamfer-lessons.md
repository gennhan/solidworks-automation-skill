# CNC Multi-Fillet/Chamfer Modeling & Acceptance Lessons

## v2 Capability Boundaries

Beyond constant-radius edge Fillets, angle-distance Chamfers, and hole-mouth Chamfers, the live-machine path now covers six isolated advanced paths. Capabilities must always be declared per "version + input topology"—never mark a capability stable across environments just because the SolidWorks UI supports it:

- Three-intermediate-control-point variable-radius Fillets, Setback corners, Face Fillets, Full Round Fillets, plane–cylinder G2 surface combinations, and asymmetric width-width Chamfers have minimal live-machine regressions on SolidWorks 2026 SP1.1.
- Hold-line / hold-face Fillets remain `blocked` on local SW2026 SP1.1: the projected Split Line and marks `2/4/8` are generated deterministically; Python, C# PIA, SWBasic, and officially required in-process unmanaged C++ were all tested, isolating the fault boundary to `ISetHoldLines` rather than a Python-only restriction. Because native probing can trigger a SolidWorks server fault, it is disabled by default and re-tested only under explicit authorization in an isolated instance.
- Vertex Chamfers, G1/G2 transitions between freeform surfaces, complex undercut relief grooves, and 5-axis surface rest-machining fillets are not yet covered.

When expanding these capabilities, consult the official API for the target SolidWorks version first, then complete creation, save, close, reopen, FeatureManager tree readback, STEP export, and multi-view preview on a minimal part. Upgrade capability status only after consecutive regressions pass.

## v2 Offline Gates

`scripts/cnc_strategy.py` checks the following before calling COM:

- All numeric values are finite and dimensions are positive; Fillets/Chamfers allowed to be zero explicitly disable the corresponding operation.
- Step width of the Boss relative to the base body, plus upper bounds for Fillet radii and Chamfer depths.
- Envelopes, edge wall thicknesses, and inter-feature clearances for counterbored mounting holes, dowel holes, center slots, and lightening pockets.
- Remaining floor thickness under counterbores and pockets, plus counterbore diameter strictly greater than through-hole diameter.
- DFM warnings for sharp inside corners on rectangular lightening pockets; rounded-slot pockets are used by default.

Default template dowel-hole positions were moved to `(0, ±24)` mm. The legacy `(±32, 0)` mm coordinates intersected the 62 mm × 16 mm center slot and could not be delivered as "independent dowel holes".

## Lessons Learned

Verification of the "CNC Aluminum Mounting Base" proved that SolidWorks COM automation can reliably generate multi-Fillet/Chamfer models, provided feature ordering and edge-selection methods are strictly controlled. The verified model contains a baseplate, center Boss, mounting holes, counterbores, dowel holes, center slot, lightening pockets, and genuine Fillet and Chamfer features, passing `sw_review` rule checks.

Key takeaways:

- For parts with many Fillets and Chamfers, keep the base body topology simple first and add complexity incrementally.
- Applying large Fillets and outer-profile Chamfers before holes and slots is far more stable than placing them after all Cuts.
- Selecting edges via B-Rep entity objects is much more reliable than auto-generated edge names or coordinate clicks.
- Always check every SolidWorks feature return value for `None` / `False`, aborting or degrading immediately on failure.
- If an output file with the same name is already open in SolidWorks, saving fails—typically with `SaveAs` error code `1`.

## Recommended APIs and Wrappers

Always prefer existing parent-skill wrappers:

```python
from sw_session import SolidWorksSession
from sw_connect import mm, get_com_member, create_empty_dispatch_variant
from sw_export import export_to_step
from sw_review import run_review
from sw_appearance import set_document_appearance
```

Common SolidWorks APIs:

```python
model.FeatureManager.FeatureExtrusion3(...)
model.FeatureManager.FeatureCut4(...)
model.FeatureManager.FeatureFillet(195, radius, 0, 0, None, None, None)
model.FeatureManager.InsertFeatureChamfer(4, 1, distance, math.pi / 4, 0, 0, 0, 0)
edge.Select2(append, 0)
model.GetBodies2(0, False)
body.GetEdges()
edge.GetCurve()
curve.IsLine()
curve.IsCircle()
curve.CircleParams()
```

Under `pywin32`, members such as `GetStartVertex`, `GetEndVertex`, and `FirstFeature` may behave like pseudo-callable properties; read them via `get_com_member()`.

## Deterministic Edge-Selection Pattern

Never rely on `Edge1`, `Edge2`, or nameless coordinate picks. Recommended pattern:

```python
def edge_points(edge):
    start_vertex = get_com_member(edge, "GetStartVertex")
    end_vertex = get_com_member(edge, "GetEndVertex")
    if not start_vertex or not end_vertex:
        return None
    return (
        tuple(get_com_member(start_vertex, "GetPoint")),
        tuple(get_com_member(end_vertex, "GetPoint")),
    )

def midpoint(edge):
    points = edge_points(edge)
    if not points:
        return None
    start, end = points
    return tuple((start[i] + end[i]) / 2.0 for i in range(3))

def select_edges(model, predicate):
    model.ClearSelection2(True)
    count = 0
    for body in get_com_member(model, "GetBodies2", 0, False) or []:
        for edge in get_com_member(body, "GetEdges") or []:
            if predicate(edge) and edge.Select2(count > 0, 0):
                count += 1
    return count
```

Classify edges by endpoints, circle center, radius, direction, and supporting plane. The template uses a 0.05 mm geometric tolerance and declares exact expected counts for each target group: 4 vertical base corners, 8 outer-contour edges after corner Fillets, and 6 hole-mouth circular edges (4 counterbores + 2 dowel holes).

Record an `Edge1`-independent geometric signature for every selection:

```json
{
  "curve": "circle",
  "center_mm": [46.0, 28.0, 18.0],
  "radius_mm": 6.5
}
```

A count mismatch indicates topological ambiguity, not "insufficient tolerance". Stop and emit all candidate signatures; never automatically widen tolerances to millimeter scale or proceed to feature API calls.

### Edge Selection on Existing Models

The template's 4/8/6 count assertions apply only to that mounting-base topology. When modifying an existing part:

1. Export a candidate edge-signature inventory and isometric preview first.
2. Constrain targets using user-provided datum planes, features, dimension bounds, and adjacent faces rather than reusing fixed template counts.
3. Record the new expected counts in the task's operation plan and get one manual confirmation.
4. Re-enumerate edges after each operation; never reuse COM `Edge` objects cached before a Fillet or Chamfer.

## Recommended Feature Order

For CNC mounting bases, connector blocks, and machined plates:

1. Base rectangular plate Extrude Boss.
2. Top Boss Extrude.
3. Large outer-contour Fillets and top/bottom edge Chamfers.
4. Lightening pockets.
5. Through mounting holes.
6. Counterbores / countersunk steps.
7. Dowel holes.
8. Center rounded slot.
9. Small hole-mouth Chamfers.
10. Save, export STEP, and review previews.

If step 3 is placed after holes and slots, SolidWorks may spend a long time solving complex topology. If it must be deferred, reduce radii and edge counts first and test group by group.

## Radius and Degradation Policies

Conservative defaults:

- Large base vertical-corner Fillets: R6–R10
- Boss vertical-corner Fillets: R3–R6
- Outer-contour Chamfers: C0.8–C2
- Boss top-face Chamfers: C0.5–C1
- Hole-mouth Chamfers: C0.3–C0.8

The template provides two explicit policies:

- `strict`: attempt only the requested size and stop on failure; suited to non-negotiable drawing deliveries.
- `progressive`: attempt 100%, 75%, and 50% of the requested value sequentially, with a floor of 0.1 mm.

`progressive` is never a silent fix. The parameter JSON must record `requested_value_mm`, `actual_value_mm`, status `degraded`, and every failed attempt; external delivery notes must cite the actual dimensions.

Manual troubleshooting order:

1. Reduce Fillet radius or Chamfer distance.
2. Reduce the number of edges selected in a single operation.
3. Move large Fillets ahead of hole/slot Cuts.
4. If the user approves, explicitly set non-critical slot/pocket Fillets to `0` and regenerate the plan.
5. Critical Fillets or Chamfers must never be skipped automatically; remain blocked if unsatisfied.

Even after a feature API returns non-null, call `ForceRebuild3(False)` and read the feature back by name from the FeatureManager tree. Advance to the next size tier only if the API returns `None`; if it returns non-null yet disappears after rebuild, stop rather than stacking further features.

## Recommended Expansion Roadmap

Ordered by value vs. risk:

1. **Generic Existing-Model Edge Inventory**: export edge–face adjacency, curve type, length, bounding box, and geometric signature so users can confirm semantic groups.
2. **Additional Machining Features**: keyways, dovetail slots, T-slots, undercut reliefs, O-ring grooves, and countersunk holes; add parameter/collision checks before wiring COM for each.
3. **Multi-Body Parts and Configurations**: store edge-selection evidence independently per solid body and configuration; never reuse transient topology references across configurations.
4. **Advanced Fillets/Chamfers**: keep multi-control-point variable Fillets, Face/Full-Round/Setback Fillets, G2 surface combinations, and width-width Chamfers as six separate execution paths with independent evidence rather than one monolithic wrapper; retain the independent negative probe for Hold Lines.

## SolidWorks 2026 Advanced Fillet Live Findings

- Variable radius: `FeatureFillet3` uses mark `1` on the target edge and mark `256` on intermediate `POINTREF` selections; control points at 25%/50%/75% read back as R3/R6/R4, and position readback values are percentages `25/50/75` rather than fractions `0.25/0.5/0.75`.
- Face Fillet: `CreateDefinition(swFmFillet)` → `Initialize(swFaceFillet)` → `SetFaces`; two face sets read back with `Type=2`.
- G2 surface combination: assign planar top face and cylindrical side face to two face sets and set `CurvatureContinuous=true`; both `Type=2` and the G2 flag must still read back after reopen.
- Full Round: also uses `ISimpleFilletFeatureData2`, assigning side set 1, center face set, and side set 2 separately with count verification, reading back `Type=3`.
- Setback: `FeatureFillet3` uses mark `1` on the three intersecting edges and mark `0` on the corner vertex; distances must be passed as `SAFEARRAY<double>`. Under `pywin32`, a plain `tuple` is accepted by COM yet solves to `None`—`VARIANT(VT_ARRAY | VT_R8, ...)` is required.
- Width-width Chamfer: `InsertFeatureChamfer` with `ChamferType=2` writes the two widths into `Width`/`OtherDist` (not the vertex chamfer slots); `GetEdgeChamferDistance` uses side indices `0/1`.
- All six modes should generate separate parts so an earlier advanced Fillet cannot alter downstream topology; mark `verified` only when save, STEP, reopen, `FeatureData`, and review reports all pass.
- Hold Line: official docs require face-set marks `2/4`, hold-line mark `8`, and setting `HoldLines`, while `ISetHoldLines` explicitly supports only in-process unmanaged C++. Accordingly, the implementation includes C# PIA, SWBasic, and an MSVC x64 native bridge rather than locking the backend to Python. SW2026 SP1.1 / Revision 34.1.1 still reproduces a server fault at the native `ISetHoldLines` call and defaults to structured blocking; the regression strictly requires `GetHoldLineCount=1` both after creation and after reopen and never misreports a regular `Fillet` or Split Line as success.

Official API references:

- [IFeatureManager.FeatureFillet3](https://help.solidworks.com/2026/English/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IFeatureManager~FeatureFillet3.html)
- [ISimpleFilletFeatureData2](https://help.solidworks.com/2026/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISimpleFilletFeatureData2.html)
- [HoldLines](https://help.solidworks.com/2025/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISimpleFilletFeatureData2~HoldLines.html)
- [ISetHoldLines (in-process unmanaged C++ only)](https://help.solidworks.com/2025/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISimpleFilletFeatureData2~ISetHoldLines.html)
- [InsertFeatureChamfer](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IFeatureManager~InsertFeatureChamfer.html)

## Open-Source Complex Bracket Regressions

The second complex regression uses MIT-licensed [parametric-bracket-library](https://github.com/archimedes-market/parametric-bracket-library) `l_gusset`, pinned to commit `5b285130...`, CadQuery 2.8.0, and generated STEP SHA-256 `cc2d38a4...`. The CadQuery source model has two perpendicular mounting plates, a triangular gusset rib, and six holes; SW2026 STEP import baseline is `1 solid / 18 faces / 49 edges`. The script applies a 4-intermediate-control-point variable-radius Fillet (positions `20/40/60/80%`, radii `1.2/1.8/0.9/1.5 mm`) and a C0.8/C1.4 width-width Chamfer on the same solid body, using post-treatment topology `20 faces / 55 edges`, reopened `FeatureData`, and 4-view review as closed-loop evidence.

The existing FreeCAD-library case continues to provide a second independent source and geometric-signature verification:

It uses FreeCAD-library's `2020_corner_bracket-Corner.step`, pinned to commit `b342740f...` and SHA-256 `25e3fbc1...`. The part comprises a base plate, upright wall, reinforcement ribs, holes, and slots; source topology reads back as `1 solid / 40 faces / 98 edges / 64 vertices`. The script locks onto the unique angled edge with endpoints `(-0,-20,3)→(-0,-3,20) mm` and length `24.041631 mm` from the manifest and creates a C0.2/C0.4 width-width Chamfer; both post-treatment and reopened topology read back as `1 solid / 41 faces / 101 edges / 66 vertices`. Complex-part runs complement the six controlled samples by proving solving and persistence on real topologies, while the six controlled samples verify exact readback of advanced parameters independently.

This case uses FreeCAD-library's [CC BY 3.0](https://github.com/FreeCAD/FreeCAD-library) license; contributor attribution and download hash are recorded in `examples/open_source_corner_bracket_case.json`.
5. **Manufacturing Acceptance**: incorporate cutter diameter, tool reach, minimum inside Fillet radius, clamping orientation, tool accessibility, and operation-sequence recommendations; passing automated rules still requires CAM/process-engineer sign-off.

## Common Failures

### Extrusion Returns `None`

Usually caused by an unclosed Sketch with complex corner fillets. Extrude a simple closed rectangular Sketch first, then add real Fillet features to the vertical edges.

### Fillet/Chamfer Hangs for a Long Time

Usually caused by complex post-cut topology, oversized radii, or overly broad edge selection. Isolate and test each edge group separately: base vertical corners, Boss vertical corners, top edges, bottom edges, and hole mouths.

### `SaveAs` Error Code 1

The target file may already be open in SolidWorks. Close any document with the same filename before creating the new part:

```python
try:
    session.close(title=Path(output_part).name)
except Exception:
    pass
```

### Semi-Transparent Preview or Unusual Shading

Do not mistake appearance artifacts for geometric failure. First verify the review report and confirm previews are non-blank. When appearance quality matters, call `set_document_appearance(model, "silver")` or color components individually in an Assembly.

## Review Checklist

Read the review report after completion and confirm at minimum:

- `evaluation.status`
- `checks.previews_created`
- `checks.previews_not_blank`
- `checks.expected_outputs_exist`
- `model.features` includes the expected `Fillet`, `Chamfer`, and `Cut` features

Even when rule checks pass, visually inspect the `isometric` and `top` previews to verify overall proportions, hole positions, counterbores, slots, pockets, and Fillet orientations.
