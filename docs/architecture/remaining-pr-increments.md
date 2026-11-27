# Incremental Fixes for Remaining PRs (2026)

Baseline main: `f7de34f`. This batch applies Scheme B to PRs #8, #11, #23, #24, and #25 while preserving verified interference checks, Queue, Reviewer, Artifact Ledger, and MCP tool names and input contracts. Native acceptance scope is SolidWorks 2026.

| Source | Current Implementation |
|---|---|
| #8 | Path imports were already covered by `9d19194`; this round enumerated the 2026 Motion type library directly and handled the original PR per overlap |
| #11 | Reused existing light/dark SVGs and update workflow, restoring README embeds without reintroducing dependencies on external dynamic chart services |
| #23 | Ported the original author's short-lived fallback process approach, verifying PID/2026 version, binding to the parent instance, and blocking explicitly on unknown/timeout; retained main's accurate per-pair interference volumes; enhanced feature errors/warnings, empty views, degenerate bounding boxes, and file-load diagnostics |
| #24 | Retained the original author's host-guard commits and enforced strict HTTPS, host, port, URL-credential, and commit-path checks at the actual request boundary; rejected redirects, enforced bounded reads, and verified SHA-256 before writing cache |
| #25 | Retained the original author's host-guard commits, completed `PATH` fallbacks across all four Agents while preserving explicit user overrides; enforced consistent canonical path checks across JSON/SQLite and bounded JSON reads; preserved explicit fake-credential fixtures |

The Pack and Go child process is a one-shot COM marshaling backend, not a new resident service. Ownership depends on actual PID rather than whether `CreateObject`/`Dispatch` returns an object; unknown snapshots, missing target documents, PID mismatches, or timeouts all block so a second staging/retry pass cannot overwrite unconfirmed outputs. Because the 2026 manifest depends on the active document, the fallback explicitly activates the specified source file and verifies the returned document path.

Because `comtypes` raises `KeyError(9)` when marshaling document arrays on this host, the fallback retrieves the manifest read-only via a same-PID `pywin32` observer while keeping actual writes isolated in the child process. Only documents explicitly opened during the run are closed; pre-existing source files and user unsaved documents are never owned by the child process.

Errors and warnings map to the two official local SDK enums separately, preserving raw numeric codes while feeding stable machine error codes into Core/MCP. `GetErrorCode2` distinguishes warnings from errors; incomplete evidence still triggers human review.

Verification and boundaries:

- On 2026 SP1.1, forced `comtypes` fallback packaged an assembly and two parts; after save and reopen, both references pointed to the delivery directory; parent proxy, unsaved documents, and open document list were preserved, and the test instance cleaned up cleanly.
- Standalone fault cases cover ownership, timeouts, JSON/UTF-8 handling, error/warning bitmasks, download redirects and pinned commits, Agent name compatibility, and config paths.
- On 2026 SP1.1, all 23 top-level features of a healthy part read back healthy, review passed, and four real BMPs were generated; an empty drawing failed review; a corrupted SLDPRT returned raw error bitmask `2097152`, classified as `SW_FILE_REQUIRES_REPAIR`. Open document list was empty afterward.
- Full local Python suite: 854 passed; Core/Eval with COM imports disabled: 125 passed; all 61 MCP tool names and input schemas matched baseline exactly; Skill/MCP/release consistency checks passed with 220 bundled runtime files.
- Frontend: 9 tests and production build passed. Toolchain security advisories surfaced during acceptance; Vitest was upgraded to patched 4.1.11 and `source-map-js` to 1.2.2, returning zero audit alerts. Only affected versions and lockfiles were modified without altering app behavior.
- Real STEP download from the pinned FreeCAD GitHub commit retrieved 132,515 bytes with SHA-256 matching the manifest; cache, invalid origin, and tampered content are covered by offline failure cases.
- Because this host lacks privileges to create file symlinks, that Rust branch is not claimed locally verified; GitHub CI prohibits silent skipping of that branch and executed and passed the out-of-bounds symlink rejection test. Canonical path checks do not claim to constitute a full OS filesystem sandbox against same-privilege attackers.
- Security scanner advisories do not automatically equate to exploitable vulnerabilities; XML rejection resides in the SVG test parser and does not claim new production XML parsing capabilities.
- No duplicate interference tool was added; existing `solidworks_interference_check` is reused and MCP stays at 61 tools.

These increments do not constitute full mold tooling, moldflow, design-review certification, or legacy-version compatibility guarantees. Final test/CI outcomes accompany the integration PR acceptance record.

Toolchain advisory references: [Vitest Security Advisory](https://github.com/vitest-dev/vitest/security/advisories/GHSA-82fw-gwwq-j7x9), [source-map-js Security Advisory](https://github.com/advisories/GHSA-68fv-2mgg-jv7q). These advisories pertain to dev/test/build dependencies and do not imply the shipped CAD application was compromised.
