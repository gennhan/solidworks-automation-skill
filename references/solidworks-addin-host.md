# SolidWorks C# Add-in Host

## Role

`dotnet/CadStudio.SolidWorks.AddinHost` is a `net48/x64` in-process host designed for long-lived event callbacks and native UI lifecycles. It does not replace short-lived Python modeling scripts, nor does it impersonate unmanaged C++-only `I*` pointer APIs; routing is governed by `capabilities.yaml::solidworks_addin_ui_events`.

The host currently provides:

- `ISwAddin.ConnectToSW/DisconnectFromSW` and `SetAddinCallbackInfo2`;
- `SldWorks` coclass events for active document change, file new, file open, and special close notifications;
- A three-command `CommandGroup`;
- A WinForms `TaskPane` using a 64-bit window handle;
- Full implementation of all 37 callbacks of SW2026 `IPropertyManagerPage2Handler9`;
- Diagnostic evidence written to `%LOCALAPPDATA%\CAD Studio\SolidWorksAddin\host-status.json`;
- Strong-name assembly identity and two deployment paths: CurrentUser COM smoke test and Machine production registration.

## Build

The local PIA directory must be specified explicitly to avoid referencing the wrong SolidWorks major version:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sw_addin_host.ps1 `
  -Action Build `
  -SolidWorksApiDir 'C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\api\redist'
```

Build outputs the assembly; Machine registration also generates and registers the sibling TLB:

```text
dotnet\CadStudio.SolidWorks.AddinHost\bin\Release\net48\CadStudio.SolidWorks.AddinHost.dll
dotnet\CadStudio.SolidWorks.AddinHost\bin\Release\net48\CadStudio.SolidWorks.AddinHost.tlb
```

## Registration and Verification

CurrentUser mode validates CLR/COM activation only and does not write fake SolidWorks Add-ins discovery keys:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sw_addin_host.ps1 -Action Register -RegistrationScope CurrentUser -SolidWorksApiDir '<api\redist>'
powershell -ExecutionPolicy Bypass -File scripts\sw_addin_host.ps1 -Action ComSmoke -RegistrationScope CurrentUser
```

In-process loading by SolidWorks requires Machine registration. Standard PowerShell triggers a single UAC prompt, and the elevated child process runs only the fixed-GUID build/register action:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sw_addin_host.ps1 -Action Register -RegistrationScope Machine -SolidWorksApiDir '<api\redist>'
powershell -ExecutionPolicy Bypass -File scripts\sw_addin_host.ps1 -Action Probe -RegistrationScope Machine
```

Machine mode runs 64-bit `.NET Framework RegAsm /codebase /tlb`, writing COM classes, the type library, `HKLM\SOFTWARE\SOLIDWORKS\Addins\{GUID}`, and the current-user startup key. Uninstall using the same assembly path:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\sw_addin_host.ps1 -Action Unregister -RegistrationScope Machine
```

## Acceptance Gate

`ISldWorks.LoadAddIn()` returning `swSuccess=0` is not sufficient by itself. A live Probe must also read the diagnostic file and satisfy every condition below:

1. `status == connected`;
2. `callbackRegistered == true`;
3. CommandGroup, TaskPane, and PropertyManagerPage are all `true`;
4. After creating a temporary part, `file_new` and active-document event counts increment, and after `CloseDoc`, `GetDocumentCount() == 0`;
5. `errors` is empty.

Run `python scripts/sw_addin_host.py` or MCP `solidworks_addin_host_status` to inspect assembly, TLB, registration scope, diagnostic contents, and exact blocker codes. CurrentUser COM registration cannot substitute for the Machine gate above.

## SW2026 Live Evidence

Local SW2026 SP1.1 (Revision `34.1.1`) has passed full regression testing:

- The Add-in is instantiated inside `SLDWORKS.exe` with `LoadAddIn=0`;
- `SetAddinCallbackInfo2`, application events, three-command CommandGroup, TaskPane, and PropertyManagerPage are all ready;
- All 37 callbacks of `IPropertyManagerPage2Handler9` are hosted by a public, COM-visible handler exposing `AutoDispatch`;
- `file_new` event count reached 1, open document count returned to 0 after closing the temporary part, and diagnostic errors remained empty;
- Regression output is saved to `output/addin-host-real/addin_host_regression_result.json`.

The regression also confirmed two failure gates: without the TLB, SW2026 may load the DLL and return `LoadAddIn=0` without instantiating `ISwAddin`; and if the PMP Handler exposes only `IUnknown` without `IDispatch`, `ICreatePropertyManagerPage` throws `InvalidCastException`.

## Known Limitations

- The repository assembly is strong-name signed for stable assembly identity, which is not a trusted-publisher Authenticode code signature. Enterprise distribution should still sign the DLL/installer via the release pipeline.
- SolidWorks locks loaded DLLs; run `UnloadAddIn` or exit SolidWorks cleanly before rebuilding rather than force-overwriting.
- Application-level `FileCloseNotify` fires only after drawing `CloseAndReopen`; for standard parts/assemblies, monitor open document counts or subscribe to document-level events.
- CommandManager layouts persist into user profiles. Keep the GUID, CommandGroup ID, and command user IDs stable after release.
- The Add-in is suited for UI, events, and long-lived callbacks; standard modeling should continue using the existing Python Automation wrappers.

## Official References

- [ISwAddin Members (SOLIDWORKS API Help 2026)](https://help.solidworks.com/2026/english/api/swpublishedapi/SolidWorks.Interop.swpublished~SolidWorks.Interop.swpublished.ISwAddin_members.html)
- [Using the C# Add-in Wizard (SOLIDWORKS API Help 2026)](https://help.solidworks.com/2026/English/api/sldworksapiprogguide/Overview/Using_SolidWorks_C__Add-In_Wizard_to_Create_C__Add-In.htm)
- [IPropertyManagerPage2Handler9 Members (SOLIDWORKS API Help 2026)](https://help.solidworks.com/2026/english/api/swpublishedapi/SolidWorks.Interop.swpublished~SolidWorks.Interop.swpublished.IPropertyManagerPage2Handler9_members.html)
- [LoadAddIn Method (SOLIDWORKS API Help 2026)](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.ISldWorks~LoadAddIn.html)
- [FileCloseNotify Delegate (SOLIDWORKS API Help 2026)](https://help.solidworks.com/2026/english/api/sldworksapi/SolidWorks.Interop.sldworks~SolidWorks.Interop.sldworks.DSldWorksEvents_FileCloseNotifyEventHandler.html)
