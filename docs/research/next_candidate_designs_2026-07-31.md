# 다음 두 후보 메커니즘 설계 — 읽기 전용

- 작성일: 2026-07-31 (Asia/Seoul)
- 기준 formal champion: `artifacts/candidates/final_day_labor/main.py`
  - SHA-256 `112AF9EC28030B53CE852927CEE986834F18F0245F3A88FB2E06F423291C9F8B`
- 범위: 설계와 사전등록안만 작성. 코드 수정, 실행 결과 생성, Save & Run, 제출, 게시, commit/push는 안 했어.
- 결론: 다음 후보는 **A. exact-market herd/execution MPC**, **B. deadline-value task-bundle matching** 두 개가 맞아. 둘 다 Fa01/Fa02 실패 장치를 재포장하지 않고, formal champion을 직접 parent로 둔다.

## 1. 먼저 고정해야 하는 사실

### 1.1 현재 기준선과 실패 경계

- `reports/final_day_labor.md:12-26`의 formal champion은 `cow_tilt` 대비 기존/신규 seed에서 각각 30-2, 31-1이고, fixed development/validation/holdout은 64-0/48-0/48-0이야. 다만 상대 풀이 약하므로 1200 또는 top-3 증거는 아니야.
- 챔피언의 유효한 인과 변화는 day 29, hour 0-3에 10 hands를 먼저 고용하는 것뿐이야. 12/13 hands는 fresh 비교에서 10 hands에 졌어(`reports/final_day_labor.md:12-19`). 따라서 “더 많은 마지막 날 인력”은 다음 후보가 아니야.
- Fa01 overflow routing은 sealed direct 74-54였지만 match score 0.578125, clustered lower 0.4765625, mean margin +445.39로 세 strength gate를 모두 실패했어(`reports/Fa_01_overflow_safe_inventory.md:45-58`). stock>=90 복귀/DROP를 다시 넣지 않는다.
- Fa02의 late crop rotation은 v1이 formal에는 40-24였지만 overflow parent에 30-34, cap2 repair도 formal 57-39=0.59375로 0.60 gate를 실패했어(`reports/Fa_02_horizon_aware_crop_rotation.md:12-20, 48-58`). “만기 지난 premium cell을 wheat/carrot으로 바꾸기”를 다시 쓰지 않는다.
- terminal carry 24-turn 강제 복귀는 3-61, mean -3,456.66이었고 seed 21000에서는 양쪽 final carry가 이미 0인데도 88,045-93,458로 졌어(`reports/Fa_02_horizon_aware_crop_rotation.md:62-74`). day 29 unit liquidation branch를 앞당기지 않는다.

### 1.2 공식 엔진에서 그대로 복제해야 할 훅

공식 원본은 commit `4f6e2763e2232605aacbade443715a9e2c9ef401`, 파일은
`references/kaggle-environments/kaggle_environments/envs/kaggriculture/kaggriculture.py`, 현재 SHA-256은
`B6DA1554674C03931EF03D3499D035D7E10894047FAECD3A8BCC471127734E5D`야.

- crop/animal 비용·생산주기와 market slope: `:11-50`. MELON/MILK/STRAWBERRY/WOOL은 glut-side 충격이 특히 가파르다.
- exact price와 $1 floor: `market_price`, `:177-197`.
- market은 order 최대 10개만 받고, SELL/BUY를 단위별 lockstep으로 처리하며 양 seat가 같은 pre-commit inventory quote를 받는다: `_process_market`, `:519-602`.
- $1 매도는 돈은 주지만 market inventory를 더 밀지 않는다: `_commit_unit`, `:626-635`.
- town demand는 **현재 turn market 처리 뒤** 적용된다: `_town_consume`, `:696-718`, `interpreter :909-914`. 즉 demand tick 직전 매도와 직후 매도는 같은 게 아니다.
- hands는 매일 사라지고 inventory는 shed cap까지만 자동 이관된 뒤 초기화된다: `_end_of_day`, `:829-851`.
- CARE는 실제 현재 소스에서 fed production에 누적 bonus `+1`이다: `_daily_refresh_animals`, `:774-800`. README식 +2로 가치평가하면 안 된다.
- 같은 turn unit action은 farmer부터 hands 순서로 적용되고, seed가 부족한 crop의 PLANT 요청은 그 crop 전체가 PASS로 바뀐다: `interpreter :881-909`.

