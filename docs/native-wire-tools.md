# Native Round-Section Paths and Mechanical Import (Pilot)

These tools use the local SOLIDWORKS PIA and do not execute caller-supplied code. Every operation requires the full path of a saved target document and the PID selected by the host MCP, serialized through the host operation lock. No new SOLIDWORKS instance is launched. Native child processes prefer the PID-named ROT entry; for 2026 instances that only register the standard active object, fallback must still verify the exact same PID and refuse to attach to any other instance.

- `solidworks_inspect_native_geometry`: Reads body names, volumes, bounding boxes, and component transforms.
- `solidworks_build_round_sweeps`: Builds native round-section sweeps inside an empty saved part. Paths are 2-point lines or 3–6 point Bezier curves; JSON numeric values are validated and converted to equations without accepting arbitrary expressions. Can also create standalone rectangular extrusions. Run `dry_run=true` first. Requires millimeter units and verifies measured path length, rectangular bounding boxes, and rebuild health. Does not auto-save.
- `solidworks_import_step_part`: Imports into a new multi-body SLDPRT; restores global import options, refuses to overwrite, and returns each body for review. The original target document is not saved.
- `solidworks_replace_component_preserving_transform`: Supports only a single unique fixed instance; preserves transforms and other component references without saving.
- `solidworks_exclude_reviewed_bodies`: Creates a `DeleteBody` feature using exact reviewed body names, preserving original import history without saving.

## Specification

```json
{"sweeps":[{"name":"Wire1","control_points_mm":[[0,0,0],[0,3,0],[3,5,0],[5,5,0]],"diameter_mm":0.9,"color":[1,0,0]}],"boxes":[]}
```

Failures may leave unsaved partial features that must be reviewed rather than blindly retried. Existing features are never overwritten or deleted. Models provide geometry only and do not prove wire harness manufacturability, crimp fit, insulation performance, pull-out force, or a native SOLIDWORKS Routing license.

The `save_requested` field in the result indicates whether the operation requested a save. Inspection, dry-run, sweep, replace, and body-exclusion operations do not return `saved=false` to indicate a save failure; a STEP import that saves successfully returns `save_requested=true, saved=true`. Actual save failures still return an execution error, and manual review requirements remain in place.

MCP and native child processes exchange JSON over UTF-8 standard input with a 1 MiB request cap, so 64 high-precision paths and non-ASCII paths do not consume Windows command-line length. Short requests retain `-InputBase64` compatibility.

Verification: input-rejection tests do not launch CAD; real SOLIDWORKS version and operation evidence should be recorded separately. This capability is currently in pilot status and requires geometric and visual review prior to release.

## Live-Machine Verification

Original author record (SOLIDWORKS 2026 SP4.1 / Python 3.10): Verified sweeps and extrusions for 38 independent bodies, multi-body STEP import, targeted body exclusion, fixed-component replacement, and save-and-reopen. Path lengths, box extents, and component transforms were read back; exported bodies passed auxiliary B-Rep checks. 8 input tests passed; 42 target-document/process integration regressions and 23 subtests passed. Other SOLIDWORKS versions were not tested. Capability remains pilot.

Maintainer review (2026-10-17, SOLIDWORKS 2026 SP01.1, Revision 34.1.1 / Python 3.12): Completed line/Bezier sweeps, rectangular extrusion, multi-body STEP import, body exclusion, fixed-component replacement, and save-and-reopen via real MCP-registered tools, PowerShell, and local PIA. Measured line length was 10 mm; measured Bezier length was 17.216903638 mm vs. theoretical sampled length 17.216903179 mm; box volume was 500 mm³. Confirmed that operations without a save request did not modify files on disk, and all three global import options were restored. The test closed only the documents and processes it created.

After installing test dependencies and confirming no user CAD instances are running, you can run the live-machine regression manually. The second argument must be a non-existent output directory; the script launches its own 2026 instance, creates isolated test models, and writes a JSON report and BMP previews. This script is excluded from automated `pytest` collection and will not launch CAD in standard CI.

```powershell
python tests/manual_native_wire_2026.py "E:\path\solidworks-automation-skill" "E:\cad-tests\native-wire-new-run"
```

Body RGB values are returned with the review results and read back immediately after creation. AP203 exports do not contain color; previews may use verified body RGB values, but must record the color source and must not claim that AP203 contains appearance data.

Live-machine body color readback exhibits 8-bit quantization (for example, input `0.70` reads back as `178/255`), so color acceptance permits a tolerance of one 8-bit step; this does not relax geometric dimension checks.
