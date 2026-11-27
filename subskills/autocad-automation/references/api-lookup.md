# AutoCAD API Lookup Path

## Official Documentation Priority

1. Autodesk AutoCAD API Overview: covers available AutoCAD programming environments including ObjectARX, Managed .NET, Visual LISP, and ActiveX.
   - https://aps.autodesk.com/developer/overview/autocad-api
2. AutoCAD Developer and ObjectARX Help: reference for Managed .NET, ActiveX/VBA, DXF Reference, AutoLISP, and Core Console.
   - https://help.autodesk.com/view/OARX/2027/ENU/
3. Managed .NET Developer's Guide: for C# plugins, transactions, document locking, entity creation, dimensions, layouts, and plotting.
   - https://help.autodesk.com/view/OARX/2027/ENU/?guid=GUID-C3F3C736-40CF-44A0-9210-55F6A939B6F2
4. ObjectARX SDK: for deep C++/C# extensions, database structures, graphics systems, and native commands.
   - https://aps.autodesk.com/developer/overview/objectarx-autocad-sdk
5. APS Design Automation: for headless cloud batch processing of DWGs.
   - https://aps.autodesk.com/en/docs/design-automation/v3

## GitHub References

- ADN-DevTech `acad-api-skill`: rules for AI agents generating AutoCAD/Civil 3D/Plant 3D .NET plugins.
  - https://github.com/ADN-DevTech/acad-api-skill
- ADN-DevTech `autocad-automation-apps`: AutoLISP, C++ CRX, and .NET bundle samples for APS Design Automation.
  - https://github.com/ADN-DevTech/autocad-automation-apps
- `reclosedev/pyautocad`: Python ActiveX automation wrapper; useful reference for coordinate points, object iteration, and lightweight API design.
  - https://github.com/reclosedev/pyautocad
- AutoCAD .NET Wizards: Visual Studio project templates for AutoCAD .NET.
  - https://github.com/ADN-DevTech/AutoCAD-Net-Wizards

## Verification Workflow

1. Choose the route first: COM/ActiveX, AutoLISP/SCR, .NET, ObjectARX, or APS.
2. Search exact object and method names, such as `ModelSpace AddLine ActiveX AutoCAD` or `DocumentLock AutoCAD .NET`.
3. Read the documentation for the target version and record method signatures, parameter types, units, return values, exceptions, and version limitations.
4. When looking for GitHub examples, prioritize official Autodesk/ADN repositories; borrow patterns from third-party repos without copying verbatim.
5. Write a minimal runnable verification script, save the output file, and inspect it with `acad_review.py`.
6. If documentation and live tests disagree, record the local version, language pack, error code, and workaround in `troubleshooting.md`.

## Common COM/ActiveX Objects

- `AutoCAD.Application`: application entry point; controls `Visible` and provides access to `Documents` and `ActiveDocument`.
- `Document`: current drawing; exposes `ModelSpace`, `PaperSpace`, `Layers`, `Blocks`, `SelectionSets`, `SaveAs`, and `SendCommand`.
- `ModelSpace`: creates geometric entities such as lines, circles, polylines, text, and dimensions.
- `Layer`: layer color, linetype, and on/off state.
- `AcadEntity`: base entity supporting `Layer` and `Color`; most objects support `GetBoundingBox`.

## Common Method Checklist

- Line: `ModelSpace.AddLine(startPoint, endPoint)`
- Circle: `ModelSpace.AddCircle(centerPoint, radius)`
- Lightweight polyline: `ModelSpace.AddLightWeightPolyline(points2d)`
- Single-line text: `ModelSpace.AddText(text, insertionPoint, height)`
- Multiline text: `ModelSpace.AddMText(insertionPoint, width, text)`
- Save: `Document.SaveAs(path)`
- Command: `Document.SendCommand(command)`
- View: `Application.ZoomExtents()`

These methods may behave differently across AutoCAD versions, language packs, and LT vs. full editions; do not promise that advanced objects or export formats work until verified locally.

## .NET Plugin Route

Switch to .NET when COM scripts become difficult to maintain or when transactions, document locking, selection filters, command registration, palette UI, or event listeners are required:

1. Use the .NET target framework and SDK references matching the target AutoCAD version.
2. Register command entry points with `CommandMethod`.
3. Wrap database modifications in transactions, and properly lock the document when operating on the active document.
4. Load the DLL via `NETLOAD` or debug launch configuration.
5. Once the plugin succeeds locally, consider packaging it as a bundle or an APS Design Automation activity.

## Documentation Usage Boundaries

- Never guess enum values, save types, Plot configurations, or command parameters from memory.
- Never treat forum answers as final authority; use forums only to identify keywords and error symptoms.
- Never copy GitHub code with unclear licensing into user projects.
- Never describe cloud APS workflows as local AutoCAD COM capabilities, and never claim local COM scripts can run directly in CI.