### 1.3 저장된 top-replay가 말해 주는 것과 말해 주지 않는 것

원본은 `references/top-replays/episode-*-replay.json` 5개고, 분석기는
`src/kaggriculture_lab/research/top_replays.py`야. 원본 해시는
`artifacts/research/top_replay_report.json`에 기록돼 있어. 이 표본은 관찰 증거지 인과 증거가 아니야.

- smlcr 4게임의 실제 PLANT/PLACE는 고정이 아니었어.
  - ep 89123012: S49/W31/M15/C6, COW3/SHEEP6, reward 107,226
  - ep 89133857: S47/W22/M15/C13, COW7/SHEEP2, reward 116,109
  - ep 89135836: S41/W44/M15/C9, COW5/SHEEP3/GOOSE1, reward 103,357
  - ep 89138818: S42/W30/M17/C10, COW6/SHEEP3, reward 115,610
  시장/상대에 적응했다는 인과는 아직 없지만, 상위권에서 하나의 7C/2S·고정 crop 골격만 가능한 건 아니라는 반증은 돼.
- 저장 표본의 peak hired hands는 10-13, 실제 HIRE 요청은 smlcr 279-291, Rui 300, Raiden 322, Danilo 323, Max 238이야. 많은 일감을 매일 다시 배정하는 문제라는 건 분명해.
- Max의 저장된 두 replay에서 `SELL:WHEAT` order가 각각 660회, 요청 수량이 14,081/14,099였어. 이 parser는 **요청**만 세고 체결 성공은 세지 않으므로 “대량 매도가 좋다”는 증거는 아니야. 오히려 exact accepted quantity와 order-slot 낭비를 따로 측정해야 한다는 근거야.
- unit action 중 move 비율은 top 표본에서 0.378-0.632, productive-action 비율은 0.248-0.420, PASS는 0.039-0.338로 넓게 퍼져 있어. PASS 감소 자체를 목표로 삼으면 안 돼. 최종 cash를 만드는 deadline/value task가 완료됐는지가 목표여야 해.

## 2. 후보 A — Exact-market herd/execution MPC

한 줄 정의: **crop grid와 day-29 unit policy는 그대로 두고, 공식 단위별 시장 곡선·town tick·상대 공급 envelope로 “지금 몇 개를 팔지”와 아직 놓지 않은 pasture의 COW/SHEEP mix를 같이 고르는 receding-horizon 경제 제어기**야.

### 2.0 구현 전 공식 엔진 반례

추가 원본 대조에서 단순 budget 오차보다 큰 실행 순서 결함을 재현했다. Formal은 day 29에
예상 SELL 대금을 budget에 먼저 더하지만 `hire_orders + orders`를 반환해 실제 엔진에는
HIRE가 SELL보다 먼저 들어간다. 돈 0, hands 9, shed MILK 20 상태에서 formal action은
`[["HIRE"], ["SELL", "MILK", 20]]`; 공식 엔진 처리 결과 HIRE는 실패하고 판매만 되어
hands 9, money 2,802가 됐다. 같은 상태의 `20 * displayed price`는 3,200으로 실제보다
398 높았다.

따라서 후보 A의 보존 invariant는 “day-29 10-hands 목표, hour 0-3 고용창, hour 14 이후
unit return”이지 literal market-order list가 아니다. A1은 self-exact nominal budget과
실제 실행 가능한 주문 순서, 특히 필요한 경우 SELL-before-HIRE를 함께 고친다. 상대의
동시 주문은 비공개이므로 내부 계산을 actual-exact라고 부르지 않는다. 공식 lockstep,
same-precommit quote, $1 floor, BUY_PRODUCT post-buy quote를 parity test로 고정한다.

### 2.1 왜 Fa01/Fa02의 반복이 아닌가

