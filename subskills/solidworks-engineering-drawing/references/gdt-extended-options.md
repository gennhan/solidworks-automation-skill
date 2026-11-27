# SW2026 Extended GD&T Structured Inputs

See [native-gdt.md](native-gdt.md) for entry points, source-file protection, and save-and-reopen rules. The fields documented here apply to both drawing-copy plans and `professionalAnnotations.geometricTolerances` in `DrawingSpec`, executed through the existing `solidworks_generate_drawing` MCP tool without adding new tools.
Legacy single-frame fields and plain-letter datum lists remain backward-compatible. Numeric examples are for API regression only and must not be used directly as production tolerances. Whenever the user requests TCVN or Vietnamese mechanical standards, load `references/tcvn_mechanical.md` (from the root skill directory) and use the ISO symbol library (`symbolLibrary: "iso"`) under the ISO Independency Principle.

## Common Datums and Datum Sub-Groups

`datums` contains up to three precedence-ordered datum compartments; each compartment may be a single letter, a single datum with modifiers, or a common datum group. Write a common group inside one compartment rather than substituting a free-form string like `"A-B"`.

```json
{
  "datums": [
    {"common": ["A", {"label": "B", "materialCondition": "M"}],
     "subDatums": [["C", "D"]]},
    "E"
  ]
}
```

The first compartment represents `A-B-(C-D)`, and the second is `E`. Every member must correspond to an existing datum or one declared in the current plan, with no duplicate letters within the same frame; a common group has 2..8 members, with up to three datum sub-groups of 2..8 members each.
Each member may independently specify `M`/`L`/`S`. Subsequent composite frames may retain only a prefix of complete datum compartments from the preceding frame and cannot split a common group.

Individual datums—and members of common groups—may also declare `modifiers`:

```json
{"label": "A", "modifiers": {
  "situation": "plane", "section": "cross", "projection": "5", "freeState": true
}}
```

`situation` accepts `plane` / `straightLine` / `point`; `section` accepts `cross` / `longitudinal`; `projection` is an explicit positive decimal length string (mm); `freeState` is a boolean.
An entire datum compartment may specify `constraints`: `translationX/Y/Z`, `rotationX/Y/Z`, `contactFeature`, `orientationOnly`, and `variableDistance` are boolean constraint flags; `translation` is an array of three signed decimal strings for the I/J/K components.
These specify feature control frame requirements and do not move model geometry. Suitability of constraints must still be confirmed by the designer.

## Frame-Level Options

For legacy single-frame items, place `options` directly on the tolerance item; for multi-frame items, place `options` inside each `frames[]` entry.
Do not supply both `frames` and top-level single-frame `options`.

| `options` Field | Structure & Meaning |
|---|---|
| `projectedZone` | `{"projection":"12","range":"4"}`; primary projection length is required, range is optional, both positive millimeter strings. Currently used for cylindrical position or axis orientation tolerances. |
| `profileZone` | Unequal profile distribution, offsets, CZ/SZ, dynamic profile, and zone constraints; see below. |
| `zoneShape` | `none` / `diameter` / `sphericalDiameter` / `square`; cylindrical/spherical diameter must agree with `diameter:true`. Composite frames cannot change zone shape. |
| `unitZone` | `separator` (`/` or `-`), positive `value`, optional `symbol`; may append `limit:{separator,value,symbol}` with second separator `X` or `-`. |
| `maxTolerance` | `{"value":"0.5","diameter":true}`; maximum tolerance must not be smaller than the primary tolerance. |
| `reciprocity` | Reciprocity requirement toggle; when enabled, the tolerance itself must also declare `materialCondition:"M"` or `"L"`. |
| `freeState` / `statistical` | Free-state and statistical tolerance flags for the tolerance value itself, expressed separately from datum-member `freeState`. |
| `symbolLibrary` | `iso` / `asme` / `gb`, mapping to `IGTOL` / `GTOL` / `GGTOL` respectively. Defaults to the legacy ISO library; composite frames cannot change symbol library. |
| `associatedFeature` | `Minimax` / `LeastSquares` / `MinimumCircumscribed` / `Tangent` / `MaximumInscribed`. |
| `derivedFeature` | Toggle for derived feature of size. |
| `associatedCharacteristic` | `C` / `CE` / `CI` / `G` / `GE` / `GI` / `X` / `N`. |
| `parametricCharacteristic` | `P` / `V` / `T` / `Q`. |
| `filters` | 1..8 explicit filter entries; see below. |

