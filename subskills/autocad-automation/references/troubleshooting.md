# AutoCAD Automation Troubleshooting

## Python Dependencies

Symptom: `ModuleNotFoundError: No module named 'win32com'`

Resolution:

```powershell
python -m pip install pywin32
python -m pywin32_postinstall -install
```

If multiple Python installations exist on the machine, install into the exact same interpreter used to execute the scripts.

## AutoCAD COM Not Found

Symptom: `Invalid class string`, `Operation unavailable`, or `AutoCAD.Application` creation fails.

Resolution:

1. Confirm that the Windows desktop edition of AutoCAD is installed.
2. Launch AutoCAD manually once to complete COM registration and initial setup.
3. Confirm the script is not running in a headless service session, remote non-GUI session, or restricted permission environment.
4. If multiple versions are installed, try the default `AutoCAD.Application` first; if needed, inspect the registry for versioned ProgIDs.

## AutoCAD Is Open but Has No Active Document

Symptom: Connection succeeds, but accessing `ActiveDocument` raises an error.

Resolution: Call `Documents.Add()` to create a new drawing, or explicitly open the target DWG.

## Accessing `Layers` / `ModelSpace` Fails After Creating a New Document

Symptom: Accessing `Layers` on the object returned by `Documents.Add()` raises `AttributeError: Add.Layers`.

Resolution: In AutoCAD 2024 + pywin32 dynamic proxy environments, the return value of `Documents.Add()` may not be a stable `AcadDocument` proxy. Rebind after calling `Documents.Add()`:

```python
app.Documents.Add()
doc = app.ActiveDocument
```

`new_document()` in `scripts/acad_session.py` already implements this pattern.

## `SendCommand` Has No Effect

Common causes:

- Missing trailing newline in the command string.
- Asynchronous command execution causes the script to save immediately before the command completes.
- Localized UI alters command names.
- The command is still waiting for user input.

Recommendations:

- Prefer the COM object model.
- Prefix commands with `_.`, such as `_.ZOOM _E`.
- Explicitly supply all parameters and trailing newlines for every command.
- Wait after sending commands and verify results with `acad_review.py`.

## Save Failures or Overwrite Risk

Resolution:

- Always use absolute paths for output files.
- Create target directories before saving.
- Save a copy before modifying an existing DWG.
- Close any other applications locking the file.
- Log exceptions on failure and do not proceed to export derivative files.

## DXF Export Fails

Symptom: `Document.SaveAs("xxx.dxf")` fails, or AutoCAD returns a garbled COM error.

Resolution: Do not rely on `SaveAs` extension inference for DXF; use `Document.Export(fileBase, "DXF", selectionSet)`. ActiveX `Export` requires a `SelectionSet` parameter even when exporting the entire drawing—create a temporary empty selection set. `export_dxf()` in `scripts/acad_session.py` already wraps this workflow.

## Stray Outer Outlines, Ellipses, Triangles, or Colored Lines in Traced Line Art

Symptoms:

- User screenshots point out extraneous outer geometry ("what is this around the outside?").
- Large arcs or long polylines appear outside a portrait, ellipses/polylines appear on the face, triangles/diagonals appear near logos, or colored wavy lines appear around splashes.
- Review layer counts show non-source-trace layers such as `PORTRAIT_OUTLINE`, `BODY_OUTLINE`, `JERSEY_OUTLINE`, `FACE_FEATURES`, `LOGO_GEOMETRY`, `WATER_SPLASH`, `JERSEY_STRIPE`, `TEXT_LOGO`, `TEXT_BRAND`, or `REVIEW_NOTES`.

Causes:

- To make the image look "closer" to the reference photo, the script manually added outer contours, facial features, logos, water splashes, or placeholder text.
- In CAD, users interpret these enhancement lines as real drawing objects or erroneous construction geometry rather than artistic embellishments.
- In-drawing review notes and scoring text also pollute final ModelSpace.

