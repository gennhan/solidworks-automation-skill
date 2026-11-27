# Native Rib Wrapper Fix: SW2024 Regression Evidence

This verification covers the 10-argument call in `sw_part.rib()`, detection of newly added features after a `VOID` return, and legacy single-sided/two-sided thickness flags. A simple right-angle bracket is used to isolate the wrapper behavior without relying on specific shift-fork surface-blending geometry.

## Environment and Reproduction

- Windows 11, SolidWorks 2024 SP0.1 (Revision 32.0.1).
- Backend is Python COM with versioned ProgID `SldWorks.Application.32`; no CAD process was running beforehand, and the test launched an exclusive visible instance for the run.
- Verified production file `scripts/sw_part.py` SHA-256: `04f2d407b00d54357a3b9438bc4ce2f5f4a0a0c14ecb455297c4a21ad7db3423`.
- Script: [tests/manual_rib_regression.py](../tests/manual_rib_regression.py). Run in an environment with no other SolidWorks processes; the output directory must be new:

```text
python tests/manual_rib_regression.py --version 2024 --output ./output/rib-native-r01
```

The script launches a visible session and operates only on documents newly created during the run; on success it saves and closes those documents while leaving the application window open. It refuses to start if an existing process or the output directory already exists. The script outputs `native-report.json`, standalone native parts, and previews; results still require visual inspection per the report flags.

## Actual Results

The bracket consists of an 80×10×40 mm base and a 10×50×40 mm upright plate, with a base volume of 52,000 mm³. The rib profile is a right triangle with a 40 mm base and 30 mm height, giving an expected added volume of 3,600 mm³ at 6 mm thickness.

| Check | Actual Result |
|---|---|
| Default two-sided, 6 mm thick | Native Rib definition `IsTwoSided=True`, side faces at Z = −3 and +3 mm, added volume ~3,600 mm³ |
| Explicit single-sided, 6 mm thick | `IsTwoSided=False`, side faces at Z = 0 and 6 mm, added volume 3,600 mm³ |
| Real sketch selection | Used wrapper sketch reference and actual selection path without replacing `_ensure_sketch_selected`; sketch passed fully defined check |
| Detection after VOID return | Returned the newly created Rib feature rather than an empty COM return |
| Creating a second rib on a part with an existing rib | Created a 4 mm thick second rib on the Z = 12 mm plane, returned the new feature, preserved the original rib; actual side faces at Z = 10 and 14 mm |
| Second rib geometry and persistence | Added volume 2,400 mm³; after save, close, and reopen, both Ribs remained, total volume 58,000 mm³, thickness definitions and side-face positions preserved |
| Non-intersecting failure | Moved rib sketch plane to Z = 100 mm; wrapper returned `None`, existing ribs were not mistakenly returned, rib count and solid volume unchanged |
| Normal model health and teardown | Single solid body, zero feature errors, warnings, or unknown states after rebuild; model previews visually inspected; 0 open documents at finish |

The final full manual regression run took approximately 52.60 seconds. This measures only the test script runtime in a prepared environment, not new-problem drawing interpretation or end-to-end modeling performance.

## Boundaries

This verifies only SW2024 SP0.1 and the standard bracket scenarios above (single/two-sided, pre-existing rib, and one non-intersecting failure case); it does not claim to cover all failure states or fix geometry issues on a specific shift fork. SW2026 was not tested here, and the capability matrix was not promoted. Normal save-reopen and preview checks were completed; the non-intersecting case retains an unconsumed sketch for diagnostic purposes and is not delivered as a passing part.

This run did not verify assembly mates, assembly interference detection, free dragging, continuous sweep, contact dynamics, loads, Motion Study, or manufacturing release; single-body rib feature results cannot serve as evidence for those capabilities. All test documents were saved and closed while keeping the run-launched visible application instance open for observation; this does not claim zero remaining CAD processes after exit. Local native checks also do not indicate that upstream CI has passed.

Subsequent documentation revisions only added docstrings to the manual script and this note; the script's AST with docstrings stripped remained identical and the production file hash remained unchanged, so the live-machine record above remains valid without re-running CAD for text-only edits.

Native files, raw reports, and previews remain in local test output and are not committed. This document retains only a sanitized result summary without local identities, paths, PIDs, or private models.
