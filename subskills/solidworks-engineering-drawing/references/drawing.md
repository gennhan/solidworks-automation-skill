# Engineering Drawing Generation Reference

## Standards

Default strictly to **TCVN/ISO** (`ISO` drafting standard, `MMGS` units, **First-Angle Projection**): always load `references/tcvn_mechanical.md` (from the root skill directory) before creating, configuring, or checking sheet formats, margins, title block/BOM conventions, first-angle projection, fits, GD&T, surface roughness, welding symbols, or general tolerance notes. Under first-angle projection, the Top view sits below the Front view and the Right view sits to the left of the Front view; SolidWorks `SetupSheet6` / `NewSheet4` projection parameters must match the view layout and be read back after creation.

Treat `GB/T`, `GB`, and `JB/T` conventions as **reference only** unless explicitly requested by the user (when explicitly requested, the GB/T route also uses first-angle projection).

## Evidence Requirements

- View objects, orientations, positions, and scales must be read back.
- The return value of `InsertModelAnnotations3/4` alone cannot prove dimensions were inserted; real `DisplayDimension` entities must be read back.
- A sheet-format filename is only candidate evidence and does not prove template compliance with TCVN/ISO (or GB/T when explicitly requested).
- PDF/BMP outputs must exist and be non-empty; PDF text bounding boxes are for risk screening only.

## API Rules

For new or unwrapped SolidWorks APIs, consult `references/api-lookup.md` and official API Help to verify signatures, enumerations, return values, and version differences before implementing. When COM returns `None` or `False`, return an explicit failure status rather than faking success.

