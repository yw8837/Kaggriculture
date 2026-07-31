from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def _replace_function(source: str, name: str, next_name: str, replacement: str) -> str:
    start = source.index(f"def {name}(")
    end = source.index(f"\ndef {next_name}(", start)
    return source[:start] + replacement.rstrip() + "\n\n" + source[end + 1 :]


CROP_PLAN = '''def _crop_plan(board_size, unlocked_quadrants, animal_slots):
    h = board_size // 2
    quadrants = set(unlocked_quadrants or ["NW"])
    shed = (h - 1, h - 1)
    mixes = {
        "NW": (("MELON", 11), ("STRAWBERRY", 5), ("CARROT", 2), ("WHEAT", 4)),
        "NE": (("STRAWBERRY", 14), ("WHEAT", 4), ("CARROT", 1)),
        "SW": (("STRAWBERRY", 20), ("WHEAT", 4), ("CARROT", 1)),
        "SE": (("STRAWBERRY", 18), ("WHEAT", 5), ("CARROT", 2)),
    }
    bounds = {
        "NW": (range(0, h), range(0, h)),
        "NE": (range(h, board_size), range(0, h)),
        "SW": (range(0, h), range(h, board_size)),
        "SE": (range(h, board_size), range(h, board_size)),
    }
    plan = {}
    for quadrant in ("NW", "NE", "SW", "SE"):
        if quadrant not in quadrants:
            continue
        xs, ys = bounds[quadrant]
        cells = [(x, y) for y in ys for x in xs if (x, y) not in animal_slots]
        cells.sort(key=lambda p: (_dist(p, shed), p[1], p[0]))
        crops = []
        for crop, count in mixes[quadrant]:
            crops.extend([crop] * count)
        while len(crops) < len(cells):
            crops.append("STRAWBERRY")
        plan.update(zip(cells, crops[:len(cells)]))
    return plan
'''


ANTI_CROP_PLAN = '''def _crop_plan(board_size, unlocked_quadrants, animal_slots, obs):
    h = board_size // 2
    quadrants = set(unlocked_quadrants or ["NW"])
    shed = (h - 1, h - 1)
    player = int(obs.get("player", 0))
    opponent_strawberries = 0
    for index, other in enumerate(obs.get("farms", []) or []):
        if index == player:
            continue
        opponent_strawberries += sum(
            isinstance(tile, dict)
            and tile.get("kind") == "PLANT"
            and tile.get("crop") == "STRAWBERRY"
            for row in other.get("tiles", []) or []
            for tile in row
        )
    contested = opponent_strawberries >= 4
    expansion_crop = "TOMATO" if contested else "STRAWBERRY"
    mixes = {
        "NW": (("MELON", 11), ("STRAWBERRY", 5), ("CARROT", 2), ("WHEAT", 4)),
        "NE": ((expansion_crop, 14), ("WHEAT", 4), ("CARROT", 1)),
        "SW": ((expansion_crop, 20), ("WHEAT", 4), ("CARROT", 1)),
        "SE": ((expansion_crop, 18), ("WHEAT", 5), ("CARROT", 2)),
    }
    bounds = {
        "NW": (range(0, h), range(0, h)),
        "NE": (range(h, board_size), range(0, h)),
        "SW": (range(0, h), range(h, board_size)),
        "SE": (range(h, board_size), range(h, board_size)),
    }
    plan = {}
    for quadrant in ("NW", "NE", "SW", "SE"):
        if quadrant not in quadrants:
            continue
        xs, ys = bounds[quadrant]
        cells = [(x, y) for y in ys for x in xs if (x, y) not in animal_slots]
        cells.sort(key=lambda p: (_dist(p, shed), p[1], p[0]))
        crops = []
        for crop, count in mixes[quadrant]:
            crops.extend([crop] * count)
        while len(crops) < len(cells):
            crops.append(expansion_crop)
        plan.update(zip(cells, crops[:len(cells)]))
    return plan
'''


