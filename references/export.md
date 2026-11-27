# File Export Reference

## Supported Export Formats

| Format | Extension | Requires ExportData | Description |
|---|---|---|---|
| STEP | `.step` `.stp` | No | Universal 3D exchange format |
| IGES | `.igs` `.iges` | No | Legacy exchange format |
| STL | `.stl` | No | 3D printing / mesh |
| Parasolid | `.x_t` `.x_b` | No | High-precision kernel format |
| PDF | `.pdf` | Yes (`IExportPdfData`) | Engineering drawing export |
| DXF/DWG | `.dxf` `.dwg` | No | 2D drawing / flat pattern |
| 3D PDF | `.pdf` | Yes | Embedded 3D PDF |
| eDrawings | `.eprt` `.easm` `.edrw` | No | Lightweight viewing format |

## SaveAs Error Codes

| Value | Name | Description |
|---|---|---|
| 0 | swGenericSaveError | Generic error |
| 1 | swReadOnlySaveError | Read-only file |
| 2 | swFileNameEmpty | Empty file name |
| 3 | swFileNameContainsAtSign | File name contains `@` |
| 5 | swFileSaveFormatNotAvailable | Format not available |
| 6 | swFileSaveAsDoNotOverwrite | Do not overwrite existing file |
| 9 | swFileSaveAsInvalidFileExtension | Invalid file extension |

## SaveAs Warning Codes

| Value | Name | Description |
|---|---|---|
| 1 | swFileSaveWarning_RebuildError | Rebuild error |
| 2 | swFileSaveWarning_NeedsRebuild | Model needs rebuild |
| 4 | swFileSaveWarning_ViewsNeedUpdate | Views need update |

## STL Export Quality Settings

```python
# 设置 STL 输出质量
# swUserPreferenceIntegerValue_e.swExportStlUnits = 78
model.SetUserPreferenceIntegerValue(78, 0)  # 0=Fine, 1=Coarse

# 设置自定义偏差和角度
# swSTLDeviation
model.SetUserPreferenceDoubleValue(0x00000F, 0.005)  # 偏差（米）
# swSTLAngleTolerance
model.SetUserPreferenceDoubleValue(0x000010, 0.174)  # 角度容差（弧度，约10°）
```

## Batch Conversion Example

```python
import os
from sw_connect import open_document

def batch_convert(sw, input_dir, output_dir, input_ext=".sldprt", output_ext=".step"):
    """批量转换目录下的所有文件"""
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(input_ext):
            input_path = os.path.join(input_dir, filename)
            base = os.path.splitext(filename)[0]
            output_path = os.path.join(output_dir, base + output_ext)

            # 打开；STEP/STP/IGES/IGS 会自动走 LoadFile4(..., "r", ...)
            errors = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            warnings = VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            model = open_document(sw, input_path, silent=True)

            if model:
                # 导出
                model.Extension.SaveAs(output_path, 0, 1, None, errors, warnings)
                sw.CloseDoc(model.GetTitle())
                print(f"已转换: {filename} -> {base + output_ext}")
```

## Auditable Batch Export

`scripts/sw_export.py::batch_export_formats()` supports multiple inputs and multiple output formats, recording the following for each output:

- SolidWorks API return value;
- File existence and byte size;
- Whether the file signature changed during this run;
- Whether the source document was already open by the user.

By default, it neither overwrites existing files nor closes SolidWorks documents that were already open by the user. When identically named source files would collide on the same target output name, it blocks immediately instead of letting the last writer overwrite the previous result.

## Pack and Go

`scripts/sw_delivery.py::pack_and_go()` uses native SolidWorks `IModelDocExtension.GetPackAndGo()`, `IPackAndGo.SetSaveToName()`, and `IModelDocExtension.SavePackAndGo()`. These signatures have been cross-checked against local SolidWorks 2024/2026 Interop assemblies, type libraries, and official API Help.

Compatibility note: Both official docs and Interop expose `GetPackAndGo()` as a zero-argument method returning `IPackAndGo`; however, local SW2024/2026 + `pywin32` runtime objects can raise "Parameter not optional." The wrapper tries the official `pywin32` zero-argument path first, then falls back to `comtypes` early binding for native Pack and Go while preserving the `pywin32` error context. `comtypes` prefers attaching to an active instance and only exits an instance if it confirms that instance was spawned by this fallback.

Safety boundaries:

1. The active document must already be saved to disk.
2. Non-empty target directories are rejected by default; proceed only with explicit `overwrite=True`.
3. Pre-save enumeration from `GetDocumentNames()` is not treated as the final success criterion; `SavePackAndGo()` runs first, followed by dependency auditing against actual files written in this run and `GetDependencies2`. `AddExternalDocuments` is for external attachments, not for patching missing native assembly parts.
4. Returns per-file sizes, SHA-256 hashes, and `produced_this_run`; never marks success if status codes are non-zero, no real files were written this run, or staged source files are missing.
5. Across three consecutive regression runs on local SW2026 SP01.1, both pre-save native enumeration and actual output contained 1 `.SLDASM` and 2 `.SLDPRT` files, with `document_count=3`, status codes all 0, `missing_dependencies=[]`, and no staging fallback used.
6. If another version or complex assembly still misses dependencies on disk, the default `fallback_policy=stage_dependencies` builds a staged package using `GetDependencies2` with `backend=solidworks-native+staged_dependencies`, `status=pilot`, and `cadstudio-pack-manifest.json`; use `fallback_policy=blocked` for strict native semantics.
7. Regardless of mode, external references, Toolbox components, configurations, suppressed components, and associated drawings still require manual spot checks.

When dependencies are missing in strict mode, stable gate fields are returned: `status=blocked`, `stage=review`, `error_code=SW_PACK_AND_GO_DEPENDENCY_ENUMERATION_INCOMPLETE`. The default staged mode returns `status=pilot` and `error_code=SW_PACK_AND_GO_NATIVE_ENUMERATION_INCOMPLETE`, indicating the package is deliverable but is not a pure native Pack and Go and requires manual review.

Before exporting each format in batch export, the source document is activated and `ActiveDoc.GetPathName()` is read back. This is necessary because SW2024 exporters such as STL may export the active document even when `IModelDoc2.Extension.SaveAs()` on a different document returns success; stop immediately on path mismatch to avoid accidentally exporting an assembly component as the target part STL.

## Coordinate Rules for Split-STEP Reassembly

When splitting a complex STEP/Compound into multiple STEP files for reliable SolidWorks import, do not assume sub-parts remain positioned at their local origin in SolidWorks. Some exporters preserve original absolute coordinates; in that case, `AddComponent5(..., x=0, y=0, z=0)` may place every sub-part by its bounding-box center at the assembly origin, causing all components to pile up on top of each other.

It is recommended that the manifest also store:

- `label`: Stable component name.
- `step`: Sub-part STEP file path.
- `color_hex`: Expected color.
- `bbox.center_mm` / `bbox.center_m`: Global bounding-box center of the sub-part prior to export.
- `bbox.size_mm`: Used to verify scale after import.

Insert components at `bbox.center_m` during assembly, and spot-check the overall assembly bounding box, key component transforms, and four-view previews before saving.

```python
center = item["bbox"]["center_m"]
component = add_component(
    assembly,
    item["native_path"],
    x=center[0],
    y=center[1],
    z=center[2],
    sw=session.sw,
)
```

Verification focus:

1. Overall assembly envelope dimensions (vehicle, frame, housing, etc.) should closely match the original STEP.
2. Do not validate component count alone; counts and color readbacks can still pass even when all components are stacked at the origin.
3. `run_review()` results must be paired with PNG/BMP visual inspection.