- shed 90 buffer, worker return, DROP를 추가하지 않는다. parent는 `final_day_labor`이고 `overflow_drop`가 아니야.
- `_crop_plan`과 만기 지난 crop 처리에는 손대지 않는다. wheat/carrot late rotation도 없다.
- terminal unit 복귀는 `final_day_labor._unit_actions`의 day 29/hour 14 branch를 byte-for-behavior로 유지한다.
- 바뀌는 건 market order의 quantity/timing/예산계산과 **미배치 pasture slot의 COW/SHEEP 선택**뿐이야. 이미 배치된 동물은 제거하거나 교체하지 않는다.

### 2.2 exact source hook

| 위치 | 현재 동작 | 후보 A 변경 |
|---|---|---|
| `final_day_labor/main.py:17-20, 340-350` | 고정 SELL_ORDER, 상품별 cap, 가능한 양을 거의 즉시 매도 | self-exact nominal marginal revenue와 다음 town tick을 본 quantity 선택 |
| `final_day_labor/main.py:351` | 예상 매출을 `quantity * current_price`로 더함 | `market_price(inv+k)`를 단위별 합산. 상대 동시 주문 scenario도 같은 pre-commit quote로 반영 |
| `final_day_labor/main.py:353-366` | 예상 판매대금으로 고용 가능 판정 후 실제 HIRE를 SELL보다 먼저 emit | 실행 state와 맞도록 feasible order를 구성하고 day29 필요 시 SELL-before-HIRE |
| `final_day_labor/main.py:157-159` | slot index 1,2만 SHEEP, 나머지 COW | 아직 비어 있는 slot만 day-level herd plan `{9/0,7/2,5/4,3/6}`에 맞춤 |
| `final_day_labor/main.py:334-393` | expanded이면 항상 7C/2S 구매 | robust-NPV가 양수인 목표까지만 BUY_ANIMAL |
| `final_day_labor/main.py:395-433` | wheat/seed/hire를 current-price식 budget 뒤에 큐잉 | exact realized-cash reserve와 10-order slot 아래에서만 큐잉 |
| official `kaggriculture.py:177-197, 519-602, 626-654, 696-718, 909-914` | 실제 price/lockstep/floor/town 순서 | agent 내부의 작은 exact oracle. 이 원본과 parity test 필수 |
| official `kaggriculture.py:19-22, 774-800` | animal yield와 CARE +1 | herd NPV 생산식 |

구현 시 `agent()`에서 unit task와 market action을 만들기 전에 `_economic_plan(obs, farm, private, slots)`를 딱 한 번 호출하고, 그 결과를 `_animal_tasks`와 `_market_actions`에 같이 넘기는 구조가 가장 작아. crop 계획과 unit scheduler는 그대로 둔다.

### 2.3 state/features

- 시간: `step/day/hour`, 남은 turn/day, 다음 town-center/shop demand tick, day boundary.
- 현금/재고: money, shed, seeds, 각 unit inventory, 남은 shed room. 단 overflow 행동은 바꾸지 않고 infeasible sale/구매를 막는 데만 쓴다.
- 시장: 상품별 current inventory/price, 공식 curve params, unlocked shops, 다음 known demand drain.
- 우리 생산: crop/animal별 tile 수, planted/placed day, yield held, 다음 생산일, fed/cared 상태, wheat feed 의무, fixed crop plan에서 예상되는 외생 공급.
- 상대 공개 생산: 상대 tile의 crop/animal 종류·나이·held yield로 만든 `low/base/high` 향후 공급 envelope. 상대 private inventory와 실제 order는 보이지 않으므로 점추정하지 않는다.
- 실행 특징: 상품별 exact `revenue(q)`, $1 floor 도달 수량, order slot 사용량, 다음 land/animal/seed/hire에 필요한 cash reserve.
- herd 후보: 이미 놓인 C/S를 하한으로 하고 총 pasture 9개 안에서만 움직인다. 불가능한 mix는 제거한다.

### 2.4 pseudocode

