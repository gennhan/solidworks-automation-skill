# Per-Run Deliverable Freshness Gate

All CAD Studio production tasks require evidence that delivered files were newly created or modified in content during the current run, uniformly across Agent providers, legacy Codex entry points, and local CAD backends.

Before invoking an executor, the worker computes a SHA-256 baseline and uses that baseline when writing the ledger. Self-reported baselines in executor output cannot override the worker's evidence. Standalone Agent runner invocations perform the same scan.

The baseline records file entries, scan root paths and root types (single file or directory), completeness, truncation flags, and scan errors. "File absent from baseline" proves a file is newly created only when the scan completed cleanly, the file extension is covered by the scan, and the file actually lies within the scanned roots. Paths are canonicalized to their real targets; directory junctions/symlinks do not expand scan scope, and scan errors are never treated as empty directories.

Meaning of ledger `producedThisRun`:

| Value | Evidence | Delivery Verdict |
|---|---|---|
| `true` | Prior file's SHA-256 changed, or a complete baseline proves the file is newly created | Eligible for downstream format and engineering checks |
| `false` | File contents are identical to pre-execution state | Rejected as a current-run deliverable |
| `null` or missing | No baseline, incomplete baseline, out-of-scope path, or uncovered file format | Requires review; never auto-delivered |

Updating timestamps alone does not pass. When new and stale files are mixed in one deliverable list, passing new files cannot mask stale ones. Files from `job.artifacts`, `result.outputs`, and `result.artifacts` all obey the same rule; altering `kind` cannot exempt real CAD files.

Legacy plain-dictionary baselines can still compare SHA-256 hashes of recorded files, but cannot prove unrecorded files are newly created. Legacy jobs lacking current-run evidence transition to review-required—re-running in a fresh output directory is recommended. Preview manifests cannot be treated as fresh merely because the source model is fresh, nor can they substitute for actual deliverable files.

Freshness proves only that a file was created or changed in content—not that model dimensions are accurate, STEP opens natively, or engineering drawings meet manufacturing standards. Native file checks, geometric reviews, and required human reviews still apply. Regenerating byte-for-byte identical files cannot be distinguished from reusing stale files by SHA-256 alone, so identical regenerations are not automatically treated as newly created; use an isolated output directory per run.

Regression commands:

```powershell
python -m pytest -q tests/test_artifact_freshness.py tests/test_workbench_queue_worker.py
python tests/solidworks_artifact_freshness_live.py
```

The live test script creates only a temporary cylinder part, saves the native file, exports STEP, saves/reopens, checks previews, and verifies newly created, stale, timestamp-touched, missing-baseline, truncated, and out-of-scope artifacts. It closes only documents created in the current run and never closes pre-existing user documents.
