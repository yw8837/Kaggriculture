# Kaggriculture 관련 대회·계획/게임 알고리즘 조사

- 조사일: 2026-07-31 (Asia/Seoul)
- 범위: 종료된 봇/게임·조합최적화 대회의 1차 후기와 구현, finite-horizon planning, MPC, DP, MCTS, market impact, task allocation, opponent modelling, robust optimization의 원 논문·공식 페이지
- 산출물 성격: 구현 전 메커니즘 백로그. 아래의 “Kaggriculture 기대효과”는 **가설**이지 실측 결과가 아니다.
- 외부 행동: 검색·읽기만 수행. Kaggle 제출/게시, Git commit/push, tracked/production 파일 수정은 하지 않았다.
- 로컬 사실 기준: Kaggle 공식 환경 commit `4f6e2763e2232605aacbade443715a9e2c9ef401`. 720턴, 종료 시 은행 현금만 보상, 미판매 재고는 무가치, 두 플레이어의 market order가 단위별로 동시 처리되고 판매가 shared inventory를 움직인다.

## 결론: 먼저 실험할 메커니즘

| 우선순위 | 메커니즘 | 이 프로젝트에서의 형태 | 핵심 반증 기준 |
|---|---|---|---|
| P0 | 종료가치가 있는 shrinking/receding-horizon 경제 계획 | 남은 턴을 상태에 넣고 crop/animal/build/land/hire/sell의 현금흐름을 계획하되 매턴 재계획. 미판매 재고 terminal value=0 | 같은 held-out seed/opponent에서 단순 ROI 정책보다 paired cash delta와 하위 10%가 개선되지 않거나 timeout 증가 시 기각 |
| P0 | 시장충격-aware 판매 스케줄 | market inventory, town 수요 tick, 상대 추정 공급, $1 floor를 포함해 즉시 일괄·분할·수요 직후 판매를 비교 | exact market simulator에서 predicted revenue 오차가 크거나, held-out에서 gross production 증가가 net cash로 전환되지 않으면 기각 |
| P0 | 글로벌 task allocation + 재배정 | 각 worker-task bid를 `한계 현금가치 - 이동/기회/실패 비용`으로 만들고 assignment 후 매턴/이벤트 시 재배정 | nearest/role-greedy 대비 idle, missed care/water, late harvest는 줄지만 최종 현금이 개선되지 않으면 기각 |
| P1 | 역할로 분기폭을 줄인 deterministic lookahead | planner가 모든 원자행동을 탐색하지 않고 grower/carer/hauler/market 역할 후보를 만들고 짧은 simulation으로 선택 | 역할 고정으로 shock 대응과 endgame liquidation이 악화되거나 horizon 증가가 불안정하면 기각 |
| P1 | 안전장치가 있는 opponent conditioning | public farm/market 행동으로 opponent archetype posterior를 갱신하되, 신뢰가 낮으면 robust 기본정책 사용 | unseen/spoof opponent에서 기본정책 대비 worst-case가 악화되면 상대 적응을 비활성화 |
| P1 | budgeted robust/scenario planning | shop unlock, weed, 상대 판매량/타이밍을 극단 하나가 아니라 제한된 uncertainty budget과 scenario로 평가 | 평균 손실이 robust 이득보다 크거나 실제 holdout coverage가 설정한 violation budget보다 낮으면 기각 |
| P2 | simultaneous-move MCTS | 시장/고수준 macro action만 Decoupled UCT/Regret Matching으로 탐색. 저수준 이동 전체에는 쓰지 않음 | 동일 CPU budget의 beam/rollout보다 lower confidence bound가 낮거나 shallow trap을 놓치면 기각 |

가장 강한 교차대회 패턴은 “완전한 전역 최적화”가 아니라 **정확한 simulator + 짧은 계획 + 매턴 재계획 + 역할/우선순위로 action space 축소 + 손실 replay 분석**이었다. Halite III 우승 구현과 Lux S2 우승 구현은 각각 원리 기반 ROI/assignment와 50-step future simulation을 사용했고, CodinGame 우승 후기들도 같은 구조를 반복한다. 반면 imitation/RL은 state를 잘못 생략하거나 validation loss를 실제 승률로 오인하면 멈춤·교착을 만들었다.

## 소스별 기록

### S0. Kaggle 공식 Kaggriculture 환경

- URL: https://github.com/Kaggle/kaggle-environments/tree/4f6e2763e2232605aacbade443715a9e2c9ef401/kaggle_environments/envs/kaggriculture
- 날짜/authority: pinned commit `4f6e276...`; 접근 2026-07-31; **공식 구현/규칙(A)**.
- 메커니즘: 720-turn finite horizon, 현금 terminal reward, 미판매 재고 0, market order 단위별 동시 처리, shared inventory 기반 비선형 price impact, town의 외생 수요, premium product의 빠른 $1 floor.
- 효과/증거: 이 항목은 관련 방법의 효과 증거가 아니라 모델 경계다. 특히 재고 장부가치를 terminal cash로 잘못 넣거나 상대 주문을 순차로 가정하면 planner가 다른 게임을 푼다.
- 실패모드: README prose만 믿고 processing order/rounding/floor를 근사; day boundary와 market refresh 시점을 한 턴 틀림.
- 반증 실험: 공식 `market`/`interpreter` tests를 oracle로 삼아 buy/sell interleaving, floor, town tick, day boundary의 작은 상태 전이를 table test로 대조.

