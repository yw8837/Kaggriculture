# Kaggriculture 내부/LB/리플레이 전수조사 — 3000 캠페인

## 결론

- 전체 리더보드 동결 시점 `2026-08-08T18:07:16.569Z`: 우리 `yw8837`은 **992위 / 3164팀, 1128.8점**이다.
- 같은 동결본에서 1위는 Seb (allegedly) 3204.4점, 25위는 Sebastian Mateus 3013.7점이다. 격차는 각각 **2075.6 / 1884.9점**이다.
- 현재 3000대 메타의 가장 강한 관측 신호는 ‘더 영리한 미세 조정’보다 **공유된 강한 농장 실행 테이프 + 소규모 시장 오버레이**다. API 상위 25의 양 좌석 표본 50개 중 38개, 19개 팀이 정확히 같은 farm-action SHA-256을 쓴다.
- 우리 최고 이력 2119.2점 계열은 그 공유 테이프보다 peak labor가 12 대 14, crop이 대략 62~82 대 94, wheat가 11~31 대 40으로 구조적으로 작다. 시장 SELL 요청만 늘린 bot_11/12는 1312.7/1225.8로 내려갔다.
- 따라서 3000 목표의 1순위는 상위 공통 농장 골격을 재구성해 강한 control로 만들고, 2순위는 1위/3위에서 관측된 실제 농장 적응을 제한된 단일 delta로 붙이는 것이다. 절대 현금이나 자기 계열 상대 로컬 승률로 승격하면 안 된다.
- 향후 파일명은 사용자 고정 규칙인 `Kag_XX - Short Description.tar.gz`; Fa/Ge/bot 접두사는 이 보고서에서 역사 제출물 식별에만 쓴다.

## 모집단과 동결 시점

| 항목 | 모집단 | 조회 UTC | 증거 |
|---|---:|---|---|
| 전체 LB | 3164팀 | 2026-08-08T18:07:16.569Z | `0AC0BCBFB782758E87D09F9B5FA3729AEA7B01B63D37F1E1E5A58F9265F5692F` zip, CSV `2D05283C1082DA8034FDE9CD40D0D4ED5845ECD20CA7324C98003336A8643FC3` |
| API LB 상세 | 첫 25행 | 2026-08-08T17:50:15.385Z | `leaderboard_top25_provenance.json` |
| 우리 제출 | 22건, 공개 episode metadata 1017행 | 2026-08-08T17:50:15.385Z | `our_submission_provenance.json`, `our_episode_inventory.jsonl` |
| 원 raw replay | 89개 / 2,382,236,899 bytes | 2026-08-08T18:16:32.544686Z 검증 | 89/89 SHA·bytes·720-step PASS |
| 공개 Code | 155 current refs | 2026-08-08T18:03:31Z/2026-08-08T18:08:30Z | `E510D00AB0AFB35E06B90EFD8EB8CC96DA08F29D8398DF682CDDDD060A7BEEC1` |
| Discussion | 57 IDs, 일부 author 미확인 | 2026-08-08T18:06:25.995844Z/2026-08-08T18:07:31.603370Z | `8A296AE0C70728883FA9A2506B263DA3A3907678F03FCAB5D2357DF6B348B767` |
| Models | 1개 미확인 record; zero-population 주장 아님 | 2026-08-08T18:07:36.430544Z | `6807E5AC0DB8B02EBE5BFF62AC764454A5CD208C3F6C8A2666934C61F8C8D60E` |
| FC37 public lineage scan | high-score output 18 refs/89 files + current source 61 success/94 rate-limit | 2026-08-08T18:16:41.929464Z/2026-08-08T18:23:06.335683Z | `C93AB3BEEA82FD3D88A2A8167B12C68DB43D49EF2FB101DFD9948C225B0D6F06` local SHA-pinned |

API 상세 25행과 17분 뒤 전체 CSV의 25위 구성은 이미 달라졌다. 아래 상위 25 분석은 반드시 각 표의 조회 시점에만 유효하다.
초기 `inventory_manifest.json`/`collection_errors.jsonl`은 API 429가 있던 historical partial snapshot이다. 5개 실패 submission을 재조회한 `repair_manifest.json`과 현재 `our_submissions.json`/`our_episode_inventory.jsonl`이 완성본이다. 원 오류 기록은 덮어쓰지 않았다.