`unitZone.symbol` and `limit.symbol` allow `none`, `diameter`, `sphericalDiameter`, `square`, and `angle`.
Tolerances, lengths, offsets, and filter cutoff values use non-exponential decimal strings up to 32 characters; `NaN`, `Infinity`, scientific notation, and unsupported fields are rejected. Negative numbers are permitted only for explicit translation components; offset sign is specified via `direction`.
Material conditions on the tolerance value follow the verified native scope; schema acceptance does not prove standard compliance or geometric suitability.

### Profile and Tolerance Zone

```json
{"options": {"profileZone": {
  "offsets": [{"direction":"outside","value":"0.1"},
              {"direction":"inside","value":"0.05"}],
  "dynamic": true, "combination":"CZ",
  "constraints":["offset","angularOffset","orientationOnly"]
}}}
```

Unequal distribution uses `unequalOutside:"0.05"`, which must not exceed the total tolerance and is mutually exclusive with `offsets`.
`offsets` accepts one or two items with `direction` set to `outside` or `inside`. Unequal distribution, offsets, and dynamic profile require `line_profile` or `surface_profile`.
`combination` is `CZ` or `SZ`; the three zone constraints must not contain duplicates. Combination and constraints may be declared independently.

### Filters

```json
{"options": {"filters": [{
  "symbol":"G", "cutOff":"0.8", "shortWave":true,
  "separator":"X", "second":{"cutOff":"2.5","longWave":true}
}]}}
```

Each entry must supply a filter symbol and a positive `cutOff`, with optional `shortWave` / `longWave`.
The symbol allowlist is `G`/`S`/`SW`/`CW`/`RG`/`RS`/`OB`/`OH`/`OD`/`CB`/`CH`/`CD`/`AB`/`AH`/`AD`/`F`/`H`.
The second band has its own cutoff and flags; dual-band filters must explicitly specify `separator:"Space"` or `"X"`.

## Observed SW2026 Format Differences and Verification

Public help and the installed XSD are starting points for investigation, but the actual API does not follow them verbatim. Local testing on SW2026 SP1.1 confirmed:

- Native UI readback for CZ/SZ uses `CombinationSymbol`; the public XSD's `Combination` node is silently dropped by the API.
- The datum section flag appears after other member modifiers in actual readback.
- Unit zones fill in an empty range-symbol node, whereas `false` default nodes are omitted.

The generator constructs XML using the verified native form and strictly validates every node, value, and ordering without masking dropped options by ignoring diffs. Failure reports pinpoint the first diverging path; any missing or altered common-group member, projection length, material condition, or CZ/SZ fails review. Unknown options are blocked before connecting to CAD and never fall back to plain `Note` text.

The live-machine matrix uses only self-created test parts, checking native writes, save-and-reopen, persistent attachments, PDF/BMP outputs, and source hashes case-by-case, and inspecting the rendered `A-B`, datum sub-groups, `P` projection lengths, profile offsets, and CZ/SZ.
The rare-combination matrix is for API verification and may intentionally stack many symbols at the same test location; it is not a manufacturable drawing deliverable.
Full automated drawing generation samples must additionally pass PDF/layout inspection and visual review.

```powershell
python -m pytest -q tests/test_sw_gdt_options.py tests/test_sw_gdt_annotation.py tests/test_sw_gdt_copy.py tests/test_sw_drawing_native.py
python tests/solidworks_gdt_extended_live.py --source C:\test\self-created.slddrw --plan C:\test\gdt-plan.json
python tests/solidworks_gdt_generation_live.py --source C:\test\self-created-plate.sldprt --extended-gdt --mcp
```

Do not run live-machine tests in parallel with `test_sw_read_guard`. Outputs remain `review_required`; this feature expresses user-supplied requirements and does not automatically prove that arbitrary parameter combinations comply with manufacturing standards.