### S1. Halite III 우승 bot — teccles

- URL: https://github.com/teccles-halite/halite3-bot/tree/8f7a549c973bc5e2ee8c56d140e131b608278701
- 날짜/authority: repo 2019-01-23, 기록 commit 2019-01-26; 접근 2026-07-31; **대회 우승자 공개 구현·후기(A-/primary implementation)**.
- 메커니즘: 각 ship이 Dijkstra travel/burn cost와 최적 mining duration을 계산해 “채우고 귀환하는 총 시간”을 score화; target을 전역 claim하고 가까운 ship에 우선권; spawn/dropoff도 payback과 ship-turn value로 평가; 충돌가치를 자원·ship 가치·지역 control로 계산; 2p에서는 opponent의 충돌 성향을 관찰해 위험 회피.
- 효과/증거: 작성자가 우승 bot이라고 명시한다. README는 다음 target까지 계획한 확장이 도움이 되지 않았고, 원리 기반 1-target model이 turn-to-turn consistency를 준다고 보고한다. Kaggriculture 기대효과는 worker-task bid와 build/hire payback을 같은 단위(남은 턴당 현금)로 통일하는 것.
- 실패모드: dropoff는 short-term patch가 누적돼 모델이 망가졌다고 회고; CLOP parameter tuning 결과도 혼재. 먼 미래를 추가하면 불확실한 예측 때문에 오히려 악화.
- 반증 실험: worker별 모든 후보 task의 marginal cash/turn matrix를 만들고 Hungarian/auction 배정 대 nearest-greedy를 paired 평가. horizon-2 successor task를 추가했을 때 개선이 재현되지 않으면 1-task bid 유지.

### S2. Lux AI Season 2 1위 — ry_andy_

- URL: https://github.com/ryandy/Lux-S2-public/tree/a3d874bb88ce404c797c65ddfcc21011659056e5
- 날짜/authority: repo 2023-12-08, commit 2023-12-09; 접근 2026-07-31; **1위 공개 구현(A-)**.
- 메커니즘: production `FUTURE_LEN=50`의 main simulation loop에서 board state를 step별 전개하고 miner/protector/transporter/blockade/attacker 등 역할과 우선순위를 순서대로 실행한다. 초반 행동 fingerprint로 특정 opponent를 식별하는 코드도 있다. 매 invocation 시간 budget을 남은 overage time과 end phase에 맞춰 조절한다.
- 효과/증거: 646팀 중 1위라고 README가 명시. 긴 future length의 self-match는 최대 한 시간 걸릴 수 있고, README가 빠른 실행용 horizon=5 ablation을 직접 안내한다. Kaggriculture에는 future-state arrays, 역할별 action generation, per-turn time budgeting이 직접 대응한다.
- 실패모드: 긴 horizon의 비용이 매우 크고, explicit opponent fingerprint는 meta가 바뀌거나 spoof되면 취약. 역할 우선순위가 잘못되면 뒤 역할이 자원을 못 받는다.
- 반증 실험: 동일 seed에서 horizon `{1,3,6,12,24}`와 warm-start 유무를 비교해 cash/runtime Pareto를 작성. 역할 호출 순서를 무작위/ablation해 실제 causal gain인지 확인. unseen opponent에서 fingerprint switch를 강제 off한 baseline과 비교.

### S3. Lux AI Season 1 공개 RL solution — Toad Brigade

- URL: https://github.com/IsaiahPressman/Kaggle_Lux_AI_2021/tree/973a6c6c63211b6c7ab6fdf50e026e458d1f6e4e
- 날짜/authority: repo 2021-07-13, final public commit 2021-12-24; 접근 2026-07-31; **상위 참가자의 공개 코드·Kaggle 원문 후기(B+/primary competition report)**.
- 메커니즘: 한 CNN이 variable number의 모든 unit action을 공동 출력하고 illegal action masking·collision resolution을 적용. sparse terminal win reward의 self-play를 reward shaping으로 bootstrap한 뒤 teacher KL로 전략 cycling을 완화. explicit game phase feature로 초/중/후반 행동을 조건화.
- 효과/증거: 저자 보고로 rules agent를 RL agent가 한 달 내 이겼고, phase feature 뒤 시기별 행동이 크게 분화. teacher는 pure self-play의 instability/cycles를 줄였다고 설명한다. 이는 “남은 턴/일 phase를 state에 명시”와 “joint coordination”의 근거이지, Kaggriculture에서 RL이 최선이라는 증거는 아니다.
- 실패모드: 일부 패배에서 fuel budget 실패와 turn 200 이후 무기력; 저자는 diverse opponent league나 shaping 유지가 필요했을 수 있다고 적는다. sparse reward와 self-play non-stationarity가 크다.
- 반증 실험: 현재 정책/optimizer 입력에서 `day`, `hour`, `turns_remaining`, next town tick을 제거하는 ablation. learned policy를 시도한다면 fixed teacher/opponent league 유무를 held-out archetype에서 비교하고 “cash가 낮을수록 PASS 증가” 같은 collapse 지표를 기록.

