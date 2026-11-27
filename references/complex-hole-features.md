# Complex Hole and Slot Feature Automation

## Supported Scope

`scripts/sw_hole_features.py` creates the following features using sketches and cut features:

- Blind holes with a specified depth.
- Through-all holes.
- Two-stage compound counterbore holes (through hole + cylindrical counterbore).
- Conical countersink holes (through hole + specified included angle).
- Straight slots with semicircular ends, supporting through-all or blind depth.
- Hole arrays created from explicit coordinates.

This module does not call `HoleWizard5`. Until the long parameter list and version differences of Hole Wizard are verified against official signatures and live SolidWorks versions, assembling its arguments from memory is prohibited.

## Units and Reference Planes

- All input lengths are in meters; convert millimeter values with `sw_connect.mm()`.
- `center`, `start`, and `end` are local 2D coordinates on the target sketch plane.
- The default reference plane is `Front Plane`; Chinese SolidWorks editions are handled automatically by `sw_part.start_sketch()`.
- Creation parameter evidence outputs both meter and millimeter fields, but millimeter fields are strictly for reporting and are never passed back to COM.

## Examples

```python
from sw_connect import mm
from sw_hole_features import (
    create_blind_hole,
    create_counterbore_hole,
    create_countersink_hole,
    create_semicircular_slot,
)

blind = create_blind_hole(model, (mm(20), mm(20)), mm(8), mm(10), name="H1_盲孔")
counterbore = create_counterbore_hole(
    model,
    (mm(50), mm(20)),
    hole_diameter=mm(6),
    counterbore_diameter=mm(12),
    counterbore_depth=mm(4),
    name="H2_沉孔",
)
countersink = create_countersink_hole(
    model,
    (mm(80), mm(20)),
    hole_diameter=mm(5),
    countersink_diameter=mm(10),
    included_angle_deg=90,
    name="H3_沉头",
)
slot = create_semicircular_slot(
    model,
    (mm(30), mm(50)),
    (mm(60), mm(50)),
    width=mm(10),
    depth=0,
    name="S1_半圆端槽",
)
```

## Verification Evidence

The creation functions return parameter evidence, not geometric acceptance conclusions. Before delivery, always perform:

1. `sw_review.collect_geometry_measurements()` to read B-Rep cylindrical faces.
2. `sw_review.validate_hole_positions()` to verify hole diameters and hole axis positions.
3. Feature parameter readback or manual section-view inspection for blind hole depths, counterbore depths, and countersink angles.
4. Semicircular slot end cylindrical faces must be classified into `slot_arc_candidates` and must not be counted as circular holes.
5. Compound holes should appear in `compound_holes` as coaxial multi-diameter hole segments.

For each hole, it is recommended to record at least: hole type, specification, quantity, datum edge location, center distance, depth/through state, dimensional tolerance, and evidence source.

## Known Limitations

- Conical countersinks are built via an angle/distance chamfer on the through-hole entry circular edge. The entry edge is filtered by center point, radius, and reference plane position rather than transient edge names; after chamfering, always inspect a section view to confirm entry direction.
- B-Rep geometry alone cannot reliably distinguish blind holes from through holes; cross-verify against creation parameters or feature definition readback.
- Hole arrays currently create individual features at explicit coordinates to prioritize auditability; Linear/Circular Pattern wrappers can be added later for large regular arrays.
