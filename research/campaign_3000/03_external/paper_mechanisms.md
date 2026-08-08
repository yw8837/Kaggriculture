# Planning·assignment·robustness 문헌을 Kaggriculture로 옮기는 법

## 1. Task allocation과 rectangular assignment

근거: P04 MRTA taxonomy, P10 rectangular assignment, T03 SciPy 공식 문서, T02 OR-Tools 공식 min-cost-flow 문서, C02 Halite 3 4위.

### 전이 가능한 부분

현재 시점의 feasible worker-task edge만 만들고, 각 edge에 다음의 사전등록된 사전식 우선순위를 둔다.

1. formal priority 위반 여부
2. 같은 priority 안에서 오늘 완료/실패 방지 여부
3. shared-resource feasible 여부
4. 경로+pickup+action 예상 turn
5. 기존 deterministic tie key

worker가 task보다 많거나 적으면 rectangular matrix와 PASS dummy를 쓴다. SciPy 공식 문서는 rectangular input과 maximize를 지원하고 modified Jonker-Volgenant를 사용한다고 명시한다. 생산 agent에서 SciPy가 보장되지 않으므로 이 문서는 의존성 승인 근거가 아니라 작은 deterministic O(n^3) 구현의 명세 근거다.

### 기존 실패와의 차이

기존 L03은 최대 18 task × 11 unit을 bitmask DP로 모두 배정했다. L01의 B1/B2는 p95 111–157 ms였고 direct mean margin도 음수였다. 따라서 “global assignment”라는 이름만 같은 후보는 금지한다.

Kag_01은 다음에만 발동해야 한다.

- 같은 formal priority의 feasible task가 2개 이상이고
- 단일 worker/resource를 서로 경쟁하며
- formal 순차 선택이 더 높은 priority task 수를 줄이지 않는다는 bounded safety check를 통과하고
- matrix size가 사전 cap 이하일 때.

### 반증 계측

- contention_trigger_turns
- assignment_action_changed_turns
- formal_priority_completed_delta
- stranded_higher_priority_tasks
- duplicate_target_or_resource_conflicts
- assignment_objective_delta
- fallback_count
- p50/p95/p99/max

실제 action change가 0이면 메커니즘 검증 실패다. win만 높고 higher-priority stranding 또는 resource conflict가 1개라도 나오면 안전 가설이 틀린 것이다.

## 2. Receding-horizon MPC

근거: P01 constrained MPC, C08/C09/C10 Kore, C01 Halite.

원리는 단순하다. 현재 상태 x에서 H-step action plan a(0:H-1)을 제한조건 아래 평가하고, 최적 plan의 첫 행동 a0만 실행한 뒤 다음 observation에서 다시 푼다.

Kag_02의 안전한 최소형은 H=1–2 day, 시장·창고·농장 자원에 한정한다. 후보 plan 수도 고정 cap으로 둔다. full farm simulator를 매번 깊게 복제하는 대신 공식 transition과 동일한 projection helper를 쓰고, 검증할 수 없는 상태에서는 exact control로 fallback한다.

### 기존 실패와의 차이

L02의 A1은 자기 주문 가격·수익과 일부 terminal order arithmetic을 바꿨고, A2는 herd target을 바꿨으며, A4는 둘을 합쳤다. 모두 NO-GO였다. Kag_02가 새 가설이 되려면 다음이 필요하다.

- 고정된 horizon과 후보 plan set
- execute-first-action-only
- uncertainty/scenario set을 실행 전 freeze
- control과 다른 행동이 발생한 정확한 trigger
- 최악/하위 분위수 손실을 목적에 포함

단순 가격 계산 수정이나 herd mix 변경이면 A1/A2/A4 재탕으로 판정한다.

## 3. Robust optimization / robust DP

근거: P06 Bertsimas–Sim, P07 Iyengar.

연속 최적화의 보장을 그대로 가져오지는 않는다. 대신 작은 finite scenario set을 사전에 고정한다.

- nominal price/inventory
- adverse price impact or low inventory
- delayed/opponent-aggressive response
- terminal resource pressure

계획 p의 점수 예시는 다음처럼 제한한다.

robust_score(p) = mean_s value(p,s) - lambda * max_s regret(p,s)

lambda와 scenario는 fresh seed를 열기 전에 고정한다. worst-case만 최대화해 nominal play를 망치는 후보도 막아야 하므로 nominal direct gate와 every-opponent noninferiority를 별도 둔다.

### 반증 계측