### S4. CodinGame Fantastic Bits 공식 우승자 postmortems

- URL: https://www.codingame.com/blog/best-programmers-reveal-magic-code/
- 날짜/authority: 2016-12-16; 접근 2026-07-31; **CodinGame 공식 블로그에 실린 1~3위 당사자 후기(A-/primary reports)**.
- 메커니즘: full simulator → multi-turn action sequence → evaluation function → GA/Monte Carlo refinement. 우승자는 100ms에 약 50,000 simulated turns를 목표로 했고, 여러 참가자가 적어도 수 turn lookahead가 필요하다고 보고. 불필요 heuristic을 삭제해 변수 수와 convergence burden을 줄였다.
- 효과/증거: 이 구조를 쓴 참가자들이 1~3위였다는 대회 결과와 당사자 보고. 그러나 새로 추가한 코드가 대회 후반 모두 실패한 참가자도 있어 “더 복잡함=더 강함”의 반례도 함께 제공한다.
- 실패모드: approximate simulator의 의도적 오차, evaluation shaping이 실제 목표를 역전(과도한 방어), opponent prediction이 전혀 개선하지 못한 사례, parameter magic/overfitting.
- 반증 실험: 각 heuristic은 단독 ablation과 sign test를 통과해야 한다. planner가 선택한 action의 exact official next-state와 approximate simulator state diff를 매 turn 기록하고 허용오차를 넘으면 search 사용 중단.

### S5. Google AI Challenge Tron 우승 postmortem — a1k0n

- URL: https://www.a1k0n.net/2010/03/04/google-ai-postmortem.html
- 날짜/authority: 2010-03-04; 접근 2026-07-31; **우승자 원문 후기(A-/primary report)**.
- 메커니즘: minimax + alpha-beta + Voronoi territory evaluation, iterative deepening, 분리된 endgame에서는 exhaustive prefix 뒤 greedy rollout. 11,691개의 top-100 replay에서 node/edge feature를 회귀해 evaluator weight를 보정.
- 효과/증거: 작성자가 대회 우승을 명시. endgame iterative deepening은 공식 소형 map에서 잘 작동했지만 큰 random map에서는 형편없었다고 직접 보고한다. 데이터 기반 evaluator도 “조금 predictive”라고만 표현한다.
- 실패모드: time limit 중간 ply 결과를 쓰는 bug, map-size distribution shift, leaderboard ranking noise, replay regression의 약한 설명력.
- 반증 실험: search는 anytime 방식으로 마지막 **완료된** depth만 반환하게 하고 강제 timeout test. evaluator weight는 replay-fit과 별개로 held-out policy improvement가 있어야 채택. map/market regime별 stratified holdout 사용.

### S6. Google Hash Code 2020 Finals 참가자 solution discussion

- URL: https://codeforces.com/blog/entry/76548
- 날짜/authority: 2020 Finals 직후(게시물 표기 6 years ago; exact timestamp 페이지에 미노출), 접근 2026-07-31; **결선 참가자들의 1차 후기(C+)**.
- 메커니즘: arm mount를 random 배정하고 task를 profit/length로 ranking한 뒤 상위 20개만 exact travel time 계산, BFS와 cell release time으로 path conflict 처리. 다른 8위 참가자는 random alpha/initial order로 greedy solution을 수백 번 재시작.
- 효과/증거: 참가자 self-report로 simultaneous-moving greedy보다 단순 순차 greedy가 더 높은 score였고, coarse ranking→상위 후보 exact evaluation이 결선 solution에 사용됨. 공식 검증 논문은 아니며 1위 방법도 아니다.
- 실패모드: 4시간 구현 제약, bug와 visualization 부족, random restart luck, mount randomization이 가장 약한 부분이라는 자가평가, arm을 매 task 후 완전 retract하는 구조적 손실.
- 반증 실험: Kaggriculture task를 cheap upper-bound로 top-k pruning 후 exact route/economic evaluation. `k={5,10,20,all}`과 restart budget을 고정 CPU에서 비교하고 seed별 선택 variance가 크면 random restart 의존을 기각.

### S7. Halite III diamond-level imitation bot postmortem — StakerNotes

- URL: https://stakernotes.com/diamond-ranked-ml-for-halite3/
- 날짜/authority: Halite III 종료 후(페이지 visible exact date 없음, 2019-era), 접근 2026-07-31; **상위 참가자 원문 실패 분석(B-/primary report)**.
- 메커니즘: top-player replay imitation, map/player/version별 multitask learning, time-to-end와 global state feature. player/version distribution을 분리하고 모든 validation stream 개선을 promotion 조건으로 사용.
- 효과/증거: validation loss 0.4~0.8에서도 lower loss가 실제 bot performance로 이어지지 않았고, final bot은 때때로 dropoff 주변에서 전체 fleet가 멈췄다. 저자는 stateless assumption과 teacher의 hidden history dependence를 원인 후보로 지목한다.
- 실패모드: behavior cloning의 covariate shift, state omission, correlated frames, changing teacher versions, supervised metric/actual objective mismatch, rare timeout.
- 반증 실험: 학습은 후순위. 시도 시 one-step action accuracy뿐 아니라 closed-loop rollouts의 invalid/PASS cascade, task deadlock, final cash를 필수 metric으로 둔다. history feature 없는 모델 대 recurrent/handcrafted state 모델을 동일 replay split에서 비교.