## 우리 제출 22건

`Games/W-D-L`은 validation을 제외하고 API에서 조회된 완료 public episode 기준이다. `local archive/main`은 현재 Desktop dirty worktree의 같은 파일명 후보이며 **Kaggle에 실제 업로드된 과거 bytes와 동일하다는 뜻이 아니다**.

| ID | 파일 | 점수 | Games | W-D-L | 승률 | 평균 margin | local archive/main SHA prefix |
|---:|---|---:|---:|---:|---:|---:|---|
| 55270999 | bot_05 - Tetsuya Tape Shield.tar.gz | 1128.8 | 108 | 50-0-58 | 0.463 | 3251.3 | `DE1ABBFC0D/1EB472AEF9` |
| 55270996 | bot_05 - Tetsuya Tape Shield.tar.gz | 1094.8 | 122 | 51-0-71 | 0.418 | 2585.7 | `DE1ABBFC0D/1EB472AEF9` |
| 55244867 | bot_12 - Live Market R2914.tar.gz | 1225.8 | 56 | 28-0-28 | 0.500 | 7525.3 | `8A15B0624C/8308D9AE06` |
| 55244861 | bot_11 - Live Market R2921.tar.gz | 1312.7 | 54 | 28-0-26 | 0.519 | 7106.3 | `2D40888EB3/2A0EF2609A` |
| 55239511 | bot_08 - Terminal Wheat Graft.tar.gz | 1463.4 | 29 | 19-0-10 | 0.655 | 17075.8 | `77D46BCCD0/3B9B4CEE58` |
| 55239508 | bot_07 - Meta Tape Shield.tar.gz | 1749.4 | 33 | 24-0-9 | 0.727 | 37287.4 | `AF68DEB651/EDB86D4A1C` |
| 55206974 | bot_05 - Tetsuya Tape Shield.tar.gz | 2119.2 | 76 | 32-0-44 | 0.421 | -768.4 | `DE1ABBFC0D/1EB472AEF9` |
| 55199616 | bot_03 - Terminal Flush Tape.tar.gz | 1678.0 | 101 | 36-0-65 | 0.356 | 681.8 | `D0D3EAF3F9/61BB757C55` |
| 55199612 | bot_02 - Zero-Waste Tape.tar.gz | 1878.5 | 47 | 29-3-15 | 0.617 | 9050.1 | `8900914D04/E73080954C` |
| 55198657 | Ge_04.tar.gz | 768.3 | 15 | 7-0-8 | 0.467 | -5966.5 | `8CDF1C40EF/9D59F2DDDB` |
| 55198655 | Ge_03.tar.gz | 724.4 | 14 | 7-0-7 | 0.500 | 6937.8 | `827C7B17ED/455ABA88CD` |
| 55185695 | Ge_02.tar.gz | 774.5 | 25 | 12-0-13 | 0.480 | -214.8 | `63F3BC795F/2A6B3368AF` |
| 55185691 | Ge_01.tar.gz | 746.5 | 24 | 12-0-12 | 0.500 | -1496.8 | `E020EAB0E5/9ED86F667D` |
| 55185510 | Ge_02.tar.gz | 757.0 | 3 | 2-0-1 | 0.667 | 6931.7 | `63F3BC795F/2A6B3368AF` |
| 55185505 | Ge_01.tar.gz | 810.5 | 2 | 2-0-0 | 1.000 | 39867.5 | `E020EAB0E5/9ED86F667D` |
| 55183485 | bot_01 - Capacity Expansion.tar.gz | 815.7 | 14 | 7-0-7 | 0.500 | 9557.1 | `F73CEDD676/B863259A8B` |
| 55171193 | Fa_04 - Frontier Trace Guard.tar.gz | 1317.1 | 65 | 33-2-30 | 0.508 | 5790.0 | `local filename NONE; tracked G1 81159A18DF` |
| 55154217 | Fa_03 - Meta Expansion.tar.gz | 889.7 | 58 | 24-0-34 | 0.414 | -9010.0 | `B2D58348CC/737DCC8BB0` |
| 55154212 | Fa_02 - Last-Chance Tiebreak.tar.gz | 913.0 | 40 | 17-0-23 | 0.425 | -5548.8 | `E1DA47187E/C3AE4A705C` |
| 55142935 | Fa_01 - Overflow-Safe Inventory.tar.gz | 1003.5 | 48 | 24-0-24 | 0.500 | 3915.2 | `1B52522D0C/0AF2CC1527` |
| 55137248 | cow_tilt.tar.gz | 991.4 | 43 | 20-0-23 | 0.465 | 2834.4 | `73F15AECDD/6CDE000228` |
| 55137246 | fast_expansion.tar.gz | 1068.0 | 18 | 12-0-6 | 0.667 | 11272.2 | `2ECB98759C/406BC82979` |