```text
base = final_day_labor_actions(obs)

if unit policy is requested:
    return base unit actions                 # crop/task/terminal behavior 보존

state = extract_visible_state(obs)
scenarios = {
    LOW_SUPPLY:   opponent sells no hidden stock; public production delayed,
    BASE_SUPPLY:  public mature yield sold at observed cadence envelope,
    GLUT_SHOCK:   1.5x public production sold at earliest feasible turn
}

for herd_mix in feasible({9C0S, 7C2S, 5C4S, 3C6S}, already_placed):
    project C/S milk, wool, fertilizer, wheat feed, care(+1), purchase cost

    for each product independently:
        candidate current-sale quantities =
            {0, all, amount-to-next-price-knee, 1/4, 1/2, 3/4 of shed}
        candidate future events =
            {next turn after town tick, next harvest, day close, terminal}
        use exact unit price curve and each opponent scenario
        keep nondominated (cash-now, expected-final-cash, worst-final-cash) plans

    combine per-product plans with a small knapsack under max 10 market orders
    simulate purchase queue in official order with exact cash, no optimistic quote*qty
    score = mean(final_cash) - 0.5 * CVaR10_loss
            - liquidity_violation_penalty - infeasible_work_penalty

champion_plan = same simulator with 7C2S and current fixed-sale rule
chosen = argmax(score)
if min_scenario(chosen - champion_plan) < +500 or any hard constraint fails:
    chosen = champion_plan

emit only currently executable orders; skip zero-stock/zero-affordability orders
assert len(market_orders) <= 10
```

`+500`은 성능 주장값이 아니라 dev 전에 고정할 안전 switch margin이야. 너무 보수적이면 A3 ablation에서 “항상 fallback”으로 바로 드러나야 해.

### 2.5 기대 이득과 최악 실패

- **설계 목표(아직 관측값 아님):** market-sensitive 상대에서 mean money +2,000~+6,000, sealed 전체에서 formal 대비 mean margin 최소 +1,500. fixed-price 예산오차, premium glut, 10-order slot 낭비가 동시에 있는 게임이면 tail보다 mean 쪽에서 큰 도약 여지가 있어.
- 가장 큰 실패는 hidden opponent inventory를 잘못 추정해 liquidity를 늦추고 land/hire/seed 구매를 놓치는 거야. 시장에서 몇백 더 벌려다 생산 자본을 잃으면 수천을 잃을 수 있어.
- 이미 배치한 동물은 되돌릴 수 없어서 early wrong mix가 lock-in될 수 있어. robust switch margin과 “이미 배치된 수가 하한”인 이유야.
- 내부 oracle이 official rounding, $1 floor, market-before-town 순서 중 하나라도 다르면 계산이 정교할수록 더 위험해.
- worst-case에서 robust gate가 너무 보수적이면 사실상 formal과 같아져 score가 안 오른다. 그 경우 안전하지만 후보로는 폐기야.

### 2.6 dev / sealed split과 promotion gate

아래 seed는 현재 저장된 config/evaluation의 최대 사용 seed 22015보다 크고 서로 겹치지 않아. **dev만 먼저 공개하고, candidate source hash·threshold·opponent hash를 고정한 뒤 sealed를 한 번만 연다.** 모든 게임은 양 seat, bootstrap은 `src/kaggriculture_lab/evaluation/runner.py:158-188`처럼 `(opponent, seed)` cluster 단위로 한다.

| 단계 | seed | opponent | raw games | 용도 |
|---|---:|---|---:|---|
| A-dev | 23000-23015 | formal champion, scenario_aware, barnyard_economist, diversified_scheduler | 16×4×2=128 | feature/threshold tuning, ablation |
| A-sealed-strength | 24000-24063 | formal champion only | 64×1×2=128 | 직접 승격 gate |
| A-sealed-robustness | 25000-25031 | scenario_aware, barnyard_economist, yumerous, hamburger_current, fast_expansion, cow_tilt | 32×6×2=384 per policy | 후보와 formal을 각각 같은 pool에 돌려 paired policy delta |

Strength gate는 모두 통과해야 해.

- failed/invalid/timeout 0.
- match score `>= 0.60`, seed-cluster bootstrap 95% lower `> 0.50`.
- mean direct margin `>= +1,500`, median direct margin `>= +1,000`.
- seat별 match score 각각 `>= 0.55`.

Robustness gate도 모두 통과해야 해.