### S8. Shrinking-horizon dynamic programming — Skaf, Boyd, Zeevi

- URL: https://stanford.edu/~boyd/papers/pdf/shdp.pdf
- 날짜/authority: received 2009-07-09, accepted 2009-12-01, published 2010; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: finite-horizon stochastic control에서 매 step 현재 상태와 conditional distribution을 갱신하고, 남은 horizon이 한 step씩 줄어드는 DP를 다시 푼다. CE-MPC가 future disturbance를 point estimate로 바꾸는 반면 SHDP는 동일 marginal의 product distribution을 사용한다.
- 효과/증거: revenue-management 두 변형에 적용. 논문은 이 방법을 exact augmented-state DP가 history explosion으로 비현실적일 때의 heuristic으로 제시한다. Kaggriculture에는 remaining-turn dependent value와 shop/opponent uncertainty 재계획 구조가 대응한다.
- 실패모드: disturbance correlation을 product marginals로 지워 미래 joint structure를 오판; state/action이 크면 매 step DP도 불가; heuristic이라 일반 optimality 보장은 없다.
- 반증 실험: exact-solvable 작은 farm/짧은 horizon에서 full DP oracle, CE-MPC, SHDP를 비교해 optimality gap을 측정. shop unlock/상대 sell의 serial correlation을 켠 scenario에서 gap이 커지면 belief state를 보강.

### S9. Economic MPC — Diehl, Amrit, Rawlings

- URL: https://doi.org/10.1109/TAC.2010.2101291 (author PDF: https://ftp.esat.kuleuven.be/pub/pub/SISTA/ida/reports/09-240.pdf)
- 날짜/authority: published online 2010-12-20, IEEE TAC 2011-03; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: tracking setpoint 대신 직접 economic stage cost를 horizon에 합산하고 constraints와 terminal equality를 포함한 optimization을 매 step 푼다. 제안 formulation의 optimal value에서 economic steady-state cost를 뺀 값이 Lyapunov 역할을 한다.
- 효과/증거: nonlinear reactor example과 nominal stability 이론. “경제 objective를 직접 feedback control에 넣되 feasibility/stability를 설계해야 한다”는 근거다. Kaggriculture에는 profit를 proxy target이 아니라 직접 objective로 쓰고 care/feed/cash constraints를 hard constraint로 두는 설계가 대응한다.
- 실패모드: 논문의 안정성 조건·steady-state/terminal equality는 finite season 게임에 그대로 성립하지 않는다. 짧은 horizon은 terminal value가 나쁘면 수확 직전 crop을 과소평가.
- 반증 실험: 동일 planner에서 terminal value `{0, liquidation-only, fitted continuation, exact short-tail}`와 horizon을 교차 ablation. feasibility violation 또는 late-game stranded inventory가 늘면 formulation 기각.

### S10. UCT — Kocsis & Szepesvári

- URL: https://sites.ualberta.ca/~szepesva/papers/ecml06.pdf
- 날짜/authority: ECML 2006; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: tree의 각 node에서 UCB1로 action sampling의 exploration/exploitation을 조절하는 Monte Carlo planning. finite-horizon/discounted MDP에서 consistency와 finite-sample error bound를 제시.
- 효과/증거: synthetic trees와 stochastic sailing에서 비교법보다 적은 sample로 같은 error에 도달했다고 보고. 큰 state space의 online planning 후보라는 증거지만, Kaggriculture joint action의 huge branching과 simultaneous opponent를 해결해주지는 않는다.
- 실패모드: rollout/evaluator bias, huge joint action, rare catastrophic branch, simulator cost. asymptotic consistency는 실제 짧은 per-turn budget의 성능 보장이 아니다.
- 반증 실험: 먼저 macro action 5~20개로 제한. 동일 simulator-call budget에서 flat rollout/beam/UCT를 비교하고 bootstrap lower bound와 timeout을 보고. 원자 worker action 전체에 UCT를 적용하지 않는다.

### S11. UCT shallow traps — Ramanujan, Sabharwal, Selman

- URL: https://ojs.aaai.org/index.php/ICAPS/article/view/13437
- 날짜/authority: 2010-05-05; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: adversarial search space의 early-loss/shallow-trap 빈도가 UCT 성공 여부를 좌우한다. Chess에는 Go보다 shallow traps가 훨씬 많고 UCT가 이를 놓친 채 불필요한 deep play를 탐색하는 현상을 보임.
- 효과/증거: “MCTS가 깊어서 안전하다”는 반례. Kaggriculture의 2-day missed water/feed, cash infeasibility, $1 glut sale 같은 얕은 비가역 손실은 rollout 평균에 묻히면 안 된다.
- 실패모드: domain-specific 결과를 그대로 일반화하면 안 되지만, hard safety filter 없이 sampling search를 쓰는 위험은 직접적이다.
- 반증 실험: curated shallow-trap suite(다음 day에 escape/weed, cash 부족, shed overflow, unsold terminal inventory)를 만들고 search별 trap miss rate를 측정. 0이 아니면 legality/safety oracle로 선필터.