핵심 해석:

- 현재 active 최신 두 건은 같은 이름의 bot_05이고 1128.8/1094.8점이다. 각각 108/122 public games에서 승률 0.463/0.418로, 단순 ‘더 기다리면 3000’ 상태가 아니다.
- 2119.2 bot_05는 76 public games, 32-44, 평균 margin -768.4다. 과거 rating peak는 강한 절대 성능 증명과 동일하지 않다.
- bot_02는 47 games, 29-3-15, 평균 margin +9050.1로 우리 이력 중 비교적 안정적이지만 rating 1878.5다.
- bot_07은 33 games, 24-9라 좋아 보이나 표본이 작고, 기존 문서가 밝힌 donor/self-lineage 오염 때문에 로컬 40-0을 재사용할 수 없다.
- 같은 파일명 bot_05 세 제출은 현재 local archive 한 개로만 매핑된다. historical upload bytes가 없으므로 서로 동일 정책이었다고 확정할 수 없다.

## API 상위 25 상세

동결: `2026-08-08T17:50:15.385Z`. `Games/W-D-L`은 해당 팀의 최고 publicScore submission 전체 metadata. `Replay`는 우리 저장본 수이며 각 팀 양 좌석 1개 요청(공유 매치 때문에 50 요청/45 unique raw)이다.

