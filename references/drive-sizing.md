# Motor Torque Verification (Drive Sizing)

`scripts/drive_sizing.py` evaluates whether a selected motor/gearbox satisfies a given mechanism and motion profile. It is a **preliminary sizing screen and audit aid** and does not replace vendor sizing software or engineer sign-off; reports always return `reviewRequired=true`. It is integrated into DRC (rule family `DRC-DRV-*`), automatically gaining fingerprinting, waivers, baseline diffing, risk scoring, regression gating, and MCP support (`cadstudio_check_drc`).

## Input: `metadata.drives[]` (drive-spec, declarative JSON that an agent can generate from natural language)

```json
{
  "id": "X轴",
  "load": {"mass_kg": 50, "incline_deg": 0, "friction_coeff": 0.1, "external_force_n": 0, "return_external_force_n": 0},
  "motion": {"distance_mm": 500, "max_speed_mm_s": 500, "accel_mm_s2": 2000, "dwell_s": 0.5, "round_trip": true},
  "transmission": {"type": "lead_screw", "lead_mm": 10, "efficiency": 0.9, "screw_diameter_mm": 20, "screw_length_mm": 600,
                   "gear_ratio": 1, "gear_efficiency": 1},
  "motor": {"peak_torque_nm": 1.5, "rated_torque_nm": 0.64, "rated_speed_rpm": 3000, "max_speed_rpm": 5000,
            "rotor_inertia_kgcm2": 0.5, "has_brake": false}
}
```
Transmission types: `lead_screw` (lead, efficiency, optional screw diameter/length to compute screw inertia), `belt` (pulley radius, efficiency). Rotor inertia can be provided in `kg·m²` or `kg·cm²`.

## Sign Conventions (A Single Wrong Sign Invalidates the Result)

- **Forward direction** = uphill / opposing external load; `incline_deg` is `0` for horizontal and `90` for vertically upward.
- **No double-counting**: Translational mass inertia enters acceleration torque solely through "reflected inertia x angular acceleration"; static force **excludes `m·a`**.
- Friction always opposes motion (`+μ·m·g·cosθ` on both forward and return strokes); gravity component is `+` on forward stroke and `-` on return stroke.
- **Negative torque during deceleration/return = motor regeneration**: RMS uses squared values, while peak uses absolute magnitude.
- Back-driving efficiency and lead-screw self-locking vary by lead and efficiency and are **not modeled**; vertical/inclined axes must explicitly declare a holding brake, otherwise flagged `critical`.

## Evaluation Criteria

| Rule | Criterion | Default Threshold (overridable via Profile) |
|---|---|---|
| DRC-DRV-001 | `T_peak x SF <= motor peak torque` | `driveTorqueSafetyFactor`=1.5 |
| DRC-DRV-002 | `T_rms <= utilization x rated torque` | `driveRmsUtilizationMax`=0.8 |
| DRC-DRV-003 | Required max speed <= motor max speed; warning if exceeding rated speed | — |
| DRC-DRV-004 | Load-to-rotor inertia ratio | warn 5 / max 10 (varies by vendor and dynamic requirements) |
| DRC-DRV-005 | Holding brake required on vertical/inclined axes | — |
| DRC-DRV-900 | Invalid drive-spec (reports failing field path) | — |

**Thresholds are engineering starting points, not standards**; outputs echo the applied thresholds alongside each item's "% margin" and "governing constraint." When motor specs are missing, corresponding items report `info` (**never treated as pass**).

## Formulas

Linear speed -> transmission shaft: lead screw `ω = v·2π/p`, belt `ω = v/r`; static torque: lead screw `T = F·p/(2π·η)`, belt `T = F·r/η`;
through gear ratio `i`: at motor shaft `T/(i·η_g)`, reflected inertia `J/i²`, speed `× i`.
Reflected load inertia: lead screw `m·(p/2π)²`, belt `m·r²`; screw shaft itself `π·ρ·L·d⁴/32`.
Acceleration torque `T_acc = [(J_load/η + J_screw + J_extra)/(i²·η_g) + J_rotor]·α`; inertia ratio still uses physical reflected inertia without efficiency factors.
Deceleration and back-driving efficiencies are not modeled separately, so when peak and RMS torques meet thresholds, only `info` is emitted and it must not be treated as a passing selection.
Across all segments -> `T_peak` (absolute maximum), `T_rms = √(ΣT²·t / Σt)`. See [Kollmorgen Application Sizing Guide](https://www.kollmorgen.com/sites/default/files/public_downloads/Application_Sizing_Guide_en-US.pdf).
The motion profile is a symmetric trapezoid, degenerating to a triangle when stroke is too short to reach maximum speed.

## Verification

`tests/test_drive_sizing.py`: anchored against a hand-calculated full example; **belt === lead screw physical equivalence** (two distinct code paths agree across 9 physical quantities); gear-ratio reflection laws; trapezoidal/triangular displacement conservation; vertical-axis return gravity-assist sign; complete rejection of invalid inputs.

## Boundaries and Future Work

- Not yet covered: screw critical speed and buckling stability, belt tension, bearing/component life, torque-speed curve (continuous/intermittent envelope), direct-drive rotary loads.
- Inputs `has_brake` and `round_trip` must be JSON booleans; omitting rotor or transmission inertia can underestimate required torque. Dwell calculations assume any declared brake is engaged and must be verified by an engineer.
- Mass, stroke, and motor specs must come from verified sources; this tool does not automatically read model mass or vendor motor catalogs.