ANIMAL_TASKS = '''def _animal_for_slot(position, slots):
    index = slots.index(position)
    return "SHEEP" if index in (1, 2, 8) else "COW"


def _animal_tasks(obs, farm, private, slots):
    day = int(obs.get("day", 0))
    prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    tasks = []
    tiles = farm["tiles"]
    for pos in slots:
        x, y = pos
        tile = tiles[y][x]
        planned = _animal_for_slot(pos, slots)
        if tile == "LOCKED":
            continue
        if isinstance(tile, dict) and tile.get("animal") in ("COW", "SHEEP"):
            animal = tile["animal"]
            product = "MILK" if animal == "COW" else "WOOL"
            if not tile.get("fed_today", False):
                _add(tasks, 0, pos, ["FEED"], "WHEAT")
            if tile.get("fertilizer_available", False):
                _add(tasks, 1, pos, ["COLLECT_FERTILIZER"])
            if day <= 27 and int(prices.get(product, 100)) >= 20 and not tile.get("cared_today", False):
                _add(tasks, 2, pos, ["CARE"])
            held = int(tile.get("yield_units", 0))
            if held >= 3 or (day >= 27 and held > 0):
                _add(tasks, 1, pos, ["HARVEST"])
        elif tile is None:
            _add(tasks, 0, pos, ["BUILD_PASTURE"])
        elif isinstance(tile, dict) and tile.get("kind") == "WEED":
            _add(tasks, 0, pos, ["DIG"])
        elif isinstance(tile, dict) and tile.get("kind") == "PASTURE" and not tile.get("animal"):
            _add(tasks, 0, pos, ["PLACE", planned], planned)
        elif isinstance(tile, dict) and tile.get("kind") == "PLANT":
            _add(tasks, 0, pos, ["DIG"])
    return tasks
'''


MARKET_ACTIONS = '''def _market_actions(obs, farm, private, animal_slots, crop_plan):
    day = int(obs.get("day", 0))
    hour = int(obs.get("hour", 0))
    shed = private.get("shed", {}) or {}
    prices = ((obs.get("market", {}) or {}).get("prices", {}) or {})
    orders = []
    budget = float(farm.get("money", 0))

    placed = {
        animal: _count_public_animals(farm, animal)
        for animal in ("COW", "SHEEP")
    }
    owned = {
        animal: placed[animal] + _total(private, animal)
        for animal in ("COW", "SHEEP")
    }
    quadrants = list(farm.get("unlocked_quadrants", []) or ["NW"])
    expanded = len(quadrants) >= 2
    target = {"COW": 6, "SHEEP": 3} if expanded else {"COW": 1, "SHEEP": 2}
    animal_count = placed["COW"] + placed["SHEEP"]
    wheat_reserve = max(8, animal_count * 3)

    for item in SELL_ORDER:
        if len(orders) >= 6:
            break
        amount = int(shed.get(item, 0))
        if item == "WHEAT" and day < 29:
            amount = max(0, amount - wheat_reserve)
        if amount <= 0:
            continue
        cap = amount if day >= 29 else 20 if item in ("MILK", "WOOL", "FERTILIZER") else 28
        quantity = min(amount, cap)
        orders.append(["SELL", item, quantity])
        budget += quantity * max(1, int(prices.get(item, 1)))

    if day >= 29:
        return orders

    extra_land = max(0, len(quadrants) - 1)
    land_costs = (1000, 2000, 4000)
    earliest = 5 if extra_land == 0 else 9 if extra_land == 1 else 15
    if (
        extra_land < 2
        and earliest <= day <= 18
        and len(orders) < 10
        and budget >= land_costs[extra_land] + (300 if extra_land == 0 else 500)
    ):
        orders.append(["BUY_LAND"])
        budget -= land_costs[extra_land]
        extra_land += 1
        expanded = True
        target = {"COW": 6, "SHEEP": 3}

    costs = {"COW": 400, "SHEEP": 500}
    for animal in ("COW", "SHEEP"):
        if len(orders) >= 10:
            break
        missing = max(0, target[animal] - owned[animal])
        affordable = max(0, int((budget - 220) // costs[animal]))
        quantity = min(missing, 2, affordable)
        if quantity > 0:
            orders.append(["BUY_ANIMAL", animal, quantity])
            budget -= quantity * costs[animal]
            owned[animal] += quantity

    wheat_total = _total(private, "WHEAT")
    wanted_wheat = max(0, max(8, (placed["COW"] + placed["SHEEP"]) * 3 + 3) - wheat_total)
    if wanted_wheat > 0 and len(orders) < 10:
        price = max(1, int(prices.get("WHEAT", 25)))
        quantity = min(wanted_wheat, max(0, int((budget - 100) // price)))
        if quantity > 0:
            orders.append(["BUY_PRODUCT", "WHEAT", quantity])
            budget -= quantity * price

    seeds = private.get("seeds", {}) or {}
    needs = {crop: 0 for crop in CROP_RULES}
    for (x, y), crop in crop_plan.items():
        tile = farm["tiles"][y][x]
        if tile is None and day <= CROP_RULES[crop][3]:
            needs[crop] += 1
    for crop in ("MELON", "STRAWBERRY", "CARROT", "WHEAT"):
        if len(orders) >= 10:
            break
        wanted = max(0, needs[crop] - int(seeds.get(crop, 0)))
        if wanted <= 0:
            continue
        cost = CROP_RULES[crop][0]
        quantity = min(wanted, 20, max(0, int((budget - 80) // cost)))
        if quantity > 0:
            orders.append(["BUY_SEED", crop, quantity])
            budget -= quantity * cost

    if hour <= 3:
        missing = max(0, 10 - len(farm.get("hands", []) or []))
        hire_index = int(farm.get("hires_today", 0))
        while missing > 0 and len(orders) < 10:
            cost = _fib(hire_index)
            if budget < cost + 20:
                break
            orders.append(["HIRE"])
            budget -= cost
            hire_index += 1
            missing -= 1
    return orders[:10]
'''


