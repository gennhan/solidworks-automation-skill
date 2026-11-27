# Custom-Property-Based Rename Preview (pilot)

This entry point reads file-level custom properties and generates a rename plan only; it does not rename, move, or overwrite SolidWorks files, nor does it update external references in assemblies or drawings.

```powershell
python scripts/sw_file_rename.py C:\work\parts --template "{图号}_{名称}" --output C:\work\rename-plan.json
```

Templates accept simple property placeholders only; missing properties, illegal Windows filenames, collisions with existing filenames, and duplicate target names within the plan are all marked `blocked`. Output reports are created exclusively without overwriting existing files, and results always require human review (CLI exit code 2). Scanning covers `SLDPRT`, `SLDASM`, and `SLDDRW` files in the target directory without recursing into subdirectories or following symbolic links.

Verified on SolidWorks 2026 SP1.1: single-part file-level property reading, preview name generation, and leaving pre-existing open documents untouched. Scanning skips SolidWorks temporary lock files starting with `~$`.

## Creating a Renamed Assembly Copy (SolidWorks 2026 Pilot)

`scripts/sw_assembly_rename.py` copies the root assembly and its entire reference closure into a brand-new directory and updates references on the closed copies; it neither modifies source files nor updates references to the source files inside other documents. Input `plans` must include the root assembly and all direct and indirect dependencies, with each entry specifying `source`, `new_name`, and `status`. All source filenames must be unique, and all target filenames must be unique and distinct from every source filename.

```powershell
python scripts/sw_assembly_rename.py --root C:\work\top.sldasm --plan C:\work\rename-plan.json --output-dir C:\work\new-assembly-copy
```

This pilot supports only single-configuration assemblies, fully resolved non-virtual components, and single-configuration, single-body non-Toolbox parts without external references. Drawings, suppressed components, multiple configurations, and Toolbox parts are unsupported. The executor audits reference closure, file hashes, component paths and transforms, part geometry, and mate health; every mate is checked individually for associated component instances, reference types, geometric parameters, and persistent entity IDs in component documents, blocking on any unresolvable mate. Assembly-context persistent IDs embed rename context and cannot be compared directly—they must first be mapped back to component documents via `GetCorresponding2`. `mate_reference_checks` in the manifest reports mate and reference counts per assembly. These checks cannot prove arbitrary motion cases or all mate design semantics. On failure, the output directory and `assembly-copy-manifest.json` are preserved for inspection—never treat an incomplete copy as a success. Passing runs remain marked `review_required` and must be verified for design intent and external documents in the target project.

## Copying Standalone Parts Under New Names

For saved `SLDPRT` files that have exactly one configuration, one solid body, an empty dependency list, zero standard external references, and zero auxiliary external references, the preview plan can be executed into a **new, non-existent directory**:

```powershell
python scripts/sw_rename_copy.py --plan C:\work\rename-plan.json --output-dir C:\work\new-copies
```

New files are created via exclusive creation and byte-for-byte copying; every entry checks source vs. copy SHA-256 and reopens in SolidWorks to verify volume, bounding box, and body count. Source files remain untouched, `copy-manifest.json` is written, and results stay `review_required` (CLI exit code 2). Execution halts immediately on failure, leaving already-created files and the manifest for inspection without auto-deleting or retrying. The target directory must not exist yet, while its parent directory must already exist. Maximum 100 parts per run.

This entry point does not handle assemblies, drawings, multi-configuration parts, multi-body parts, or parts with detected external references, nor does it update references to the source part from other files. An empty reference check does not prove no hidden external references exist—engineers must still verify copies, and this must never be used as a reference-safe rename for assemblies. SW2026 SP1.1 has verified two-part property preview, source hashing, copying, and reopen checks; other SolidWorks versions have not yet been live-tested.

Standalone copies are used instead of in-place renaming because in local SW2026 testing, `SavePackAndGo` still mutated the source file even when opened read-only, and assembly Pack and Go manifests omitted two actually present components. The standalone part entry point continues to block parts with references; the assembly copy entry point performs reference replacement only within the constrained scope above. See official [`GetDependencies2`](https://help.solidworks.com/2025/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IModelDoc2~GetDependencies2.html) and [`ListExternalFileReferencesCount`](https://help.solidworks.com/2023/English/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IModelDocExtension~ListExternalFileReferencesCount.html) docs.

This command shares an inter-process mutex lock with tolerance extraction and live hole-position analysis entry points; other clients, legacy commands, and manual GUI actions are not protected by this lock, so avoid modifying or closing documents while they are being read.

Implementation direction references community contribution [PR #36](https://github.com/wzyn20051216/solidworks-automation-skill/pull/36).
