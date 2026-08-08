from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path
from typing import Any

RELEASE_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = RELEASE_ROOT.parents[2]

CANONICAL_SOURCE = (
    PROJECT_ROOT / "experiments/source_snapshots/fa04_top_trace/G1_sell_guard.py"
)
CANONICAL_LICENSE = PROJECT_ROOT / "third_party/fa04_frontier_lab/LICENSE"
CANONICAL_ENGINE_SUMMARY = PROJECT_ROOT / "research/campaign_3000/05_engine_screen/summary.json"
CANONICAL_ENGINE_COMPARISON = (
    PROJECT_ROOT / "research/campaign_3000/05_engine_screen/engine_comparison.json"
)
CANONICAL_ENGINE_CONFIG = (
    PROJECT_ROOT / "research/campaign_3000/05_engine_screen/screen_config.json"
)
CANONICAL_PRIVATE_RELEASE_MANIFEST = (
    PROJECT_ROOT / "research/campaign_3000/07_release/local_build/release_manifest.json"
)
CANONICAL_PRIVATE_RELEASE_SPEC = (
    PROJECT_ROOT / "research/campaign_3000/07_release/release_spec.json"
)
PUBLIC_SOURCE = RELEASE_ROOT / "public_source/main.py"
PUBLIC_LICENSE = RELEASE_ROOT / "LICENSE"
LOCAL_ENGINE_SUMMARY = RELEASE_ROOT / "evidence/engine_screen_summary.json"
LOCAL_ENGINE_COMPARISON = RELEASE_ROOT / "evidence/engine_comparison.json"
LOCAL_ENGINE_CONFIG = RELEASE_ROOT / "evidence/engine_screen_config.json"
LOCAL_PRIVATE_RELEASE_MANIFEST = RELEASE_ROOT / "evidence/private_release_manifest.json"
LOCAL_PRIVATE_RELEASE_SPEC = RELEASE_ROOT / "evidence/private_release_spec.json"
NOTEBOOK_DIR = RELEASE_ROOT / "kaggle_code_draft"
NOTEBOOK_PATH = NOTEBOOK_DIR / "kaggriculture-fixed-trace-safety-baseline.ipynb"
METADATA_PATH = NOTEBOOK_DIR / "kernel-metadata.json"
ARCHIVE_PATH = RELEASE_ROOT / "artifact/kaggriculture_fixed_trace_safety_baseline.tar.gz"
MANIFEST_PATH = RELEASE_ROOT / "release_manifest.json"
HASHES_PATH = RELEASE_ROOT / "SHA256SUMS"
EXTERNAL_PAYLOAD_PATH = RELEASE_ROOT / "external_action_payload.json"

