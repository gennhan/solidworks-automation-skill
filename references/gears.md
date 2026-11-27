# Gear Solid Modeling and Assembly Linkage Routing

## First Determine What the User Needs

| User Intent | Correct Path | Prohibited Approach |
|---|---|---|
| Draw a gear, model a gear part, generate real tooth geometry | Use `scripts/sw_gear.py` for standard external spur gears; route other gear types to dedicated modeling workflows | Using a Gear Mate instead of modeling gear solid geometry |
| Two meshing gears linked together, draggable transmission, gear ratio | `sw_assembly.add_gear_mate_by_cylinders()` | Using fake script animations to impersonate a Gear Mate |
| Production-grade industrial gears | Confirm tooth system, profile shift, backlash, tolerances, tip/lead modifications, material, and strength; use dedicated gear tools and engineer review | Presenting visualization tooth profiles as production-ready gear geometry |

When the user simply asks to "draw a gear," do not automatically jump to assembly mates just because the skill is active. Manufacturing tasks require module, tooth count, pressure angle, face width, and bore diameter; for visual demos only, default parameters may be used but must be explicitly stated in the result.

## Current Supported Scope

`SpurGearSpec` covers only standard full-depth, external, straight-tooth involute cylindrical spur gears:

- Pitch diameter: `d = m * z`
- Base circle diameter: `db = d * cos(alpha)`
- Addendum (tip) diameter: `da = d + 2m`
- Dedendum (root) diameter: `df = d - 2.5m`
- Pitch circle tooth thickness: `s = pi * m / 2`

Tooth flanks are sampled along the base-circle involute `inv(alpha) = tan(alpha) - alpha`. When the root circle lies below the base circle, the current implementation uses radial transitions and root arcs rather than an actual hob-generated trochoid root fillet. The script reports theoretical undercut risk, but does not automatically apply profile shift.

## Minimal Invocation

```python
from sw_gear import SpurGearSpec, create_external_spur_gear

spec = SpurGearSpec(
    module_mm=2.0,
    teeth=24,
    pressure_angle_deg=20.0,
    face_width_mm=10.0,
    bore_diameter_mm=10.0,
    involute_segments=14,
)
feature, evidence = create_external_spur_gear(model, spec)
```

`evidence` returns analytical dimensions, undercut risk, profile density, and known limitations. Always follow up with `collect_geometry_measurements()` to read back tip bounding dimensions and center bore from SolidWorks B-Rep, and perform save, STEP export, four-view visual review, and close/reopen verification.

## Verified Case

Live test case on SolidWorks 2026 SP1.1 (Revision 34.1.1): `m=2`, `z=24`, `alpha=20°`, face width `10 mm`, bore `10 mm`. Result: single solid body; B-Rep readback both after creation and after reopening measured `52 x 52 x 10 mm` with a `10 mm` internal cylindrical bore; both SLDPRT and STEP saved to disk; four-view rule review returned `pass/100`. Because production root geometry, backlash, and tolerances are not covered, this capability remains `pilot` and `review_required`.

## Scope Not to Be Claimed Automatically

- Helical gears, herringbone gears, bevel gears, internal gears, racks, and worm gears;
- Profile shift coefficients, backlash, tip/lead crowning modifications, and exact hobbed root fillets;
- TCVN/ISO/AGMA (or GB reference) tolerance grades, materials, heat treatment, contact/bending strength, or NVH verification;
- Treating high sampling density as a zero-cost default: more chordal segments slow down SolidWorks modeling, STEP export, and B-Rep traversal.

## References

- KHK, Calculation of Gear Dimensions: <https://khkgears.net/gear-knowledge/gear-technical-reference/calculation-gear-dimensions/>
- SOLIDWORKS API Help, `ISketchManager::CreateSpline3`: <https://help.solidworks.com/2021/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISketchManager~CreateSpline3.html>

The `CreateSpline3` reference only documents the boundary of smooth-curve experimentation: while strongly typed `SAFEARRAY(double)` can create splines in SW2026, full-circle gear profiles still cannot extrude reliably. Therefore, the verified path retains chordal discretization and never misrepresents "COM returned a spline object" as a valid solid body.
