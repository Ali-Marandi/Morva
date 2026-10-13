from __future__ import annotations

import ast
import json
from pathlib import Path

MANIFEST_PATH = Path("contracts/historical_integrity_manifest_m4_86.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _path_module(path: str) -> str:
    normalized = path.removesuffix(".py")
    assert normalized.startswith("src/")
    return normalized[4:].replace("/", ".")


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
        elif isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
    return modules


def _component_map(
    manifest: dict[str, object],
) -> dict[str, str]:
    module_to_layer: dict[str, str] = {}
    for layer in manifest["layers"]:
        layer_id = layer["id"]
        component_modules = layer["component_modules"]
        assert component_modules
        assert _path_module(layer["path"]) in component_modules
        for module in component_modules:
            assert module not in module_to_layer, (
                f"component module {module} is assigned more than once"
            )
            module_to_layer[module] = layer_id
    return module_to_layer


def _declared_edges(
    manifest: dict[str, object],
    module_to_layer: dict[str, str],
) -> dict[str, set[str]]:
    edges = {layer["id"]: set() for layer in manifest["layers"]}
    for layer in manifest["layers"]:
        source_id = layer["id"]
        for module in layer["required_modules"]:
            target_id = module_to_layer.get(module)
            if target_id is not None:
                edges[source_id].add(target_id)
    return edges


def _reconstructed_edges(
    manifest: dict[str, object],
    module_to_layer: dict[str, str],
) -> dict[str, set[str]]:
    guarded_modules = set(module_to_layer)
    edges = {layer["id"]: set() for layer in manifest["layers"]}
    for layer in manifest["layers"]:
        source_id = layer["id"]
        observed = _imports(Path(layer["path"])) & guarded_modules
        declared = set(layer["required_modules"]) & guarded_modules
        assert observed == declared, (
            f"{source_id} guarded imports differ from manifest: "
            f"observed={sorted(observed)}, declared={sorted(declared)}"
        )
        edges[source_id] = {module_to_layer[module] for module in observed}
    return edges


def _visit(
    node: str,
    edges: dict[str, set[str]],
    visiting: set[str],
    visited: set[str],
) -> None:
    assert node not in visiting, f"cycle detected at {node}"
    if node in visited:
        return
    visiting.add(node)
    for dependency in edges[node]:
        _visit(dependency, edges, visiting, visited)
    visiting.remove(node)
    visited.add(node)


def test_component_module_aliases_are_complete_and_unique() -> None:
    manifest = _manifest()
    layers = manifest["layers"]
    ids = [layer["id"] for layer in layers]
    assert len(ids) == len(set(ids)) == 5
    assert set(manifest["graph"]["sequence"]) == set(ids)
    module_to_layer = _component_map(manifest)
    assert len(module_to_layer) >= len(layers)
    assert module_to_layer[
        "morva.persistence.historical_m4_75_verification_receipt_history_integrity_m4_77"
    ] == "m4_77_runtime"


def test_ast_reconstructed_edges_match_declared_graph() -> None:
    manifest = _manifest()
    module_to_layer = _component_map(manifest)
    declared = _declared_edges(manifest, module_to_layer)
    reconstructed = _reconstructed_edges(manifest, module_to_layer)
    assert reconstructed == declared


def test_reconstructed_graph_is_acyclic_and_backward_ordered() -> None:
    manifest = _manifest()
    sequence = manifest["graph"]["sequence"]
    module_to_layer = _component_map(manifest)
    edges = _reconstructed_edges(manifest, module_to_layer)
    positions = {layer_id: index for index, layer_id in enumerate(sequence)}
    assert len(sequence) == len(positions) == len(edges) == 5
    assert set(sequence) == set(edges)

    visited: set[str] = set()
    for node in sequence:
        _visit(node, edges, set(), visited)
    assert visited == set(sequence)

    for layer_id, dependencies in edges.items():
        assert layer_id not in dependencies
        for dependency in dependencies:
            assert positions[dependency] < positions[layer_id], (
                f"{layer_id} depends on later layer {dependency}"
            )


def test_manifest_graph_contains_m477_persistence_dependency() -> None:
    manifest = _manifest()
    module_to_layer = _component_map(manifest)
    edges = _reconstructed_edges(manifest, module_to_layer)
    assert "m4_77_runtime" in edges["m4_78_runtime"]
    assert "m4_77_runtime" in edges["m4_79_persistence"]
    assert "m4_77_runtime" in edges["m4_80_runtime"]
    assert "m4_77_runtime" in edges["m4_81_persistence"]
