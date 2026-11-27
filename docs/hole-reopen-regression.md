# Issue #82: Reopened-Part Through-Hole Diagnostics and Regression

## Current Conclusion

The [original report](https://github.com/wzyn20051216/solidworks-automation-skill/issues/82) targets SolidWorks 2024 build `32.5.0`, project `v2.1.1` / `36bc337`. The report states that the same hole wrapper succeeds on a newly created part, whereas `FeatureCut4` returns empty on a reopened part, while a bare sketch cut at the same coordinates succeeds.

The issue lists scripts, outputs, and part filenames, but currently includes no downloadable attachment links; the local machine only has SolidWorks 2026. **The SW2024 root cause is not yet confirmed, and passing the 2026 regression must not be described as resolving #82.** This batch does not modify cut direction, end conditions, sketch selection strategy, or auto-retry behavior, and does not close the original issue.

## Deliverables

- Raises `HoleFeatureCreationError` (compatible with `RuntimeError`) when a circular hole cut returns empty, preserving the original error prefix and attaching `SW_HOLE_NOT_CREATED`.
- Performs a read-only post-failure readback of selection count, whether a sketch is still being edited, body count, sketch entity and contour counts, and the requested plane, sketch, depth, and fixed-direction semantics.
- MCP preserves structured `diagnostics` with an explicit `retryable=false`. If reading an individual COM diagnostic member fails, `null` is recorded without masking the original failure.
- Diagnostic state is explicitly marked `after_failed_cut`, rather than a pre-call selection snapshot. Read failures are not inferred as "no bodies" or "no sketch".
- Does not save, delete the failed sketch, or repeat the cut; diagnostics exclude document paths, PIDs, and model geometry.

## Repeatable Native Acceptance

Run in a single, version-explicit, blank SolidWorks session, or let the script launch a dedicated instance for the run. The output directory must not exist beforehand:

```powershell
python tests/manual_hole_reopen.py --version 2026 --output output/hole-reopen-new-run
# 在 SW2024 原环境采集相同矩阵，不代表本轮已执行：
python tests/manual_hole_reopen.py --version 2024 --output output/hole-reopen-2024-new-run
```

The script creates an 80×60×20 mm plate, using both a blank plate and a plate with one existing 6 mm through-hole as baselines. It compares the wrapper on a new part, the wrapper after save-and-reopen, reopening with the sketch cache cleared, a bare sketch cut, and reopening plus invoking the hole tool via standalone MCP stdio. Every successful call verifies an actual solid volume change of approximately `565.486678 mm³`, along with rebuild health, a second save-and-reopen cycle, and native previews.

A non-intersecting hole is also used to verify failure diagnostics and confirm that solid volume remains unchanged. The script cleans up only the test artifacts registered during the run; exiting user-started instances is outside the script's ownership.

## Current SW2026 Results

In SolidWorks 2026 SP1.1 (`34.1.1`), all 10 successful comparison cases above passed, with actual solid volume changes for the newly added hole ranging from `565.486677646157` to `565.486677646171 mm³`, matching the calculated value for a 6 mm hole through a 20 mm plate. Existing holes were preserved; results created via standalone MCP maintained accurate volume after save-and-reopen, with no rebuild errors, warnings, or unknown states. Native previews for both single-hole and dual-hole models were visually inspected.

Both the direct API and standalone MCP returned the new diagnostics for the non-intersecting hole: selection count 1, not in sketch-edit mode, 1 solid body, 1 sketch entity, and 1 contour; MCP read back `SW_HOLE_NOT_CREATED` and `retryable=false`. Solid volume remained unchanged after failure, with no automatic retry. Upon completion, run-owned documents were closed, the self-launched process exited, and the process list returned to its original state.

SHA-256 of tested production files:

- `scripts/sw_part.py`: `5661ebb75bee0a8c11a2e31acee078111c3dc7d3ae90e0782a56e5d5034ea066`
- `scripts/sw_hole_features.py`: `248ed52385728e57806f35d21c255d39243e7182cc9e000493c8f1701dbf1eca`

Original models, BMPs, and reports remain local; this record contains no machine paths or PIDs. This verifies the 2026 regression and diagnostic functionality, not proof of a fix for the original SW2024 failure.

## Follow-up Root-Cause Gate

The original report's `repro_hole_bug.py`, outputs, and `repro_plate.SLDPRT` are needed to reproduce the issue on SW2024 `32.5.0`. Key points to compare include: actual sketch references before and after creation, selection sets, sketch-plane-to-body intersection direction, and the actual parameters and document identity between the wrapper and bare calls.

The official [FeatureCut4 documentation](https://help.solidworks.com/2024/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.ifeaturemanager~featurecut4.html) distinguishes `Sd`, `Dir`, end conditions on both sides, and body scope. An empty return alone is insufficient to determine root cause; do not reverse cut direction based on version year, and do not mask failures with unbounded retries.

## Offline Regression Record

Running `python -m pytest -q` on the standalone diagnostics branch based on `524a4a3`: 1766 passed, 17 skipped, plus two pre-existing dependency warnings. After integrating into main (`ad4b457`) with the ROT fix, re-verification of connection ownership, document identity, hole diagnostics, sketch selection, and release contracts passed all 71 tests:

```powershell
python -m pytest -q tests/test_sw_session_ownership.py tests/test_mcp_hole_diagnostics.py tests/test_sw_hole_features.py tests/test_sw_connect_open_document.py tests/test_mcp_document_identity.py tests/test_mcp_document_binding_integration.py tests/test_sw_part_sketch_selection.py tests/test_release_check.py tests/test_sync_bundled_skill.py
python scripts/validate_skill.py
python scripts/release_check.py
```

Bundled skill sync, integrity, and release contract checks passed; these offline results do not substitute for live-machine acceptance of the original SW2024 failure.
