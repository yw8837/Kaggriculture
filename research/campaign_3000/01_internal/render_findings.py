from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent


def read_json(name: str) -> Any:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def fmt(value: float | None, digits: int = 1) -> str:
    if value is None:
        return "UNVERIFIED"
    return f"{float(value):.{digits}f}"


def median(summary: dict[str, Any], key: str) -> float | None:
    value = summary.get(key)
    return value.get("median") if isinstance(value, dict) else None


def main() -> None:
    full_lb = read_json("leaderboard_full_snapshot.json")
    api_lb = read_json("leaderboard_top25_provenance.json")
    ours = read_json("our_submission_provenance.json")
    comparative = read_json("comparative_metrics.json")
    public_join = read_json("leaderboard_public_join.json")
    replay_integrity = read_json("replay_integrity_report.json")
    local_source = read_json("local_source_map.json")

    our_team = full_lb["our_team"]
    full_top = full_lb["top25"][0]
    full_cut = full_lb["top25"][-1]
    gap_first = float(full_top["Score"]) - float(our_team["Score"])
    gap_cut = float(full_cut["Score"]) - float(our_team["Score"])

    lines: list[str] = []
    lines.extend(
        [
            "# Kaggriculture 내부/LB/리플레이 전수조사 — 3000 캠페인",
            "",
            "## 결론",
            "",
            f"- 전체 리더보드 동결 시점 `{full_lb['observed_at_utc']}`: 우리 `yw8837`은 **{our_team['Rank']}위 / {full_lb['population_rows']}팀, {our_team['Score']}점**이다.",
            f"- 같은 동결본에서 1위는 {full_top['TeamName']} {full_top['Score']}점, 25위는 {full_cut['TeamName']} {full_cut['Score']}점이다. 격차는 각각 **{gap_first:.1f} / {gap_cut:.1f}점**이다.",
            "- 현재 3000대 메타의 가장 강한 관측 신호는 ‘더 영리한 미세 조정’보다 **공유된 강한 농장 실행 테이프 + 소규모 시장 오버레이**다. API 상위 25의 양 좌석 표본 50개 중 38개, 19개 팀이 정확히 같은 farm-action SHA-256을 쓴다.",
            "- 우리 최고 이력 2119.2점 계열은 그 공유 테이프보다 peak labor가 12 대 14, crop이 대략 62~82 대 94, wheat가 11~31 대 40으로 구조적으로 작다. 시장 SELL 요청만 늘린 bot_11/12는 1312.7/1225.8로 내려갔다.",
            "- 따라서 3000 목표의 1순위는 상위 공통 농장 골격을 재구성해 강한 control로 만들고, 2순위는 1위/3위에서 관측된 실제 농장 적응을 제한된 단일 delta로 붙이는 것이다. 절대 현금이나 자기 계열 상대 로컬 승률로 승격하면 안 된다.",
            "- 향후 파일명은 사용자 고정 규칙인 `Kag_XX - Short Description.tar.gz`; Fa/Ge/bot 접두사는 이 보고서에서 역사 제출물 식별에만 쓴다.",
            "",
            "## 모집단과 동결 시점",
            "",
            "| 항목 | 모집단 | 조회 UTC | 증거 |",
            "|---|---:|---|---|",
            f"| 전체 LB | {full_lb['population_rows']}팀 | {full_lb['observed_at_utc']} | `{full_lb['archive']['sha256']}` zip, CSV `{full_lb['member']['sha256']}` |",
            f"| API LB 상세 | 첫 25행 | {api_lb['leaderboard_observed_at_utc']} | `leaderboard_top25_provenance.json` |",
            f"| 우리 제출 | {ours['submission_count']}건, 공개 episode metadata 1017행 | {ours['api_observed_at_utc']} | `our_submission_provenance.json`, `our_episode_inventory.jsonl` |",
            f"| 원 raw replay | {replay_integrity['raw_replays']['total']}개 / {sum(row['bytes'] for row in [json.loads(line) for line in (ROOT / 'replay_inventory.jsonl').read_text(encoding='utf-8').splitlines() if line]):,} bytes | {replay_integrity['created_at_utc']} 검증 | 89/89 SHA·bytes·720-step PASS |",
            f"| 공개 Code | 155 current refs | {public_join['source_evidence']['code_inventory.jsonl']['observed_at_utc']} | `{public_join['source_evidence']['code_inventory.jsonl']['sha256']}` |",
            f"| Discussion | 57 IDs, 일부 author 미확인 | {public_join['source_evidence']['discussion_inventory.jsonl']['observed_at_utc']} | `{public_join['source_evidence']['discussion_inventory.jsonl']['sha256']}` |",
            f"| Models | 1개 미확인 record; zero-population 주장 아님 | {public_join['source_evidence']['model_inventory.jsonl']['observed_at_utc']} | `{public_join['source_evidence']['model_inventory.jsonl']['sha256']}` |",
            f"| FC37 public lineage scan | high-score output 18 refs/89 files + current source 61 success/94 rate-limit | {public_join['source_evidence']['lineage_summary.json']['observed_at_utc']} | `{public_join['source_evidence']['lineage_summary.json']['sha256']}` local SHA-pinned |",
            "",
            "API 상세 25행과 17분 뒤 전체 CSV의 25위 구성은 이미 달라졌다. 아래 상위 25 분석은 반드시 각 표의 조회 시점에만 유효하다.",
            "초기 `inventory_manifest.json`/`collection_errors.jsonl`은 API 429가 있던 historical partial snapshot이다. 5개 실패 submission을 재조회한 `repair_manifest.json`과 현재 `our_submissions.json`/`our_episode_inventory.jsonl`이 완성본이다. 원 오류 기록은 덮어쓰지 않았다.",
            "",
            "## 우리 제출 22건",
            "",
            "`Games/W-D-L`은 validation을 제외하고 API에서 조회된 완료 public episode 기준이다. `local archive/main`은 현재 Desktop dirty worktree의 같은 파일명 후보이며 **Kaggle에 실제 업로드된 과거 bytes와 동일하다는 뜻이 아니다**.",
            "",
            "| ID | 파일 | 점수 | Games | W-D-L | 승률 | 평균 margin | local archive/main SHA prefix |",
            "|---:|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in ours["rows"]:
        perf = row["public_episode_performance"]
        matches = row["local_source_mapping"]["local_filename_matches"]
        if matches:
            archive = matches[0]
            main_member = next(
                (member for member in archive.get("members", []) if member["name"] == "main.py"),
                None,
            )
            source = archive["sha256"][:10] + "/" + (
                main_member["sha256"][:10] if main_member else "NO_MAIN"
            )
        elif row["submission_id"] == 55171193:
            source = "local filename NONE; tracked G1 81159A18DF"
        else:
            source = "UNVERIFIED"
        lines.append(
            "| {id} | {file} | {score:.1f} | {games} | {wins}-{draws}-{losses} | {rate:.3f} | {margin:.1f} | `{source}` |".format(
                id=row["submission_id"],
                file=row["file_name"].replace("|", "/"),
                score=row["public_score"],
                games=perf["games"],
                wins=perf["wins"],
                draws=perf["draws"],
                losses=perf["losses"],
                rate=perf["win_rate"],
                margin=perf["mean_margin"],
                source=source,
            )
        )

    lines.extend(
        [
            "",
            "핵심 해석:",
            "",
            "- 현재 active 최신 두 건은 같은 이름의 bot_05이고 1128.8/1094.8점이다. 각각 108/122 public games에서 승률 0.463/0.418로, 단순 ‘더 기다리면 3000’ 상태가 아니다.",
            "- 2119.2 bot_05는 76 public games, 32-44, 평균 margin -768.4다. 과거 rating peak는 강한 절대 성능 증명과 동일하지 않다.",
            "- bot_02는 47 games, 29-3-15, 평균 margin +9050.1로 우리 이력 중 비교적 안정적이지만 rating 1878.5다.",
            "- bot_07은 33 games, 24-9라 좋아 보이나 표본이 작고, 기존 문서가 밝힌 donor/self-lineage 오염 때문에 로컬 40-0을 재사용할 수 없다.",
            "- 같은 파일명 bot_05 세 제출은 현재 local archive 한 개로만 매핑된다. historical upload bytes가 없으므로 서로 동일 정책이었다고 확정할 수 없다.",
            "",
            "## API 상위 25 상세",
            "",
            f"동결: `{api_lb['leaderboard_observed_at_utc']}`. `Games/W-D-L`은 해당 팀의 최고 publicScore submission 전체 metadata. `Replay`는 우리 저장본 수이며 각 팀 양 좌석 1개 요청(공유 매치 때문에 50 요청/45 unique raw)이다.",
            "",
            "| Rank | Team | Score | Submission | Games | W-D-L | Win | Mean margin | Replay | Public exact-name evidence |",
            "|---:|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in api_lb["rows"]:
        perf = row["highest_scoring_submission_episode_performance"]
        code = row["public_code"]
        exact = code.get("exact_display_name_matches") or []
        inferred = code.get("unverified_inferences") or []
        if exact:
            public_status = f"Code exact {len(exact)}"
        elif inferred:
            public_status = "Code inference 1 (UNVERIFIED)"
        else:
            public_status = "none observed in frozen inventory"
        lines.append(
            "| {rank} | {team} | {score:.1f} | {sub} | {games} | {wins}-{draws}-{losses} | {rate:.3f} | {margin:.1f} | {replays} | {public} |".format(
                rank=row["rank"],
                team=row["team_name"].replace("|", "/"),
                score=row["leaderboard_score"],
                sub=perf["submission_id"],
                games=perf["games"],
                wins=perf["wins"],
                draws=perf["draws"],
                losses=perf["losses"],
                rate=perf["win_rate"],
                margin=perf["mean_margin"],
                replays=len(row["sampled_public_replays"]),
                public=public_status,
            )
        )

    top = comparative["top25_sample"]
    our_sample = comparative["our_sample"]
    bot05 = comparative["ours_by_file"]["bot_05 - Tetsuya Tape Shield.tar.gz"]
    bot07 = comparative["ours_by_file"]["bot_07 - Meta Tape Shield.tar.gz"]
    lines.extend(
        [
            "",
            "Public exact-name join은 이름 동일성만 확인했다. Rayk Kretzschmar는 두 Code가 exact match다: `kaggriculture-findings-from-zero-to-top-meta` v15 (source `CBE0CABA...`, license 미확인)와 `kaggriculture-rank-your-agent` v10 (source `C9D5EB18...`, Apache-2.0). Lester Leong↔fle3n은 추정일 뿐 identity-proven이 아니다. Discussion/Models는 exact-name match가 관측되지 않았지만 inventory 한계 때문에 ‘없음’으로 단정하지 않는다.",
            "",
            "## 리플레이 패턴",
            "",
            "아래 SELL 값은 **요청된 market order 빈도**다. 체결량으로 해석하면 안 된다. 또한 두 cohort의 상대 강도가 달라 absolute cash를 strength로 비교하면 안 된다.",
            "",
            "| Metric (median) | Top25 50 obs | 우리 44 obs | bot_05 6 obs | bot_07 2 obs |",
            "|---|---:|---:|---:|---:|",
            f"| Peak hands | {median(top, 'peak_hands'):.1f} | {median(our_sample, 'peak_hands'):.1f} | {median(bot05, 'peak_hands'):.1f} | {median(bot07, 'peak_hands'):.1f} |",
            f"| Hire order turns | {median(top, 'total_hire_orders'):.1f} | {median(our_sample, 'total_hire_orders'):.1f} | {median(bot05, 'total_hire_orders'):.1f} | {median(bot07, 'total_hire_orders'):.1f} |",
            f"| First land step | {median(top, 'first_land_step'):.1f} | {median(our_sample, 'first_land_step'):.1f} | {median(bot05, 'first_land_step'):.1f} | {median(bot07, 'first_land_step'):.1f} |",
            f"| Third quadrant step | {median(top, 'quadrant3_step'):.1f} | {median(our_sample, 'quadrant3_step'):.1f} | {median(bot05, 'quadrant3_step'):.1f} | {median(bot07, 'quadrant3_step'):.1f} |",
            f"| Peak crops total | {median(top, 'peak_crops_total'):.1f} | {median(our_sample, 'peak_crops_total'):.1f} | {median(bot05, 'peak_crops_total'):.1f} | {median(bot07, 'peak_crops_total'):.1f} |",
            f"| Strawberry | {median(top, 'peak_strawberry'):.1f} | {median(our_sample, 'peak_strawberry'):.1f} | {median(bot05, 'peak_strawberry'):.1f} | {median(bot07, 'peak_strawberry'):.1f} |",
            f"| Wheat | {median(top, 'peak_wheat'):.1f} | {median(our_sample, 'peak_wheat'):.1f} | {median(bot05, 'peak_wheat'):.1f} | {median(bot07, 'peak_wheat'):.1f} |",
            f"| Peak animals | {median(top, 'peak_animals_total'):.1f} | {median(our_sample, 'peak_animals_total'):.1f} | {median(bot05, 'peak_animals_total'):.1f} | {median(bot07, 'peak_animals_total'):.1f} |",
            f"| Requested SELL turns | {median(top, 'sell_order_turns'):.1f} | {median(our_sample, 'sell_order_turns'):.1f} | {median(bot05, 'sell_order_turns'):.1f} | {median(bot07, 'sell_order_turns'):.1f} |",
            f"| Unit non-PASS rate | {median(top, 'non_pass_rate'):.3f} | {median(our_sample, 'non_pass_rate'):.3f} | {median(bot05, 'non_pass_rate'):.3f} | {median(bot07, 'non_pass_rate'):.3f} |",
            f"| Max shed units | {median(top, 'max_shed_units'):.1f} | {median(our_sample, 'max_shed_units'):.1f} | {median(bot05, 'max_shed_units'):.1f} | {median(bot07, 'max_shed_units'):.1f} |",
            f"| Final shed units | {median(top, 'final_shed_units'):.1f} | {median(our_sample, 'final_shed_units'):.1f} | {median(bot05, 'final_shed_units'):.1f} | {median(bot07, 'final_shed_units'):.1f} |",
            f"| Day27+ SELL turns | {median(top, 'endgame_sell_turns_d27plus'):.1f} | {median(our_sample, 'endgame_sell_turns_d27plus'):.1f} | {median(bot05, 'endgame_sell_turns_d27plus'):.1f} | {median(bot07, 'endgame_sell_turns_d27plus'):.1f} |",
            "",
            "패턴 해석:",
            "",
            "- 공유 top tape 중앙값은 14 hands, 94 crops(42 strawberry/12 melon/40 wheat), 14 animals(8 cow/6 sheep), shed peak 96, terminal shed/carried 0이다.",
            "- 19-team dominant farm-action hash는 `FC37F8688680DA949DB44C9444DCB9541488B4E10D9F432CC42648D6423F1B26`; ranks 4,6,8-20,22-25에서 38/38 관측이 일치했다.",
            "- 상위 25 중 23개 팀은 서로 다른 seed·반대 seat 두 게임에서 farm action hash가 동일했다. 이들 대부분의 full-action 차이는 market 7~27 steps뿐이다. MD Concepcion은 market 포함 720-step action 전체가 두 게임에서 동일했다.",
            "- rank1 Seb와 rank3 HealthStone만 farm actions가 각각 579/573 steps 달랐다. 즉 최상단에는 공개 공통 테이프를 그대로 쓰지 않는 실제 적응 계열도 존재한다.",
            "- 공개 lineage 음성 검색은 high-score kernel output 18 refs/89 files(AST 18/18, literal tapes 20)에서 FC37 exact match 0, current source API 성공 61/155(94건 429, literal tapes 15)에서 match 0이었다. 초기 PRVSIYAN Frontier V12 세 alignment도 불일치했다. 이는 부재 증명이 아니며 compressed/generated tape를 놓칠 수 있어 FC37은 여전히 UNMAPPED다.",
            "- 우리 replay 표본의 final cash 중앙값이 top보다 높지만 상대 풀과 selection이 다르다. 우리 44표본의 target win 42/44 역시 ‘각 제출에서 고른 두 게임’ 편향이라 rating/strength 추론에 쓰지 않는다.",
            "",
            "## 확인된 평가 결함과 영향",
            "",
            "| 결함 | 원본 증거 | 영향 |",
            "|---|---|---|",
            "| Legacy runner DONE 덮어쓰기 | runner `B0341417...`는 final state만 읽음; official env `B6DA1554...`는 마지막에 모든 status를 DONE으로 설정 | 과거 `failures=0`은 ERROR/TIMEOUT/INVALID 부재 증명이 아님 |",
            "| 재현 기록 | `docs/BOT_DESIGN_SPEC.md` `93FF99DA...` lines 427-431: step300 RuntimeError→418 ERROR steps→final DONE/DONE→valid4/failed0 | 크래시가 정상 저현금 패배처럼 집계 가능 |",
            "| donor/self-lineage 오염 | 같은 문서: bot_07 40게임 중 24게임(60%)이 donor/조상 계열; bot_11/12도 같은 의심 | 40-0, 0.656, 0.625 로컬 수치를 승격 근거로 재사용 금지 |",
            "| half-layer seam 검사 | farmer만 같았으나 hands step6부터 104곳, market step0부터 292곳 차이 | ‘깨끗한 graft’ 주장 철회, full action layer 비교 필요 |",
            "| absolute cash cohort 비교 | 우리 표본은 약한 상대/선택 편향, top 표본은 동형 top-vs-top 다수 | cash·표본 win은 cross-cohort strength 지표가 아님 |",
            "| historical byte ambiguity | API는 과거 upload archive bytes를 제공하지 않음; 같은 이름 재사용 | 현재 local archive와 submitted policy의 byte identity는 UNVERIFIED |",
            "",
            "다만 저장된 우리 public replay 44개는 63,272 ACTIVE + terminal DONE 88, terminal pair 44/44 DONE/DONE였다. 이것은 그 44개 public game에서 비정상 status가 관측되지 않았다는 좁은 증거일 뿐, 1017 metadata 전체나 과거 로컬 grid를 복구하지 않는다. 세부 계약은 `runner_done_overwrite_defect.json`에 고정했다.",
            "",
            "## 3000 목표에 바로 연결되는 후보 가설",
            "",
            "1. **Kag_01 — FC37 farm reconstruction + frozen-safe market baseline.** 19팀/38관측 공통 farm tape를 공개 replay에서 byte-provenance와 함께 재구성한다. 먼저 action parity 720/720을 여러 seed/seat에서 확인하고, market은 관측된 중앙 schedule을 고정한다. 이 후보는 ‘혁신’이 아니라 3000 meta의 재현 가능한 강한 control이다.",
            "2. **Kag_02 — adaptive farm switch.** Seb/HealthStone 두 좌석 replay에서 공통 tape와 갈라지는 최초 상태·행동을 추출하고, 관측 가능한 state에만 의존하는 한 개 switch를 붙인다. identity/episode/seed lookup은 금지한다. FC37 control 대비 외부 top opponents에서 개선이 없으면 버린다.",
            "3. **시장 overlay는 후순위·제한 delta.** 공유 cluster의 농장 hash는 같고 market만 7~27 steps 변한다. 농장 parity를 먼저 고정한 뒤 SELL quantity/timing 한 종류만 실험한다. bot_11/12처럼 SELL 요청 수만 늘리는 방향은 실전 하락 이력이 있다.",
            "4. **평가 gate.** donor/자기조상 제외, top25에서 최소 FC37 cluster·rank1 adaptive·rank3 adaptive 포함, 동일 seed/seat/scenario paired grid, seed-cluster bootstrap, every-opponent floor, stepwise status scan, raw+receipt+source hash를 요구한다. fresh sealed seed는 selection 완료 전 열지 않는다.",
            "",
            "## 미확인/과장 금지 범위",
            "",
            "- 상위 25의 private source와 exact uploaded archive는 확인 불가다.",
            "- 4,166개 top metadata row 중 raw는 45 unique episodes만 저장했다. 나머지를 분석했다고 쓰지 않는다.",
            "- 우리 1,017 metadata row 중 raw는 44 episodes만 저장했다. status scan의 범위도 44개다.",
            "- FC37 cluster의 exact public Code lineage는 UNMAPPED다. 초기 Frontier V12와는 불일치만 확인했다.",
            "- Ray 외 top25 Code author exact-name match는 동결된 155 current refs에서 관측되지 않았다. ‘공개 코드가 없다’는 뜻이 아니다.",
            "- Discussion은 57 IDs 중 exact-name match가 없었으나 일부 author가 미확인이다. Models도 1 record만 확보했으므로 전수 zero-population 주장이 아니다.",
            "- replay market SELL은 요청(action)이지 실제 체결량이 아니다.",
            "- 3000/top3는 목표이지 이 조사만으로 보장되지 않는다.",
            "",
            "## 핵심 machine-readable 산출물",
            "",
            "- `leaderboard_top25_provenance.json`: 25행 rank/team/score/highest-score submission 전체 성적/양 좌석 replay/code join.",
            "- `our_submission_provenance.json`: 22건 score/episode/W-D-L/local archive·main 후보/업로드 byte 미확인 표시.",
            "- `submission_policy_source_map.json`: 22건별 policy family, 역사 문서/ledger 근거, local archive/main 후보, historical upload byte 미확인 표시.",
            "- `replay_inventory.jsonl`: 89 raw의 campaign-worktree-relative POSIX path, URL, episode, seed, SHA, bytes, selection provenance.",
            "- `replays_raw/*.json`: 약 2.38 GB라 Git에는 넣지 않고 local ignored evidence로 유지한다. 재수집 URL/명령과 exact hash chain은 inventory/integrity/manifest에 남겼다.",
            "- `replay_feature_report.json`: 89 replay의 Python-native dict/list features; `System.Object[]` 표시는 PowerShell display/재직렬화 문제였고 원 JSON schema 문제가 아니다.",
            "- `comparative_metrics.json`: 94 target observations, cohort/policy summaries, full episode metadata performance, action fingerprints.",
            "- `leaderboard_public_join.json`: Code/Discussion/Model exact-name join과 absence scope.",
            "- `local_source_map.json`: Desktop dirty worktree read-only source/archive index 135개와 22 submission filename candidates.",
            "- `replay_integrity_report.json`: 89/89 raw SHA·bytes·schema/status check.",
            "- `runner_done_overwrite_defect.json`: legacy runner 결함과 영향 경계.",
            "- `evidence_manifest.json`: 모든 비-raw 산출물 hash와 89 raw inventory/hash chain.",
        ]
    )

    output = ROOT / "findings.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"{output} {output.stat().st_size} {sha256(output)}")
    print(f"source_index_count={local_source['source_index_count']}")


if __name__ == "__main__":
    main()