EXPECTED_SOURCE_SHA256 = "81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922"
EXPECTED_LICENSE_SHA256 = "C71D239DF91726FC519C6EB72D318EC65820627232B2F796219E87DCF35D0AB4"
ENGINE_SUMMARY_SHA256 = "193FB33CA537681E510C74C9E6ED947CD1FB0D806911BB1C93AF95AC8C50D94F"
ENGINE_COMPARISON_SHA256 = (
    "7FBC90385D085932544E693836CA4B24EC28E9AAD7A28DB9AA442E22FB46B2F6"
)
ENGINE_CONFIG_SHA256 = "49AA865CF993DE29D22715C593FAA81134C2E97F3A5C25AE00589D3ACC311E72"
PRIVATE_RELEASE_MANIFEST_SHA256 = (
    "DCF7C3CD881941386480746D7BF1F505BF0F067D3021D8274B613861D48B7625"
)
PRIVATE_RELEASE_SPEC_SHA256 = "BBE3B7DA2C14B5C4DD752AE67C55FD1898E1B9DF613162DA7FCAEC32009680F4"
KAG_01_SOURCE_SHA256 = "997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6"
KAG_02_SOURCE_SHA256 = "62FB5A5F66F0011092A2B51E3192879BA583D5D815D761F176091C615657147A"
RAY_SOURCE_SHA256 = "6CC3B69E487052A8DEDC1A90D0D1296BA38577349E8D3BA8147E583605378F73"
KAG_01_ARCHIVE_SHA256 = "184F687C474933A7215DB97E8C5A5F823AE79233EEA42D04B70EABC001BF9E16"
KAG_02_ARCHIVE_SHA256 = "37EA53D3046E3D1DA914F8A89C6F4BB02E240E1BB85857BDA149273FC4DD974C"
KAG_01_NOTEBOOK_SHA256 = "0C8D17DA3266804597EA753A401FDEAE8AAF4E04CDE305C2E7F9C6FF61CDF895"
KAG_02_NOTEBOOK_SHA256 = "01003AADA83D0688DB40A01B19D4886871EE0A2317A5F8F897E82FB78130A431"
KAG_01_PREPUSH_SHA256 = "1AAEC168EBD026810BBF8F9965DCA8DE0D8DB578914944C71A953D8177A43140"
KAG_02_PREPUSH_SHA256 = "2FE18CE217182ACC3EF49C1225DD8BA24C5D8F7E98D0CCFD7C7EC8C9DCF94443"
KAG_01_METADATA_SHA256 = "F58F72FDC99FB5FB828732EF93546F0285F02024643884D88EAFCAF768B98746"
KAG_02_METADATA_SHA256 = "A32152D8D2DA2BE06D08C7F2C01C401BA84EA7B4BC8E69F189110FC54A3EDCFA"

CODE_TITLE = "Kaggriculture Agent | Fixed Trace + Safe Selling"
DISCUSSION_TITLE = "Kaggriculture Strategy | Replay Agents, Sell Guards & Engine Drift"
KERNEL_ID = "yw8837/kaggriculture-fixed-trace-safety-baseline"
ARCHIVE_NAME = ARCHIVE_PATH.name
EXISTING_BASELINE_URL = (
    "https://www.kaggle.com/code/yw8837/kaggriculture-strong-expansion-baseline"
)


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest().upper()


def read_expected(path: Path, expected_sha256: str) -> bytes:
    payload = path.read_bytes()
    actual = sha256(payload)
    if actual != expected_sha256:
        raise ValueError(f"SHA-256 mismatch for {path}: expected {expected_sha256}, got {actual}")
    return payload


def bootstrap() -> None:
    """Copy only hash-pinned source, license, and result evidence into the boundary."""
    source = read_expected(CANONICAL_SOURCE, EXPECTED_SOURCE_SHA256)
    license_payload = read_expected(CANONICAL_LICENSE, EXPECTED_LICENSE_SHA256)
    summary = read_expected(CANONICAL_ENGINE_SUMMARY, ENGINE_SUMMARY_SHA256)
    comparison = read_expected(CANONICAL_ENGINE_COMPARISON, ENGINE_COMPARISON_SHA256)
    config = read_expected(CANONICAL_ENGINE_CONFIG, ENGINE_CONFIG_SHA256)
    private_release = read_expected(
        CANONICAL_PRIVATE_RELEASE_MANIFEST,
        PRIVATE_RELEASE_MANIFEST_SHA256,
    )
    private_spec = read_expected(
        CANONICAL_PRIVATE_RELEASE_SPEC,
        PRIVATE_RELEASE_SPEC_SHA256,
    )
    PUBLIC_SOURCE.parent.mkdir(parents=True, exist_ok=True)
    LOCAL_ENGINE_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    PUBLIC_SOURCE.write_bytes(source)
    PUBLIC_LICENSE.write_bytes(license_payload)
    LOCAL_ENGINE_SUMMARY.write_bytes(summary)
    LOCAL_ENGINE_COMPARISON.write_bytes(comparison)
    LOCAL_ENGINE_CONFIG.write_bytes(config)
    LOCAL_PRIVATE_RELEASE_MANIFEST.write_bytes(private_release)
    LOCAL_PRIVATE_RELEASE_SPEC.write_bytes(private_spec)


