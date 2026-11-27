# Approximate Sprocket Solid (pilot)

`scripts/sw_sprocket.py` generates an **approximate, polyline-profile SolidWorks solid** from a given chain pitch, roller diameter, tooth count, thickness, and bore diameter for visual and geometric demonstration. It is not a standard sprocket generator: chain engagement, strength, service life, and manufacturing standards are unverified and it must not be used for production design. The sketch is not fully constrained or parametric—to change parameters, regenerate from scratch—and results remain `review_required`.

The interface requires an empty part with no solid bodies; it validates inputs first, then creates the sketch and extrusion, without saving, renaming, or overwriting files. If modeling fails mid-way, partial sketches may remain in the part, so only use it in a newly created document. The caller is responsible for saving to a new path, exporting, and reviewing previews.

```python
from scripts.sw_session import SolidWorksSession
from scripts.sw_sprocket import SprocketSpec, create_approximate_sprocket

with SolidWorksSession(visible=True) as session:
    model = session.new_part()
    spec = SprocketSpec(chain_pitch_mm=12.7, roller_diameter_mm=7.92,
                        teeth=17, thickness_mm=6, bore_diameter_mm=10)
    feature, evidence = create_approximate_sprocket(model, spec)
    # 保存到本次新建且未占用的路径；随后导出并审查实际几何和预览。
```

The nominal root diameter `pitch_diameter - roller_diameter` differs from the minimum diameter of the actual polyline profile; the bore diameter is constrained by the actual polyline minimum diameter. `profile_min_diameter_mm` reports this geometric boundary and is not a meshing dimensional tolerance.

Run `python tests/solidworks_sprocket_live.py` for manual regression testing in a fresh temporary directory. One 17-tooth, 10 mm bore case on SW2026 SP1.1 has verified single-body output, volume, bounding box, save/reopen, STEP export, and views. Automated review still flags sketch constraints for manual check; other parameter sets and SolidWorks versions have not yet been verified on live instances.

Implementation direction references community contribution [PR #36](https://github.com/wzyn20051216/solidworks-automation-skill/pull/36).
