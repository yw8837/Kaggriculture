from __future__ import annotations

import argparse
import ast
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentSpec:
    output_name: str
    notebook_dir: str
    cell_indexes: tuple[int, ...]
    method: str
    variable: str | None = None
    entrypoint: str = "agent"


SPECS = (
    AgentSpec(
        "harvest_pulse.py",
        "alexandergremyakov__harvest-pulse-adaptive-landrush-baseline",
        (1,),
        "writefile",
    ),
    AgentSpec(
        "getting_started.py",
        "bovard__kaggriculture-getting-started",
        (10,),
        "writefile",
        entrypoint="melon_maxxer",
    ),
    AgentSpec("chaitanya_mixed.py", "chaitanyajamble__kaggriculture", (1,), "writefile"),
    AgentSpec(
        "basic_simple.py", "dheerajkannaujiya__start-with-basic-simple", (2,), "writefile"
    ),
    AgentSpec(
        "diversified_scheduler.py",
        "ektarr__diversified-scheduler-baseline-kaggriculture",
        (5,),
        "literal",
        "AGENT_SOURCE",
    ),
    AgentSpec(
        "visualized_guide.py",
        "georgymamarin__kaggriculture-visualized-what-every-crop-pays",
        (39,),
        "writefile",
    ),
    AgentSpec("pavlo_baseline.py", "pavloivanin__kaggriculture-baseline", (1,), "writefile"),
    AgentSpec(
        "scenario_aware.py",
        "pilkwang__kaggriculture-scenario-aware-economic-policy",
        (8, 10, 12, 14, 16),
        "agentfile",
    ),
    AgentSpec(
        "barnyard_economist.py",
        "romanrozen__strong-statr-baseline-agent-lb-950",
        (6,),
        "writefile",
    ),
    AgentSpec(
        "hamburger_current.py",
        "romantamrazov__kaggriculture-hamburger",
        (2,),
        "literal",
        "AGENT_SOURCE",
    ),
    AgentSpec(
        "hamburger_base.py",
        "romantamrazov__kaggriculture-hamburger",
        (6,),
        "literal",
        "BASE_AGENT_SOURCE",
    ),
    AgentSpec(
        "yumerous.py",
        "romantamrazov__kaggriculture-yumerous",
        (4,),
        "literal",
        "AGENT_SOURCE",
    ),
)


def _cell_source(notebook: dict, index: int) -> str:
    source = notebook["cells"][index]["source"]
    return "".join(source) if isinstance(source, list) else source


def _strip_magic(source: str) -> str:
    lines = source.splitlines()
    if not lines or not lines[0].startswith("%%"):
        raise ValueError("expected a notebook cell magic on the first line")
    return "\n".join(lines[1:]).lstrip("\n") + "\n"


def _literal(source: str, variable: str) -> str:
    tree = ast.parse(source)
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        if any(isinstance(target, ast.Name) and target.id == variable for target in targets):
            value = ast.literal_eval(node.value)
            if not isinstance(value, str):
                raise TypeError(f"{variable} is not a string")
            return value.rstrip() + "\n"
    raise ValueError(f"assignment to {variable} not found")


def extract_agent(notebook: dict, spec: AgentSpec) -> str:
    sources = [_cell_source(notebook, index) for index in spec.cell_indexes]
    if spec.method == "writefile":
        return _strip_magic(sources[0])
    if spec.method == "agentfile":
        return "".join(_strip_magic(source) for source in sources)
    if spec.method == "literal" and spec.variable:
        return _literal(sources[0], spec.variable)
    raise ValueError(f"unsupported extraction method: {spec.method}")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def run(source_root: Path, output_root: Path) -> dict:
    output_root.mkdir(parents=True, exist_ok=True)
    records = []
    for spec in SPECS:
        notebooks = sorted((source_root / spec.notebook_dir).glob("*.ipynb"))
        if len(notebooks) != 1:
            raise ValueError(f"expected one notebook for {spec.notebook_dir}, found {len(notebooks)}")
        notebook_path = notebooks[0]
        notebook_bytes = notebook_path.read_bytes()
        notebook = json.loads(notebook_bytes)
        source = extract_agent(notebook, spec)
        if spec.entrypoint != "agent":
            source = f"{source.rstrip()}\n\nagent = {spec.entrypoint}\n"
        compile(source, spec.output_name, "exec")
        tree = ast.parse(source)
        has_agent_function = any(
            isinstance(node, ast.FunctionDef) and node.name == "agent" for node in tree.body
        )
        has_agent_alias = any(
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "agent" for target in node.targets)
            for node in tree.body
        )
        if not (has_agent_function or has_agent_alias):
            raise ValueError(f"top-level agent function missing in {spec.output_name}")
        output_path = output_root / spec.output_name
        output_bytes = source.encode("utf-8")
        output_path.write_bytes(output_bytes)
        records.append(
            {
                "output": output_path.as_posix(),
                "source_notebook": notebook_path.as_posix(),
                "source_notebook_sha256": _sha256(notebook_bytes),
                "source_cells": list(spec.cell_indexes),
                "extraction_method": spec.method,
                "source_entrypoint": spec.entrypoint,
                "output_sha256": _sha256(output_bytes),
                "bytes": len(output_bytes),
            }
        )
    manifest = {"schema_version": 1, "agents": records}
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract public Kaggle agents reproducibly")
    parser.add_argument("--source", type=Path, default=Path("references/kaggle-kernels"))
    parser.add_argument(
        "--output", type=Path, default=Path("artifacts/opponents/public_kaggle")
    )
    args = parser.parse_args()
    manifest = run(args.source, args.output)
    print(json.dumps({"agents": len(manifest["agents"]), "output": str(args.output)}))


if __name__ == "__main__":
    main()
