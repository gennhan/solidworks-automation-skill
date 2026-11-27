# Engineering Drawing API Reference

## Creating Views

### Standard Three Views

```python
drawing.Create3rdAngleViews2(partPath)  # 第三角投影法
drawing.CreateFirstAngleViews2(partPath) # 第一角投影法
```

### Custom Views

```python
view = drawing.CreateDrawViewFromModelView3(
    ModelName,     # str: 零件/装配体路径
    ViewName,      # str: 视图方向（见下表）
    X, Y, Z        # float: 放置位置（米）
)
```

View orientation names:
| Name | Description |
|---|---|
| `*Front` | Front view |
| `*Back` | Back view |
| `*Top` | Top view |
| `*Bottom` | Bottom view |
| `*Left` | Left view |
| `*Right` | Right view |
| `*Isometric` | Isometric view |
| `*Trimetric` | Trimetric view |
| `*Dimetric` | Dimetric view |

### Setting View Scale

```python
view.ScaleRatio = (1.0, 2.0)  # 1:2 比例
view.ScaleRatio = (2.0, 1.0)  # 2:1 比例
```

## Dimensioning

### Automatic Dimensioning (Model Items)

```python
drawing.InsertModelAnnotations3(
    InsertType,    # int: 0=整个模型
    AnnotationType, # int: 32768=标记为工程图的模型尺寸
    DuplicateDims, # bool
    AutoArrange,   # bool
    UseDoc,        # bool
    UseView        # bool
)
```

> Dynamic `pywin32` proxies in SW2024/2026 typically expose `InsertModelAnnotations3` on the drawing `IModelDoc2` rather than `IModelDocExtension`. Skill scripts try the document object first, then fall back to the legacy Extension proxy. `32` is geometric tolerances (GD&T), whereas `32768` is model dimensions marked for drawing; if the call returns `False` or no dimension entities can be read back, do not mark dimension evidence as verified.
>
> This API only imports `DisplayDimension` items that already exist in the model. For parts with undimensioned rectangles or only extrusion parameters, call `sw_part.auto_dimension_sketch()` while in sketch edit mode or create model dimensions explicitly during parametric modeling; do not expect the drawing API to invent dimensions out of thin air.
>
> The capability manifest records this path separately as `drawing_dimension_insertion=verified` (SW2024/2026). On SW2026 SP01.1, three consecutive runs read back 3 real views and 6 real dimension entities. Full engineering drawing delivery remains `drawings_and_bom=pilot` because dimension layout, hole/slot locating chains, sheet borders, title blocks, and BOMs still require manual visual review.

### SW2026 Dimension Text Bounding Evidence

Reflection on local `SolidWorks.Interop.sldworks.dll` confirms:

- `IAnnotation.GetPosition()` returns the annotation anchor point.
- `IAnnotation.GetTextFormat(index)` / `GetTextFormatCount()` returns the text format.
- `ITextFormat.CharHeight`, `WidthFactor`, and `CharSpacingFactor` provide font sizing metrics.
- `IDisplayDimension.GetText(swDimensionTextParts_e)` reads user text segments.
- `IAnnotation` has no native bounding-box API for dimension text; do not call or claim `GetBox()` exists.

Therefore, `scripts/sw_drawing.py::estimate_dimension_text_box()` produces only a conservative estimated bounding envelope:

1. Centered at `IAnnotation.GetPosition()`.
2. Estimates unrotated text width and height from character count, `CharHeight`, `WidthFactor`, and `CharSpacingFactor`.
3. Because the API does not expose dimension text angle, constructs a square envelope sized to the rectangle's diagonal to cover any arbitrary rotation.
4. Padding is `max(1 mm, 0.4 * CharHeight)`; when fields are missing, conservative defaults are used and confidence is lowered.
5. `GetText(0)` in SW2026 may not return the formatted primary dimension value; when missing, a conservative placeholder width of 8 monospace characters is assumed.

Reports must retain the following fields and must never present estimated values as native bounding evidence:

```json
{
  "box_source": "estimated",
  "box_confidence": "low | medium | unavailable",
  "box_evidence": {
    "native_bounding_box_available": false,
    "method": "annotation_position_text_format_arbitrary_rotation_envelope",
    "padding_m": 0.001,
    "orientation_assumption": "unknown_angle_conservative_square_envelope"
  }
}
```