AGENT = '''def agent(obs):
    farms = obs.get("farms", []) or []
    player = int(obs.get("player", 0))
    if player < 0 or player >= len(farms):
        return {"farmer": ["PASS"], "hands": [], "market": []}
    farm = farms[player]
    private = obs.get("private", {}) or {}
    board_size = len(farm.get("tiles", [])) or 10
    quadrants = list(farm.get("unlocked_quadrants", []) or ["NW"])
    expanded = len(quadrants) >= 2
    all_animal_slots = _cow_slots(board_size, expanded)
    animals_owned = sum(
        _count_public_animals(farm, animal) + _total(private, animal)
        for animal in ("COW", "SHEEP")
    )
    active_count = min(len(all_animal_slots), max(3, animals_owned))
    animal_slots = all_animal_slots[:active_count]
    crop_plan = _crop_plan(board_size, quadrants, set(all_animal_slots))
    actions = _unit_actions(obs, farm, private, animal_slots, crop_plan)
    return {
        "farmer": actions[0] if actions else ["PASS"],
        "hands": actions[1:] if len(actions) > 1 else [],
        "market": _market_actions(obs, farm, private, all_animal_slots, crop_plan),
    }
'''


def build_fast_expansion(base: str) -> str:
    source = base.replace("TARGET_HANDS_CORE = 8", "TARGET_HANDS_CORE = 10")
    source = source.replace("TARGET_HANDS_EXPANDED = 11", "TARGET_HANDS_EXPANDED = 10")
    source = _replace_function(source, "_crop_plan", "_add", CROP_PLAN)
    source = _replace_function(source, "_animal_tasks", "_crop_tasks", ANIMAL_TASKS)
    source = source.replace(
        '1 if need == "COW" else 4',
        '1 if need in ("COW", "SHEEP") else 4',
    )
    source = _replace_function(source, "_market_actions", "agent", MARKET_ACTIONS)
    source = source[: source.index("def agent(")] + AGENT
    compile(source, "fast_expansion.py", "exec")
    return source.rstrip() + "\n"


