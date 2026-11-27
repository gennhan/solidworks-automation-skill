# Engineering Drawing API Verification Checklist

Consult official SolidWorks documentation or local Interop assemblies before implementing any of the following APIs:

- `SetupSheet6`, `NewSheet4`
- `CreateFirstAngleViews2`, `Create3rdAngleViews2`
- `CreateDrawViewFromModelView3`
- `InsertModelAnnotations3/4`
- `InsertBomTable4`
- `CreateSectionViewAt5`, `CreateDetailViewAt4`
- `InsertDatumTag2`, `InsertSurfaceFinishSymbol3`, `InsertWeldSymbol`

Maintain a minimal verification script to inspect returned objects, save operations, exports, and read-back results.
