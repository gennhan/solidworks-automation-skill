# Complex Mechanical Model Capability Routing

## Probe First, Execute Second

Before starting a complex mechanical task, run:

```powershell
python scripts\sw_capability_probe.py --output capability_report.json
```

The report separates three dimensions:

- `type_library_present`: The local installation includes the interface definitions.
- `implementation_status`: Whether this skill provides a wrapper validated by live regression tests.
- `ready_for_unattended_use`: Whether unattended execution is permitted.

Having a type library installed does not guarantee a valid license or verified automation. Capabilities marked `reference_only`, `not_implemented`, or `pilot` without evidence must never be reported to the user as completed.

## Current Capability Levels

| Domain | Current Level | Execution Rules |
|---|---|---|
| Parametric parts, holes/slots, fillets/chamfers | Verified | May run live COM; must emit parameter JSON and review report |
| Assemblies, Concentric/Distance/Gear Mates | Verified | Must verify degrees of freedom and Mate feature tree |
| Motion Study rotary motors | Verified | After calculating, call `collect_motion_study_summary()` to verify results are not out of date |
| Engineering Drawings | Pilot | Must manually review sheet borders, views, dimension chains, and TCVN/ISO format (or GB/T reference format when requested) |
| Configurations, Design Tables | Reference only | Run a minimal sample regression before applying to customer models |
| Sheet Metal | Pilot (SW2026 open-profile Base Flange) | Must read back native SheetMetal/BaseFlange/FlatPattern, manufacturing parameters, reopen check, and flat-pattern DXF |
| Weldments | Pilot (SW2026 HSS planar frame) | Must read back WeldmentFeature/WeldMemberFeat, per-item body count, length, quantity, angles, source properties, and reopen evidence |
| Complex Surfacing, Molds/Tooling | Pilot | `create-ocp-loft/create-ocp-surface` builds and reopens constrained ruled/smooth Lofts and Sweep/Knit/Thicken; G1/G2 continuity and curvature radius use discrete sampling evidence only; complex paths and molds remain gated |
| Routing | Pilot | Only `routing-preflight` or `check-routing` allowed; native writes must remain blocked without add-in/license evidence |
| Simulation/FEA | Pilot | `run-fea` runs constrained linear/nonlinear statics and parses final-step contact penetration/pressure/slip; `run-fea-convergence` executes 3–8 linear or nonlinear mesh sequences; plasticity, contact, and convergence all require engineering review |

## Complex Parts

1. Decompose the model into base solid, primary functional features, interface features, manufacturing features, and cosmetic features.
2. Prefer stable datums, fully constrained sketches, and named features; never rely on `Edge1`, screen coordinates, or incidental selection order.
3. Complex surfaces must specify continuity targets (G0/G1/G2), parting/draft, wall thickness, and manufacturability.
4. Sheet metal must record thickness, material, inner bend radius, K-factor/bend table, bend direction, and flat-pattern DXF.
5. Weldments must record profile standard, cut lengths, miters, welds, cut list, and machining allowances.
6. Configurations/Design Tables must verify each configuration rebuilds cleanly, has reasonable mass properties, and avoids output filename collisions.

## Complex Assemblies and Motion

1. Build a DOF budget: list the expected 6 degrees of freedom for every moving component, then remove them mate by mate.
2. Use Concentric mate + axial locating mate (rotation unlocked) for rotating parts; use Slot/Distance/Limit mates for linear motion.
3. Contact, friction, springs, dampers, gravity, and collisions are outside the current "verified rotary motor" scope.
4. Motion deliverables must include study type, duration, motor count, external force count, feature count, result presence, and `results_out_of_date`.
5. Playable animation does not prove mechanism validity; also inspect interference, travel limits, velocity/acceleration, driving force/torque, and mate reaction forces.
6. Motion Analysis depends on add-ins and licenses; when absent, explicitly downgrade to Animation/Basic Motion and never fabricate analysis outputs.

## New Capability Development Gate

1. Confirm interfaces, signatures, enumerations, and versions from local `.tlb` files or official SolidWorks API docs.
2. Build a minimal regression specimen—never experiment directly on complex user assemblies.
3. Wrap behind a narrow interface in `scripts/sw_*.py` with explicit checks on every COM return value.
4. Add offline unit tests and a live SolidWorks regression script.
5. Generate machine-readable acceptance evidence and multi-view previews.
6. Document failure modes in `references/troubleshooting.md` before marking a capability `Pilot`; promote to `Verified` only after consecutive passing live regressions.
