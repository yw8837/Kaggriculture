# 종료된 알고리즘 봇 대회 사례와 Kaggriculture 전이 분석

## 범위와 증거 등급

- 조사 창: 2026-08-08 17:40Z–18:01Z.
- 모집단은 웹 전체가 아니라 다음 쿼리군으로 한정했다: Halite II–IV, Lux AI S1/S2, Kore 2022, Hungry Geese, Google AI Challenge/Ants, Fighting Game AI, GVGAI, simultaneous-move MCTS.
- 우승/상위 솔루션의 작성자 저장소·공식 writeup·공식 대회 저장소·동료심사 논문만 메커니즘 근거로 썼다. 검색 스니펫만 있는 자료는 근거로 쓰지 않았다.
- Q010에서 Kore 1위 페이지는 Insane Search로 HTTP 200이었지만 본문 추출이 실패했다. Q028의 Jina 재시도에서 7,514-byte 본문을 회수해 그때부터만 VERIFIED로 승격했다.
- 라이선스 미표시 저장소는 아이디어를 요약했을 뿐 코드를 복사할 권한으로 해석하지 않았다.
- 따라서 이 문서는 쿼리 manifest 내 조사 완료본이지 인터넷 전체의 전수조사라는 주장은 아니다.

## 사례별 메커니즘

| 사례 | 원본 | 핵심 메커니즘 | Kaggriculture에 적용 | 적용하지 않을 것 | 최소 delta와 반증 |
|---|---|---|---|---|---|
| Halite III 1위 | C01 | 각 함선에서 모든 셀로 Dijkstra, 채굴량/턴 효율, 충돌 위험, spawn/dropoff ROI, 이전 버전·공격형·수비형 회귀 상대 | 노동자 경로비용과 기회비용을 분리하고 상대 위험을 시나리오로 스트레스 | 무허가 코드 복사, Halite 전용 수식 이식 | 하나의 opportunity-cost 항만 추가. fresh both-seat에서 per-opponent money와 match가 함께 개선되지 않으면 폐기 |
| Halite III 4위 | C02 | 첫 Hungarian으로 목표를 공동 배정하고 두 번째 Hungarian으로 즉시 이동 충돌 제거; 시간초과 시 문제 축소·캐시 | Kag_01의 직접 근거. 순차 allocator의 자원 선점/중복 목표를 작은 직사각 assignment로 교정 | 기존 B1/B2처럼 모든 task를 지수 DP로 풀기 | rare-contention top-k만 O(n^3) 배정. 높은 priority 작업 stranding 0, 보호 lane exact, p95 gate 실패 시 NO-GO |
| Halite IV 4위 | C03 | 역할·지배도·안전도·linear assignment. 진화적 parameter tuning은 대칭/overfit 때문에 폐기 | 관측 상태로만 opponent archetype과 역할을 정의하고 lineage-held-out 검증 | 상대 rank/identity 분기, 노출 seed에서 parameter sweep | 하나의 고정 trigger만 preregister. archetype 안정성 또는 held-out 이득이 없으면 폐기 |
| Lux AI S1 1위 | C04 | phase feature, IMPALA self-play, frozen teacher KL, 초기 shaping 후 sparse reward, action mask | phase-aware feature와 action legality 검증, frozen control 회귀, replay state adversarial test | 현 시점의 full RL replacement | 생산 delta 대신 test generator. replay-derived state가 공식 simulator에서 재현되지 않으면 사용 금지 |
| Lux Open | C05/C06 | massive-agent policy/action factorization | 장기적으로 worker/action representation 참고 | 현 제출 주기의 대규모 RL 학습 | 현재 후보 없음 |
| Hungry Geese 5위 | C07/C12 | AlphaZero self-play, simultaneous DUCT, collision penalty, dead-end filter, 40–60회 Numba search | 동시행동 때문에 일반 sequential MCTS가 위험하다는 경고; offline counterfactual search | 곧바로 online MCTS 탑재 | 한 replay/state offline evaluator만. runtime·simulator parity 실패 시 폐기 |
| Kore 2022 1위 | C10 | replay 시각화로 이슈를 찾고 작은 수정 반복; 시간축 damage ledger, 거의 모든 route 평가, 확장/채굴/공격 phase, 캐시 최적화, 146개 버전 | replay를 가설 생성에 쓰되 fresh seed는 검증에 보존. 1–2일 resource ledger와 상대 반응 시나리오 | 수십 parameter를 노출 결과로 조정하거나 1개 lineage에만 최적화 | replay 실패 1개→issue card 1개→delta 1개. 원 source lineage 밖에서 이득 없으면 폐기 |
| Kore 2022 5위 | C08 | 미래 incoming force difference, coordinated guaranteed attacks, expansion timing, route ROI와 danger. 잘못된 수정 사례도 공개 | Kag_02의 보수적 horizon ledger/feasibility 근거 | Kore 경로·capture 코드를 그대로 변환 | fixed shock set에서 first action only. worst-case cash/p10 및 모든 opponent가 gate를 못 넘으면 폐기 |
| Kore 2022 4위 | C09 | proactive rescue, future placeholders, opponent launch prediction, joint defense | 상대 반응을 낙관적 한 점이 아니라 작은 scenario set으로 둠 | identity 기반 opponent oracle | observable response scenario 하나만 추가. 가정이 틀린 lane에서 손실이면 폐기 |
| Google AI Challenge archive | C13 | 반복 가능한 match infrastructure와 공개 bot 생태계 | opponent pool 다양성/양 seat/회귀 champion 원칙 | README만으로 winner mechanism을 추론 | 방법론만 사용 |
| Fighting Game AI / GVGAI | P13/P14 | rolling horizon action sequence, opponent model, game별 hyperparameter 민감도 | offline macro-action teacher 가능성 | 현 단계 production online RHEA; tuning 공간이 너무 크고 선택편향 위험 | production pair 이후 별도 연구. untouched game/state set 없으면 시작하지 않음 |