### S12. simultaneous-move MCTS — Lanctot et al.

- URL: https://repository.tudelft.nl/record/uuid%3A814a4ba7-9508-410e-ba12-79de980cb67b
- 날짜/authority: conference paper 2013; 접근 2026-07-31; **peer-reviewed primary experiment(B+)**.
- 메커니즘: simultaneous Tron을 sequential game 또는 matrix-at-node로 모델링하고 Sequential UCT, Decoupled UCT, Exp3, Regret Matching을 비교.
- 효과/증거: 네 board에서 Decoupled UCB1-Tuned가 전체 62.3%, Regret Matching 53.1%, sequential model 계열 51.4~54.3% win으로 보고됨. 특정 domain 결과지만 simultaneous player orders를 가짜 순차 완전정보로 두는 위험을 보여준다.
- 실패모드: Kaggriculture는 Tron과 payoff/branching/partial information이 다르다. decoupled selection도 joint-action correlation을 놓칠 수 있고 숫자를 전이하면 안 된다.
- 반증 실험: 1~3 turn의 작은 market subgame을 exhaustive normal-form oracle로 만들고 sequential UCT/decoupled/regret matching의 exploitability와 chosen-order revenue를 비교.

### S13. Optimal execution with market impact — Almgren & Chriss

- URL: https://doi.org/10.21314/JOR.2001.041
- 날짜/authority: manuscript 2000-12, Journal of Risk 2000/2001; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: fixed horizon에 position을 청산할 때 permanent/temporary impact와 volatility risk를 함께 최소화해 expected cost-uncertainty efficient frontier를 구성.
- 효과/증거: linear impact model에서 explicit optimal trajectory를 제시. Kaggriculture에는 “생산량”과 “판매량/시점”을 분리하고, 큰 sale이 이후 가격을 낮추므로 revenue trajectory를 최적화해야 한다는 구조적 유사성이 있다.
- 실패모드: Kaggriculture에는 금융 가격 Brownian risk나 temporary/permanent impact 구분이 없고, deterministic price curve·town drain·opponent order가 있다. 공식을 복사하면 모델 오용.
- 반증 실험: 공식 market simulator에서 총 판매량을 고정하고 bulk/equal-slice/demand-after/adaptive schedule의 exact cash만 비교. 금융식 trajectory가 simulator search보다 못하면 폐기하고 “impact-aware scheduling” 아이디어만 유지.

### S14. Dynamic supply/demand and resilience — Obizhaeva & Wang

- URL: https://stuff.mit.edu/people/wangj/pap/ObizhaevaWang13.pdf
- 날짜/authority: Journal of Financial Markets 2013, DOI `10.1016/j.finmar.2012.09.001`; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: supply/demand의 static depth뿐 아니라 trade 후 회복 속도(resilience)를 state에 넣어 optimal execution을 계산. 제시 model의 전략은 initial/final discrete trade와 중간 flow를 혼합한다.
- 효과/증거: 논문 예에서 recovery half-life가 0.90/5.40/27.03분일 때 even strategy 대비 cost saving 0.33%/1.88%/7.41%를 보고. Kaggriculture의 대응물은 endogenous recovery가 아니라 알려진 town consumption cadence와 상대 구매/판매다.
- 실패모드: recovery process가 다른데 수치를 전이하거나, town unlock randomness와 opponent coupling을 무시. shared inventory가 회복되지 않는 구간에서는 slicing이 이득이 아닐 수 있다.
- 반증 실험: price recovery를 `town-only`, `opponent-buy`, `none`으로 분해한 counterfactual replay. timing gain이 실제 town/opponent flow에서만 발생하는지 확인하고, 없으면 bulk sale 단순화를 유지.

### S15. Auction algorithm — Bertsekas

- URL: https://faculty.engineering.asu.edu/bertsekas/wp-content/uploads/sites/129/2019/10/The-Auction-Algorithm-A-Distributed-Relaxation-Method-for-the-Assignment-Problem.pdf
- 날짜/authority: Annals of Operations Research 14, 1988; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: unassigned agent가 object에 bid하고 price를 올리며 highest bidder에게 배정하는 assignment algorithm; dual relaxation 해석과 scaling implementation의 complexity를 제시.
- 효과/증거: 고전 assignment problem을 parallelizable하게 푸는 exact/epsilon 구조. Kaggriculture의 worker-task one-to-one allocation에서 duplicated targets와 local greedy 충돌을 없애는 후보.
- 실패모드: task가 bundle/sequence이고 worker skill·inventory·deadline이 path-dependent이면 단일 assignment matrix가 미래 기회비용을 못 담는다.
- 반증 실험: 짧은 exact enumeration 가능한 worker≤4/task≤8 상태에서 bid matrix assignment의 cash regret를 oracle과 비교. regret가 inventory/deadline state에서 집중되면 bid feature를 보강하거나 bundle planner로 승격.

