"""Produce a source-level static summary of downloaded public kernel outputs."""

from __future__ import annotations

import ast
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from map_public_tapes import _literal_tapes

ROOT = Path(__file__).resolve().parent
OUTPUT_ROOT = ROOT / "raw" / "kernel_outputs"
CONSTANT_TOKENS = (
    "ROUTE",
    "MODEL",
    "MEMORY",
    "THRESH",
    "HORIZON",
    "PREEMPT",
    "SHIFT",
    "FORECAST",
    "PREMIUM",
    "EXPERT",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _source_summary(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(text)
    except SyntaxError as exc:
        return {
            "parse_status": "SYNTAX_ERROR",
            "parse_error": repr(exc),
            "docstring": None,
            "top_level_definitions": [],
            "selected_constants": {},
            "literal_tapes": [],
        }
    definitions: list[str] = []
    constants: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            definitions.append(node.name)
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names = [target.id for target in targets if isinstance(target, ast.Name)]
        if not names or not any(token in names[0] for token in CONSTANT_TOKENS):
            continue
        try:
            value = repr(ast.literal_eval(node.value))
        except (ValueError, TypeError, MemoryError, RecursionError):
            value = ast.unparse(node.value)
        constants[names[0]] = value[:200]
    return {
        "parse_status": "AST_PASS_STATIC_ONLY",
        "parse_error": None,
        "docstring": ast.get_docstring(tree),
        "top_level_definitions": definitions,
        "selected_constants": constants,
        "literal_tapes": _literal_tapes(text),
    }


def main() -> None:
    rows: list[dict[str, Any]] = []
    main_hash_groups: dict[str, list[str]] = defaultdict(list)
    for directory in sorted(path for path in OUTPUT_ROOT.iterdir() if path.is_dir()):
        main = directory / "main.py"
        if not main.exists():
            continue
        ref = directory.name.replace("__", "/", 1)
        main_sha = _sha(main)
        main_hash_groups[main_sha].append(ref)
        rows.append(
            {
                "ref": ref,
                "main_path": main.relative_to(ROOT).as_posix(),
                "main_sha256": main_sha,
                "main_bytes": main.stat().st_size,
                "execution_status": "STATIC_ONLY_NOT_EXECUTED",
                **_source_summary(main),
            }
        )
    (ROOT / "kernel_static_analysis.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    clone_groups = [
        {"main_sha256": digest, "refs": refs}
        for digest, refs in sorted(main_hash_groups.items())
        if len(refs) > 1
    ]
    print(
        json.dumps(
            {
                "rows": len(rows),
                "ast_pass": sum(row["parse_status"] == "AST_PASS_STATIC_ONLY" for row in rows),
                "clone_groups": clone_groups,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