def deterministic_archive(payload: bytes) -> bytes:
    compressed = io.BytesIO()
    with (
        gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as gz,
        tarfile.open(fileobj=gz, mode="w") as archive,
    ):
        info = tarfile.TarInfo("main.py")
        info.size = len(payload)
        info.mode = 0o644
        info.mtime = 0
        info.uid = 0
        info.gid = 0
        info.uname = ""
        info.gname = ""
        archive.addfile(info, io.BytesIO(payload))
    return compressed.getvalue()


def markdown_cell(cell_id: str, text: str) -> dict[str, Any]:
    return {
        "id": cell_id,
        "cell_type": "markdown",
        "metadata": {},
        "source": text.splitlines(keepends=True),
    }


def code_cell(cell_id: str, text: str) -> dict[str, Any]:
    return {
        "id": cell_id,
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": text.splitlines(keepends=True),
    }


def build_notebook(
    source: bytes,
    archive_sha256: str,
    license_text: str,
    notice_text: str,
) -> dict[str, Any]:
    source_text = source.decode("utf-8")
    overview = f"""# {CODE_TITLE}

This notebook releases a deterministic, readable Kaggriculture learning agent built around one
simple idea: replay a fixed 719-action plan, but repair two common failure modes from the live
observation before returning an action.

It is deliberately an older and materially weaker public baseline, not the current private
competition agent. The exact public source lost all 32 local games against the two stronger
private-source references used for separation, across eight consumed seeds and both seats under
`kaggle-environments==1.32.6`. That is local head-to-head evidence, not a ladder rating estimate.

**Artifact identity:** `{EXPECTED_SOURCE_SHA256}` (SHA-256). The title contains no score claim,
and this release makes no promise about a Kaggle rating.
"""
    mental_model = """## 1. The useful mental model: plan plus guardrail

A fixed trace is an **open-loop plan**: at turn `t`, return the action recorded for turn `t`.
That makes it deterministic and easy to audit, but brittle when the opponent or engine changes
the state. This baseline adds a narrow **closed-loop safety layer**:

| Layer | Reads | Does | Does not do |
|---|---|---|---|
| Schedule | current step | chooses the recorded farmer, hand, and market actions | search, plan, or model the opponent |
| Hand normalizer | current number of hands | truncates extra actions and pads missing ones with `PASS` | reassign work intelligently |
| Sell guard | shed plus same-turn shed movement | clamps or removes impossible `SELL` orders | forecast price or optimize order size |

This pattern is useful beyond Kaggriculture: keep a simple policy legible, then put state-aware
checks at the interface where invalid assumptions become costly.
"""
    anatomy = """## 2. Reading the agent from the bottom up

The source is large because `SCHEDULE` stores 719 explicit actions. The reusable logic is small:

1. `_expected_hands` reads the live farm and determines how many hand actions are legal.
2. `_normalize_hands` keeps the scheduled list aligned with that live count.
3. `_predicted_shed` starts from observed storage, then accounts for same-turn `DROP` and
   `PICKUP` actions made on shed tiles.
4. `_guard_sells` processes sell orders in order, clamping each to the remaining predicted stock.
5. `agent` selects the scheduled step, applies the guards, and returns the three action channels.

Notice the ordering: storage is predicted **after** normalizing unit actions and **before**
validating market sales. A guard built from the pre-action shed alone would reject valid same-turn
deposits or allow sales after a pickup removed the stock.
"""
    provenance = """## 3. Provenance and license

This is not presented as a newly invented trajectory.

- Upstream notebook: [Kaggriculture Frontier Lab | High-Score + Visuals](https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-lab-high-score-visuals) by PRVSIYAN.
- Upstream license displayed on Kaggle: Apache License 2.0.
- Teacher evidence: public episode `89256171`, team `radiant-allomancer`, player `0`.
- Replay SHA-256: `ADADDE60EEFB93B56DBE9922B51D5D1970803F89DDF0EEEE67B9890024090405`.
- Local modifications: independent schedule regeneration, observation-based hand normalization,
  and impossible-sell drift guards.

The exact attribution stays in `main.py`. The release bundle also carries the Apache-2.0 license
and a NOTICE file. Please retain the attribution when forking.
"""
    engine_lesson = """## 4. Why the engine version belongs in every result

An exact same-cell local diagnostic compared versions 1.32.2 and 1.32.6 on 20 games. Every final
reward tuple changed, and 16 of 20 win/tie/loss outcomes changed. The only resolved default
configuration change was `townCenterSellInterval: 12 -> 24`.

That diagnostic used already-consumed development seeds, so it is evidence of **engine
sensitivity**, not promotion evidence. It teaches three practical rules:

1. Pin `kaggle-environments==1.32.6` when publishing a current benchmark.
2. Record the resolved environment configuration, not just the package version.
3. Never carry a score or win rate across engine versions as if it measured the same policy game.

A historical remote submission record cannot repair missing byte provenance. Kaggle does not
expose the old uploaded archive here, so this release does not attach any historical ladder score
to the exact source below.
"""
    source_cell = "%%writefile main.py\n" + source_text
    smoke = f'''# Engine-free identity, compile, schedule, and sell-guard checks.
import hashlib
import runpy
from pathlib import Path

payload = Path("main.py").read_bytes()
assert hashlib.sha256(payload).hexdigest().upper() == "{EXPECTED_SOURCE_SHA256}"
compile(payload, "main.py", "exec")

policy = runpy.run_path("main.py")
assert len(policy["SCHEDULE"]) == 719
assert policy["SOURCE_MODE"] == "sell_guard"
assert policy["_guard_sells"](
    [["SELL", "WHEAT", 3], ["SELL", "WHEAT", 2]],
    {{"WHEAT": 4}},
) == [["SELL", "WHEAT", 3], ["SELL", "WHEAT", 1]]
print("source identity, compile, schedule, and sell-guard probe: PASS")
'''
    evaluation = """## 6. A benchmark that survives scrutiny

For any change, run a paired matrix rather than one convenient game:

- use the same seeds for baseline and challenger;
- run both physical seats for every seed/opponent pair;
- complete the full 720-turn horizon;
- separate development, confirmation, and holdout seeds;
- record `DONE/DONE`, exceptions, hidden abnormal statuses, and invalid actions;
- report match score, money margin, lower tail, runtime percentiles, and worst case;
- hash source, resolved configuration, cell registry, and raw results before interpretation.

The local separation check for this release used eight consumed seeds, both seats, and exact
source hashes. Each of the two stronger private-source references went 16-0 against this public
source. Across a wider five-public-agent screen, the public source went 0-80. Those results make
the intended strength gap concrete, but the consumed seeds and selected opponents still prevent
them from becoming a general rating forecast.
"""
    experiments = f"""## 7. Experiments worth trying

Keep the baseline fixed and change only one mechanism at a time:

1. **Guard ablation:** remove `_guard_sells`; count invalid or wasteful sales.
2. **State-triggered fallback:** detect schedule drift and switch to a tiny reactive policy.
3. **End-game liquidation:** replace only the final-day market orders.
4. **Price-aware sizing:** preserve the route but cap sales using observed price and remaining days.
5. **Engine robustness:** repeat identical cells under two pinned versions and explain differences.

If you prefer a fully reactive, shorter starting point, compare this trace baseline with the
[existing public expansion baseline]({EXISTING_BASELINE_URL}). The useful question is not which
single score is larger; it is which assumptions survive paired both-seat tests.
"""
    package_cell = f'''import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

SOURCE_PATH = Path("main.py")
OUTPUT_NAME = "{ARCHIVE_NAME}"
EXPECTED_SOURCE_SHA256 = "{EXPECTED_SOURCE_SHA256}"
EXPECTED_ARCHIVE_SHA256 = "{archive_sha256}"

payload = SOURCE_PATH.read_bytes()
actual_source_sha256 = hashlib.sha256(payload).hexdigest().upper()
assert actual_source_sha256 == EXPECTED_SOURCE_SHA256

compressed = io.BytesIO()
with (
    gzip.GzipFile(filename="", mode="wb", fileobj=compressed, mtime=0) as gz,
    tarfile.open(fileobj=gz, mode="w") as archive,
):
    info = tarfile.TarInfo("main.py")
    info.size = len(payload)
    info.mode = 0o644
    info.mtime = 0
    info.uid = info.gid = 0
    info.uname = info.gname = ""
    archive.addfile(info, io.BytesIO(payload))

output_path = Path("/kaggle/working") / OUTPUT_NAME
output_path.write_bytes(compressed.getvalue())
actual_archive_sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest().upper()
assert actual_archive_sha256 == EXPECTED_ARCHIVE_SHA256
with tarfile.open(output_path, "r:gz") as archive:
    assert archive.getnames() == ["main.py"]
    assert archive.extractfile("main.py").read() == payload

print(json.dumps({{
    "artifact": OUTPUT_NAME,
    "source_sha256": actual_source_sha256,
    "archive_sha256": actual_archive_sha256,
    "archive_bytes": output_path.stat().st_size,
    "competition_submission_performed": False,
}}, indent=2))
'''
    limits = """## 8. Claims and limitations

| Statement | Evidence type | Limit |
|---|---|---|
| The displayed source is the audited G1 artifact | exact SHA-256 and byte-for-byte release check | identity, not strength |
| It lost 32/32 to the two private-source references | local 1.32.6 both-seat screen | consumed seeds; not a rating estimate |
| It lost 80/80 in the five-agent public screen | local 1.32.6 both-seat screen | selected opponents; not a population estimate |
| Expected Kaggle rating | **unknown; no claim made** | only a future public run could observe it |

The policy is open-loop, opponent-blind, tied to one public replay, sensitive to state and engine
drift, and intentionally weaker than the unpublished final agents. Packaging creates an archive;
it does **not** upload Code, publish a Discussion, or submit to the competition.
"""
    license_and_notice = f"""## 9. License and attribution notice

The full Apache License 2.0 and release notice are included here so the public notebook remains
self-contained. Keep both when redistributing the agent.

<details>
<summary>Apache License 2.0 — full text</summary>

```text
{license_text.rstrip()}
```
</details>

### Release notice

{notice_text.rstrip()}
"""

    return {
        "cells": [
            markdown_cell("overview", overview),
            markdown_cell("plan-plus-guardrail", mental_model),
            markdown_cell("agent-anatomy", anatomy),
            markdown_cell("provenance-and-license", provenance),
            markdown_cell("engine-version-lesson", engine_lesson),
            code_cell("audited-agent-source", source_cell),
            code_cell("compile-and-guard-probe", smoke),
            markdown_cell("evaluation-blueprint", evaluation),
            markdown_cell("next-experiments", experiments),
            code_cell("deterministic-package", package_cell),
            markdown_cell("claims-and-limitations", limits),
            markdown_cell("license-and-notice", license_and_notice),
        ],
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3",
            },
            "language_info": {"name": "python", "version": "3"},
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def file_record(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": path.relative_to(RELEASE_ROOT).as_posix(),
        "bytes": len(payload),
        "sha256": sha256(payload),
    }