- formal의 같은 seed/opponent replay 대비 mean money delta `>= +1,000`, median `>= +750`.
- paired p10 money delta `>= -500`; opponent별 mean delta 최저값 `>= -750`.
- pool match-score delta `>= -0.02`; failed game 0.
- exact simulator가 한 turn SELL revenue/next inventory를 official engine과 비교한 parity suite에서 mismatch 0. 이건 score gate가 아니라 선행 필수조건이야.

### 2.7 runtime budget

- 720-call replay에서 invalid output 0, planner fallback/exception 0.
- agent call p95 `<= 8 ms`, p99 `<= 15 ms`, max `<= 50 ms`. 현재 formal p95 1.4787 ms/max 2.2181 ms보다 느려지는 걸 허용하되 100 ms 기존 상한보다 충분히 낮게 잡는다.
- herd 후보 최대 4, scenario 3, 상품 9, quantity 후보 최대 6으로 제한하고 상품별 Pareto pruning 뒤 10-slot knapsack만 한다. rollout tree/MCTS는 넣지 않는다.
- 시간이 40 ms를 넘기면 완성되지 않은 plan을 쓰지 말고 formal market action으로 즉시 fallback한다.

### 2.8 ablation / kill rule

- A0: untouched formal champion.
- A1: exact accepted-quantity/price-impact sale queue만, herd 7C/2S 고정.
- A2: herd mix MPC만, 기존 fixed sale queue.
- A3: full이지만 상대 scenario를 BASE 하나로 고정.
- A4: full.

동일 A-dev 128게임에서 A4가 A0보다 mean money `>= +1,000`이고, `max(A1,A2,A3)`보다 `>= +300`이어야 full interaction을 유지해. 아니면 이득이 난 단일 부품만 별도 후보로 다시 사전등록하고 A4는 폐기해. crop plan hash/출력과 day29 hour>=14 unit action이 A0와 동일하다는 differential test도 필수야.

### 2.9 왜 rating 1200 보장이 아닌가

현지 cash/match-score와 Kaggle rating 사이의 고정 변환식이 없어. 저장 top replay는 5게임·몇 팀의 관찰이고 실제 code도 없으며, 상대 private inventory와 현 ladder pool도 달라. 이 후보는 fixed 7C/2S와 시장 실행의 구조적 빈틈을 노리지만, sealed local 통과조차 1200이나 top-3를 보장하지 않아.

## 3. 후보 B — Deadline-value task-bundle matching

한 줄 정의: **현재 “priority 먼저, 거리 다음” greedy worker-task pairing을, deadline·예상 terminal cash·pickup/action 선후관계·공유재고 예약을 포함한 작은 assignment 문제로 바꾸고 첫 action만 실행하는 receding-horizon scheduler**야.

### 3.1 왜 기존 실패/단순 labor 실험과 다른가

- hands 목표는 매 turn/day 모두 formal과 동일하게 둔다. 12/13 final-day hands 실험을 반복하지 않는다.
- market order, crop grid, 7C/2S, land timing, overflow/DROP, day29 terminal branch를 모두 그대로 둔다.
- 새 메커니즘은 **같은 worker 수가 어떤 일감을 어떤 순서로 끝내느냐**뿐이야. top replay의 많은 daily HIRE는 노동량이 크다는 근거지만 “더 고용”의 근거로 쓰지 않는다.
- PASS를 벌점으로 두지 않는다. 가치가 음수인 task면 idle이 정답일 수 있어.

### 3.2 exact source hook

현재 formal도 task를 전역으로 보긴 하지만 optimal assignment가 아니야.

