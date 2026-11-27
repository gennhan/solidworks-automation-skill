# Design Spec-Driven Modeling

Describe a part using a **version-controllable design specification file**, then let the executor idempotently rebuild the model.

## Why It Is Needed

Imperative calls (`sketch_circle` -> `extrude_boss` -> `save`) work for one-off scripts, but not for product iteration: what an engineer actually wants to do is "change the mounting plate thickness to 8 mm and switch the four M6 holes to M8," rather than rewriting the entire modeling sequence. Three key benefits of specification files:

1. **Diffable / Committable** — Commit design intent rather than disposable scripts.
2. **Idempotent Rebuilds** — The same specification produces a consistent FeatureManager tree structure every time.
3. **Built-in Verification** — The `verify` block automatically reads back geometry after build and compares against expectations.

## Minimal Working Specification

```json
{
  "schema_version": "1.0",
  "part_name": "motor_mount",
  "units": "mm",
  "base": { "type": "rect_plate", "width": 120, "height": 80, "thickness": 8 },
  "holes": [
    { "id": "H1", "type": "through", "diameter": 6.6, "position": [15, 15] },
    { "id": "H2", "type": "through", "diameter": 6.6, "position": [105, 15] },
    { "id": "H3", "type": "through", "diameter": 6.6, "position": [15, 65] },
    { "id": "H4", "type": "through", "diameter": 6.6, "position": [105, 65] }
  ],
  "fillets": [ { "radius": 4, "axis": "z", "convex_only": true } ],
  "verify": { "envelope_mm": [120, 80, 8], "hole_count": 4, "tolerance_mm": 0.1 }
}
```

## Coordinate System Convention (Important)

**The origin is at the bottom-left corner of the plate**, with the plate face lying in the first quadrant of the XY plane and extruded along +Z.

Thus `position: [15, 15]` directly means "15 from the left edge, 15 from the bottom edge" on an engineering drawing, eliminating mental math for center offsets. This matches the default hole-dimensioning convention on mechanical drawings.

> If a hole center falls outside the plate or a hole wall breaches the boundary, the executor raises an error **before** creating holes and lists the out-of-bounds holes. In SolidWorks, out-of-bounds holes are silently rejected (appearing as "feature succeeded but does not exist"), so up-front validation immediately reveals a coordinate issue rather than an API failure.

## Field Reference

### `base` (Base Solid)

| type | Required Fields | Description |
|---|---|---|
| `rect_plate` | `width` `height` `thickness` | Rectangular plate with origin at bottom-left corner |
| `cylinder` | `diameter` `height` | Cylinder with axis at origin |
| `none` | — | Do not create a base solid; build only subsequent features (must be **explicitly** specified) |

Omitting `base` raises `SPEC_EMPTY`: accidentally omitting it and intentionally building only subsequent features are different intents and must not be conflated.

### `holes` (Holes)

| type | Required Fields |
|---|---|
| `through` | `diameter` `position` |
| `blind` | `diameter` `depth` `position` |
| `counterbore` | `diameter` `counterbore_diameter` `counterbore_depth` `position` |
| `countersink` | `diameter` `countersink_diameter` `angle` (default 90, included angle) `position` |

Always provide an `id`. If omitted, IDs are auto-assigned (`H1`, `H2`, ...) with a warning—inspection records require stable traceability IDs, whereas auto-numbering shifts when new holes are inserted.

**Hole Patterns**: Attach a `pattern` field to a hole definition to define multiple holes at once; the executor expands them into individual holes with unique IDs:

```json
{ "id": "B", "type": "through", "diameter": 5.5, "position": [60, 40],
  "pattern": { "type": "circular", "count": 6, "radius": 30, "start_angle": 0 } }
```

```json
{ "id": "L", "type": "through", "diameter": 5.5, "position": [10, 10],
  "pattern": { "type": "linear", "count": 4, "dx": 20, "dy": 0 } }
```

For `circular`, hole positions are offset relative to `position`; `start_angle` is in degrees, with 0° along the +X direction.

### `fillets` (Fillets)

```json
{ "radius": 4, "axis": "z", "convex_only": true }
```

