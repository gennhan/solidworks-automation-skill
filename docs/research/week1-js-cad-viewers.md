# Week 1: JS CAD Preview Research

Research date: 2026-07-31. Metrics are sourced from public GitHub REST repository metadata; stars and forks change over time.

| Project | Stars | Forks | License | Suitable Use | Week 1 Decision |
|---|---:|---:|---|---|---|
| [three.js](https://github.com/mrdoob/three.js) | 114,133 | 36,455 | MIT | WebGL scenes, GLTF/STL/OBJ loaders, interactive controls | Adopted as CAD Studio preview foundation |
| [Online3DViewer](https://github.com/kovacsv/Online3DViewer) | 3,617 | 759 | MIT | Multi-format browser viewer supporting STEP/IGES/STL/OBJ, etc. | Evaluate format adapters and UI capabilities later |
| [replicad](https://github.com/sgenoud/replicad) | 661 | 78 | MIT | In-browser OpenCascade parametric modeling | Reference for future browser-side parametric experiments; excluded from Week 1 runtime |
| [three-cad-viewer](https://github.com/bernhard-42/three-cad-viewer) | 380 | 65 | MIT | Three.js-based CAD viewer component | Reference for tree hierarchy, selection, and camera interaction |
| [occt-import-js](https://github.com/kovacsv/occt-import-js) | 278 | 54 | LGPL-2.1 | OpenCascade WASM import for STEP/IGES/BREP | Defer bundling directly into MIT main package; run process-isolation and license assessment first |
| [ThatOpen/engine_components](https://github.com/ThatOpen/engine_components) | 691 | 204 | MIT | BIM/IFC components and 3D engine | Not an exact match for mechanical CAD goals; not adopted for now |

## Week 1 Implementation Boundaries

- SolidWorks deliverables prioritize displaying STL, GLB/GLTF, and OBJ; Three.js loaders are dynamically imported to avoid blocking initial load.
- DXF uses a read-only browser parser fallback covering `LINE`, `CIRCLE`, and `LWPOLYLINE`; parse failures display clear errors instead of fabricating CAD success.
- True geometry previews for STEP/IGES and DWG remain grounded in native SolidWorks/AutoCAD exported PNGs or meshes; wireframe placeholders are never presented as solid previews.
- Local paths are accessed exclusively via Tauri `convertFileSrc`; diagnostic bundles remain sanitized and never upload CAD files, prompts, or secrets.

## Follow-up Evaluations

1. Evaluate LGPL integration of `occt-import-js` in an isolated Worker; decide whether to enable browser-side STEP previews after legal and bundle-size checks.
2. Benchmark Online3DViewer against the current Three.js component for large-model load time, memory usage, and mobile-viewport interaction.
3. Add structured display of DXF layers, dimensions, and drawing frames; fall back to native AutoCAD BMP/PNG previews for complex entities.