| 위치 | 현재 동작 | 후보 B 변경 |
|---|---|---|
| `final_day_labor/main.py:162-193` | animal task에 정수 priority 0/1/2 | deadline, avoided-loss, exact product value를 가진 job 생성 |
| `final_day_labor/main.py:195-231` | crop task에 priority 3-8, WATER면 그 turn 다른 task 생략 | water/harvest/plant의 slack과 successor를 같이 평가 |
| `final_day_labor/main.py:234-242` | Manhattan + pickup 1회 거리만 cost | `pickup→travel→action` bundle 길이, day expiry, switching/opportunity cost |
| `final_day_labor/main.py:282-298` | 모든 pair 중 `(priority, cost, 좌표...)` 최소 하나를 반복 선택 | top-K job에 Hungarian/auction assignment + idle dummy |
| `final_day_labor/main.py:300-307` | PLANT seed만 사후 차감 | wheat/animal/seed/shed를 farmer→hands 실행 순서로 선예약·repair |
| official `kaggriculture.py:297-415, 480-505` | unit action legality/수확/FEED/CARE | task bundle과 payoff의 oracle |
| official `kaggriculture.py:721-735, 738-800` | crop decay, water/weed, feed/escape, yield | deadline과 missed-task loss |
| official `kaggriculture.py:881-909` | farmer→hands 순차 적용, crop seed atomic block | assignment 뒤 resource-conflict repair 순서 |

구현 훅은 `_unit_actions` 내부의 `while free_units and free_tasks`만 교체하는 게 1차 범위야. task generator에 metadata를 보태되 `_market_actions`, `_crop_plan`, 고용 수는 건드리지 않는다.

### 3.3 state/features

- worker별 position, carried item/수량, shed까지 거리, 현재 reservation/이전 target.
- job별 target, terminal action, 필요한 item, earliest start, deadline step, route length, slack.
- water: `watered_today`, `consecutive_unwatered`, crop maturity/held yield. 두 번째 miss의 weed 전환은 hard avoided-loss.
- animal: `fed_today`, `consecutive_unfed`, next production, held/max_held, `cared_today`, CARE +1, fertilizer_available. 두 번째 miss의 escape는 hard avoided-loss.
- harvest: held units의 exact conservative sale value, 다음 생산 때 max-held로 잘릴 양, crop `max_lifespan_step` decay.
- build/place/plant: seed/animal availability, 첫 수확이 horizon 안인지, 그 뒤 요구되는 water/feed work.
- global resource: shed WHEAT/COW/SHEEP, seeds, unit별 inventory를 farmer→hands 순서로 예약한 잔량.
- assignment history: 같은 target 유지 보너스와 target switch 비용. module state를 쓰면 `step==0`에서 player별 상태를 반드시 reset하고 replay 재실행 결정성이 같아야 해.

### 3.4 pseudocode

```text
base_tasks = existing animal_tasks + crop_tasks
jobs = []

for task in base_tasks:
    deadline = exact_deadline(task, tile, day, hour, engine rules)
    avoided_loss = value lost if deadline is missed
    direct_value = conservative marginal sale value of produced/collected units
    successor = best feasible next task near target within 2 actions
    upper_bound = direct_value + avoided_loss + successor.value
    jobs.append(metadata)

jobs = all emergency jobs + top K=18 non-emergency jobs by upper_bound

for worker in farmer_then_hands:
    for job in jobs:
        bundle = shortest feasible [pickup?, moves..., terminal_action]
        if bundle length > remaining turns today or resource unavailable:
            bid = -INF
        else:
            slack = deadline_step - current_step - bundle_length
            bid = direct_value + avoided_loss
                  + 0.35 * successor_value
                  - opportunity_cost_per_turn * bundle_length
                  - switch_penalty
                  - late_penalty(slack)
    add IDLE dummy with bid 0

assignment = maximize total bid with one worker/job via Hungarian or auction
simulate first actions in official farmer->hands order:
    reserve shed items/seeds and repair conflicts
    reject any illegal or atomic-PLANT-blocking combination

for each worker:
    keep previous target if still feasible and new bid improvement < hysteresis
    emit only bundle[0]

if day >= 29 and hour >= 14:
    return untouched formal terminal unit branch
```

`opportunity_cost_per_turn`은 product current price가 아니라 formal replay에서 같은 phase의 완료 job value 중앙값으로 dev에서 한 번 고정해. economic value를 전혀 못 계산하는 early build/dig에는 기존 priority를 큰 avoided-loss prior로 변환하고, cash로 억지 환산하지 않는다.

### 3.5 기대 이득과 최악 실패

