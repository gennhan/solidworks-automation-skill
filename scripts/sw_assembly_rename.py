"""装配体副本改名：计划、引用闭包及受控执行。"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence
import json
import math
import os
import shutil

try:
    from .sw_file_rename import _valid_filename
    from .sw_connect import get_com_member
    from .sw_read_guard import SolidWorksReadGuard
    from .sw_rename_copy import _open_checked, _sha256, _snapshot
    from .sw_session import SolidWorksSession
    from .sw_assembly import iter_feature_tree
    from .sw_review import _feature_health
except ImportError:
    from sw_file_rename import _valid_filename
    from sw_connect import get_com_member
    from sw_read_guard import SolidWorksReadGuard
    from sw_rename_copy import _open_checked, _sha256, _snapshot
    from sw_session import SolidWorksSession
    from sw_assembly import iter_feature_tree
    from sw_review import _feature_health


def prepare_assembly_plan(root: str | Path, plans: Sequence[Mapping[str, Any]]) -> list[dict[str, str]]:
    """校验显式文件映射；不打开 SolidWorks，也不修改文件。"""
    root_path = Path(root).expanduser().resolve(strict=True)
    if not root_path.is_file() or root_path.suffix.casefold() != ".sldasm":
        raise ValueError("Root document must be an existing SLDASM")
    if not isinstance(plans, list) or not 1 <= len(plans) <= 200:
        raise ValueError("Plan must contain 1..200 files")
    result, sources, targets, original_names = [], set(), set(), set()
    for row in plans:
        if not isinstance(row, Mapping) or row.get("status") not in ("planned", "unchanged"):
            raise ValueError("Plan contains invalid or blocked entries")
        source, name = row.get("source"), row.get("new_name")
        if not isinstance(source, str) or not source or not isinstance(name, str):
            raise ValueError("Source path and target name must be strings")
        source_path = Path(source).expanduser().absolute()
        if source_path.is_symlink() or not source_path.is_file() or source_path.name.startswith("~$"):
            raise ValueError("Source file does not exist, is a symlink, or is a lock file")
        extension = source_path.suffix.casefold()
        if extension not in (".sldprt", ".sldasm"):
            raise ValueError("Only parts and assemblies are supported")
        if (Path(name).name != name or not _valid_filename(name) or name.startswith("~$")
                or Path(name).suffix.casefold() != extension):
            raise ValueError("Target name is invalid or does not match file type")
        source_path = source_path.resolve(strict=True)
        key, target_key = str(source_path).casefold(), name.casefold()
        if key in sources or target_key in targets:
            raise ValueError("Duplicate source file or target name")
        if source_path.name.casefold() in original_names:
            raise ValueError("Duplicate source filename; SolidWorks may erroneously reuse same-named documents")
        sources.add(key)
        targets.add(target_key)
        original_names.add(source_path.name.casefold())
        result.append({"source": str(source_path), "new_name": name})
    if str(root_path).casefold() not in sources:
        raise ValueError("Plan does not include root assembly")
    if original_names & targets:
        raise ValueError("Copy name must not match any source filename to avoid open-document name conflicts")
    return result


def validate_reference_graph(root: str | Path, entries: Sequence[Mapping[str, str]],
                             dependencies: Mapping[str, Sequence[str]]) -> list[str]:
    """校验完整闭包和循环，返回子文档先于父文档的路径顺序。"""
    by_key = {str(Path(item["source"]).resolve()).casefold(): str(Path(item["source"]).resolve()) for item in entries}
    root_key = str(Path(root).resolve()).casefold()
    if len(by_key) != len(entries) or root_key not in by_key:
        raise ValueError("Duplicate source file or root document missing from plan")
    graph = {}
    for parent, children in dependencies.items():
        parent_key = str(Path(parent).resolve()).casefold()
        if parent_key not in by_key or parent_key in graph or not isinstance(children, (list, tuple)):
            raise ValueError("Invalid reference list")
        resolved_children = []
        for child in children:
            if not isinstance(child, str) or not Path(child).is_absolute():
                raise ValueError("Reference path must be a verifiable absolute path")
            child_key = str(Path(child).resolve()).casefold()
            if child_key not in by_key:
                raise ValueError("Reference not in plan; cannot copy safely")
            if child_key not in resolved_children:
                resolved_children.append(child_key)
        graph[parent_key] = resolved_children
    if set(graph) != set(by_key):
        raise ValueError("Every source document must have a confirmed reference list")
    state, order = {}, []

    def visit(key):
        if state.get(key) == 1:
            raise ValueError("Circular reference detected")
        if state.get(key) == 2:
            return
        state[key] = 1
        for child in graph[key]:
            visit(child)
        state[key] = 2
        order.append(by_key[key])

    visit(root_key)
    if len(order) != len(by_key):
        raise ValueError("Plan contains files outside the root assembly reference closure")
    return order


def _direct_references(model) -> list[str]:
    """返回官方 GetDependencies2 的直接依赖；读取不完整时停止。"""
    values = get_com_member(model, "GetDependencies2", False, True, False)
    if not isinstance(values, (list, tuple)) or len(values) % 2:
        raise ValueError("Unable to confirm direct reference list")
    paths = []
    for index in range(1, len(values), 2):
        path = str(values[index] or "")
        if not path or not Path(path).is_absolute() or not Path(path).is_file():
            raise ValueError("Reference missing or path cannot be confirmed")
        paths.append(str(Path(path).resolve()))
    return paths


def _assembly_snapshot(model) -> dict[str, Any]:
    if get_com_member(model, "GetType") != 2 or get_com_member(model, "GetSaveFlag") not in (False, 0):
        raise ValueError("Document must be a saved assembly with no unsaved changes")
    configurations = get_com_member(model, "GetConfigurationNames")
    if not isinstance(configurations, (tuple, list)) or len(configurations) != 1:
        raise ValueError("Only single-configuration assemblies are currently supported")
    extension = get_com_member(model, "Extension")
    counts = (get_com_member(extension, "ListExternalFileReferencesCount"),
              get_com_member(model, "ListAuxiliaryExternalFileReferencesCount"))
    if any(isinstance(count, bool) or not isinstance(count, int) or count != 0 for count in counts):
        raise ValueError("Assembly contains external file references or reference count cannot be confirmed")
    components = get_com_member(model, "GetComponents", False)
    if not isinstance(components, (tuple, list)) or not components:
        raise ValueError("Unable to confirm assembly components")
    records = []
    for component in components:
        path = str(get_com_member(component, "GetPathName") or "")
        state = get_com_member(component, "GetSuppression")
        virtual = get_com_member(component, "IsVirtual")
        model_ref = get_com_member(component, "GetModelDoc2")
        if not path or not Path(path).is_file() or state not in (2, 3) or virtual is not False or model_ref is None:
            raise ValueError("Component is missing, virtual, suppressed, or not fully resolved")
        if get_com_member(model_ref, "GetSaveFlag") not in (False, 0):
            raise ValueError("Component has unsaved changes")
        transform = get_com_member(component, "Transform2")
        matrix = get_com_member(transform, "ArrayData") if transform is not None else None
        if not isinstance(matrix, (tuple, list)) or len(matrix) != 16 or not all(math.isfinite(float(v)) for v in matrix):
            raise ValueError("Unable to confirm component transform")
        records.append({"path": str(Path(path).resolve()), "configuration": str(get_com_member(component, "ReferencedConfiguration") or ""),
                        "state": state, "transform": [float(v) for v in matrix]})
    mates = []
    for feature, _ in iter_feature_tree(model):
        kind = str(get_com_member(feature, "GetTypeName2") or "")
        if kind.startswith("Mate") and kind != "MateGroup":
            health = _feature_health(feature)
            if health.get("health_status") != "healthy":
                raise ValueError("Mate is unhealthy or its health status cannot be confirmed")
            mate = get_com_member(feature, "GetSpecificFeature2")
            count = get_com_member(mate, "GetMateEntityCount")
            if isinstance(count, bool) or not isinstance(count, int) or not 1 <= count <= 64:
                raise ValueError("Unable to confirm mate reference count")
            entities = []
            for index in range(count):
                entity = get_com_member(mate, "MateEntity", index)
                component = get_com_member(entity, "ReferenceComponent")
                reference = get_com_member(entity, "Reference")
                if component is None or reference is None:
                    raise ValueError("Mate reference is missing or unsupported for resolution")
                owner = get_com_member(component, "GetModelDoc2")
                owner_extension = get_com_member(owner, "Extension")
                # 装配环境的持久 ID 会随文件名变化，必须映射回组件文档比较。
                underlying = get_com_member(owner_extension, "GetCorresponding2", reference)
                identity = get_com_member(owner_extension, "GetPersistReference3", underlying) if underlying is not None else None
                parameters = get_com_member(entity, "EntityParams")
                component_id = get_com_member(component, "GetID")
                path = str(get_com_member(component, "GetPathName") or "")
                reference_type = get_com_member(entity, "ReferenceType2")
                if (not isinstance(identity, (list, tuple, bytes, memoryview)) or not identity
                        or not path or not Path(path).is_file()
                        or isinstance(component_id, bool) or not isinstance(component_id, int) or component_id < 0
                        or isinstance(reference_type, bool) or not isinstance(reference_type, int)
                        or not isinstance(parameters, (list, tuple)) or not parameters
                        or not all(math.isfinite(float(value)) for value in parameters)):
                    raise ValueError("Mate entity identity or geometry parameters cannot be confirmed")
                entities.append({"path": str(Path(path).resolve()), "component_id": component_id,
                                 "reference_type": reference_type, "parameters": list(parameters),
                                 "persistent_id": list(identity)})
            mates.append({"name": str(get_com_member(feature, "Name") or ""), "type": kind,
                          "error_code": health["error_code"], "entities": entities})
    return {"components": records, "mates": sorted(mates, key=lambda item: (item["name"], item["type"]))}


def _compare_assembly(before: Mapping[str, Any], after: Mapping[str, Any], destination_by_source: Mapping[str, str], *, identity_comparator=None) -> None:
    mate_metadata = lambda rows: [{key: value for key, value in row.items() if key != "entities"} for row in rows]
    if mate_metadata(before["mates"]) != mate_metadata(after["mates"]) or len(before["components"]) != len(after["components"]):
        raise ValueError("Assembly mate or component count mismatch")
    for original, copied in zip(before["mates"], after["mates"]):
        old_entities, new_entities = original.get("entities"), copied.get("entities")
        if not old_entities or not new_entities or len(old_entities) != len(new_entities) or identity_comparator is None:
            raise ValueError("Mate is missing per-entity verification evidence")
        for old, new in zip(old_entities, new_entities):
            expected = destination_by_source.get(old["path"].casefold())
            if (expected is None or expected.casefold() != new["path"].casefold()
                    or old["component_id"] != new["component_id"] or old["reference_type"] != new["reference_type"]
                    or len(old["parameters"]) != len(new["parameters"])
                    or not all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9) for a, b in zip(old["parameters"], new["parameters"]))
                    or identity_comparator(new["path"], old["persistent_id"], new["persistent_id"]) is not True):
                raise ValueError("Mate component, geometric entity, or parameter mismatch")
    remaining = list(after["components"])
    for item in before["components"]:
        expected = destination_by_source.get(item["path"].casefold())
        if expected is None:
            raise ValueError("Component reference not included in plan")
        for candidate in remaining:
            if (candidate["path"].casefold() == expected.casefold()
                    and candidate["configuration"] == item["configuration"] and candidate["state"] == item["state"]
                    and all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9)
                            for a, b in zip(item["transform"], candidate["transform"]))):
                remaining.remove(candidate)
                break
        else:
            raise ValueError("Component path, configuration, state, or transform mismatch")


def copy_assembly(root: str | Path, plans: Sequence[Mapping[str, Any]], output_dir: str | Path) -> dict[str, Any]:
    """复制单配置装配及依赖，仅在隔离副本中替换引用并重开核验。"""
    entries = prepare_assembly_plan(root, plans)
    target = Path(output_dir).expanduser().absolute()
    if target.exists() or target.is_symlink() or not target.parent.is_dir():
        raise ValueError("Output directory must not exist and its parent directory must exist")
    target.mkdir(mode=0o700, exist_ok=False)
    report = {"status": "blocked", "reviewRequired": True, "outputs": [], "mate_reference_checks": [], "error": None,
              "limitations": ["Supports only single-configuration, fully resolved parts without external references and single-configuration assemblies.", "Source files and their external usages are not modified.", "Toolbox parts, drawings, virtual or suppressed components, multiple configurations, and other external references are unsupported."]}
    try:
        with SolidWorksReadGuard(), SolidWorksSession(version=2026, visible=True) as session:
            hashes, snapshots, dependencies = {}, {}, {}
            for entry in entries:
                source = Path(entry["source"])
                hashes[str(source)] = _sha256(source)
                model = _open_checked(session, source)
                dependencies[str(source)] = _direct_references(model)
                if source.suffix.casefold() == ".sldprt":
                    toolbox = get_com_member(get_com_member(model, "Extension"), "ToolboxPartType")
                    if isinstance(toolbox, bool) or toolbox != 0:
                        raise ValueError("Toolbox parts or parts whose type cannot be confirmed are unsupported")
                snapshots[str(source)] = _snapshot(model) if source.suffix.casefold() == ".sldprt" else _assembly_snapshot(model)
                if any(owned is model for owned in session._owned_documents):
                    session.close(model=model)
            order = validate_reference_graph(root, entries, dependencies)
            destinations = {item["source"].casefold(): str(target / item["new_name"]) for item in entries}
            for source in order:
                with Path(source).open("rb") as reader, Path(destinations[source.casefold()]).open("xb") as writer:
                    shutil.copyfileobj(reader, writer, length=1024 * 1024)
                    writer.flush()
                    os.fsync(writer.fileno())
                if _sha256(Path(source)) != hashes[source] or _sha256(Path(destinations[source.casefold()])) != hashes[source]:
                    raise RuntimeError("Source file changed or copy checksum verification failed")
            for source in order:
                for reference in dependencies[source]:
                    if not session.sw.ReplaceReferencedDocument(destinations[source.casefold()], reference, destinations[reference.casefold()]):
                        raise RuntimeError("Failed to replace copy reference")
            for source in order:
                copy_path = Path(destinations[source.casefold()])
                model = _open_checked(session, copy_path)
                if copy_path.suffix.casefold() == ".sldasm":
                    owners = {str(Path(get_com_member(component, "GetPathName")).resolve()).casefold(): get_com_member(component, "GetModelDoc2")
                              for component in get_com_member(model, "GetComponents", False)}

                    def same_identity(path, before, after):
                        owner_extension = get_com_member(owners[path.casefold()], "Extension")
                        if hasattr(owner_extension, "_FlagAsMethod"):
                            owner_extension._FlagAsMethod("IsSamePersistentID")
                        # pywin32 的 tuple 会转为 VARIANT 数组；此 API 要求 SAFEARRAY(byte)。
                        return get_com_member(owner_extension, "IsSamePersistentID", memoryview(bytes(before)), memoryview(bytes(after))) == 1

                    actual = _assembly_snapshot(model)
                    _compare_assembly(snapshots[source], actual, destinations, identity_comparator=same_identity)
                    report["mate_reference_checks"].append({"source": source, "mate_count": len(actual["mates"]),
                                                            "entity_count": sum(len(row["entities"]) for row in actual["mates"]),
                                                            "status": "pass"})
                else:
                    actual = _snapshot(model)
                    expected = snapshots[source]
                    if not math.isclose(actual["volume_mm3"], expected["volume_mm3"], rel_tol=1e-7, abs_tol=1e-5) or any(
                            not math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-5) for a, b in zip(actual["size_mm"], expected["size_mm"])):
                        raise RuntimeError("Part copy geometry mismatch")
                if any(owned is model for owned in session._owned_documents):
                    session.close(model=model)
                report["outputs"].append({"source": source, "source_sha256": hashes[source], "path": str(copy_path), "sha256": _sha256(copy_path)})
            if any(_sha256(Path(path)) != digest for path, digest in hashes.items()):
                raise RuntimeError("Source file changed")
            report["status"] = "review_required"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
    manifest = target / "assembly-copy-manifest.json"
    with manifest.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    report["manifest"] = str(manifest)
    return report


def main(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Create a renamed copy of a single-configuration assembly in a new directory and verify components and mates.")
    parser.add_argument("--root", required=True, help="Source root assembly")
    parser.add_argument("--plan", required=True, help="JSON file containing the plans list")
    parser.add_argument("--output-dir", required=True, help="New directory (must not exist)")
    args = parser.parse_args(argv)
    path = Path(args.plan).expanduser()
    if path.stat().st_size > 4 * 1024 * 1024:
        parser.error("Plan file exceeds 4 MiB")
    plan = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(plan, dict):
        parser.error("Plan must be a JSON object")
    result = copy_assembly(args.root, plan.get("plans"), args.output_dir)
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 2 if result["status"] == "review_required" else 1


if __name__ == "__main__":
    raise SystemExit(main())
