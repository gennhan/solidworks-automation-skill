# Engineering Drawing Review Reference

Engineering drawing review is structured into three layers:

1. Structural evidence: sheet size, sheet format, projection method, views, scale, dimensions, tables, and output files.
2. Manufacturing evidence: dimension chains, hole/slot size/quantity/location, title block, BOM, and sheet-metal flat-pattern evidence.
3. Visual evidence: BMP/PNG visual inspection results and PDF vector text bounding-box risks.

Missing evidence in any layer prevents upgrading to unattended release. Confirmed collisions use `fail`; estimates or PDF text risks use `warning`; missing key specifications or sheet-metal flat-pattern evidence use `blocked` / `review_required`.

Structured verification rules:

- Dimension IDs must match exactly, verifying view, kind, value/text, dimensional tolerance, and datum item-by-item; `D1` must never match `D10`.
- Hole requirements must match one-to-one by specification, quantity, and every location. Thread callouts accept only dedicated thread/hole-callout evidence and must never be inferred from matching numbers or plain hole diameters.
- Diameter symbols in PDFs may be rendered as vector graphics, leaving only `4X 10` in the text layer; the reviewer treats such quantity-prefixed text as a dimension-position match candidate, but the text layer alone cannot prove that the diameter symbol is present or that the hole count is accurate—native dimensions, model hole evidence, and visual review are still required.
- BOM checks accept only `swTableAnnotation_BillOfMaterials` with non-empty data rows; when a configuration is requested, it must match exactly.
- A sheet-format template candidate is not equivalent to verified title-block field contents; remain `review_required` when fields cannot be read back.
- Standard, isometric, section, and detail views requested in `DrawingSpec` must each appear in structural evidence.
- Professional annotations must originate from `IView` center mark, centerline, datum, GTOL, surface finish, or weld symbol entities, and hole callouts must come from `IDisplayDimension.IsHoleCallout`; plain `Note` text with matching strings cannot substitute.
- Annotation center marks should be iterated via `IView.GetFirstCenterMark2` and `ICenterMark.GetNext`; `GetCenterMarks` is a legacy fallback only and does not cover all center-mark types on its own.
- `professionalAnnotations` are matched item-by-item by view, type, quantity, and text. Datum labels match exactly (`A` must never match `AB`).
- Modern GTol frames in SolidWorks 2026 are read using 1-based indexing via `IGtolFrame.GetSymbolXml` to extract symbols, primary tolerances, and datum letters; unknown formats or unparseable XML never fabricate frame contents. This readback provides annotation evidence only and does not validate full GD&T semantics or manufacturing suitability. [Official API Reference](https://help.solidworks.com/2024/english/api/sldworksapi/SolidWorks.interop.sldworks~SolidWorks.interop.sldworks.IGtolFrame~GetSymbolXml.html).