### S16. MRTA taxonomy — Gerkey & Matarić

- URL: https://robotics.stanford.edu/~gerkey/research/final_papers/mrta-taxonomy.pdf
- 날짜/authority: International Journal of Robotics Research 23(9), 2004; 접근 2026-07-31; **peer-reviewed primary analysis(A)**.
- 메커니즘: task allocation을 single/multi-task robot, single/multi-robot task, instantaneous/time-extended assignment로 분류하고, 반복 재배정의 computation/communication/solution-quality tradeoff를 분석.
- 효과/증거: “allocation 알고리즘”을 문제 구조와 update frequency에 맞춰 선택해야 함을 formalize. Kaggriculture는 worker가 turn마다 한 action을 하면서 여러 단계 task를 수행하므로 time-extended, dynamic reassignment 성격이 강하다.
- 실패모드: allocation과 path/economic schedule을 분리하면 이동 중 target thrash나 care deadline miss. 너무 잦은 재배정은 switching cost를 무시한다.
- 반증 실험: replan cadence `{매턴, 이벤트, 6턴, 하루}`와 commitment penalty를 교차 비교. task-switch count, travel without productive action, missed deadline, cash를 함께 보고.

### S17. Deep opponent modelling — He et al.

- URL: https://proceedings.mlr.press/v48/he16.html
- 날짜/authority: ICML 2016; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: opponent observation을 DQN에 넣고 mixture-of-experts로 strategy pattern을 supervision 없이 분리; explicit multitask opponent model도 비교.
- 효과/증거: simulated soccer와 trivia에서 DQN variants보다 우수하다고 보고. Kaggriculture에는 public farm/market trajectory로 producer/hoarder/dumper/buyer archetype을 추정해 supply scenario를 조건화하는 가설로만 전이 가능.
- 실패모드: adaptive opponent의 moving target, 적은 관측, archetype collapse, opponent가 행동을 바꾸거나 의도적으로 spoof. model gain이 evaluation opponent set overfit일 수 있다.
- 반증 실험: opponent identity를 숨긴 held-out archetype과 midgame strategy switch/spoof agents를 포함. posterior calibration, action prediction보다 **policy cash gain과 worst-case loss**를 promotion 기준으로 사용.

### S18. Safety vs exploitability in opponent modelling — Wang et al.

- URL: https://is.mpg.de/ei/publications/wangbmp2011
- 날짜/authority: AAAI 2011; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: actual opponent strategy를 높은 확률로 포함하는 strategy set을 유지하고, 관측이 적을 때 minimax safety를 지키다가 evidence가 쌓이면 exploit하는 방식.
- 효과/증거: finite-stage stochastic games, repeated RPS, human-robot table tennis에서 적용; 저자는 high-probability로 minimax payoff 이상을 유지하며 preference exploitation이 가능하다고 보고.
- 실패모드: confidence set이 miscalibrated되면 safety guarantee가 무의미; Kaggriculture의 payoff/model class가 논문 가정과 다름.
- 반증 실험: robust baseline 대비 adaptive policy의 lower-tail cash가 허용폭 안일 때만 switch. archetype posterior entropy/coverage threshold를 pre-register하고 spoof suite에서 safety violation rate 측정.

### S19. Budgeted robust optimization — Bertsimas & Sim

- URL: https://pubsonline.informs.org/doi/10.1287/opre.1030.0065
- 날짜/authority: published online 2004-02-01; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: 모든 uncertain coefficient가 동시에 최악이라고 가정하지 않고 uncertainty budget으로 conservatism을 조절; robust counterpart가 여전히 LP이고 discrete optimization으로 확장 가능.
- 효과/증거: portfolio, knapsack, Netlib numerical results와 probabilistic violation bound. Kaggriculture에서는 모든 crop 가격·shop·opponent를 동시에 최악으로 두는 지나친 보수성을 피하는 설계 근거.
- 실패모드: uncertainty set/independence가 실제 joint tail을 못 담으면 bound가 오판; budget을 held-out 결과에 맞춰 사후 tuning하면 overfit.
- 반증 실험: budget `Γ`를 dev에서 고정하고 nominal/Γ-grid/full-worst를 holdout에서 mean, 10th percentile, minimum cash로 비교. 목표 violation rate coverage가 깨지면 set 재설계 전 promotion 금지.

### S20. Robust MDP — Nilim & El Ghaoui

