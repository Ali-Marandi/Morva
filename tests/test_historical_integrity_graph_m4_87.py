from __future__ import annotations

import json
from pathlib import Path

MANIFEST_PATH = Path("contracts/historical_integrity_manifest_m4_86.json")


def _manifest() -> dict[str, object]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _layer_module(path: str) -> str:
    normalized = path.removesuffix(".py")
    assert normalized.startswith("src/")
    return normalized[4:].replace("/", ".")


def _graph() -> tuple[list[str], dict[str, set[str]]]:
    manifest = _manifest()
    layers = manifest["layers"]
    sequence = manifest["graph"]["sequence"]
    ids = [layer["id"] for layer in layers]
    module_to_id = {_layer_module(layer["path"]): layer["id"] for layer in layers}
    edges: dict[str, set[str]] = {layer_id: set() for layer_id in ids}

    for layer in layers:
        source_id = layer["id"]
        for required in layer["required_modules"]:
            target_id = module_to_id.get(required)
            if target_id is not None:
                edges[source_id].add(target_id)
    return sequence, edges


def _visit(
    node: str,
    edges: dict[str, set[str]],
    visiting: set[str],
    visited: set[str],
) -> None:
    if node in visiting:
        raise AssertionError(f"cycle detected at {node}")
    if node in visited:
        return
    visiting.add(node)
    for dependency in edges[node]:
        _visit(dependency, edges, visiting, visited)
    visiting.remove(node)
    visited.add(node)


def test_integrity_graph_sequence_is_manifest_complete() -> None:
    sequence, edges = _graph()
    assert len(sequence) == len(edges) == 5
    assert len(set(sequence)) == len(sequence)
    assert set(sequence) == set(edges)


def test_integrity_graph_is_acyclic() -> None:
    _, edges = _graph()
    visited: set[str] = set()
    for node in edges:
        _visit(node, edges, set(), visited)


def test_integrity_graph_dependencies_point_backward() -> None:
    sequence, edges = _graph()
    position = {layer_id: index for index, layer_id in enumerate(sequence)}
    for layer_id, dependencies in edges.items():
        for dependency in dependencies:
            assert position[dependency] < position[layer_id], (
                f"{layer_id} depends on later layer {dependency}"
            )


def test_integrity_graph_declares_expected_milestones_in_order() -> None:
    sequence, _ = _graph()
    assert sequence == [
        "m4_77_runtime",
        "m4_78_runtime",
        "m4_79_persistence",
        "m4_80_runtime",
        "m4_81_persistence",
    ]
