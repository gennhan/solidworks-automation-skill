# P0-2.1 Public Evidence Index (2026-10-27)

This directory contains only **privacy-reviewed, publication-safe** summaries of P0-2.1 acceptance evidence.
The raw evidence archive is not stored here and remains local on the maintainer's machine.

| Item | Value |
| --- | --- |
| Stage | P0-2.1 (gripper mechanical retention + tolerance proposals + 5-run live static travel) |
| Branch | `test/p0-real-gripper-retention-travel-2026` |
| Frozen source at acceptance | `df4d4c9a4143602d5af7077a7be7b19cee4850c2` |
| Final commit (docs & evidence index only) | `b414341b70dbc75b845f0f494817b4eab2674284` |
| Official suite | `output/p0-2-1-real-five-05` (all 5 runs `acceptance passed`) |

## Files

| File | Contents | Redacted |
| --- | --- | --- |
| `p0-2-1-work-state.json` | Stage work state: official suite, historical failure context, pending items, terminal state | No (verbatim, zero sensitive hits) |
| `p0-2-1-evidence-sha256.json` | 548-entry per-file SHA-256 manifest (relative paths) | **Yes**, updated digests for redacted evidence |
| `p0-2-1-independent-seal-verification.json` | Independent seal verification: archive hash, 549 entries, byte-level comparison, 45 poses and 20 over-travel checks | No |
| `suite-summary.redacted.json` | 5-run suite summary (`acceptance_status` / `suite_checks` / `metrics` / per-run verdicts) | **Yes**, local absolute path prefix replaced with `<repo>` |
| `manifest.json` | Original hash vs. published hash per file plus privacy review verdict | — |

## How to Verify

Published digests are computed over Git-stored UTF-8 LF bytes; `.gitattributes` enforces LF checkout for these JSON files. Original digests record the pre-redaction source bytes and may differ due to redaction or line-ending normalization.

```bash
# 1. 逐文件核对发布包完整性（以本目录为基准）
python - <<'PY'
import json, hashlib, pathlib
root = pathlib.Path("docs/architecture/evidence/p0-2-1-2026-10-27")
m = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
for f in m["files"]:
    digest = hashlib.sha256((root / f["published"]).read_bytes()).hexdigest()
    print(f["published"], "OK" if digest == f["published_sha256"] else "MISMATCH")
PY

# 2. 核对声明值是否自洽（549 成员 / 190 原生哈希 / 45 静态状态 / 20 越限控制）
cat docs/architecture/evidence/p0-2-1-2026-10-27/p0-2-1-independent-seal-verification.json
```

## Privacy Review Conclusion

| Item | Conclusion |
| --- | --- |
| Scan scope | Personal names, emails, usernames, hostnames, home directories, session IDs, UUIDs, tokens, private keys, local absolute paths |
| `p0-2-1-work-state.json` | Zero hits; `exec_session_id` is `null` |
| `p0-2-1-evidence-sha256.json` | Zero hits (relative paths only) |
| `p0-2-1-independent-seal-verification.json` | Zero hits |
| `p0-2-1-real-five-05/summary.json` | **5 local absolute path hits**, redacted prior to publication |

**Redacted copies are not original files.** Redacted files and the updated manifest have `published_sha256` values distinct from `original_sha256`; `manifest.json` records both, and redacted copies must never be cited as raw original evidence.

## Known Limitations (Do Not Overlook)

1. **Raw evidence archive is not in the repository.** `output/p0-2-1-evidence-20261027.zip` (26,746,788 bytes / 549 members / SHA-256 `16a5e333…f3b4`) stays on the maintainer's machine. External reviewers **can verify declared values and manifests**, but **cannot independently replay** the raw evidence.
2. **`.gitignore` is not security.** Files in this directory are public because they passed the privacy review above, not because of gitignore rules.
3. **Hash parity does not mean safe to publish.** SHA-256 proves byte integrity only, not suitability for public release.
4. **`work-state.json` is a historical snapshot.** Its `offline_final: "1034 passed / 1 skipped"` reflects the offline suite at acceptance time; current offline regression is 1035 passed / 1 skipped (after adding governance gate tests). This historical value is **not edited** to avoid altering historical records.
5. **Local pass ≠ release pass.** Five passing local runs confirm only this SolidWorks 2026 host; remote CAD CI has never completed a successful run, and cross-machine deployment is unverified.

## Handling of Other Evidence Files

`p0-2-1-real-gripper-travel-2026-10-27.json` previously contained local paths and user directories and has been redacted in place; its published digest was updated in this directory's manifest. The updated manifest is a derivative file while `manifest.json` preserves the original manifest digest. The original sealed archive was not modified, and published copies must not be treated as original bytes. Repository history and prior clones may still contain pre-redaction content. Other historical evidence and sealing records were not altered by this update.