- URL: https://people.eecs.berkeley.edu/~elghaoui/pubs_rob_mdp.html
- 날짜/authority: Operations Research 53(5), 2005; 접근 2026-07-31; **peer-reviewed primary paper(A)**.
- 메커니즘: uncertain transition matrix의 set을 두고 robust DP recursion으로 worst-case expected value를 최적화; likelihood/entropy uncertainty set에서는 classical recursion과 거의 같은 complexity를 보고.
- 효과/증거: path-planning example에서 uncertainty level을 거칠게 추정해도 classical optimal policy보다 worst-case expected travel time이 좋았다고 보고. Kaggriculture에는 shop/weed/opponent market transition uncertainty에 대한 robust value backup이 대응.
- 실패모드: rectangular uncertainty 가정이 실제 time-correlated opponent/shop 과정과 어긋날 수 있고, worst-case policy가 평균 cash를 과도하게 희생.
- 반증 실험: exact small MDP에서 rectangular robust DP와 correlated scenario tree를 비교. correlation 때문에 policy ranking이 뒤집히면 rectangular DP를 쓰지 않고 scenario rollout로 유지.

## 교차소스 설계안과 실험 순서

### 1. 먼저 “현금흐름 oracle”을 작게 만든다

S1/S8/S9의 공통점은 action을 동일 경제 단위로 비교한다는 점이다. 작은 상태(한 quadrant, worker 1~2, crop subset, opponent market fixed)에서는 backward DP/MILP로 exact optimum을 구해 heuristic의 regret를 측정할 수 있다. terminal cash만 세고 inventory는 0으로 둔다.

최초 falsification suite:

1. 남은 1/2/6/12/24/48턴에서 plant/harvest/sell 선택.
2. 다음 day boundary 직전 missed-water/feed와 farm-hand expiry.
3. $1 floor가 가까운 premium product의 bulk/sliced sale.
4. known town demand 직전/직후 판매.
5. shed overflow와 미판매 terminal inventory.

### 2. task allocation과 route를 완전히 분리하지 않는다

S1/S15/S16을 합치면 bid는 단순 Manhattan distance가 아니라 `예상 판매현금 × 성공확률 - travel - switching - deadline failure - displaced-task opportunity cost`여야 한다. 일단 top-k task 후보를 cheap bound로 만들고 exact path/action feasibility로 재평가한다(S6). role은 후보 생성용이지 hard lock이 아니다.

### 3. 시장은 금융 공식을 복사하지 말고 official state transition을 푼다

S13/S14에서 가져올 것은 “order size와 timing을 생산결정과 분리하고, impact state를 continuation value에 넣는다”는 메커니즘이다. Kaggriculture에는 금융 volatility/resilience가 없으므로 official one-unit interleaving, rounding, floor, town drain을 그대로 simulation해야 한다. 상대 주문은 동시에 결정되므로 sequential omniscient assumption을 피한다(S12).

### 4. 상대 적응은 robust default 위에서만 허용한다

S2의 explicit fingerprint와 S17의 learned archetype은 강하지만 brittle하다. S18 방식으로 confidence가 낮을 때 기본 robust policy, 높을 때만 supply/market response를 조건화한다. identity별 overfit을 막기 위해 opponent name이 아닌 관찰 가능한 생산·판매 feature만 쓴다.

### 5. MCTS는 macro layer의 challenger다

UCT는 action 수를 줄인 뒤에만 의미가 있다. crop portfolio, hire count, sell schedule 같은 macro action을 tree node로 두고 저수준 worker action은 deterministic scheduler가 실행한다. shallow irreversible loss는 hard filter하고(S11), simultaneous market response는 decoupled/regret matching 또는 scenario sampling으로 처리한다(S12).

## 권장 계측

- `cash`, liquidatable inventory value(진단용일 뿐 reward 아님), stranded terminal inventory
- product별 생산량, 실현 sale revenue, counterfactual no-impact revenue, slippage
- market inventory/price curve, town tick 전후 order timing, opponent inferred flow
- worker productive-action rate, idle/PASS, travel-only turns, target switches
- missed watering/feed, weed/escape, late harvest/decay, shed overflow, invalid/no-op action
- planner runtime p50/p95/max, completed horizon/depth, fallback count
- opponent posterior entropy/calibration, adaptive switch count, robust-baseline regret

## 검색 쿼리 manifest

### Agent-Reach 상태와 실패

- `agent-reach doctor --json` — GitHub=`gh CLI`, web=`Jina Reader`, Exa=`Exa via mcporter`로 표시.
- 실제 Exa 호출: `Lux AI Challenge 2021 winning solutions paper postmortem official` (`numResults=6`) — HTTP 429 free MCP rate limit. 상태표의 `ok`와 달리 쿼리는 실패했다. 이후 GitHub CLI와 일반 웹 검색으로 fallback.
- Insane Search는 사용하지 않았다. 특정 URL의 403/WAF 우회가 필요한 retained source가 없었다.

### Agent-Reach GitHub CLI 검색

```text
halite 3 winner bot
lux ai season 2 winner solution
google hash code winner solution
halite3
lux-ai
hashcode 2020
FUTURE_LEN repo:ryandy/Lux-S2-public
future repo:ryandy/Lux-S2-public path:luxry
```

첫 세 쿼리는 exact phrase가 너무 좁아 빈 결과였고, 아래 세 broad query에서 retained repos를 찾았다. `gh api`로 README, tree, commit metadata와 Lux S2 `agent_act.py`의 future loop를 원문 확인했다.

### 웹 검색 쿼리