Even when no overlaps are found among all estimated boxes, `review_drawing_layout()` still returns `review_required / DRAWING_LAYOUT_ESTIMATED_EVIDENCE_REQUIRES_VISUAL_REVIEW`. When estimated boxes intersect, it returns `DRAWING_LAYOUT_ESTIMATED_COLLISION_RISK`, and the finding must carry `evidence_source=estimated` and `confirmed_collision=false`; only native bounding evidence may use `DRAWING_LAYOUT_COLLISION_DETECTED` to report a confirmed collision. Non-empty BMP/PDF files only prove preview artifacts exist and do not automatically prove dimensions are overlap-free; final visual inspection is mandatory.

A stronger non-COM approach is to export PDF via SolidWorks natively and then call `sw_review.inspect_pdf_text_layout()` to read real vector text span bounding boxes from the PDF. This detects actual overlaps between extractable text spans more reliably than character-width estimation and requires no OCR; however, it still cannot prove there are no collisions between text and dimension lines, geometry lines, or outlined fonts. Intentional overlapping elements in title blocks (such as `"第 张"` + page number fields in Chinese templates) can also produce real bounding-box intersections, so findings flag overlap risk rather than declaring a visual defect outright. Install PyMuPDF if missing:

```powershell
python -m pip install -r requirements-pdf.txt
```

If dependencies are installed in a custom directory, point `CADSTUDIO_PYMUPDF_PATH` to that directory.

Accordingly, the hierarchy of drawing layout bounding evidence is: PDF vector text bounds > COM anchor/font conservative estimation > OCR, with one final PDF/BMP visual review retained before delivery.

### Adding Dimensions Manually

```python
# 先选择两个实体
drawing.Extension.SelectByID2("Edge1@View1", "EDGE", 0, 0, 0, False, 0, None, 0)
drawing.Extension.SelectByID2("Edge2@View1", "EDGE", 0, 0, 0, True, 0, None, 0)
# 添加尺寸
drawing.AddDimension2(x, y, 0)  # 尺寸标注放置位置
```

## Notes and Annotations

```python
# 添加注释
note = drawing.InsertNote(text)

# 添加表面粗糙度符号
drawing.InsertSurfaceFinishSymbol3(...)

# 添加焊接符号
drawing.InsertWeldSymbol(...)

# 添加基准符号
drawing.InsertDatumTag2(...)
```

## BOM Tables

```python
bom = drawing.InsertBomTable4(
    TemplateName,  # str: BOM 模板路径(.sldbomtbt)
    X, Y,          # float: 位置
    BomType,       # int: 1=顶层, 2=仅零件, 3=缩进
    Configuration, # str: 配置名
    TableAnchor,   # str: 锚点名
    Hidden         # bool: 是否包含隐藏组件
)
```

## Sheet Operations

```python
# 获取当前图纸
sheet = drawing.GetCurrentSheet()

# 获取所有图纸名称
names = drawing.GetSheetNames()

# 激活指定图纸
drawing.ActivateSheet(sheetName)

# 添加新图纸
drawing.NewSheet4(
    Name,        # str: 图纸名称
    PaperSize,   # int: 纸张大小（5=A4, 6=A3, 7=A2, 8=A1, 9=A0）
    TemplateIn,  # int: 12=自定义
    Scale1,      # float: 比例分子
    Scale2,      # float: 比例分母
    FirstAngle,  # bool: 第一角投影法
    Template,    # str: 图纸格式路径
    W, H,        # float: 宽高
    PropertySheet, # str
    Zone_LeftMargin, Zone_RightMargin, Zone_TopMargin, Zone_BottomMargin,
    Zone_Col, Zone_Row  # int: 分区
)

# 设置图纸格式
sheet.SetTemplateName(formatPath)  # .slddrt 文件路径
```

## Exporting PDF

```python
from scripts.sw_drawing import export_sheet_to_pdf

# 从受控会话取得真实应用对象；SW2026 不依赖 ModelDoc2.GetSldWorksObject。
if not export_sheet_to_pdf(drawing, "output.pdf", sw_app=session.sw):
    raise RuntimeError("PDF 导出失败")
```