def build_anti_meta(fast_expansion: str) -> str:
    source = _replace_function(fast_expansion, "_crop_plan", "_add", ANTI_CROP_PLAN)
    source = source.replace(
        'for crop in ("MELON", "STRAWBERRY", "CARROT", "WHEAT"):',
        'for crop in ("MELON", "STRAWBERRY", "TOMATO", "CARROT", "WHEAT"):',
    )
    source = source.replace(
        "crop_plan = _crop_plan(board_size, quadrants, set(all_animal_slots))",
        "crop_plan = _crop_plan(board_size, quadrants, set(all_animal_slots), obs)",
    )
    compile(source, "anti_meta.py", "exec")
    return source.rstrip() + "\n"


def build_animal_tilt(fast_expansion: str, cows: int, sheep: int) -> str:
    if (cows, sheep) == (5, 4):
        sheep_slots = "(1, 2, 7, 8)"
    elif (cows, sheep) == (7, 2):
        sheep_slots = "(1, 2)"
    else:
        raise ValueError("unsupported animal tilt")
    source = fast_expansion.replace("(1, 2, 8)", sheep_slots)
    source = source.replace(
        '{"COW": 6, "SHEEP": 3}',
        f'{{"COW": {cows}, "SHEEP": {sheep}}}',
    )
    compile(source, f"animal_tilt_{cows}_{sheep}.py", "exec")
    return source.rstrip() + "\n"


def build_staged_herd(cow_tilt: str) -> str:
    opening = (
        'target = {"COW": 7, "SHEEP": 2} if expanded else {"COW": 1, "SHEEP": 2}'
    )
    staged = '''target = (
        {"COW": 7, "SHEEP": 2}
        if len(quadrants) >= 3
        else {"COW": 4, "SHEEP": 2}
        if expanded
        else {"COW": 1, "SHEEP": 2}
    )'''
    source = cow_tilt.replace(opening, staged, 1)
    source = source.replace(
        'expanded = True\n        target = {"COW": 7, "SHEEP": 2}',
        '''expanded = True
        target = (
            {"COW": 7, "SHEEP": 2}
            if extra_land >= 2
            else {"COW": 4, "SHEEP": 2}
        )''',
        1,
    )
    if source == cow_tilt or staged not in source:
        raise ValueError("staged-herd transformation did not apply")
    compile(source, "staged_herd.py", "exec")
    return source.rstrip() + "\n"


def build_final_day_labor(source_agent: str, filename: str, target_hands: int = 10) -> str:
    early_return = '''    if day >= 29:
        return orders
'''
    final_day = '''    if day >= 29:
        hire_orders = []
        if hour <= 3:
            missing = max(0, FINAL_DAY_HANDS - len(farm.get("hands", []) or []))
            hire_index = int(farm.get("hires_today", 0))
            while missing > 0 and len(hire_orders) < 10:
                cost = _fib(hire_index)
                if budget < cost + 20:
                    break
                hire_orders.append(["HIRE"])
                budget -= cost
                hire_index += 1
                missing -= 1
        return (hire_orders + orders)[:10]
'''.replace("FINAL_DAY_HANDS", str(target_hands))
    source = source_agent.replace(early_return, final_day, 1)
    if source == source_agent or final_day not in source:
        raise ValueError("final-day-labor transformation did not apply")
    compile(source, filename, "exec")
    return source.rstrip() + "\n"