def build_external_payload(notebook_record: dict[str, Any], metadata_record: dict[str, Any]) -> None:
    discussion = file_record(RELEASE_ROOT / "discussion_draft.md")
    payload = {
        "schema_version": 1,
        "status": "DRAFT_ONLY_NOT_EXECUTED",
        "execution_authorized": False,
        "external_calls_performed": [],
        "required_fresh_authority": "exact Code push and Discussion publication",
        "strength_gate": {
            "status": "PASS_LOCAL_SEPARATION_NON_PROMOTION",
            "public_source_sha256": EXPECTED_SOURCE_SHA256,
            "Kag_01_source_sha256": KAG_01_SOURCE_SHA256,
            "Kag_02_source_sha256": KAG_02_SOURCE_SHA256,
            "Kag_01_local_archive_sha256": KAG_01_ARCHIVE_SHA256,
            "Kag_02_local_archive_sha256": KAG_02_ARCHIVE_SHA256,
            "Kag_01_local_notebook_sha256": KAG_01_NOTEBOOK_SHA256,
            "Kag_02_local_notebook_sha256": KAG_02_NOTEBOOK_SHA256,
            "Kag_01_prepush_sha256": KAG_01_PREPUSH_SHA256,
            "Kag_02_prepush_sha256": KAG_02_PREPUSH_SHA256,
            "public_losses_vs_Kag_01": 16,
            "public_losses_vs_Kag_02": 16,
            "engine": "kaggle-environments==1.32.6",
            "limitations": "consumed seeds 23000-23007; both seats; not a rating estimate",
        },
        "actions": [
            {
                "sequence": 1,
                "kind": "kaggle_discussion_create",
                "enabled": False,
                "interface": "manual_or_separately_authorized_browser",
                "competition": "kaggriculture",
                "title": DISCUSSION_TITLE,
                "body": discussion,
                "existing_public_baseline_url": EXISTING_BASELINE_URL,
                "new_code_url": f"https://www.kaggle.com/code/{KERNEL_ID}",
                "link_state_at_publication": "EXPECTED_SLUG_PUBLISHED_IN_SEQUENCE_2",
            },
            {
                "sequence": 2,
                "kind": "kaggle_code_push",
                "enabled": False,
                "command_argv": [
                    "kaggle",
                    "kernels",
                    "push",
                    "-p",
                    "research/campaign_3000/08_public_release/kaggle_code_draft",
                ],
                "kernel_id": KERNEL_ID,
                "title": CODE_TITLE,
                "visibility": "public",
                "competition_submission": False,
                "notebook": notebook_record,
                "metadata": metadata_record,
                "expected_code_url": f"https://www.kaggle.com/code/{KERNEL_ID}",
            },
        ],
        "forbidden_actions": [
            "kaggle competitions submit",
            "competition Save & Run submission",
            "credential creation or disclosure",
            "publishing any source other than the exact allowlisted public SHA-256",
        ],
        "post_action_receipts_required": [
            "returned kernel ref and version",
            "remote visibility and COMPLETE status",
            "downloaded notebook SHA-256",
            "downloaded output archive SHA-256 and root main.py SHA-256",
            "published Discussion URL and rendered-title/body check",
            "explicit confirmation that no competition submission occurred",
        ],
    }
    EXTERNAL_PAYLOAD_PATH.write_bytes(json_bytes(payload))