| Rank | Team | Score | Submission | Games | W-D-L | Win | Mean margin | Replay | Public exact-name evidence |
|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | Seb (allegedly) | 3204.4 | 55299100 | 119 | 107-0-12 | 0.899 | 17872.4 | 2 | none observed in frozen inventory |
| 2 | tao wu11 | 3138.4 | 55345236 | 77 | 74-0-3 | 0.961 | 7552.6 | 2 | none observed in frozen inventory |
| 3 | HealthStone | 3136.6 | 55341106 | 85 | 79-0-6 | 0.929 | 13837.3 | 2 | none observed in frozen inventory |
| 4 | Mohamed abdelrazik | 3128.1 | 55343482 | 82 | 81-0-1 | 0.988 | 7598.2 | 2 | none observed in frozen inventory |
| 5 | kevin park | 3113.2 | 55349527 | 71 | 67-0-4 | 0.944 | 7098.9 | 2 | none observed in frozen inventory |
| 6 | Lester Leong | 3111.0 | 55348654 | 74 | 64-0-10 | 0.865 | 10449.6 | 2 | Code inference 1 (UNVERIFIED) |
| 7 | Syed Muhammad Gillani | 3109.1 | 55346836 | 79 | 73-0-6 | 0.924 | 10074.4 | 2 | none observed in frozen inventory |
| 8 | mrgrishninsb | 3102.0 | 55337518 | 92 | 75-0-17 | 0.815 | 4191.2 | 2 | none observed in frozen inventory |
| 9 | Forrest | 3093.7 | 55351460 | 69 | 66-0-3 | 0.957 | 8102.3 | 2 | none observed in frozen inventory |
| 10 | lucaskna | 3092.3 | 55351607 | 67 | 63-0-4 | 0.940 | 9294.8 | 2 | none observed in frozen inventory |
| 11 | saikyo | 3083.3 | 55348136 | 76 | 74-0-2 | 0.974 | 8294.4 | 2 | none observed in frozen inventory |
| 12 | Rayk Kretzschmar | 3082.1 | 55345266 | 78 | 71-0-7 | 0.910 | 7017.3 | 2 | Code exact 2 |
| 13 | kakuteki | 3078.8 | 55334137 | 108 | 78-0-30 | 0.722 | 2270.5 | 2 | none observed in frozen inventory |
| 14 | Howon Kang | 3074.9 | 55350305 | 70 | 64-0-6 | 0.914 | 8435.8 | 2 | none observed in frozen inventory |
| 15 | Kenjo1209 | 3047.7 | 55350869 | 72 | 64-0-8 | 0.889 | 8737.1 | 2 | none observed in frozen inventory |
| 16 | MD Concepcion | 3045.2 | 55346092 | 82 | 69-0-13 | 0.841 | 5732.6 | 2 | none observed in frozen inventory |
| 17 | 风沙星辰 | 3040.0 | 55347083 | 100 | 61-27-12 | 0.610 | 5917.7 | 2 | none observed in frozen inventory |
| 18 | kglctf | 3039.6 | 55350603 | 84 | 61-16-7 | 0.726 | 7140.6 | 2 | none observed in frozen inventory |
| 19 | tomo11111 | 3034.2 | 55347742 | 89 | 64-17-8 | 0.719 | 6707.4 | 2 | none observed in frozen inventory |
| 20 | Ibad Ur Rahman | 3032.2 | 55346155 | 88 | 66-16-6 | 0.750 | 7722.8 | 2 | none observed in frozen inventory |
| 21 | Marcus | 3029.1 | 55339397 | 103 | 78-0-25 | 0.757 | 5130.4 | 2 | none observed in frozen inventory |
| 22 | Matthew Labrador | 3028.2 | 55350882 | 70 | 68-0-2 | 0.971 | 8433.2 | 2 | none observed in frozen inventory |
| 23 | Shivam_2212 | 3019.4 | 55345819 | 93 | 62-16-15 | 0.667 | 6709.0 | 2 | none observed in frozen inventory |
| 24 | lingyu07 | 3013.6 | 55347101 | 99 | 65-21-13 | 0.657 | 6541.6 | 2 | none observed in frozen inventory |
| 25 | Auxileon | 3013.0 | 55340360 | 94 | 72-0-22 | 0.766 | 6094.5 | 2 | none observed in frozen inventory |

Public exact-name join은 이름 동일성만 확인했다. Rayk Kretzschmar는 두 Code가 exact match다: `kaggriculture-findings-from-zero-to-top-meta` v15 (source `CBE0CABA...`, license 미확인)와 `kaggriculture-rank-your-agent` v10 (source `C9D5EB18...`, Apache-2.0). Lester Leong↔fle3n은 추정일 뿐 identity-proven이 아니다. Discussion/Models는 exact-name match가 관측되지 않았지만 inventory 한계 때문에 ‘없음’으로 단정하지 않는다.

## 리플레이 패턴

아래 SELL 값은 **요청된 market order 빈도**다. 체결량으로 해석하면 안 된다. 또한 두 cohort의 상대 강도가 달라 absolute cash를 strength로 비교하면 안 된다.

| Metric (median) | Top25 50 obs | 우리 44 obs | bot_05 6 obs | bot_07 2 obs |
|---|---:|---:|---:|---:|
| Peak hands | 14.0 | 11.5 | 12.0 | 12.0 |
| Hire order turns | 263.0 | 298.0 | 298.0 | 306.0 |
| First land step | 59.0 | 84.0 | 84.5 | 84.5 |
| Third quadrant step | 79.5 | 108.5 | 130.5 | 130.5 |
| Peak crops total | 94.0 | 42.5 | 62.0 | 82.5 |
| Strawberry | 42.0 | 25.5 | 40.0 | 40.0 |
| Wheat | 40.0 | 8.0 | 11.0 | 31.5 |
| Peak animals | 14.0 | 14.0 | 14.0 | 14.0 |
| Requested SELL turns | 181.0 | 121.5 | 389.0 | 377.0 |
| Unit non-PASS rate | 0.848 | 0.739 | 0.946 | 0.946 |
| Max shed units | 96.0 | 99.0 | 94.0 | 100.0 |
| Final shed units | 0.0 | 0.0 | 2.0 | 2.0 |
| Day27+ SELL turns | 37.0 | 33.5 | 51.0 | 64.0 |

