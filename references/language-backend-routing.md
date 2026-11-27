# Multi-Language CAD Backend Routing

## Core Principles

Do not generalize "a specific `I*` method cannot be called from Python" into "the entire capability cannot use Python." First clarify whether the goal is a business capability or an exact interface signature, then select in this order:

1. When an Automation-compatible counterpart exists (non-`I` method, `CreateMassProperty`, etc.), prefer Python `pywin32`.
2. When encountering `SAFEARRAY`, `BYREF`, or `object/out` marshaling differences, try explicit `VARIANT`, `comtypes`, and C# PIA in turn, always reading back actual artifacts.
3. Only when official documentation explicitly states "in-process, unmanaged C++ only" and the task strictly requires native interface semantics should an isolated native C++ Add-in/bridge be used.
4. Events, `PropertyManagerPage`, `TaskPane`, and long-lived callbacks belong in a C# Add-in.
5. Switching languages cannot bypass missing licenses, missing add-ins, or data that the API simply does not expose.

## Executable Queries

```powershell
# 查看全部原子操作和候选后端
python scripts/backend_router.py --list

# 常规底层数组任务：允许 Automation 等价接口，优先 Python
python scripts/backend_router.py `
  --operation solidworks_pointer_array_api `
  --available solidworks-com-pywin32

# 明确要求原始 I* 指针语义：选择原生 C++
python scripts/backend_router.py `
  --operation solidworks_pointer_array_api `
  --available solidworks-com-pywin32 `
  --available solidworks-native-cpp `
  --exact-api

# 已知 SW2026 SP1.1 保持线阻塞：返回 KNOWN_HOST_REVISION_BLOCKER
python scripts/backend_router.py `
  --operation fillet_hold_lines_exact `
  --available solidworks-native-cpp `
  --solidworks-revision 34.1.1
```

The single source of truth for capabilities and routing is `capabilities.yaml`. Callers should pass actually detected backends, SolidWorks Revision, add-ins, and license states to the router, never mistaking "listed in manifest" for "available on this machine." When `--available` is omitted, the router conservatively returns `unavailable` rather than assuming runtimes are installed.

## Verified Interface Boundaries

| Interface / Scenario | Official Boundary | Preferred Strategy |
|---|---|---|
| `ISldWorks.IGetDocuments` | Returns pointer array; in-process unmanaged C++ only | Use Automation interface for general document traversal; C++ only for exact raw semantics |
| `IModelDocExtension.IGetMassProperties` / `IBody2.IGetMassProperties` | Returns double pointer array; unsupported in managed languages | Prefer `GetMassProperties` / `CreateMassProperty`; C++ only for raw arrays |
| `IModelDocExtension.IListExternalFileReferences` | Multiple pointer arrays; in-process unmanaged C++ only | Prefer supported Automation dependency/external-reference routes; C++ only for strict raw semantics |
| `ISldWorks.IGetDocumentDependencies2` | Native string pointers; in-process unmanaged C++ only | Use `GetDependencies2` for standard delivery; C++ only for raw interface |
| `IModelDoc2.IGetConfigurationNames` | Name pointer array; in-process unmanaged C++ only | Use `GetConfigurationNames` in Python/C# |
| `ISimpleFilletFeatureData2.ISetHoldLines` | In-process unmanaged C++ only | Native C++ is the only exact path; SW2026 SP1.1 known host fault remains blocked |
| `IPropertyManagerPage2` / Events / TaskPane | Requires stable handlers and Add-in lifecycle | C# Add-in; Python handles only external orchestration |
| `IAnnotation` exact text bounding box | API does not expose required data | Conservative estimation + PDF/image readback + manual visual review; changing languages cannot fabricate it |

Official references:

- [IGetDocuments](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISldWorks~IGetDocuments.html)
- [IGetMassProperties](https://help.solidworks.com/2026/english/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IModelDocExtension~IGetMassProperties.html)
- [IListExternalFileReferences](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IModelDocExtension~IListExternalFileReferences.html)
- [IGetDocumentDependencies2](https://help.solidworks.com/2026/English/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.ISldWorks~IGetDocumentDependencies2.html)
- [IGetConfigurationNames](https://help.solidworks.com/2026/english/api/sldworksapi/SOLIDWORKS.Interop.sldworks~SOLIDWORKS.Interop.sldworks.IModelDoc2~IGetConfigurationNames.html)
- [ISetHoldLines](https://help.solidworks.com/2025/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISimpleFilletFeatureData2~ISetHoldLines.html)
- [C# Add-in Template and Event Structure](https://help.solidworks.com/2026/English/api/sldworksapiprogguide/Overview/Using_SolidWorks_C__Add-In_Wizard_to_Create_C__Add-In.htm)
- [PropertyManagerPage2](https://help.solidworks.com/2026/English/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.IPropertyManagerPage2.html)

## Current Backend Roles

- Python remains the default orchestration language for standard modeling, assemblies, drawings, export, configuration families, properties, and auditing.
- C# PIA serves as a strongly typed Automation marshaling fallback, not a replacement for unmanaged `I*` pointer APIs.
- C# Add-in owns events, UI integration, and long-lived host lifecycles.
- Native C++ handles only officially restricted unmanaged interfaces and necessary low-level high-throughput geometry, requiring version allowlisting, crash isolation, and live regression tests.
- SWBasic/VBA is used for minimal main-thread reproduction and compatibility diagnostics inside SolidWorks, not as a replacement for native C++.
- Python/OCP handles headless open-format geometry; it cannot create native SolidWorks FeatureManager trees.
- AutoCAD native DWG database operations should prefer C# .NET rather than forcing Python through unstable ActiveX paths.
- CalculiX/Elmer uses Python to generate inputs, orchestrate native solvers, and audit outputs; passing checks do not equal engineering certification.

## Planned Extensions

Ordered from highest to lowest priority:

1. Productionize the C# Add-in: main-thread task queue, versioned installer, Authenticode signing, and upgrade/rollback; basic events, PropertyManagerPage, and TaskPane host already pass live SW2026 tests.
2. Safe native C++ bridge: wrap only unmanaged interfaces confirmed by official docs, with per-entry process/version gating.
3. Sheet metal expansion: multi-bend sequences, forming tools, and complex flat-pattern interference; U-channel Base Flange and flat-pattern DXF already pass live tests.
4. Weldment expansion: gussets, end caps, complex corner treatments, and multi-configuration cut lists; HSS rectangular frame with length/angle readback already passes live tests.
5. Configuration family expansion: derived configurations, display states, per-configuration suppression, and design tables; never reuse unverified legacy signatures.
6. Native Routing/Simulation adapters: enable only when complete add-in and license evidence is present.
