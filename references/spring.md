# Open-Ended Constant-Pitch Helical Spring Solid (pilot)

`scripts/sw_spring.py` creates a fully constrained base circle, a native SolidWorks Helix/Spiral, and a circular-profile swept boss in a new empty part. The generated geometry is an open-ended, constant-pitch spring—end coils are neither closed nor ground; it does not automatically select materials or verify spring rate, fatigue, solid height, or manufacturing standards, and results always remain `review_required`.

The input `helix_height_mm` is the **axial travel of the wire centerline**, not the free length of the solid spring body. The solid ends extend axially further due to wire diameter; actual solid extents are read back via `IBody2.GetExtremePoint`. `clockwise` maps to the direction parameter of the SolidWorks Helix feature relative to the selected sketch plane; do not equate it directly to left-hand or right-hand winding specified on an engineering drawing without checking the orientation reference.

The legacy pure-geometry function `compression_spring_helix` retains the field name `free_length_mm` for compatibility, but it likewise represents centerline axial travel; its `end_type` affects estimation only and does not generate closed or ground ends. Returned `limitations` record these boundaries; never treat estimated stiffness or solid height as manufacturing acceptance values.

```python
from pathlib import Path
import tempfile
from scripts.sw_session import SolidWorksSession
from scripts.sw_spring import OpenHelicalSpringSpec, create_open_helical_spring

output = Path(tempfile.mkdtemp(prefix="spring_demo_"))
with SolidWorksSession(version=2026, visible=True) as session:
    model = session.new_part()
    spec = OpenHelicalSpringSpec(wire_diameter_mm=3, mean_diameter_mm=24,
                                 helix_height_mm=48, turns=6, clockwise=False)
    feature, evidence = create_open_helical_spring(model, spec)
    if not session.save(model, str(output / "open_spring.sldprt")):
        raise RuntimeError("保存失败")
    # 按具体任务导出 STEP、生成预览并人工审查。
```

Pilot constraints: wire diameter `0.1–50 mm`, mean diameter at most `500 mm` and at least `4x` wire diameter, centerline height at most `2000 mm`, `1–20` turns; pitch at least `1.25x` wire diameter and at most half the mean diameter. These are conservative implementation bounds, not spring design standards. The API only accepts an empty part with no existing solid bodies; on failure, partial sketches or intermediate features may remain, so only use it in a freshly created document.

Running `python tests/solidworks_spring_live.py` validates two examples (6 turns and reversed 5.5 turns) in a new temporary directory: it reads back handedness, turns, pitch, and height, compares against theoretical volume and B-Rep extrema, saves, exports STEP, reopens, and checks previews. Only these two cases on SW2026 SP1.1 have completed live verification; other parameter combinations and SolidWorks versions require further verification.

Related APIs: [SolidWorks InsertHelix](https://help.solidworks.com/2021/english/api/sldworksapi/solidworks.interop.sldworks~solidworks.interop.sldworks.imodeldoc2~inserthelix.html), [IBody2.GetExtremePoint](https://help.solidworks.com/2014/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IBody2~GetExtremePoint.html). Implementation direction references community contribution [PR #36](https://github.com/wzyn20051216/solidworks-automation-skill/pull/36).
