# Vietnamese Mechanical Engineering Standards (TCVN) Reference

Use this reference whenever the user requests Vietnamese mechanical drawing standards (**TCVN**) or Vietnam manufacturing documentation. Most modern mechanical TCVN standards are harmonized with **ISO** and use **First-Angle Projection**.

---

## 1. Mandatory SolidWorks Document Baseline

Configure every SolidWorks Part, Assembly, and Drawing under TCVN with these exact document settings:

| Parameter | SolidWorks Setting | TCVN / ISO Basis |
| :--- | :--- | :--- |
| **Overall Drafting Standard** | `ISO` | Harmonized TCVN-ISO |
| **Unit System** | `MMGS` (mm, g, s) | TCVN 7583-1:2006 |
| **Projection Type** | `First Angle` (Góc chiếu thứ nhất) | TCVN 8-30:2003 (ISO 128-30) |
| **Decimal Separator** | Comma `,` (or dot `.` if CNC/ERP strictly requires) | TCVN 7284-0:2003 |
| **Technical Font** | Unicode-safe font (`ISOCPEUR`, `Arial`, or company template font) | TCVN 7284-0:2003 (ISO 3098-0) |

---

## 2. Drawing Presentation Standards (Trình bày bản vẽ)

### 2.1 Sheet Formats & Margins (TCVN 7285:2003 / ISO 5457)

| Format | Size (mm) | Default Orientation | Left Binding Margin | Top / Bottom / Right |
| :--- | :--- | :--- | :--- | :--- |
| **A0** | 841 x 1189 | Landscape | 20 mm | 10 mm |
| **A1** | 594 x 841 | Landscape | 20 mm | 10 mm |
| **A2** | 420 x 594 | Landscape | 20 mm | 10 mm |
| **A3** | 297 x 420 | Landscape | 20 mm | 10 mm |
| **A4** | 210 x 297 | Portrait | 20 mm | 10 mm |

* **Frame Border:** Continuous wide line, minimum thickness `0.7 mm`.
* **Custom Templates (Optional):** If available, load from `assets/templates-tcvn/` (e.g., `A4-TCVN.drwdot`, `A3-TCVN.drwdot`).

### 2.2 Title Block & Parts List / BOM (TCVN 3821:2008 & TCVN 3824:2008)
* **Title Block (Khung tên):** Bottom-right corner (or full bottom width on A4 portrait), max width `180 mm`. Required fields: Part Name (`Tên gọi`), Drawing No. (`Ký hiệu`), Material (`Vật liệu`), Scale (`Tỷ lệ`), Mass (`Khối lượng`), Sheet/Total (`Tờ/Số tờ`), Designed/Checked/Approved.
* **Parts List / BOM (Bảng kê):** Placed directly above the title block (growing upward) on assembly drawings, or on a separate A4 sheet. Columns: `TT`, `Ký hiệu`, `Tên gọi`, `SL`, `Vật liệu`, `Ghi chú`.

### 2.3 Scales, Lines & Text (TCVN 7286:2003, TCVN 8-20/24:2002, TCVN 7284-0:2003)
* **Preferred Scales:** Full `1:1`; Enlargement `2:1, 5:1, 10:1, 20:1, 50:1`; Reduction `1:2, 1:5, 1:10, 1:20, 1:50, 1:100`.
* **Line Width Ratio:** Maintain `2:1` between wide (`S`) and narrow (`S/2`) lines.
  * A3/A4 default: `0.5 mm` (visible outlines) / `0.25 mm` (dimension, extension, hatch, centerlines).
  * A0–A2 default: `0.7 mm` / `0.35 mm`.
* **Line Types:** Visible edges (continuous wide), hidden edges (dashed narrow), centerlines/axes (long-dashed dotted narrow), cutting planes (long-dashed dotted narrow with wide ends).
* **Text Height:** Nominal heights `2.5, 3.5, 5, 7, 10 mm`. Standard dimension text: `3.5 mm` on A3/A4.

### 2.4 Views, Sections & Hatching (TCVN 8-30:2003, TCVN 8-40:2003, TCVN 8-50:2005)
* **Projection Layout (First Angle):** Top view placed **below** front view; Left view placed to the **right** of front view. Always display the First-Angle projection symbol in the title block.
* **Sections & Cuts (Hình cắt & Mặt cắt):** Label cutting planes with uppercase letters (`A-A`, `B-B`) using arrows pointing in the viewing direction. Do **not** hatch solid shafts, bolts, pins, keys, or thin ribs cut longitudinally.
* **Hatching (Ký hiệu vật liệu):** Narrow continuous lines at $45^\circ$ (or $135^\circ$ for adjacent mating parts) for metals (`ISO Steel` / `ANSI31` pattern in SolidWorks); cross-hatched for plastics/non-metals.