패턴 해석:

- 공유 top tape 중앙값은 14 hands, 94 crops(42 strawberry/12 melon/40 wheat), 14 animals(8 cow/6 sheep), shed peak 96, terminal shed/carried 0이다.
- 19-team dominant farm-action hash는 `FC37F8688680DA949DB44C9444DCB9541488B4E10D9F432CC42648D6423F1B26`; ranks 4,6,8-20,22-25에서 38/38 관측이 일치했다.
- 상위 25 중 23개 팀은 서로 다른 seed·반대 seat 두 게임에서 farm action hash가 동일했다. 이들 대부분의 full-action 차이는 market 7~27 steps뿐이다. MD Concepcion은 market 포함 720-step action 전체가 두 게임에서 동일했다.
- rank1 Seb와 rank3 HealthStone만 farm actions가 각각 579/573 steps 달랐다. 즉 최상단에는 공개 공통 테이프를 그대로 쓰지 않는 실제 적응 계열도 존재한다.
- 공개 lineage 음성 검색은 high-score kernel output 18 refs/89 files(AST 18/18, literal tapes 20)에서 FC37 exact match 0, current source API 성공 61/155(94건 429, literal tapes 15)에서 match 0이었다. 초기 PRVSIYAN Frontier V12 세 alignment도 불일치했다. 이는 부재 증명이 아니며 compressed/generated tape를 놓칠 수 있어 FC37은 여전히 UNMAPPED다.
- 우리 replay 표본의 final cash 중앙값이 top보다 높지만 상대 풀과 selection이 다르다. 우리 44표본의 target win 42/44 역시 ‘각 제출에서 고른 두 게임’ 편향이라 rating/strength 추론에 쓰지 않는다.

## 확인된 평가 결함과 영향

| 결함 | 원본 증거 | 영향 |
|---|---|---|
| Legacy runner DONE 덮어쓰기 | runner `B0341417...`는 final state만 읽음; official env `B6DA1554...`는 마지막에 모든 status를 DONE으로 설정 | 과거 `failures=0`은 ERROR/TIMEOUT/INVALID 부재 증명이 아님 |
| 재현 기록 | `docs/BOT_DESIGN_SPEC.md` `93FF99DA...` lines 427-431: step300 RuntimeError→418 ERROR steps→final DONE/DONE→valid4/failed0 | 크래시가 정상 저현금 패배처럼 집계 가능 |
| donor/self-lineage 오염 | 같은 문서: bot_07 40게임 중 24게임(60%)이 donor/조상 계열; bot_11/12도 같은 의심 | 40-0, 0.656, 0.625 로컬 수치를 승격 근거로 재사용 금지 |
| half-layer seam 검사 | farmer만 같았으나 hands step6부터 104곳, market step0부터 292곳 차이 | ‘깨끗한 graft’ 주장 철회, full action layer 비교 필요 |
| absolute cash cohort 비교 | 우리 표본은 약한 상대/선택 편향, top 표본은 동형 top-vs-top 다수 | cash·표본 win은 cross-cohort strength 지표가 아님 |
| historical byte ambiguity | API는 과거 upload archive bytes를 제공하지 않음; 같은 이름 재사용 | 현재 local archive와 submitted policy의 byte identity는 UNVERIFIED |

다만 저장된 우리 public replay 44개는 63,272 ACTIVE + terminal DONE 88, terminal pair 44/44 DONE/DONE였다. 이것은 그 44개 public game에서 비정상 status가 관측되지 않았다는 좁은 증거일 뿐, 1017 metadata 전체나 과거 로컬 grid를 복구하지 않는다. 세부 계약은 `runner_done_overwrite_defect.json`에 고정했다.

## 3000 목표에 바로 연결되는 후보 가설