def build() -> dict[str, Any]:
    source = read_expected(PUBLIC_SOURCE, EXPECTED_SOURCE_SHA256)
    license_payload = read_expected(PUBLIC_LICENSE, EXPECTED_LICENSE_SHA256)
    read_expected(LOCAL_ENGINE_SUMMARY, ENGINE_SUMMARY_SHA256)
    read_expected(LOCAL_ENGINE_COMPARISON, ENGINE_COMPARISON_SHA256)
    read_expected(LOCAL_ENGINE_CONFIG, ENGINE_CONFIG_SHA256)
    read_expected(LOCAL_PRIVATE_RELEASE_MANIFEST, PRIVATE_RELEASE_MANIFEST_SHA256)
    read_expected(LOCAL_PRIVATE_RELEASE_SPEC, PRIVATE_RELEASE_SPEC_SHA256)
    compile(source, "main.py", "exec")

    archive = deterministic_archive(source)
    ARCHIVE_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARCHIVE_PATH.write_bytes(archive)
    archive_record = file_record(ARCHIVE_PATH)

    notebook = build_notebook(
        source,
        archive_record["sha256"],
        license_payload.decode("utf-8"),
        (RELEASE_ROOT / "NOTICE.md").read_text(encoding="utf-8"),
    )
    metadata = {
        "id": KERNEL_ID,
        "title": CODE_TITLE,
        "code_file": NOTEBOOK_PATH.name,
        "language": "python",
        "kernel_type": "notebook",
        "is_private": False,
        "enable_gpu": False,
        "enable_tpu": False,
        "enable_internet": False,
        "machine_shape": "",
        "dataset_sources": [],
        "competition_sources": ["kaggriculture"],
        "kernel_sources": [],
        "model_sources": [],
    }
    NOTEBOOK_DIR.mkdir(parents=True, exist_ok=True)
    NOTEBOOK_PATH.write_bytes(json_bytes(notebook))
    METADATA_PATH.write_bytes(json_bytes(metadata))
    notebook_record = file_record(NOTEBOOK_PATH)
    metadata_record = file_record(METADATA_PATH)
    build_external_payload(notebook_record, metadata_record)

    manifest = {
        "schema_version": 1,
        "status": "LOCAL_PUBLIC_RELEASE_DRAFT_NO_EXTERNAL_ACTION",
        "selected_titles": {
            "kaggle_code": CODE_TITLE,
            "discussion": DISCUSSION_TITLE,
        },
        "public_source": {
            **file_record(PUBLIC_SOURCE),
            "canonical_sha256": EXPECTED_SOURCE_SHA256,
            "compile": "PASS",
            "recorded_actions": 719,
            "episode_steps": 720,
            "mode": "sell_guard",
        },
        "provenance": {
            "upstream_title": "Kaggriculture Frontier Lab | High-Score + Visuals",
            "upstream_author": "PRVSIYAN",
            "upstream_url": (
                "https://www.kaggle.com/code/prvsiyan/"
                "kaggriculture-frontier-lab-high-score-visuals"
            ),
            "upstream_license": "Apache-2.0",
            "license": file_record(PUBLIC_LICENSE),
            "teacher_episode_id": 89256171,
            "teacher_team": "radiant-allomancer",
            "teacher_player": 0,
            "teacher_replay_sha256": (
                "ADADDE60EEFB93B56DBE9922B51D5D1970803F89DDF0EEEE67B9890024090405"
            ),
            "modifications": [
                "independent schedule regeneration from the attributed public replay",
                "observation-based hand normalization",
                "impossible-SELL drift guards",
            ],
        },
        "strength_separation": {
            "status": "PASS_EXACT_LOCAL_HEAD_TO_HEAD_NON_PROMOTION",
            "engine": "kaggle-environments==1.32.6",
            "seeds": list(range(23000, 23008)),
            "seed_status": "CONSUMED_SCREEN",
            "seats": [0, 1],
            "Kag_01": {
                "designated_source_sha256": KAG_01_SOURCE_SHA256,
                "local_archive_sha256": KAG_01_ARCHIVE_SHA256,
                "local_archive_bytes": 19099,
                "local_notebook_sha256": KAG_01_NOTEBOOK_SHA256,
                "local_prepush_sha256": KAG_01_PREPUSH_SHA256,
                "local_metadata_sha256": KAG_01_METADATA_SHA256,
                "package_status": "LOCAL_PACKAGE_BUILT_EXTERNAL_ACTIONS_HOLD",
                "games_vs_public": 16,
                "wins_vs_public": 16,
                "public_losses": 16,
            },
            "Kag_02": {
                "designated_source_sha256": KAG_02_SOURCE_SHA256,
                "local_archive_sha256": KAG_02_ARCHIVE_SHA256,
                "local_archive_bytes": 17360,
                "local_notebook_sha256": KAG_02_NOTEBOOK_SHA256,
                "local_prepush_sha256": KAG_02_PREPUSH_SHA256,
                "local_metadata_sha256": KAG_02_METADATA_SHA256,
                "package_status": "LOCAL_PACKAGE_BUILT_EXTERNAL_ACTIONS_HOLD",
                "games_vs_public": 16,
                "wins_vs_public": 16,
                "public_losses": 16,
            },
            "five_public_agent_screen": {
                "games": 80,
                "public_source_wins": 0,
                "public_source_ties": 0,
                "public_source_losses": 80,
                "failures": 0,
            },
            "evidence": {
                "summary_path": "evidence/engine_screen_summary.json",
                "summary_sha256": ENGINE_SUMMARY_SHA256,
                "engine_comparison_path": "evidence/engine_comparison.json",
                "engine_comparison_sha256": ENGINE_COMPARISON_SHA256,
                "screen_config_path": "evidence/engine_screen_config.json",
                "screen_config_sha256": ENGINE_CONFIG_SHA256,
                "private_release_manifest_path": "evidence/private_release_manifest.json",
                "private_release_manifest_sha256": PRIVATE_RELEASE_MANIFEST_SHA256,
                "private_release_spec_path": "evidence/private_release_spec.json",
                "private_release_spec_sha256": PRIVATE_RELEASE_SPEC_SHA256,
                "origin_directory": "research/campaign_3000/05_engine_screen",
            },
            "interpretation_limit": (
                "Exact local separation on consumed seeds; not promotion evidence, a hidden "
                "strength estimate, or a Kaggle rating forecast."
            ),
        },
        "score_claim_contract": {
            "score_claim_for_exact_public_source": None,
            "expected_public_rating": "UNKNOWN",
            "historical_remote_evidence": {
                "submission_id": 55171193,
                "file_name": "Fa_04 - Frontier Trace Guard.tar.gz",
                "api_snapshot_score": 1317.1,
                "upload_byte_identity": (
                    "UNVERIFIED_KAGGLE_HISTORICAL_UPLOAD_BYTES_UNAVAILABLE"
                ),
                "may_be_claimed_for_this_release": False,
                "included_in_public_title_or_copy": False,
            },
        },
        "engine_1_32_6_lesson": {
            "same_cells": 20,
            "reward_tuples_changed": 20,
            "outcomes_changed": 16,
            "resolved_default_change": "townCenterSellInterval: 12 -> 24",
            "interpretation": "engine sensitivity only; consumed seeds; non-promotion",
        },
        "code_exclusion": {
            "allowlisted_agent_source_sha256": [EXPECTED_SOURCE_SHA256],
            "explicitly_not_copied_source_sha256": [
                KAG_01_SOURCE_SHA256,
                KAG_02_SOURCE_SHA256,
                RAY_SOURCE_SHA256,
            ],
            "basis": "release main.py is byte-identical to the audited G1 canonical source",
        },
        "artifacts": {
            "archive": {
                **archive_record,
                "members": ["main.py"],
                "payload_sha256": EXPECTED_SOURCE_SHA256,
                "deterministic_metadata": True,
            },
            "notebook": notebook_record,
            "kernel_metadata": {
                **metadata_record,
                "draft_visibility": "public",
                "is_private": False,
                "external_push_performed": False,
            },
            "discussion": file_record(RELEASE_ROOT / "discussion_draft.md"),
            "titles": file_record(RELEASE_ROOT / "titles.json"),
            "external_action_payload": file_record(EXTERNAL_PAYLOAD_PATH),
        },
        "authority": {
            "external_publish_authorized": False,
            "publication_order": ["discussion", "kaggle_code"],
            "kaggle_code_push_performed": False,
            "discussion_publish_performed": False,
            "competition_submission_performed": False,
            "browser_control_performed": False,
        },
        "release_gate": {
            "local_draft": "PASS",
            "exact_source_separation": "PASS",
            "external_publication": "HOLD_FOR_EXPLICIT_USER_AUTHORIZATION_AND_FRESH_AUDIT",
        },
    }
    MANIFEST_PATH.write_bytes(json_bytes(manifest))
    write_hashes()
    return manifest


def write_hashes() -> None:
    ignored = {HASHES_PATH.name}
    files = sorted(
        path
        for path in RELEASE_ROOT.rglob("*")
        if path.is_file()
        and path.name not in ignored
        and "__pycache__" not in path.parts
        and ".pytest_cache" not in path.parts
    )
    lines = [f"{sha256(path.read_bytes())}  {path.relative_to(RELEASE_ROOT).as_posix()}" for path in files]
    HASHES_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the local-only public release draft")
    parser.add_argument(
        "command",
        choices=("bootstrap", "build", "all"),
        nargs="?",
        default="build",
    )
    args = parser.parse_args()
    if args.command in {"bootstrap", "all"}:
        bootstrap()
    if args.command in {"build", "all"}:
        manifest = build()
        print(json.dumps(manifest["artifacts"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