### 2.5 Dimensioning Rules (TCVN 7583-1:2006 / ISO 129-1)
* Place values **above and parallel** to horizontal/inclined dimension lines, and to the **left** of vertical dimension lines (readable from bottom and right).
* Closed filled arrows ($15^\circ$ to $30^\circ$), length `3.5–4 mm`.
* Prefix rules: Diameter `Ø`, Radius `R`, Spherical diameter `SØ`, Square `□`, 45-degree chamfer `2x45°` (or `C2` only if explicitly requested).

---

## 3. Limits, Fits & Hole/Shaft Tolerances (Dung sai lỗ & Lắp ghép)

Standard basis: **TCVN 2244:1999 / TCVN 2244-1:2010 (ISO 286-1)** and **TCVN 2245:1999 (ISO 286-2)**.

### 3.1 System Selection
* **Default to Hole-Basis System (Hệ thống lỗ cơ bản - `H`):** Keep the hole lower deviation at zero (`H6, H7, H8, H9, H11`) and vary the shaft tolerance to achieve the desired fit.
* Use **Shaft-Basis System (`h`)** only for standard commercial bright-drawn shafts, bearing outer rings, or multiple components mounted on a single unstepped shaft.

### 3.2 Common Hole Tolerance Grades (Dung sai lỗ phổ biến)

| Hole Class | Typical Manufacturing Process | Typical Engineering Application |
| :--- | :--- | :--- |
| **H6** | Honing, internal grinding, precision reaming | High-precision instrument spindles, master gauges |
| **H7** | Reaming, fine boring, broaching, internal grinding | **Primary default for precision fits** (bearings, gears, couplings, dowel pins) |
| **H8** | Fine turning, drilling + reaming, CNC milling | General sliding/running fits, sleeves, bushings |
| **H9** | Standard CNC milling, drilling, boring | Loose fits, non-critical locating bores, keyways (`N9`/`JS9`) |
| **H11** | Standard drilling, punching, flame/laser cutting | Clearance holes for fasteners, coarse moving parts |

### 3.3 Preferred Hole-Basis Fits (Các lắp ghép ưu tiên)

| Fit Category | Fit Designation | Characteristics & Typical Application |
| :--- | :--- | :--- |
| **Loose Clearance** | `H11/c11` | Large clearance for dusty/corrosive environments, agricultural/heavy machinery |
| **Free Running** | `H9/d9` | Large running clearance for high-speed or thermally expanding shafts |
| **Close Running** | `H8/f7` | Accurate rotating shafts with grease/oil lubrication (general gearboxes) |
| **Sliding Fit** | `H7/g6` | Minimal clearance; precision sliding/guiding (pistons, guide bushings, valves) |
| **Locational Clearance** | `H7/h6` | Snug fit, assembled by hand without force; stationary locating rings, spigots |
| **Transition (Light)** | `H7/js6` | Very small clearance or interference; easy assembly/disassembly with light tap (couplings, pulleys) |
| **Transition (Medium)** | `H7/k6` | Accurate centering with light press/mallet (gears, bearing inner rings under light load) |
| **Transition (Tight)** | `H7/m6`, `H7/n6` | Tight centering requiring light press; keyed hubs, heavy-duty gears |
| **Interference (Press)** | `H7/p6` | Light press fit for ferrous parts; non-removable without press |
| **Interference (Heavy)** | `H7/r6`, `H7/s6` | Heavy press/shrink fit transmitting torque without keys (bronze rims, heavy collars) |

* **SolidWorks Annotation Rule:** For assembly drawings, show combined fit (e.g., `Ø40 H7/g6`). For part drawings, show the ISO tolerance class **plus** explicit numeric deviations in parentheses or stacked format (e.g., `Ø40 H7 (+0.025 / 0)`) using SolidWorks **Fit with tolerance** dimension style.

### 3.4 General Tolerances (Dung sai chung — TCVN 2263-1:2007 & TCVN 2263-2:2007 / ISO 2768)
Always add a mandatory general tolerance note above the title block when untoleranced dimensions exist:
* **General CNC / Machining default:** `General tolerances: TCVN 2263-1-mK` (`ISO 2768-mK`).
* **Fine precision machining:** `TCVN 2263-1-fH` (`ISO 2768-fH`).
* **Sheet metal / coarse parts:** `TCVN 2263-1-cL` (`ISO 2768-cL`).

---

## 4. GD&T & Surface Roughness (Dung sai hình học & Độ nhám)

### 4.1 Geometric Tolerancing (TCVN 5906:2007 / ISO 1101 & TCVN 5907:2007 / ISO 5459)
* Use SolidWorks **ISO** Geometric Tolerance frames (`Flatness`, `Perpendicularity`, `Parallelism`, `Concentricity`, `Circular/Total Runout`, `Position`).
* **Datum Targets:** Uppercase letters (`A`, `B`, `C`) inside a square frame attached to a filled or open triangle per ISO 5459.
* **Key Rule:** Never combine incompatible ASME-only modifiers unless explicitly requested; adhere to ISO Independency Principle (Envelope requirement `(E)` must be explicitly stated if needed).

