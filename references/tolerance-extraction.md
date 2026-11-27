# Displayed Dimension Tolerance Extraction (pilot)

`scripts/sw_tolerance_extract.py` reads a saved SolidWorks model or drawing in read-only mode and extracts displayed dimensions, types, and tolerance limits for the active configuration into a new CSV file; it neither modifies the model nor overwrites existing files.

```powershell
python scripts/sw_tolerance_extract.py C:\work\part.SLDPRT --output C:\work\tolerances.csv
```

The report status is always `review_required` (CLI exit code 2). Currently, only linear dimensions and bilateral tolerances have been live-tested on temporary parts in SolidWorks 2026 SP1.1 (`+0.10/-0.05 mm` matches direct COM readback). Radian-to-degree conversion for angular dimensions has offline unit tests; assemblies, drawings, angular dimensions, and other SolidWorks versions have not yet been verified on live instances.

- Iterates only over displayed dimensions in the active configuration; hidden dimensions, other configurations, and completeness of all dimensions must be manually verified.
- When an interface is unavailable, raises an exception, or encounters an unsupported type, it records the item as incomplete or skipped and never treats missing tolerances as zero.
- Linear dimensions use `mm` and angular dimensions use degrees; unsupported dimension types are skipped with a notice.
- CSV output escapes text that could trigger spreadsheet formula injection; users should still verify file provenance before opening.
- The command uses a controlled SolidWorks session and will not close pre-existing user documents opened prior to this read.
- This command shares an inter-process mutex lock with rename preview and live hole-position analysis entry points; other clients, legacy commands, and manual GUI actions are not protected by this lock, so avoid modifying or closing documents while they are being read.

Implementation approach references community contribution [PR #36](https://github.com/wzyn20051216/solidworks-automation-skill/pull/36). Actual tolerance API calls were rewritten against the local 2026 type library and live testing: the return values of `GetMinValue2` / `GetMaxValue2` are status codes, while actual limits are read from output parameters.
