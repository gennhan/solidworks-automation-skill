# SolidWorks 2026 Regression for the Rib Feature Fix

After integrating PR #83 onto main (`fbaf604`), the production script was verified on SolidWorks 2026 SP1.1 (Revision `34.1.1`). The SHA-256 of the tested `scripts/sw_part.py` is `5661ebb75bee0a8c11a2e31acee078111c3dc7d3ae90e0782a56e5d5034ea066`.

Live-machine verification invoked `run()` in `tests/manual_rib_regression.py`, with an exclusive blank session managed by `SolidWorksSession(version=2026, wait_seconds=60, visible=True)`. Sketch selection, `InsertRib`, geometry readback, and save-and-reopen were all executed as real COM operations.

| Scenario | Result |
| --- | --- |
| Two-sided, 6 mm thick | Side faces at Z = −3 and 3 mm, added volume ~3,600 mm³ |
| Single-sided, 6 mm thick | Side faces at Z = 0 and 6 mm, added volume 3,600 mm³ |
| Creating a second rib in a part with an existing rib | Returned the second rib; original rib preserved, 4 mm thick, side faces at Z = 10 and 14 mm |
| Second rib persistence | Both ribs and their thickness definitions persisted after save, close, and reopen; total volume ~58,000 mm³ |
| Non-intersecting sketch | Returned `None`; existing rib count and solid volume remained unchanged |
| Model health and teardown | No feature errors, warnings, or unknown states after rebuild; 0 open documents at finish, run-launched instance exited |

Native previews for single-sided, two-sided, and dual-rib models were visually reviewed. Native models, previews, and raw reports remain local; the public record contains sanitized results only.

The original manual entry point can be re-run from an exclusive blank session. The output directory must not exist; the script itself leaves the application window open for observation.

```powershell
python tests/manual_rib_regression.py --version 2026 --output output/rib-sw2026-new-run
```

This verification covers the right-angle bracket and failure path described above. Complex rib profiles, assemblies, motion, and manufacturing release require separate task-specific verification. See [rib-sw2024-regression.md](rib-sw2024-regression.md) for the contributor's SW2024 record.