1. **Kag_01 — FC37 farm reconstruction + frozen-safe market baseline.** 19팀/38관측 공통 farm tape를 공개 replay에서 byte-provenance와 함께 재구성한다. 먼저 action parity 720/720을 여러 seed/seat에서 확인하고, market은 관측된 중앙 schedule을 고정한다. 이 후보는 ‘혁신’이 아니라 3000 meta의 재현 가능한 강한 control이다.
2. **Kag_02 — adaptive farm switch.** Seb/HealthStone 두 좌석 replay에서 공통 tape와 갈라지는 최초 상태·행동을 추출하고, 관측 가능한 state에만 의존하는 한 개 switch를 붙인다. identity/episode/seed lookup은 금지한다. FC37 control 대비 외부 top opponents에서 개선이 없으면 버린다.
3. **시장 overlay는 후순위·제한 delta.** 공유 cluster의 농장 hash는 같고 market만 7~27 steps 변한다. 농장 parity를 먼저 고정한 뒤 SELL quantity/timing 한 종류만 실험한다. bot_11/12처럼 SELL 요청 수만 늘리는 방향은 실전 하락 이력이 있다.
4. **평가 gate.** donor/자기조상 제외, top25에서 최소 FC37 cluster·rank1 adaptive·rank3 adaptive 포함, 동일 seed/seat/scenario paired grid, seed-cluster bootstrap, every-opponent floor, stepwise status scan, raw+receipt+source hash를 요구한다. fresh sealed seed는 selection 완료 전 열지 않는다.

## 미확인/과장 금지 범위

- 상위 25의 private source와 exact uploaded archive는 확인 불가다.
- 4,166개 top metadata row 중 raw는 45 unique episodes만 저장했다. 나머지를 분석했다고 쓰지 않는다.
- 우리 1,017 metadata row 중 raw는 44 episodes만 저장했다. status scan의 범위도 44개다.
- FC37 cluster의 exact public Code lineage는 UNMAPPED다. 초기 Frontier V12와는 불일치만 확인했다.
- Ray 외 top25 Code author exact-name match는 동결된 155 current refs에서 관측되지 않았다. ‘공개 코드가 없다’는 뜻이 아니다.
- Discussion은 57 IDs 중 exact-name match가 없었으나 일부 author가 미확인이다. Models도 1 record만 확보했으므로 전수 zero-population 주장이 아니다.
- replay market SELL은 요청(action)이지 실제 체결량이 아니다.
- 3000/top3는 목표이지 이 조사만으로 보장되지 않는다.

## 핵심 machine-readable 산출물

- `leaderboard_top25_provenance.json`: 25행 rank/team/score/highest-score submission 전체 성적/양 좌석 replay/code join.
- `our_submission_provenance.json`: 22건 score/episode/W-D-L/local archive·main 후보/업로드 byte 미확인 표시.
- `submission_policy_source_map.json`: 22건별 policy family, 역사 문서/ledger 근거, local archive/main 후보, historical upload byte 미확인 표시.
- `replay_inventory.jsonl`: 89 raw의 campaign-worktree-relative POSIX path, URL, episode, seed, SHA, bytes, selection provenance.
- `replays_raw/*.json`: 약 2.38 GB라 Git에는 넣지 않고 local ignored evidence로 유지한다. 재수집 URL/명령과 exact hash chain은 inventory/integrity/manifest에 남겼다.
- `replay_feature_report.json`: 89 replay의 Python-native dict/list features; `System.Object[]` 표시는 PowerShell display/재직렬화 문제였고 원 JSON schema 문제가 아니다.
- `comparative_metrics.json`: 94 target observations, cohort/policy summaries, full episode metadata performance, action fingerprints.
- `leaderboard_public_join.json`: Code/Discussion/Model exact-name join과 absence scope.
- `local_source_map.json`: Desktop dirty worktree read-only source/archive index 135개와 22 submission filename candidates.
- `replay_integrity_report.json`: 89/89 raw SHA·bytes·schema/status check.
- `runner_done_overwrite_defect.json`: legacy runner 결함과 영향 경계.
- `evidence_manifest.json`: 모든 비-raw 산출물 hash와 89 raw inventory/hash chain.