## 공통 패턴

1. 상위 rule bot은 거대한 한 번의 최적화보다 replay에서 구체적인 패배 원인을 찾아 작은 수정과 회귀 상대 풀로 닫았다.
2. joint assignment는 반복해서 등장하지만, 성공 사례는 polynomial solver·문제 축소·캐시·fallback을 같이 썼다. 우리 기존 B1/B2의 bitmask DP는 이 조건을 어겨 runtime과 direct margin에서 실패했다.
3. horizon planning은 미래를 정확히 맞히는 oracle이 아니라 기회비용, 위험, 확정 가능한 행동, 첫 행동만 실행하는 receding-horizon 구조로 쓰였다.
4. 상대 모델은 상대 이름/순위가 아니라 observable behavior나 fixed scenario로 제한해야 일반화와 규칙 준수가 가능하다.
5. 전체 RL/MCTS는 강력하지만 compute, 디버깅, simultaneous-action modelling, package/runtime 위험이 크다. 지금은 replay state 생성과 offline falsification에만 쓰는 게 합리적이다.
6. parameter search는 특히 초반 공개 LB와 반복 seed에서 overfit하기 쉽다. 후보 하나·fresh pool·사전 gate가 필수다.

## 현재 프로젝트의 음성 대조군

로컬 원본 L01–L03을 직접 대조했다.

- A1 exact self market: direct 13–19, margin -1,197.59, NO-GO.
- A2 adaptive herd: direct 11–21, margin -2,957.41, NO-GO.
- A4 combined: direct 3–29, margin -4,671.31, NO-GO.
- B1 global DP: direct 17–15지만 margin -70.88, p95 157.47 ms, NO-GO.
- B2 deadline DP: direct 18–14지만 margin -169.81, p95 111.81 ms, NO-GO.
- B4: max 254.44 ms로 matrix를 열기 전에 runtime NO-GO.

따라서 외부 아이디어를 적용한다는 이유로 이 실패 메커니즘을 이름만 바꿔 반복하면 안 된다. Kag_01은 지수 DP가 아닌 좁은 O(n^3) contention repair, Kag_02는 단일 self-price/herd 교체가 아닌 preregistered uncertainty-set receding horizon이어야 한다.

## 검색 수익 체감 2차 패스

2차 패스에서 DUCT 이론, RHEA, OR-Tools min-cost-flow를 추가했다. 하지만 즉시 production 가치가 높은 새 세 번째 축은 나오지 않았다. 오히려 다음을 강화했다.

- online MCTS/RHEA는 simultaneous-action·branching·parameter tuning 비용 때문에 보류.
- polynomial assignment와 short-horizon robust MPC 두 축을 먼저 각각 단일 delta로 평가.
- bandit/ensemble은 제출 agent가 경기 간 상태를 유지하지 못하므로 agent 내부 학습이 아니라 local experiment budget 관리에만 사용.

이 판단은 “더 찾을 자료가 없다”는 뜻이 아니다. 현재 Kag_01/Kag_02 설계 결정을 바꿀 정도의 추가 1차 원본이 2차 패스에서 나오지 않았다는 뜻이다.
