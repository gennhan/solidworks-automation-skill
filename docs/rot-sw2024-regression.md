# Optional ROT Attachment Fallback: SW2024 Native Regression

## Environment and Candidate Identity

- Windows, SolidWorks 2024 SP0.1, `RevisionNumber = 32.0.1`.
- Exactly one version-explicit, already-running target instance was present during verification, with a visible window.
- Backend is Python COM with versioned ProgID `SldWorks.Application.32`; attached to an existing user instance rather than launching a new exclusive instance or taking exit ownership.
- Tested `scripts/sw_connect.py` SHA-256: `1fc00d022d41b345bc3d619c3b3aa76bbed73ed2bb7640ad5016fdae79b604f3`.
- Versioned `GetActiveObject` was naturally unavailable on this machine; no ROT lookup fault was injected.
- Raw reports remain local; this document contains only a sanitized summary with no PIDs, document identities, or machine paths.

## Actual Results

| Entry Point | `SW_ATTACH_EXISTING_DISPATCH` | Result |
|---|---|---|
| Direct Python API | Unset | Returned `SW_INSTANCE_NOT_READY`; connection call did not invoke `Dispatch` |
| Direct Python API | `1` | Attached to original PID via real versioned `Dispatch`; `started_by_cad_studio=False` |
| Newly launched MCP stdio server | Unset | `solidworks_connect` returned `SW_INSTANCE_NOT_READY` |
| Newly launched MCP stdio server | `1` | `solidworks_connect` attached to original PID and read back year 2024 |

After every test group, the process list, open document list, active document identity, and window visibility were verified unchanged. The test created a dedicated empty part and marked it unsaved; after the connection and MCP client exited, that document remained open and unsaved, and the SolidWorks instance was not terminated. After verification finished, only this dedicated test document was closed without saving, restoring the original blank session.

Creating the observation snapshot in the test script performs one additional real versioned `Dispatch` and also verifies its PID, version, and process list; this setup call is not counted in the "connection call" totals in the table. This does not constitute a general guarantee that the constructor is side-effect-free.

## Reproduction

Run from the repository root using a Python environment with project dependencies installed. First verify that a single instance of the target version is running; when using `--create-test-document`, that instance must also have no open documents. The output directory must not exist.

```powershell
python tests/manual_rot_attachment.py --version 2024 --create-test-document --output outputs/rot-native-new-run
```

Without `--create-test-document`, the script only verifies the existing document state. It does not save documents or exit SolidWorks; if verification aborts midway, the dedicated unsaved document may remain open and should be handled after inspecting the report and window.

The script spawns an isolated MCP server with temporary process environment variables without altering user configuration. If natural ROT is available, the script additionally injects a ROT lookup failure for the direct API while still executing a real `Dispatch`; the report distinguishes this clearly via `controlled_rot_failure`. MCP results reflect the natural environment without fabricating ROT failures.

## Verification Boundaries

- SW2026 was not tested here; this record does not claim to meet the project's SW2026 native acceptance target.
- Rejection paths—such as unknown version, multiple instances of the same version or ambiguous target when version is unspecified, mismatched PID, version mismatch, or changed/unreadable process lists—are covered by offline tests rather than manufactured on a live machine.
- `Dispatch` may launch an additional instance in some installations. The fallback is disabled by default; on identity mismatch, subsequent operations halt without taking exit ownership of the unknown instance and without auto-retrying. Inspect running instances and unsaved documents first.
- This option provides an explicit opt-in recovery path and does not fix the Windows ROT mechanism.
- This run did not verify model geometry, assembly mates, interference, exports, motion, loads, or manufacturing release, nor did it test save-and-reopen on existing models. It verifies only connection behavior, document-state preservation, and session state after client exit, and does not indicate upstream CI passage.

Subsequent documentation revisions only added docstrings to the manual script and this note; the script's AST with docstrings stripped remained identical and the production file hash remained unchanged, so the live-machine record above remains valid without re-running CAD for text-only edits.

## Combined Check with the Rib-Fix PR

Based on common upstream commit `36bc337357723b9763759ff06e4a1afab990b823`, combined with `783319a6583e195e5cf1499ff1ae4ef4151a1c4d` from [Rib Fix PR #83](https://github.com/wzyn20051216/solidworks-automation-skill/pull/83): the two changes have no overlapping files, apply cleanly in either order, and yield the exact same Git tree. All 61 regression tests covering the rib wrapper, connection ownership, document identity, and release contract passed on the combined result.

This is an offline integration check and does not execute a live-machine CAD regression of the combined version; it does not replace each PR's individual SW2024 record, nor does it represent SW2026 or upstream CI verification. Conclusions apply only to the commits listed above and must be re-evaluated after further upstream or branch changes.