def build_drop_policy(source_agent: str, filename: str, mode: str) -> str:
    marker = "    while free_units and free_tasks:\n"
    if mode == "overflow":
        condition = '''# Shed capacity is 100. Start returning carried goods at 90 so the
    # end-of-day drop phase has a ten-item safety buffer instead of discarding overflow.
    shed_load = sum(int(value) for value in shed.values())
    carried_load = sum(sum(int(value) for value in inv.values()) for inv in invs)
    drop_units = shed_load + carried_load >= 90'''
    elif mode == "carrier":
        condition = '''sellable = {
        "CARROT", "TOMATO", "STRAWBERRY", "MELON",
        "EGG", "MILK", "WOOL", "FERTILIZER",
    }
    drop_units = False'''
    else:
        raise ValueError(f"unsupported drop mode: {mode}")
    per_unit_condition = (
        "sum(int(value) for value in invs[i].values()) > 0"
        if mode == "overflow"
        else "sum(int(invs[i].get(item, 0)) for item in sellable) >= 6"
    )
    gate = (
        f"if not drop_units or not ({per_unit_condition}):"
        if mode == "overflow"
        else f"if not ({per_unit_condition}):"
    )
    insertion = f'''    {condition}
    for i in sorted(tuple(free_units)):
        {gate}
            continue
        s = _nearest_shed(len(farm["tiles"]), farm["tiles"], positions[i])
        actions[i] = ["DROP"] if positions[i] == s else _move(farm["tiles"], positions[i], s)
        free_units.remove(i)

'''
    source = source_agent.replace(marker, insertion + marker, 1)
    if source == source_agent or insertion not in source:
        raise ValueError("drop-policy transformation did not apply")
    if mode == "overflow":
        strategy_notes = '''# Fa_01 strategy notes
# - Scale to ten daily hands and buy land early to compound crop production.
# - Use a seven-cow/two-sheep expanded herd while reserving enough wheat for feed.
# - Route loaded workers back before the 100-item shed cap can destroy inventory.
# - Hire ten hands before final-day liquidation so harvest does not stop early.
#
# These comments document the mechanism for audit and a future public-baseline write-up.
# The exact production artifact remains private; any public release is a weaker ablation.

'''
        source = strategy_notes + source
    compile(source, filename, "exec")
    return source.rstrip() + "\n"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def run(base_path: Path, output_root: Path) -> dict:
    base = base_path.read_text(encoding="utf-8")
    fast_expansion = build_fast_expansion(base)
    anti_meta = build_anti_meta(fast_expansion)
    sheep_tilt = build_animal_tilt(fast_expansion, 5, 4)
    cow_tilt = build_animal_tilt(fast_expansion, 7, 2)
    staged_herd = build_staged_herd(cow_tilt)
    final_day_labor = build_final_day_labor(cow_tilt, "final_day_labor.py")
    final_day_labor_12 = build_final_day_labor(cow_tilt, "final_day_labor_12.py", 12)
    final_day_labor_13 = build_final_day_labor(cow_tilt, "final_day_labor_13.py", 13)
    overflow_drop = build_drop_policy(final_day_labor, "overflow_drop.py", "overflow")
    carrier_drop = build_drop_policy(final_day_labor, "carrier_drop.py", "carrier")
    staged_herd_final = build_final_day_labor(staged_herd, "staged_herd_final.py")
    labor_rush = fast_expansion.replace(
        'missing = max(0, 10 - len(farm.get("hands", []) or []))',
        'missing = max(0, 12 - len(farm.get("hands", []) or []))',
    )
    if labor_rush == fast_expansion:
        raise ValueError("labor-rush transformation did not apply")
    compile(labor_rush, "labor_rush.py", "exec")
    candidates = {
        "cow_compounder": base,
        "fast_expansion": fast_expansion,
        "anti_meta": anti_meta,
        "sheep_tilt": sheep_tilt,
        "cow_tilt": cow_tilt,
        "staged_herd": staged_herd,
        "final_day_labor": final_day_labor,
        "final_day_labor_12": final_day_labor_12,
        "final_day_labor_13": final_day_labor_13,
        "overflow_drop": overflow_drop,
        "carrier_drop": carrier_drop,
        "staged_herd_final": staged_herd_final,
        "labor_rush": labor_rush,
    }
    records = []
    for name, source in candidates.items():
        path = output_root / name / "main.py"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = source.encode("utf-8")
        path.write_bytes(payload)
        records.append({"name": name, "path": path.as_posix(), "sha256": _sha256(payload)})
    manifest = {
        "schema_version": 1,
        "base_path": base_path.as_posix(),
        "base_sha256": _sha256(base_path.read_bytes()),
        "candidates": records,
    }
    manifest_path = output_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build reproducible Kaggriculture candidates")
    parser.add_argument(
        "--base",
        type=Path,
        default=Path("artifacts/opponents/public_kaggle/hamburger_base.py"),
    )
    parser.add_argument("--output", type=Path, default=Path("artifacts/candidates"))
    args = parser.parse_args()
    print(json.dumps(run(args.base, args.output)))


if __name__ == "__main__":
    main()