- **설계 목표(아직 관측값 아님):** formal 대비 mean money +1,500~+5,000. 하루에 deadline 높은 task 1-2개를 더 완료하거나 pickup/no-op·target thrash를 줄이면 30일 누적에서 수천 단위 여지가 있다는 가설이야.
- 최악 실패는 cash value가 당장 안 보이는 WATER/FEED를 밀어 weed/escape를 만드는 거야. 두 번째 miss와 당일 남은 slack은 soft score가 아니라 hard emergency로 처리해야 해.
- 독립 assignment는 shared WHEAT/animal/seed와 multi-step precedence를 완전히 표현하지 못해. 그래서 official farmer→hands 순서의 reservation/repair가 없으면 여러 worker가 같은 재고를 잡고 no-op가 날 수 있어.
- top-K pruning이 멀리 있는 필수 task를 버리거나, 매 turn 재계산이 target thrash를 만들 수 있어. emergency 무조건 포함과 hysteresis가 필요해.
- module history reset이 새 episode에서 새면 재현성/좌석 오염이 생긴다. history-off ablation과 two-run action hash 일치가 필수야.
- travel/PASS 비율이 좋아져도 cash가 안 오르면 실패야. top replay에서도 높은 score와 낮은 move/PASS가 단조 관계가 아니었어.

### 3.6 dev / sealed split과 promotion gate

| 단계 | seed | opponent | raw games | 용도 |
|---|---:|---|---:|---|
| B-dev | 26000-26015 | formal champion, diversified_scheduler, scenario_aware, yumerous | 16×4×2=128 | bid/K/hysteresis, ablation |
| B-sealed-strength | 27000-27063 | formal champion only | 64×1×2=128 | 직접 승격 gate |
| B-sealed-robustness | 28000-28031 | scenario_aware, barnyard_economist, yumerous, hamburger_current, fast_expansion, cow_tilt | 32×6×2=384 per policy | 후보와 formal의 paired policy delta |

Strength gate:

- failed/invalid/timeout 0.
- match score `>= 0.60`, clustered 95% lower `> 0.50`.
- mean direct margin `>= +1,500`, median `>= +1,000`; seat별 match score `>= 0.55`.

Robustness gate:

- formal의 같은 replay set 대비 mean money delta `>= +750`, median `>= +500`.
- paired p10 delta `>= -500`, opponent별 mean delta 최저값 `>= -750`.
- pool match-score delta `>= -0.02`; failed game 0.
- mechanism diagnostics:
  - baseline hard water/feed miss가 있던 strata에서는 count `>=40%` 감소; baseline 0인 strata는 0 유지.
  - duplicate-resource/atomic-PLANT no-op 0.
  - value-weighted completed-job per paid hand-turn `>=5%` 증가 **또는** travel-without-completion `>=10%` 감소. 둘 중 하나만 좋아져도 cash gate는 별도로 반드시 통과해야 해.

### 3.7 runtime budget

- 720 calls에서 p95 `<= 8 ms`, p99 `<= 15 ms`, max `<= 50 ms`, invalid 0.
- worker 최대 11(10 hands+farmer), job은 emergency 전부+비긴급 top 18로 제한. 20~30 크기 assignment의 O(n^3)는 이 예산 안에서 끝나야 해.
- exact path는 현 BFS를 재사용하고 `(source,target,unlocked-mask)` cache를 둔다. 40 ms에서 미완성 solver 결과를 쓰지 말고 기존 greedy로 fallback한다.
- fallback rate는 runtime replay에서 0이어야 promotion 가능해. fallback이 발생하면 실제 sealed score가 어떤 코드 경로의 결과인지 불명확해져.

### 3.8 ablation / kill rule

- B0: untouched formal.
- B1: assignment solver만 사용하되 기존 `(priority, distance)` cost 유지. greedy-vs-global 효과 분리.
- B2: B1 + exact deadline/avoided-loss.
- B3: B2 + marginal cash value.
- B4: B3 + successor bundle/hysteresis/resource reservation = full.
- B5: B4에서 history/hysteresis만 off. state leakage 없이 gain이 유지되는지 확인.