### 4.2 Surface Roughness (TCVN 5707:2007 / ISO 1302)
* Primary parameter: `Ra` (in micrometers, $\mu\text{m}$), or `Rz` for very rough/very fine surfaces.
* Typical machining mapping:
  * `Ra 12.5 – 25`: Rough turning/milling, non-functional clearance faces.
  * `Ra 6.3`: Semi-rough machined surfaces, bolt seating faces.
  * `Ra 3.2`: Standard CNC machined faces, non-critical mating faces.
  * `Ra 1.6`: Precision mating faces, static sealing surfaces, keyways.
  * `Ra 0.8`: Bearing journals, oil seal seats, precision sliding fits (`H7/g6`).
  * `Ra 0.4` or finer: Ground shafts, hydraulic cylinder bores.
* Place the general roughness symbol in the **top-right corner** of the drawing, e.g., `Ra 6.3 (Ra 1.6, Ra 0.8)`.

---

## 5. Welding Standards (Tiêu chuẩn mối hàn & Kết cấu hàn)

### 5.1 Weld Symbols on Drawings (TCVN 12251:2018 / ISO 2553; legacy TCVN 3734:1989)
* **SolidWorks Setting:** Use **ISO Weld Symbol** style (dual reference line: **solid line** + **dashed identification line**).
  * Symbol placed on the **solid line** = Arrow side (phía mũi tên).
  * Symbol placed on the **dashed line** = Other side (phía đối diện mũi tên).
  * Symmetrical welds on both sides: omit the dashed line.
* **Fillet Weld Sizing (Mối hàn góc):** Explicitly prefix dimension with **`a`** (design throat thickness, chiều cao tính toán) or **`z`** (leg length, cạnh mối hàn), e.g., `a5` or `z7`, where $a \approx 0.7 \times z$.
* **Intermittent Welds:** Format as `n x l (e)` where `n` = number of weld elements, `l` = length of each element, `e` = distance between elements.
* **Weld Tail Information:** Specify welding process number per **ISO 4063** (`111` = SMAW/Hàn que, `135` = MAG/CO2, `141` = TIG) and quality level per **TCVN 7472:2005 (ISO 5817)** (`B` = stringent, `C` = intermediate/default structural, `D` = moderate).
* **Field / All-Around Flags:** Circle at bend = Weld all around; Flag at bend = Field/site weld.

### 5.2 General Tolerances for Welded Constructions (TCVN 7296:2003 / ISO 13920)
For weldment drawings, replace or supplement TCVN 2263 with a weldment tolerance note:
* **Linear & Angular classes:** `A` (finest) to `D` (coarsest).
* **Straightness, Flatness & Parallelism classes:** `E` (finest) to `H` (coarsest).
* **Standard Industrial Default:** `Weldment general tolerances: TCVN 7296-BF` (equivalent to `ISO 13920-BF`) or `TCVN 7296-CG` for heavy structural frames.

---

## 6. Threads, Fasteners & Standard Machine Elements

* **Metric Threads (TCVN 2254 / TCVN 7290 / ISO 68-1 & ISO 261):**
  * Coarse pitch: `M12` (pitch omitted). Fine pitch: `M12x1.25`.
  * Thread tolerance (TCVN 1917:1993 / ISO 965-1): Default internal `6H`, external `6g` (e.g., `M12-6H`, `M12x1.25-6g`).
  * Drawing representation (TCVN 5909:1995 / ISO 6410-1): Major diameter (external) / minor diameter (internal) drawn in **continuous wide** line; thread root drawn in **continuous narrow** line (approx. 3/4 circle in end view). Always use SolidWorks **Cosmetic Thread** rather than modeling helical geometry on standard fasteners.
* **Fastener Property Classes (TCVN 1916:1995 / ISO 898-1):** Specify bolt strength class in BOM/notes (e.g., `Bulông M10x30 - Cấp bền 8.8`, `10.9`, or stainless `A2-70` / `A4-80`).
* **Parallel Keys & Keyways (TCVN 2261:1977 / ISO 2491):** Standard shaft keyway width tolerance `N9` (normal) or `JS9` (light/sliding); hub keyway `JS9` or `P9`.

---

## 7. Agent Execution & Verification Checklist

Before finalizing any TCVN SolidWorks part or 2D drawing, verify:
1. Document drafting standard is `ISO`, unit system is `MMGS`, and sheet projection is explicitly **First Angle**.
2. Left margin is `20 mm`; no views overlap the title block, BOM, or technical notes.
3. All mating bores/shafts use **Hole-Basis (`H`)** fits where practical and display numeric deviation values on detail drawings.
4. Mandatory technical notes block above the title block includes:
   * General tolerances (`TCVN 2263-1-mK` for machined parts, or `TCVN 7296-BF` for weldments).
   * General surface roughness (top-right corner) and heat treatment / coating / deburring notes (`Vát mép sắc 0.5x45°` / `Break all sharp edges 0.5x45°`).
5. Weld symbols use ISO dual reference lines with explicit `a` or `z` leg/throat prefixes and ISO 4063 / TCVN 7472 callouts where required.
6. Any Vietnamese text in title blocks or notes renders cleanly with Unicode fonts (no missing glyphs).