| Field | Description |
|---|---|
| `radius` | Fillet radius |
| `axis` | `x` / `y` / `z` / `vertical` / `all`; fillet only edges parallel to this axis |
| `convex_only` | Fillet only convex edges (external profile) |
| `concave_only` | Fillet only concave edges (internal corners) |

A DFM warning is issued if the fillet radius exceeds half the plate thickness (SolidWorks may fail to generate or self-intersect).

When no matching edges are found, the fillet is **skipped and logged as a warning** rather than falling back to "operate on the current selection set"—the latter would apply fillets to unintended edges and create hard-to-debug geometry.

### `verify` (Post-Build Verification)

| Field | Description |
|---|---|
| `envelope_mm` | Expected bounding box dimensions `[length, width, height]` |
| `hole_count` | Expected number of holes |
| `tolerance_mm` | Dimensional tolerance (default `0.1`) |
| `min_mass_g` / `max_mass_g` | Lower and upper mass limits |

Verification results have three states: `pass` (all checks satisfied), `warn` (deviations found, manual review required), and `skipped` (no `verify` block provided). **Deviations do not automatically trigger failure**—legitimate design changes also alter dimensions, so an engineer must judge the difference.

## Units

`units` supports `mm` (default), `cm`, `m`, and `in`. All lengths in the spec are written in that unit and normalized to millimeters by the executor. **No unit guessing**: unknown units immediately return an error.

## Usage

```
# 只校验，不建模型（改规格时反复调用）
design_spec_validate  { "spec_path": "D:/designs/motor_mount.json" }

# 校验并构建
design_spec_build     { "spec_path": "D:/designs/motor_mount.json",
                        "output_path": "D:/designs/motor_mount.sldprt" }
```

You can also invoke it directly from Python:

```python
from scripts.design_spec import load_design_spec
from scripts.build_from_spec import build_from_spec
from scripts.sw_connect import connect_solidworks, new_document, save_document

validation = load_design_spec("D:/designs/motor_mount.json")
assert validation["status"] == "ok", validation["errors"]

sw, _ = connect_solidworks()
model = new_document(sw, "part")
audit = build_from_spec(model, validation["normalized"])
print(audit["status"], audit["verification"])
save_document(model, "D:/designs/motor_mount.sldprt")
```

## Return Structure and Evidence

The audit result returned by `build_from_spec` includes:

| Field | Meaning |
|---|---|
| `status` | `ok` / `warn` / `error` |
| `steps` | Execution record for each step (feature name, location, success flag) |
| `hole_count_requested` / `hole_count_created` | Requested hole count vs. actually created hole count |
| `fillet_results` | Number of selected edges and feature name for each fillet |
| `warnings` | Non-blocking issues (DFM hints, skipped fillets, unassigned material) |
| `errors` | Blocking errors with actionable next steps |
| `measurements.bounding_box` | Read-back bounding box (mm) |
| `measurements.mass_properties` | Read-back mass, volume, and material |
| `verification` | Comparison results against the `verify` block |

Check `steps` for incremental auditing: it itemizes which hole was placed at what position and which feature it created, making item-by-item drawing verification straightforward.

## Common Error Codes

| Error Code | Meaning and Remediation |
|---|---|
| `SPEC_UNIT_UNSUPPORTED` | Unit not in supported list; change to `mm`/`cm`/`m`/`in` |
| `SPEC_EMPTY` | `base` not defined; check if omitted accidentally or explicitly set `"type": "none"` |
| `SPEC_HOLE_ID_DUPLICATE` | Duplicate hole `id`; assign unique values |
| `SPEC_FIELD_MISSING` | Missing required dimensional field for the hole type |
| `SPEC_NOT_POSITIVE` | Dimension must be positive |
| `SPEC_HOLE_TYPE` | Unknown hole type |
| `SPEC_HOLES_TOO_MANY` | Hole count exceeds the limit of 200 |
| `SPEC_JSON_INVALID` | JSON syntax error with parse location |
| `SPEC_FILE_MISSING` | File path does not exist (use an absolute path) |

The validator **returns all errors at once** rather than stopping on the first error, so you can fix everything in a single pass.