Resolution:

1. Standard "trace image to CAD" final deliverables must retain only vectorized lines from the original image, such as `TRACE_DARK` and `TRACE_LIGHT`.
2. Delete or turn off all manually enhanced/construction layers; never rely solely on verbal disclaimers.
3. Write review notes, scores, and generation parameters to JSON/Markdown reports rather than final ModelSpace.
4. Include prohibited layers in the verification checklist and enforce 0 entities:

```python
aux_layers = [
    "PORTRAIT_OUTLINE", "BODY_OUTLINE", "JERSEY_OUTLINE",
    "OUTER_GUIDE", "CONSTRUCTION", "FACE_FEATURES",
    "LOGO_GEOMETRY", "WATER_SPLASH", "JERSEY_STRIPE",
    "TEXT_LOGO", "TEXT_BRAND", "REVIEW_NOTES",
]
assert all(layer_counts.get(name, 0) == 0 for name in aux_layers)
```

5. If the user explicitly requests enhancements or reconstruction, place enhancement objects on dedicated layers and state in the final response that they are manual enhancement layers that can be turned off.

Postmortem lessons:

- Do not equate "recognizable" with "manually guessed lines". The primary goal of reference line-art tracing is cleanliness, fidelity, and zero extraneous entities.
- Colored auxiliary layers, wave lines, placeholder text, and construction geometry may technically raise automated similarity scores while undermining user trust.
- Final acceptance criteria must include negative checks: no extra auxiliary layers, no in-drawing note text, and no decorative lines absent from the source image.

## AutoCAD COM Transient Call Rejection or Garbled Errors

Symptoms:

- Batch line drawing or layer creation raises `pywintypes.com_error: (-2147418111, ...)`, often with garbled error text.
- `Layers.Item()`, `Layers.Add()`, or `ModelSpace.AddLine()` intermittently fails, then succeeds on rerun.

Causes:

- Desktop AutoCAD COM is a single-threaded, interactive automation target that is momentarily busy during drafting, regeneration, document opening, or export.
- Concurrent access to the same AutoCAD instance amplifies this instability.

Resolution:

1. Execute AutoCAD COM operations serially; never run review, preview, and drafting in parallel.
2. Add bounded retries with backoff around high-frequency COM calls, especially layer creation, `AddLine`, `SelectionSets`, `Export`, and `SaveAs`.
3. Wait 1–2 seconds after creating or opening a document before rebinding `app.ActiveDocument`.
4. When generating many entities in bulk, call `Regen()` / `live_update()` every few hundred entities rather than too frequently.

Example:

```python
for attempt in range(12):
    try:
        ent = model.AddLine(p0, p1)
        break
    except Exception:
        if attempt == 11:
            raise
        time.sleep(0.08 + attempt * 0.04)
```

## ModelSpace Cannot Be Enumerated Directly

Symptom: `for entity in session.model` raises `TypeError: This object does not support enumeration`.

Cause: Under certain AutoCAD/pywin32 dynamic proxies, `ModelSpace` does not expose a Python iterable interface, though it still supports `Count` and `Item(index)`.

Resolution: Iterate using the `Count` / `Item(i)` pattern in review scripts:

```python
ms = doc.ModelSpace
for i in range(int(ms.Count)):
    entity = ms.Item(i)
```

## `SaveAs` Fails When Overwriting a Currently Open DWG

Symptom: Generation completes, but `SaveAs(target)` reports an error saving the document because the target file already exists or is currently open in AutoCAD.

Resolution:

1. Do not force-overwrite an existing file currently open by the user.
2. Output to a new versioned or semantic filename such as `_approved` or `_trace_only`.
3. Verify file existence and size after saving before proceeding to export DXF/previews.

## `SelectionSets` or `Export` Proxy Exceptions

Symptoms:

