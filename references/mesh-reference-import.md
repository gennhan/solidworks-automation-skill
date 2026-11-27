# High-Fidelity Mesh Reference Model Import

When users ask for "authentic factory look," "1:1 replica," or "not a concept blockout" for cars, consumer electronics, or sculpted figures, first clarify whether the goal is an editable engineering solid or a high-fidelity visual reference. High-fidelity visual references should normally start from a publicly available 3D model or multi-view blueprints rather than hand-crafting low-poly prisms from scratch and endlessly tweaking them.

## Applicable Scenarios

- User explicitly requests real-product visual fidelity (e.g., "factory Xiaomi SU7," "1:1 replica from public reference").
- Goal is presentation, proportion checking, styling reference, or an underlay for subsequent reverse engineering.
- Inputs are mesh or DCC formats such as `.glb`, `.gltf`, `.obj`, `.stl`, `.fbx`, or `.blend`.

Unsuitable scenarios:

- User needs parametrically editable mechanical features, Class-A surfacing suitable for engineering drawings, or sheet metal structures.
- User requires internal mechanisms, assembly mates, dimensional tolerances, or manufacturing features—remodel parametrically or reverse-engineer component by component instead of calling a triangle mesh an engineering solid.

## Workflow Selection

1. Source reliable input first: user-supplied model files take priority, followed by downloadable public models, and finally multi-view orthographic blueprints for contour reconstruction.
2. Record provenance and license: even for public models, log URL, author, license, and download date; non-commercial statements do not waive attribution or share-alike terms.
3. Preserve raw source files: keep original GLB/FBX/OBJ alongside converted OBJ/STL in the same working directory and write a `manifest.json`.
4. Normalize scale and axes: inspect the bounding box first, then scale to true nominal dimensions; automotive models commonly use `X=width`, `Y=height`, `Z=length`.
5. Prefer importing OBJ: OBJ is more likely to preserve materials, tinted glass, lamp assemblies, and interiors; STL is stable but typically drops materials.
6. Always perform four-view visual inspection after importing into SolidWorks. A rule-based `pass` score only proves "non-blank / file exists," not that it looks like the target object.

## GLB/FBX/BLEND Conversion Recommendations

SolidWorks support for GLB/FBX/BLEND is unstable; convert beforehand:

- When Blender is available: import into Blender and export OBJ/STL while preserving the texture directory.
- When Python is available: load GLB with `trimesh` and export OBJ/STL; prefer OBJ to preserve materials.
- Never convert high-poly meshes directly to STEP. Mesh-to-STEP produces massive faceted triangle B-Reps that easily hang SolidWorks `LoadFile4` or drop the RPC connection.

### Optional Python Dependencies

Mesh conversion is not a core dependency for normal SolidWorks modeling, but check these upfront when handling GLB/GLTF/OBJ/STL inspection, scaling, or texture export:

| Library | Purpose |
|---|---|
| `trimesh` | Load GLB/GLTF/OBJ/STL, compute bounding boxes, export OBJ/STL/PLY |
| `pygltflib` | Fine-grained parsing of GLTF/GLB metadata and assets |
| `numpy` | Scaling transforms and coordinate-axis remapping |
| `Pillow` | Texture image I/O and preview utilities |

Check command:

```powershell
python - <<'PY'
import importlib.util
for name in ["trimesh", "pygltflib", "numpy", "PIL"]:
    print(name, "OK" if importlib.util.find_spec(name) else "MISSING")
PY
```

If missing, prompt the user to install:

```powershell
python -m pip install -r SKILL_DIR\requirements-mesh.txt
```

These libraries may not be needed if you are simply importing an existing OBJ/STL into SolidWorks, but are typically required for converting GLB/FBX/BLEND or rescaling to real-world dimensions.

Example scaling script:

```python
import numpy as np
import trimesh

scene = trimesh.load(r"E:\source\SU7.glb", force="scene")
mesh = scene.dump(concatenate=True)

# 源模型轴向：X=宽，Y=高，Z=长；目标尺寸单位 m。
target_extents = np.array([1.963, 1.455, 4.997])
scale = target_extents / scene.extents
center_xz = np.array([
    (scene.bounds[0][0] + scene.bounds[1][0]) / 2,
    0,
    (scene.bounds[0][2] + scene.bounds[1][2]) / 2,
])

vertices = mesh.vertices.copy()
vertices[:, 0] = (vertices[:, 0] - center_xz[0]) * scale[0]
vertices[:, 1] = (vertices[:, 1] - scene.bounds[0][1]) * scale[1]
vertices[:, 2] = (vertices[:, 2] - center_xz[2]) * scale[2]
mesh.vertices = vertices

mesh.export(r"E:\work\reference_scaled_m.obj")
mesh.export(r"E:\work\reference_scaled_m.stl")
```

## Stable SolidWorks Import Usage

Preferred command:

```powershell
python scripts\sw_import_mesh_reference.py `
  E:\work\reference_scaled_m.obj `
  E:\work\reference_obj.SLDPRT `
  --units m `
  --model-type graphics `
  --review-dir E:\work\review_obj
```

Key details:

- Do not open OBJ/STL as regular parts via `OpenDoc6()`; some SW2024 setups return `errors=2097152`.
- When importing OBJ/STL via `LoadFile4()`, never pass `None` as the 3rd argument—this triggers `Type mismatch`.
- The reliable call is `LoadFile4(path, "r", create_empty_dispatch_variant(), errors)`.
- STEP/STP/IGES/IGS still follow the foreign CAD path in `sw_connect.open_document()`: `GetImportFileData()` + `LoadFile4(..., "r", import_data, errors)`.
- Default high-poly styling meshes to `graphics` import; use `surface` or `solid` only when solid stitching is explicitly required.

## Review Criteria

After importing, verify at least:

1. Output `.SLDPRT` exists and has a reasonable size.
2. `run_review()` exports four views (`isometric/front/top/right`).
3. Isometric view clearly shows overall styling, and front/side/top proportions match the target object.
4. Key recognizable features are present (e.g., roofline, lamps, wheels, side glass, front/rear bumpers on a vehicle).
5. Colors and materials are not polluted by selection highlighting; call `ClearSelection2(True)` before capturing previews.
6. Clarify the model type to the user: a mesh reference model is not native parametric surfacing, and manufacturing-grade deliverables require component-wise reverse engineering on top of it.

## SU7 Case Lessons Learned

- Wrong path: hand-scripting layered prisms/capsules for a car body and iteratively tacking on lamps, wheels, and glass. When the user wants an authentic SU7, that baseline drifts regardless of refinement.
- Right path: source a public SU7 mesh model, log provenance and license, convert to OBJ/STL, scale to `4997 x 1963 x 1455 mm`, and import into SolidWorks.
- Key API pitfall: `OpenDoc6()` failing on OBJ/STL does not mean the file is corrupted; passing `None` to `LoadFile4()` also fails. Pass an empty Dispatch variant.
- Material lesson: OBJ is far more likely than STL to preserve glass, tail lights, interior, and wheel finishes; keep STL as a geometry-only fallback.
- Review lesson: an automated `pass` score does not mean it looks like the target vehicle. Always open preview images and visually check brand-defining features, proportions, and stray floating parts.