- predicted_vs_realized cash/resource error
- nominal money delta
- worst-scenario money delta
- paired p10 delta
- every-opponent mean money delta
- impossible order/overflow/discard
- fallback and runtime

## 4. Simultaneous-move MCTS / DUCT

근거: C07, P02, P15, P16.

Tron 사례에서 DUCT UCB1-Tuned가 해당 실험의 최고 성능을 냈고, NeurIPS 논문은 Hannan-consistent selection의 수렴 조건을 다룬다. 이는 “MCTS를 쓰면 강하다”는 증거가 아니라 sequential UCT로 상대 행동을 순서화하면 artifact가 생길 수 있다는 경고다.

Kaggriculture는 두 player 행동이 함께 처리되므로 online search를 만들 경우 joint action 또는 simultaneous selection을 모델링해야 한다. 현재는 다음 이유로 production 후보에서 제외한다.

- worker별 action 조합의 branching factor
- opponent policy uncertainty
- simulator copy cost
- single-file runtime gate
- rollout value function 선택편향

허용 가능한 첫 단계는 replay state 한 개에서 작은 macro-action set을 offline으로 비교하고 공식 simulator parity를 확인하는 diagnostic이다.

## 5. POMCP와 opponent modelling

근거: P03, P11, P14, C03/C09.

POMCP는 black-box simulator와 particle belief로 큰 POMDP를 계획한다. specialized experts와 opponent-model RHEA는 상황별 policy 선택을 뒷받침한다. 그러나 Kaggriculture production agent는 경기 간 학습 상태를 보존할 수 없고, 상대 identity/path를 사용하면 일반화·규칙·provenance가 깨진다.

따라서 opponent model은 다음 observable feature에만 제한한다.

- early herd/crop/build counts
- observed market order type and quantity
- expansion timing
- resource pressure and worker count

이것으로 고정된 archetype을 선택하더라도 lineage-held-out opponent gate가 필요하다. 현재는 Kag_01/Kag_02 이후 backlog다.

## 6. Bandit와 expert ensemble

근거: P08 UCB, P09 EXP3, P11 specialized experts.

적용 가능: 로컬에서 어떤 preregistered 가설에 계산 budget을 줄지 정하는 scheduler.

적용 불가: 제출 agent가 과거 경기 결과를 기억한다고 가정하는 online bandit, 경기 중 무작위 expert switching, sealed 결과를 보고 allocation rule을 바꾸는 것.

Bandit scheduler를 쓰더라도 promotion CI를 적응적으로 소비하면 선택편향이 생긴다. 후보별 fresh pool과 최종 confirmation은 bandit 밖에 둬야 한다.

## 7. Rolling Horizon Evolution / AlphaZero / full RL

근거: P12–P14, C04–C07.

강점은 긴 action sequence와 self-play distribution을 직접 최적화하는 것이다. 하지만 Lux와 RHEA 원본 모두 game-specific parameter, compute, training stability, state exploration의 중요성을 보여준다. 현재 대회에서 바로 production으로 쓰면 검증보다 tuning loop가 커진다.

즉시 적용은 다음 두 가지로 제한한다.

- 상위 replay의 중간 state를 공식 simulator regression corpus로 사용
- deterministic candidate의 실패 state를 찾는 offline teacher/search

policy network나 evolutionary plan을 바로 제출 agent로 쓰지는 않는다.

## 적용 우선순위

| 우선순위 | 방법 | 판단 | 이유 |
|---:|---|---|---|
| 1 | bounded rectangular assignment | Kag_01 후보 | winner 사례가 반복되고 기존 exponential DP의 runtime 결함을 직접 피할 수 있음 |
| 2 | short-horizon robust MPC | Kag_02 후보 | 경제/자원 게임에 직접 맞고 기존 A1/A2 실패와 구분 가능한 uncertainty-set delta가 있음 |
| 3 | observable opponent archetype gate | backlog diagnostic | 충분한 replay cluster와 lineage-held-out gate가 먼저 필요 |
| 4 | offline simultaneous MCTS/RHEA | research only | simulator parity와 runtime을 먼저 증명해야 함 |
| 5 | full RL/self-play | defer | 현재 cadence·compute·provenance에 부적합 |

어떤 문헌도 3000점, 메달, top-3를 보장하지 않는다. 문헌은 가설 생성 근거이고 strength claim은 공식 simulator의 fresh, both-seat, diverse-opponent, scenario-balanced evidence로만 결정한다.