- `doc.SelectionSets.Add(name)` raises `AttributeError: <unknown>.Add`.
- `doc.Export(...)` raises `AttributeError: Open.Export` or other proxy misalignment errors.
- DXF or BMP preview export fails independently even though the DWG saved successfully.

Causes:

- AutoCAD is busy, the active document proxy is misaligned, or the COM dynamic proxy has not stabilized immediately after opening a read-only drawing.

Resolution:

1. Execute serially; avoid running `acad_review.py` and `acad_preview.py` simultaneously.
2. Wait after opening a source file, then re-acquire `app.ActiveDocument`.
3. Delete any leftover `SelectionSet` with the same name before creating a new one; retry on failure.
4. If BMP preview fails while DWG/DXF and entity checks pass, explicitly state "native preview export failed" in the final report and present the completed verification evidence—never fabricate screenshots.

## Window Screenshots Occluded or Black

Symptom: OS screenshot succeeds, but the view is covered by another foreground window or yields only a small black image.

Resolution:

1. Window screenshots only prove what is currently visible on the desktop, not that the DWG itself is correct.
2. Prefer exporting a native preview via `scripts/acad_preview.py` using AutoCAD's `Document.Export(..., "BMP", selectionSet)`.
3. Call `Regen()` and `ZoomExtents()` before exporting; inspect borders, views, text, dimensions, and overlaps with an image viewer after export.
4. If an OS screenshot is still needed, confirm the AutoCAD window is unobstructed before calling the screenshot helper; occluded screenshots cannot serve as pass evidence.

## Drafting Process Not Visible

Symptom: The script successfully generates the DWG, but the user cannot see AutoCAD opening or drawing entities step-by-step.

Resolution:

1. Use the default mode of `scripts/acad_draw.py` without `--fast`.
2. Confirm `live_preview` is not set to `false`; the default should be `true`.
3. Call `AutoCADSession.activate_window()` to bring AutoCAD to the foreground where possible, then call `live_update()` after each step.
4. If other desktop windows repeatedly steal focus, step-by-step drawing may still be occluded; in that case, AutoCAD native previews remain the final review evidence.

## SelectionSet Name Conflict

Symptom: Creating a selection set fails because the name already exists.

Resolution: Iterate through `doc.SelectionSets`, delete any `SelectionSet` with the matching name, and then create the new one.

## Bounding Box Read Failure

Some objects, empty objects, or proxy objects do not support `GetBoundingBox`. Review scripts should skip them and log the error rather than failing the entire run.

## Unstable PDF/Plot Output

PDF output depends on plotters, PC3 files, page setups, CTB/STB plot style tables, and background plotting settings. During automation:

- Prefer an existing template's `PageSetup`.
- Disable background plotting or wait for `Plot` to finish.
- Check the output PDF file size afterward.
- Manually open the PDF before critical deliveries to verify borders, orientation, scale, and lineweights.

## Task Instance Falsely Reported as Still Running After Exit

Symptom: The drawing, DWG/DXF, and previews were generated, and `acad.exe` is no longer visible on the system, yet the regression report still states that the task-launched AutoCAD instance did not exit within the timeout.

Cause: Both `Quit()` and `TerminateProcess()` may return before Windows asynchronously finishes tearing down the process object. Checking only once or waiting too briefly misclassifies exit-status propagation delay as a leftover process.

Resolution:

1. Record only the PID launched via `DispatchEx` and resolved from the AutoCAD main window handle; never call `Quit()` or force-terminate when attached to an existing user instance.
2. Politely call `Quit()` first and wait on the exact PID; if that times out, terminate only the recorded task PID, wait again, and perform a final exit-status check.
3. Preserve `owned_process_id`, `quit_requested`, `forced_termination_used`, `process_exit_confirmed`, and cleanup errors in the report; never let CLI exception handlers overwrite the original cleanup evidence.
4. If failures persist, check running processes with `Get-Process acad -ErrorAction SilentlyContinue` first, then investigate using the reported PID; never bulk-kill user AutoCAD instances by process name.
