# Appearance and Material Reference

## Core Rules

SolidWorks' 9-element material property array must be passed to COM as a `SAFEARRAY(double)`. Never assign a plain Python `list` directly to `MaterialPropertyValues`; under `pywin32` late-bound dispatch, a plain list can be marshaled incorrectly so RGB values land in positions 2, 5, and 8, causing the model to render almost entirely green.

Stable wrappers live in `scripts/sw_appearance.py`:

- `material_variant()`: Wraps the 9-element array as `VT_ARRAY | VT_R8`.
- `set_document_appearance()`: Writes and reads back document-level RGB values.
- `set_feature_appearance()`: Writes and reads back feature-level RGB values.
- `set_component_appearance()`: Writes and reads back assembly component-level RGB values.
- `apply_component_palette()`: Applies colors in batch and produces per-component audit results.
- `verify_appearance()`: Compares expected RGB values against COM readback values.

## Recommended Usage

```python
from sw_appearance import (
    apply_component_palette,
    set_document_appearance,
    set_feature_appearance,
    verify_appearance,
)

set_document_appearance(model, "iron_red")
set_feature_appearance(feature, "armor_gold")
assert verify_appearance(model, "iron_red")["ok"]

reports = apply_component_palette([
    (body_component, "aqua_blue"),
    (glass_component, "glass_tint"),
    (rear_light_component, "signal_red"),
    (rim_component, "silver"),
])
assert all(item["ok"] for item in reports)
```

## Preset Colors

| Name | Description |
|---|---|
| `iron_red` | Deep red armor |
| `armor_gold` | Gold armor |
| `dark_gunmetal` | Dark metal / joints |
| `arc_blue` | Blue emissive part |
| `silver` | Silver metal |
| `black` | Black |
| `white` | White |
| `aqua_blue` | Aqua blue body paint |
| `glass_tint` | Dark tinted glass |
| `signal_red` | Tail light / warning red |
| `light_cyan` | Light blue emissive part |
| `tire_black` | Tire black |
| `graphite` | Graphite gray |

## Verified API Signatures

Reflection results from local SolidWorks 2024 SP3.1 `SolidWorks.Interop.sldworks.dll`:

```text
IModelDoc2.MaterialPropertyValues = Object
IModelDocExtension.SetMaterialPropertyValues(Object, Int32, Object) -> void
IFeature.SetMaterialPropertyValues(Object) -> bool
IFeature.SetMaterialPropertyValues2(Object, Int32, Object) -> void
IComponent2.SetMaterialPropertyValues2(Object, Int32, Object) -> void
IComponent2.GetMaterialPropertyValues2(Int32, Object) -> Object
```

Configuration options: `swThisConfiguration=1`, `swAllConfiguration=2`, `swSpecifyConfiguration=3`. A setter returning `void` succeeds if no COM exception is raised—do not wrap it in `bool(method(...))` to test success; always rely on `verify_appearance()` readback as the source of truth.

## Multi-Color Assembly Workflow

1. Set the base document-level color on each source part and save.
2. After inserting components, apply component-level color overrides as needed.
3. Read back the first three RGB values after every write; stop immediately on mismatch.
4. Call `assembly.ClearSelection2(True)` before saving.
5. Clear selection and redraw again before capturing previews so green selection highlights do not obscure true appearances.
6. Inspect at least one color isometric view and one orthographic view showing lights/wheel hubs or key detail features.

## Stability Recommendations

- Multi-feature coloring within a single part can be affected by SolidWorks version, display states, and feature merging.
- For models with strict appearance requirements, split them into multiple parts and apply document-level appearance to each part.
- For complex projects, output an assembly so component hierarchy expresses colors, materials, and replaceable modules.
- Do not treat "setter did not throw an exception" as proof of correct color; always read back RGB.
- Do not capture screenshots while components, faces, or edges remain selected; green selection highlighting interferes with visual review.
- After generation, always export preview images with `sw_review.py` to verify color contrast and visual separation.
