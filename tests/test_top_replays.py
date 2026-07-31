from __future__ import annotations

from kaggriculture_lab.research.top_replays import analyze_agent


def _observation(day: int, hour: int, step: int, money: int, hands: int) -> dict:
    return {
        "day": day,
        "hour": hour,
        "step": step,
        "player": 0,
        "farms": [
            {
                "money": money,
                "hands": [[0, 0]] * hands,
                "hires_today": hands,
                "unlocked_quadrants": ["NW"],
                "tiles": [[None]],
            }
        ],
        "private": {"shed": {}, "seeds": {}, "inventories": [{}]},
        "market": {"prices": {}, "inventory": {}},
        "town": {"unlocked_shops": []},
    }


def test_actions_are_attributed_to_the_previous_observation() -> None:
    replay = {
        "info": {"TeamNames": ["agent"]},
        "steps": [
            [
                {
                    "observation": _observation(0, 0, 0, 3000, 0),
                    "action": {},
                    "reward": None,
                    "status": "ACTIVE",
                }
            ],
            [
                {
                    "observation": _observation(0, 1, 1, 2999, 1),
                    "action": {
                        "farmer": ["PASS"],
                        "hands": [],
                        "market": [["HIRE"]],
                    },
                    "reward": None,
                    "status": "ACTIVE",
                }
            ],
            [
                {
                    "observation": _observation(1, 0, 2, 3024, 0),
                    "action": {
                        "farmer": ["PASS"],
                        "hands": [["PASS"]],
                        "market": [["SELL", "WHEAT", 1]],
                    },
                    "reward": 3024,
                    "status": "DONE",
                }
            ],
        ],
    }

    report = analyze_agent(replay, 0)

    assert report["initial_market"]["day"] == 0
    assert report["initial_market"]["hour"] == 0
    assert report["hires_by_day"] == {0: 1}
    assert report["market_order_counts"] == {"HIRE": 1, "SELL:WHEAT": 1}
    assert report["daily"][0]["cash_delta"] == 24
    assert report["daily"][0]["market_order_counts"] == {"HIRE": 1, "SELL:WHEAT": 1}
    assert report["daily"][0]["unit_action_capacity"] == 3
    assert report["daily"][1]["market_order_counts"] == {}
