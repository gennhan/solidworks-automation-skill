# Advanced Features Reference

## Table of Contents

- [Custom Properties](#custom-properties)
- [Design Tables and Configurations](#design-tables-and-configurations)
- [Sheet Metal Design](#sheet-metal-design)
- [Weldment Design](#weldment-design)
- [Surface Modeling](#surface-modeling)
- [Simulation/FEA](#simulationfea)

---

## Custom Properties

```python
# 获取属性管理器
# 空字符串 = 文件级属性，配置名 = 配置特定属性
props = model.Extension.CustomPropertyManager("")

# 读取属性
val = ""
resolved = ""
was_resolved = False
is_linked = False
result = props.Get6("Description", False, val, resolved, was_resolved, is_linked)
# resolved 包含解析后的值

# 写入/更新属性
# 类型: 30=文本, 2=数字, 11=Yes/No, 64=日期
props.Add3("Description", 30, "主轴零件 Rev A", 1)  # 1=覆盖
props.Add3("Material", 30, "Steel 1045", 1)
props.Add3("Weight", 2, "2.5", 1)
props.Add3("PartNumber", 30, "PN-001-001", 1)

# 删除属性
props.Delete2("OldProperty")

# 获取所有属性名称
count = props.Count
names = props.GetNames()
```

## Design Tables and Configurations

### Configuration Management

```python
from sw_document_data import (
    activate_configuration,
    create_configuration,
    inspect_configurations,
    update_dimension_mm,
)

# 使用官方 AddConfiguration3 创建并激活；默认同名配置幂等复用。
created = create_configuration(
    model,
    "加工",
    comment="CNC 工况",
    alternate_name="MACHINED",
)

# 使用官方 ShowConfiguration2，并以活动配置名回读而非单独 COM 返回值判定。
activated = activate_configuration(model, "加工")

# 用显式 VT_ARRAY|VT_BSTR 写入指定配置，API 内部单位自动换算为米。
dimension = update_dimension_mm(
    model,
    "D1@Boss-Extrude1",
    50.0,
    configuration_mode="specific",
    configuration_names=["加工"],
)

evidence = inspect_configurations(model)
```

Verified on live SW2026: configuration creation, switching, configuration-specific dimensions/properties, and save/reopen readback. Because `AddConfiguration3` automatically activates the newly created configuration, calling `ShowConfiguration2` again may return `False`; the executor records the raw return value but uses `ConfigurationManager.ActiveConfiguration.Name` readback and rebuild status as success evidence. Design tables, derived configurations, display states, and large-scale suppression matrices remain outside the `pilot` scope.

### Design Tables

```python
# 插入设计表（从 Excel）
design_table = model.InsertFamilyTableOpen(excelFilePath)

# 编辑完成后关闭
model.CloseFamilyTable()

# 更新设计表
model.InsertFamilyTableEdit()
```

## Sheet Metal Design

### Basic Operations

```python
from sw_sheet_metal import BaseFlangeSpec, create_base_flange

# 先创建并退出开放或闭合草图，再使用现代 FeatureData API。
feature = create_base_flange(
    model,
    sketch_name,
    BaseFlangeSpec(
        thickness=0.002,
        bend_radius=0.0025,
        depth=0.100,
        k_factor=0.42,
    ),
)
```

This wrapper uses `CreateDefinition(swFmBaseFlange)`, `IBaseFlangeFeatureData.Initialize`, and `CreateFeature` without guessing deprecated long-parameter interfaces. Verified on SW2026 SP01.1 with an open U-shaped profile, two real bends, and save/reopen; Edge Flange, Miter Flange, and Lofted Bend remain gated under `pilot`.

### Flat Pattern Export

```python
from sw_export import export_flat_pattern_dxf

# 零件必须先保存；选项位掩码默认为“展开几何(1) + 折弯线(4)”。
export_flat_pattern_dxf(model, dxfPath, include_bend_lines=True)
```

In `ExportToDWG2`, the 5th parameter is a 12-double alignment array and the 8th parameter is the sheet metal options bitmask; do not pass multiple booleans mistaking them for "geometry / bend lines / sketches / hidden edges."

### Sheet Metal Parameters

```python
# 获取钣金特征数据
feat = model.FeatureByName("Sheet-Metal1")
sheet_metal_data = feat.GetDefinition()
thickness = sheet_metal_data.Thickness    # 板厚
bend_radius = sheet_metal_data.BendRadius # 折弯半径
```

## Weldment Design

### Cut List

```python
from sw_weldment import (
    create_structural_member,
    ensure_cut_list,
    export_cut_list_csv,
    set_cut_list_properties,
    weldment_evidence,
)

member = create_structural_member(
    model,
    profile_path,
    [sketch_segments],
    apply_corner_treatment=True,
)
ensure_cut_list(model)
set_cut_list_properties(model, {"PROFILE_DESIGNATION": "HSS1x1x16ga"})
evidence = weldment_evidence(model)
export_cut_list_csv(evidence, csv_path)
```

In SW2026, `InsertWeldmentCutList2` under Python `IDispatch` can be projected as a pseudo-property returning `None`; the wrapper invokes it via `DISPATCH_METHOD` using DISPID 174 confirmed from the local type library. The rectangular frame regression groups bodies by their longest bounding-box edge, producing two distinct `CutListFolder` entries rather than merging members of different lengths.

### Structural Members

```python
from sw_weldment import create_weldment_profile

# 型材文档中先完成并退出闭合轮廓草图；可写入型材/BOM 来源属性。
profile = create_weldment_profile(
    profile_model,
    profile_sketch,
    profile_path,
    properties={"DESCRIPTION": "HSS1x1x16ga", "MATERIAL": "steel_a500b"},
)
```

`create_structural_member()` internally uses `CreateStructuralMemberGroup` and the latest `InsertStructuralWeldment5`, marshaling path segments and groups as `VT_ARRAY | VT_DISPATCH` safe arrays so callers do not have to guess long signatures or rely on the active selection set.

## Surface Modeling

```python
# 拉伸曲面
feature_mgr.InsertExtrudedSurface(depth, flip, dir, t1, t2, d1, d2)

# 旋转曲面
feature_mgr.InsertRevolvedRefSurface(...)

# 放样曲面
feature_mgr.InsertLoftRefSurface2(...)

# 扫描曲面
feature_mgr.InsertSweepRefSurface(...)

# 平面区域
feature_mgr.InsertPlanarRefSurface()

# 修剪曲面
feature_mgr.InsertTrimSurface2(...)

# 缝合曲面
feature_mgr.InsertSewRefSurface(True, False, 0.001)

# 曲面加厚为实体
feature_mgr.InsertThickenSheet(thickness, False, True)
```

## Simulation/FEA

> Requires the SolidWorks Simulation add-in to be installed.

```python
# 获取 Simulation 插件
cos_works = sw.GetAddInObject("SldWorks.Simulation")
if not cos_works:
    print("Simulation 插件未安装或未激活")

study_mgr = cos_works.StudyManager

# 创建静态分析算例
study = study_mgr.CreateStudy(
    model,
    "StaticStudy1",
    0  # 0=Static, 1=Frequency, 2=Buckling, 3=Thermal, 5=Fatigue
)

# 添加材料（通过 SolidBody）
# 添加约束（Fixed, Roller/Slider, Prescribed）
# 添加载荷（Force, Pressure, Gravity, Torque）

# 运行分析
study.RunAnalysis()

# 获取结果
results = study.Results
# 应力、位移、安全系数等
```

### Study Types

| Value | Type | Description |
|---|---|---|
| 0 | Static | Static analysis |
| 1 | Frequency | Frequency analysis |
| 2 | Buckling | Buckling analysis |
| 3 | Thermal | Thermal analysis |
| 4 | Drop Test | Drop test |
| 5 | Fatigue | Fatigue analysis |
| 6 | Nonlinear | Nonlinear analysis |
