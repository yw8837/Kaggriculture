"""Build byte-controlled C02 meta ablations from the attributed public source.

V0 is the exact public C02 control.  A1, B1, and C1 each change one declared
axis only; exact replacement counts make upstream drift fail closed.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

SOURCE_CONTROL_SHA256 = "C60147472E416CC1A9106FF2868023C69AB51220E8F959E05E861038CDC46E2E"
VALID_MODES = ("V0", "A1", "B1", "C1", "D1", "D2", "E1")

_CROP_MIX_V0 = '''CROP_MIX = {
    "NW": {"MELON": 10, "WHEAT": 4, "CARROT": 2},
    "NE": {"WHEAT": 4, "CARROT": 1},
    "SW": {"WHEAT": 4, "CARROT": 1},
    "SE": {"WHEAT": 5, "CARROT": 2},
}
'''
_CROP_MIX_A1 = '''CROP_MIX = {
    "NW": {"MELON": 10, "WHEAT": 2, "CARROT": 2},
    "NE": {"WHEAT": 0, "CARROT": 1},
    "SW": {"WHEAT": 0, "CARROT": 1},
    "SE": {"WHEAT": 5, "CARROT": 2},
}
'''

_HERD_TARGETS_V0 = '''    targets = {
        "COW": max(3 if target_total >= CORE_HERD else 0, owned["COW"]),
        "SHEEP": max(1 if target_total >= CORE_HERD else 0, owned["SHEEP"]),
    }
'''
_HERD_TARGETS_B1 = '''    targets = {
        "COW": max(1 if target_total >= CORE_HERD else 0, owned["COW"]),
        "SHEEP": max(1 if target_total >= CORE_HERD else 0, owned["SHEEP"]),
    }
'''

_CORE_SEQUENCE_V0 = '''    assigned = {"COW": 0, "SHEEP": 0}
    roles = {}
    core_sequence = ("COW", "COW", "COW", "SHEEP")
'''
_CORE_SEQUENCE_B1 = '''    assigned = {"COW": 0, "SHEEP": 0}
    roles = {}
    core_limit = min(CORE_HERD, desired_animals)
    core_counts = {"COW": 0, "SHEEP": 0}
    core_sequence = []
    for animal in ("COW", "SHEEP"):
        if len(core_sequence) < core_limit and targets[animal] > 0:
            core_sequence.append(animal)
            core_counts[animal] += 1
    opponents = _opponent_animal_counts(obs)
    while len(core_sequence) < core_limit:
        eligible = tuple(
            animal
            for animal in ("COW", "SHEEP")
            if core_counts[animal] < targets[animal]
        )
        animal = max(
            eligible,
            key=lambda name: (
                _livestock_score(
                    obs,
                    name,
                    core_counts[name],
                    opponents[name],
                ),
                -core_counts[name],
                name == "COW",
            ),
        )
        core_sequence.append(animal)
        core_counts[animal] += 1
    core_sequence = tuple(core_sequence)
'''

_LAND_V0 = "LAND_OPEN_DAYS = (5, 9)\n"
_LAND_C1 = "LAND_OPEN_DAYS = (8, 9)\n"

_SELL_RETURN_V0 = '''    if left <= 12:
        forced = int(math.ceil(have / float(max(1, left - 1))))
        quantity = max(quantity, min(have, forced))
    return quantity
'''
_SELL_RETURN_D1 = '''    if left <= 12:
        forced = int(math.ceil(have / float(max(1, left - 1))))
        quantity = max(quantity, min(have, forced))
    if item == "WHEAT":
        quantity = min(quantity, 4)
    return quantity
'''

_FEED_STOCK_V0 = "FEED_STOCK_DAYS = 3\n"
_FEED_STOCK_D2 = "FEED_STOCK_DAYS = 1\n"

_ROLE_DAY_V0 = '''def _role_plan(obs, farm):
    private = obs.get("private", {}) or {}
'''
_ROLE_DAY_E1 = '''def _role_plan(obs, farm):
    day = int(obs.get("day", 0) or 0)
    private = obs.get("private", {}) or {}
'''

_FIXED_CROPS_V0 = '''        fixed = dict(CROP_MIX[quadrant])
        if quadrant == "NW":
'''
_FIXED_CROPS_E1 = '''        fixed = dict(CROP_MIX[quadrant])
        if day >= 5:
            fixed["WHEAT"] = 2 if quadrant == "NW" else 0
        if quadrant == "NW":
'''


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def _with_newline(marker: str, newline: str) -> str:
    return marker.replace("\n", newline)


def _replace_exact(
    source: str,
    old: str,
    new: str,
    *,
    newline: str,
    expected: int = 1,
) -> str:
    old = _with_newline(old, newline)
    new = _with_newline(new, newline)
    actual = source.count(old)
    if actual != expected:
        raise ValueError(
            f"expected {expected} exact marker(s), found {actual}: {old[:80]!r}"
        )
    return source.replace(old, new)


def build_c02_meta_family(source_control: bytes, mode: str) -> bytes:
    """Return one deterministic C02 family member while preserving line endings."""
    if mode not in VALID_MODES:
        raise ValueError(f"unknown mode {mode!r}; expected one of {VALID_MODES}")
    if _sha256(source_control) != SOURCE_CONTROL_SHA256:
        raise ValueError("source is not the frozen attributed public C02 control")
    if mode == "V0":
        return source_control

    source = source_control.decode("utf-8")
    newline = "\r\n" if "\r\n" in source else "\n"
    if mode == "A1":
        source = _replace_exact(
            source,
            _CROP_MIX_V0,
            _CROP_MIX_A1,
            newline=newline,
        )
    elif mode == "B1":
        source = _replace_exact(
            source,
            _HERD_TARGETS_V0,
            _HERD_TARGETS_B1,
            newline=newline,
        )
        source = _replace_exact(
            source,
            _CORE_SEQUENCE_V0,
            _CORE_SEQUENCE_B1,
            newline=newline,
        )
    elif mode == "C1":
        source = _replace_exact(source, _LAND_V0, _LAND_C1, newline=newline)
    elif mode == "D1":
        source = _replace_exact(
            source,
            _SELL_RETURN_V0,
            _SELL_RETURN_D1,
            newline=newline,
        )
    elif mode == "D2":
        source = _replace_exact(
            source,
            _FEED_STOCK_V0,
            _FEED_STOCK_D2,
            newline=newline,
        )
    elif mode == "E1":
        source = _replace_exact(
            source,
            _ROLE_DAY_V0,
            _ROLE_DAY_E1,
            newline=newline,
        )
        source = _replace_exact(
            source,
            _FIXED_CROPS_V0,
            _FIXED_CROPS_E1,
            newline=newline,
        )

    built = source.encode("utf-8")
    compile(built, f"<fa04_c02_meta_{mode}>", "exec")
    return built


def build_file(source: Path, output: Path, mode: str) -> str:
    payload = build_c02_meta_family(source.read_bytes(), mode)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(payload)
    return _sha256(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build exact C02 meta-family snapshots")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("experiments/source_snapshots/fa04_c02_meta"),
    )
    parser.add_argument("--modes", nargs="+", choices=VALID_MODES, default=VALID_MODES)
    args = parser.parse_args()
    for mode in args.modes:
        output = args.output_dir / f"{mode}.py"
        digest = build_file(args.source, output, mode)
        print(f"{mode} {digest} {output}")


if __name__ == "__main__":
    main()
