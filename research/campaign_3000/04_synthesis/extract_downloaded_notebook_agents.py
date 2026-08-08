"""Extract auditable agent source from downloaded public Kaggle notebooks."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import zlib
from pathlib import Path


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _assignments(source: str) -> dict[str, object]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return {}
    values: dict[str, object] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                values[target.id] = value
    return values


def extract(notebook: dict) -> tuple[bytes, int, str]:
    candidates: list[tuple[int, int, bytes, str]] = []
    for index, cell in enumerate(notebook.get("cells", [])):
        if cell.get("cell_type") != "code":
            continue
        source = "".join(cell.get("source", []))
        lines = source.splitlines()
        if lines and lines[0].strip().lower() == "%%writefile main.py":
            payload = ("\n".join(lines[1:]) + "\n").encode("utf-8")
            candidates.append((4, index, payload, "WRITEFILE_MAIN_PY"))
        values = _assignments(source)
        literal = values.get("AGENT_SOURCE")
        if isinstance(literal, str):
            candidates.append((3, index, literal.encode("utf-8"), "AGENT_SOURCE_LITERAL"))
        b64 = values.get("AGENT_B64")
        if isinstance(b64, str):
            candidates.append((3, index, base64.b64decode(b64), "AGENT_B64_LITERAL"))
        parts = values.get("_AGENT_B85_PARTS")
        if isinstance(parts, (list, tuple)) and all(isinstance(part, str) for part in parts):
            packed = "".join(parts).encode("ascii")
            candidates.append(
                (3, index, zlib.decompress(base64.b85decode(packed)), "B85_ZLIB_PARTS")
            )
    failures = []
    for _priority, index, payload, method in sorted(candidates, reverse=True):
        try:
            source = payload.decode("utf-8")
            compile(source, "main.py", "exec")
            tree = ast.parse(source)
        except (UnicodeDecodeError, SyntaxError) as exc:
            failures.append(f"cell {index} {method}: {type(exc).__name__}")
            continue
        has_agent = any(
            isinstance(node, ast.FunctionDef) and node.name == "agent" for node in tree.body
        ) or any(
            isinstance(node, ast.Assign)
            and any(isinstance(target, ast.Name) and target.id == "agent" for target in node.targets)
            for node in tree.body
        )
        if has_agent:
            return payload, index, method
        failures.append(f"cell {index} {method}: top-level agent missing")
    raise ValueError("no executable top-level agent found; " + "; ".join(failures))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)
    records = []
    for notebook_path in sorted(args.input_root.rglob("*.ipynb")):
        notebook_bytes = notebook_path.read_bytes()
        notebook = json.loads(notebook_bytes)
        payload, cell_index, method = extract(notebook)
        output_name = notebook_path.parent.name + ".py"
        output_path = args.output_root / output_name
        output_path.write_bytes(payload)
        records.append(
            {
                "notebook": notebook_path.as_posix(),
                "notebook_sha256": _sha(notebook_bytes),
                "cell_index": cell_index,
                "method": method,
                "output": output_path.as_posix(),
                "output_sha256": _sha(payload),
                "bytes": len(payload),
                "compile": "PASS",
            }
        )
    manifest = {"schema_version": 1, "agents": records}
    manifest_path = args.output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"agents": len(records), "manifest": str(manifest_path)}, sort_keys=True))


if __name__ == "__main__":
    main()
