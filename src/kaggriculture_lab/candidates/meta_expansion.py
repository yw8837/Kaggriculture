"""Build isolated Fa_03 labor/herd meta ablations from final_day_labor.

The observed live-meta shape (12 hands, three quadrants, and a roughly 5C/5S
herd) is only a prior. These modes keep the formal unit scheduler, crop
planner, land policy, and terminal branch intact so local screening can
separate the labor and herd axes.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

FORMAL_PARENT_SHA256 = "112AF9EC28030B53CE852927CEE986834F18F0245F3A88FB2E06F423291C9F8B"
VALID_MODES = ("M1", "M2", "M3")

_NORMAL_HIRE_TARGET = '        missing = max(0, 10 - len(farm.get("hands", []) or []))\n'
_META_HIRE_TARGET = '        missing = max(0, 12 - len(farm.get("hands", []) or []))\n'

_EXPANDED_SLOT_TAIL = """            (h + 4, h - 1),
            (h, h - 2),
"""
_BALANCED_SLOT_TAIL = """            (h + 4, h - 1),
            (h, h - 2),
            (h + 1, h - 2),
"""

_FORMAL_ANIMAL_MAPPING = '    return "SHEEP" if index in (1, 2) else "COW"\n'
_BALANCED_ANIMAL_MAPPING = (
    '    return "SHEEP" if index in (1, 2, 7, 8, 9) else "COW"\n'
)

_FORMAL_EXPANDED_TARGET = '{"COW": 7, "SHEEP": 2}'
_BALANCED_EXPANDED_TARGET = '{"COW": 5, "SHEEP": 5}'


def _sha256(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()


def _replace_last(source: str, old: str, new: str) -> str:
    """Replace only the ordinary (pre-terminal) hire target occurrence."""
    if source.count(old) != 2:
        raise ValueError(f"expected two formal hire targets, found {source.count(old)}")
    prefix, suffix = source.rsplit(old, 1)
    return prefix + new + suffix


def _replace_exact(source: str, old: str, new: str, count: int) -> str:
    actual = source.count(old)
    if actual != count:
        raise ValueError(f"expected {count} exact marker(s), found {actual}: {old!r}")
    return source.replace(old, new)


def build_meta_expansion(source_agent: str, mode: str) -> str:
    """Return one deterministic, self-contained Fa_03 meta candidate source."""
    if mode not in VALID_MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {VALID_MODES}")
    if _sha256(source_agent) != FORMAL_PARENT_SHA256:
        raise ValueError("source agent is not the frozen final_day_labor parent")

    built = source_agent
    if mode in {"M1", "M2"}:
        built = _replace_last(built, _NORMAL_HIRE_TARGET, _META_HIRE_TARGET)

    if mode in {"M1", "M3"}:
        built = _replace_exact(built, _EXPANDED_SLOT_TAIL, _BALANCED_SLOT_TAIL, 1)
        built = _replace_exact(
            built,
            _FORMAL_ANIMAL_MAPPING,
            _BALANCED_ANIMAL_MAPPING,
            1,
        )
        built = _replace_exact(
            built,
            _FORMAL_EXPANDED_TARGET,
            _BALANCED_EXPANDED_TARGET,
            2,
        )

    compile(built, f"<fa03_meta_expansion_{mode}>", "exec")
    return built


def build_meta_expansion_file(parent: Path, output: Path, mode: str) -> Path:
    source = parent.read_text(encoding="utf-8")
    built = build_meta_expansion(source, mode)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(built, encoding="utf-8", newline="")
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one Fa_03 meta expansion ablation")
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--mode", choices=VALID_MODES, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    path = build_meta_expansion_file(args.parent, args.output, args.mode)
    print(path.as_posix())


if __name__ == "__main__":
    main()