```text
site:arxiv.org Lux AI Challenge 2021 paper winning solutions resource planning
Lux AI Season 2 winner solution official GitHub postmortem
Halite III winner solution postmortem official
Halite IV winning bot solution GitHub postmortem

Lux AI Challenge 2021 competition paper NeurIPS primary source pdf
site:proceedings.neurips.cc Lux AI Challenge 2021 competition track
site:github.com Lux AI Season 1 winning solution post competition writeup
site:kaggle.com/c/lux-ai-2021/discussion winning solution Lux AI 2021

Economic model predictive control without terminal constraints Angeli Amrit Rawlings 2012 PDF
Model predictive control for economic optimization Diehl Amrit Rawlings 2011 primary paper PDF
A Tutorial on Dynamic Programming finite horizon Bellman primary source inventory control PDF
Finite horizon stochastic dynamic programming resource allocation primary paper

Kocsis Szepesvari 2006 Bandit based Monte-Carlo Planning ECML PDF UCT primary
Monte Carlo Tree Search shallow traps adversarial games Ramanujan Sabharwal Selman 2010 PDF
MCTS finite horizon planning deterministic optimization rollout policy primary paper
Decoupled UCT simultaneous move games opponent modelling primary paper

Almgren Chriss Optimal Execution of Portfolio Transactions 2000 PDF primary source market impact
Kyle continuous auctions insider trading 1985 Econometrica PDF market impact primary
Obizhaeva Wang optimal trading strategy supply demand dynamics 2013 primary paper PDF
Transient price impact market manipulation no dynamic arbitrage Gatheral 2010 primary paper PDF

Gerkey Mataric 2004 taxonomy multi robot task allocation primary paper PDF
Bertsekas auction algorithm distributed relaxation 1988 task assignment primary paper PDF
multi robot task allocation sequential single task auction algorithm empirical comparison primary paper
multi agent path finding task allocation conflict based search integrated primary paper PDF

opponent modeling repeated games policy prediction primary paper game AI PDF
opponent modeling in multi-agent reinforcement learning primary survey experiments nonstationarity paper PDF
Bertsimas Sim price of robustness 2004 primary paper PDF
robust MDP uncertainty sets Iyengar 2005 primary paper PDF

Iyengar 2005 Robust Dynamic Programming Mathematics of Operations Research PDF
Nilim El Ghaoui robust control of Markov decision processes uncertainty 2005 PDF
scenario approach robust optimization Campi Garatti exact feasibility theorem primary paper PDF
distributionally robust optimization Markov decision process rectangularity failure primary paper

CodinGame contest winner postmortem MCTS resource management bot official blog
site:codingame.com/blog winner bot postmortem MCTS contest
Google AI Challenge Ants winner postmortem official 2011 bot
Google Hash Code final winner solution postmortem scheduling official blog

"Hash Code" "1st place" solution GitHub final round
"Google Hash Code" "winning solution" team 2022 final
"Hash Code 2021" "first place" solution algorithm
site:github.com/google/coding-competitions-archive hash code official

"Monte Carlo Tree Search for Simultaneous Move Games" authors 2013 Tron
site:ieeexplore.ieee.org "Monte Carlo Tree Search for Simultaneous Move Games"
site:aaai.org simultaneous move MCTS Tron Decoupled UCT regret matching
Lanctot simultaneous move MCTS Tron paper

site:math.nyu.edu Almgren Chriss "Optimal Execution of Portfolio Transactions" pdf
site:nyu.edu "Optimal Execution of Portfolio Transactions" Almgren Chriss PDF
site:toronto.edu Almgren Chriss optimal execution PDF
Robert Almgren Optimal Execution of Portfolio Transactions author PDF
```

### 수렴 판단

- 첫 pass에서 대회 구현/후기와 8개 method family를 모두 확보.
- 두 번째 targeted pass는 simultaneous-move MCTS, robust-MDP rectangularity, optimal-execution 원문을 보강했지만 새 상위 메커니즘 family는 추가하지 못했다.
- 마지막 author/DOI pass는 URL authority만 높였고 backlog 순서를 바꾸지 않았다. 따라서 이 범위에서는 diminishing useful mechanisms로 판단한다. 이것은 “웹의 모든 자료를 검색했다”는 뜻이 아니다.

## 남은 불확실성

- Kaggriculture 공식 competition data는 규칙 미수락 403 blocker 때문에 확인하지 못했다. 우회하지 않았다.
- retained Hash Code source는 우승자 공식 write-up이 아니라 결선 참가자 1차 토론이다. 메커니즘 근거의 authority를 C+로 낮췄다.
- 금융 market-impact 논문의 정량 효과는 Kaggriculture로 전이할 수 없다. official simulator 실험 전에는 판매 분할의 이득을 단정하면 안 된다.
- Lux/Halite의 unit collision·공간 경쟁은 별도 farm grid인 Kaggriculture와 다르다. 여기서 전이하는 것은 global assignment, rollout, opponent-conditioned market response뿐이다.
- 어떤 메커니즘도 로컬 Kaggriculture 실험으로 검증하지 않았다. 이 문서는 research gate 산출물이지 promotion evidence가 아니다.
