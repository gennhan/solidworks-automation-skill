# Optional ROT Attachment Fallback: SolidWorks 2026 Acceptance

PR #84 was independently integrated onto main (`524a4a3`), with an additional fix preventing attachment from overwriting `Visible` on an existing window.
`visible` applies only to instances newly launched by the current run; standard ROT, delayed ROT, and optional `Dispatch` attachment all preserve the user's window state.
After fallback, the full PID→version map is compared, and execution is rejected if any version changes or becomes unknown.

## Live-Machine Evidence

- SolidWorks 2026 SP1.1, Revision `34.1.1`.
- Tested `scripts/sw_connect.py` SHA-256: `32aef993532ca1db6eabd5118bdda87474bdeea2812612a20e27a4c077baa460`.
- The run launched its own exclusive instance and then treated it as an existing instance to verify attachment; attachment entry points consistently reported `started_by_cad_studio=False`.
- Verified both a visible window with a dedicated unsaved part and a hidden window with a blank session: 8 cases per group, 16 cases total.
- Both the direct Python API and standalone MCP stdio covered natural ROT and controlled ROT lookup failures, with the toggle both off and on.
- When natural ROT was available, all paths connected to the same PID. Under controlled lookup failure, `Dispatch` was blocked by default with `SW_INSTANCE_NOT_READY`; when explicitly enabled, real versioned `Dispatch` returned the same PID.
- Every case intentionally requested the opposite `visible` state from the existing window; the process list, document list, active document, unsaved flag, and window visibility were all preserved.
- Both the instance and documents remained intact after the MCP client exited; at teardown, the dedicated blank document was closed without saving, and the outermost owner exited the self-launched instance.

Natural ROT worked on this machine, so the failure condition was injected solely by replacing `GetActiveObject`; `Dispatch`, process enumeration, and SolidWorks COM operations executed natively. No claim is made of reproducing a natural ROT failure on this machine.
Raw reports remain local; the public record contains no PIDs or private machine paths. The SW2024 record is the contributor's original report (see [rot-sw2024-regression.md](rot-sw2024-regression.md)) and was not independently re-verified in this run.

## Rerun and Boundaries

Use a single, version-explicit existing instance; the output directory must not exist. The dedicated unsaved test document can only be created in a blank session.

```powershell
python tests/manual_rot_attachment.py --version 2026 --create-test-document --output output/rot-native-new-run
```

When natural ROT is available, the script additionally injects lookup failures for both the direct API and the standalone MCP server; all attachment tests request the opposite visibility parameter. The script itself does not exit SolidWorks. After an abnormal abort, inspect the dedicated unsaved document rather than automatically cleaning up unknown documents.

`SW_ATTACH_EXISTING_DISPATCH=1` remains disabled by default. On other installations, `Dispatch` may launch a new process, and post-hoc identity verification cannot prevent the constructor call itself; on identity mismatch, execution halts without exiting the unknown process or auto-retrying. This feature does not fix Windows ROT and does not constitute modeling, motion, or manufacturing acceptance.
