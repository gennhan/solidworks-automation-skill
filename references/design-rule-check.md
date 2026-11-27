# Neutral Document Design Rule Check (pilot)

DRC checks the provided `NeutralCadDocument` evidence across hole locations, wall thickness, standard parts, assemblies, drawing relationships, and optional motor/drive sizing; it complements `check-dfm`, which focuses on manufacturing processes. Results are intended for engineering review only and **cannot replace physical/live model measurements, standards compliance verification, or engineer sign-off**.

```powershell
python scripts/cad_studio.py list-drc-rules
python scripts/cad_studio.py check-drc --input examples/drc_sample_part.cadstudio.json --output out/drc.json
python scripts/cad_studio.py check-drc --input part.cadstudio.json --output out/drc.json --rule-pack drilling_panel --profile custom.json
```

MCP exposes `cadstudio_list_drc_rules` and `cadstudio_check_drc`. The former returns rules, default thresholds, and built-in rule packs; the latter reads neutral JSON plus optional `profile_paths` and writes a versioned report without overwriting existing files. Writing a report is a write operation and still requires approval under strict MCP approval mode. In discovery mode, search for "design rule check" (or `"设计规则审计"`).

Profiles are data-only JSON files and execute no code. You can override listed thresholds via `thresholds`, disable rules via `disabledRules`, and add restricted field comparisons via `customRules`. `holeEdgeDistanceRatio` multiplies the **hole diameter** to determine the minimum edge distance from hole wall to part edge, whereas `holeSpacingRatio` multiplies the larger hole's **radius** to determine the center-distance threshold—the two use different bases. For example, for a 6 mm diameter hole requiring at least 2x diameter edge distance, configure `holeEdgeDistanceRatio: 2.0`, corresponding to a 12 mm minimum edge distance. Thresholds in built-in rule packs are initial recommendations only and must be reviewed against actual operating conditions.

A `status` of `fail` indicates rule failures, and `warning` indicates warnings; if no risks are found but evidence is missing or skipped, the status is `review_required` and the CLI exits with code 2. Passing items never imply unprovided evidence is compliant; reports always retain `reviewRequired=true`. Risk scores, clause notes, and thresholds in the report do not constitute safety certification or comprehensive standards compliance proof.

Pass `--baseline` and `--fail-on-regression` to compare design revisions. If a prior issue disappears from a candidate revision simply because the corresponding evidence is missing, the gate does not treat it as fixed. The underlying `scripts/design_rule_check.py` also supports waivers with rationale, owner, and effective dates; dates are checked against the current UTC date by default, and expired or not-yet-effective waivers are not applied. Waivers are not independent approvals or electronic signatures.

Motor/drive data is provided via `metadata.drives[]`; see [drive-sizing.md](drive-sizing.md) for details. When geometric evidence is needed, read the model first through verified SolidWorks workflows and confirm units and semantics; DRC does not automatically populate all parameters from an active model.

Implementation references community contribution [PR #36](https://github.com/wzyn20051216/solidworks-automation-skill/pull/36), with thanks to contributor geekx.