B-dev에서 full이 B0보다 mean money `>= +750`이고 p10이 `>= -500` 이내여야 sealed로 간다. assignment metrics만 좋아지고 money가 안 오르거나, WATER/FEED hard miss가 하나라도 늘면 바로 폐기해. market action, hire count/day, crop target, placed herd target이 B0와 동일하다는 differential replay check도 필수야.

### 3.9 왜 rating 1200 보장이 아닌가

이 후보의 직접 근거는 formal source의 greedy 구조와 official deadline/resource semantics야. 저장 top replay에는 target identity와 체결/no-op 전수가 없어서 “상위권이 이 assignment를 쓴다”는 증거가 없어. local pool에서 +1,500을 만들어도 ladder 상대 분포와 rating 변동성 때문에 1200을 보장할 수 없다.

## 4. 공통 opponent/source lock

sealed 등록 시 아래 현재 파일과 hash를 그대로 receipt에 넣고, start/end hash 일치를 확인해야 해.

| 이름 | source | 현재 SHA-256 |
|---|---|---|
| formal champion | `artifacts/candidates/final_day_labor/main.py` | `112AF9EC28030B53CE852927CEE986834F18F0245F3A88FB2E06F423291C9F8B` |
| scenario_aware | `artifacts/opponents/public_kaggle/scenario_aware.py` | `13EBE04AAE9DC6C6788E7790383D8FBF47222DAA8AD4E88CAD82EC769FA16BF5` |
| barnyard_economist | `artifacts/opponents/public_kaggle/barnyard_economist.py` | `018DACF6372B5358F171DB35322D083D0C09AFD89B475C4C31C827912AB92C8E` |
| diversified_scheduler | `artifacts/opponents/public_kaggle/diversified_scheduler.py` | `FAD8A5B0BD89DBA0318EBD1F4B470F6347F84905A559C251536BB6FB934B2F7E` |
| yumerous | `artifacts/opponents/public_kaggle/yumerous.py` | `80399ADCA27D96C3E34B7D154050C114BCD74E1190A779E4ADB35D8034EF2960` |
| hamburger_current | `artifacts/opponents/public_kaggle/hamburger_current.py` | `A0F6B394C2DA7D420DECF448575B85E540C3249BF4AF1A3C69FA9B643411B793` |
| fast_expansion | `artifacts/candidates/fast_expansion/main.py` | `406BC82979637A42F2848382AD5E0248C403BBB346D09CF93859DC2D5761F25C` |
| cow_tilt | `artifacts/candidates/cow_tilt/main.py` | `6CDE0002281620BAED323D0EDA5DBF48A6D0B7C4B8A3564BC951A757805E621E` |

이 opponent들은 “현 1200 메타”의 완전한 복제본이 아니야. strong/public/경제형/스케줄형과 현재 lineage를 섞은 regression pool일 뿐이야.

## 5. 권장 순서와 최종 kill 기준

1. **A부터**: formal source의 `quantity * current_price`가 official unit-impact와 직접 불일치해서 가장 명확한 엔진 훅이 있고, Fa02 결론인 “terminal production/sale scheduling을 먼저 해결”에도 맞아.
2. A가 sealed NO-GO면 seed/threshold를 보고 고치지 말고 종료해. B는 완전히 다른 26000+ dev/27000+ sealed로 독립 진행한다.
3. B는 same-labor/same-market differential을 먼저 통과해야 해. 다른 경제 결정을 슬쩍 섞으면 인과 후보가 아니야.
4. 어느 후보든 평균만 오르고 clustered lower, p10, failure/runtime 중 하나가 gate를 못 넘으면 formal champion은 그대로 유지한다.
5. 두 후보를 합치는 건 각자 독립 sealed GO 후의 별도 신규 hypothesis여야 해. A+B를 바로 합치면 어느 메커니즘이 이겼는지 알 수 없어.

최종적으로 이 문서는 **큰 도약 가능성이 있는 두 실험 계약**이지, 성능 결과가 아니야. 현재 증거로 확실히 말할 수 있는 건 “Fa01/Fa02 실패를 반복하지 않으면서 formal의 두 구조적 빈틈을 독립적으로 검증할 수 있다”까지야.
