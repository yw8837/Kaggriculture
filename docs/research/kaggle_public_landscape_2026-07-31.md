# Kaggriculture 공개 인텔리전스 조사

- 접근일: 2026-07-31 (KST)
- 라이브 리더보드 스냅샷: 2026-07-31 23:06:02 KST / 14:06:02 UTC
- 공개 리플레이 원본 회수: 2026-07-31 23:14:21–23:14:35 KST / 14:14:21–14:14:35 UTC
- 범위: Kaggle 공개 Code·Discussion·Dataset·Leaderboard·Episode, GitHub 공개 저장소·커밋·PR·이슈
- 쓰기 경계: 이 문서만 생성했다. Kaggle save/run/submit, 외부 게시, git commit/push, production/Fa 수정은 하지 않았다.

## 0. 결론부터

1. 현재 상위권 공개 리플레이는 단일 “메타 빌드”가 아니야. Rui의 고정 2구역 혼합 농장, smlcr의 빠른 3구역·딸기/밀 적응, Raiden의 14인·작물/가축 적응, Victor의 0일 전 구역 매입·후반 가축, Max의 좌석별 가축 비대칭, Danilo의 대규모 혼합 재배가 함께 살아 있다.
2. 그래도 공통점은 분명해. 조사한 상위 6팀은 모두 11–15명 피크 인원, 가축, 토지 확장, 밀 조달을 사용했다. 공개 starter류의 5×5 고정 melon/wheat 농사만으로는 현재 상위권을 설명 못 한다.
3. 결과 분산이 크다. 같은 submission에서 Victor는 66,255–165,388, Max는 29,357–97,520이었다. 한 게임 또는 최고점 하나로 우열을 일반화하면 안 된다.
4. Rui의 5게임은 실제 상태 지표가 정확히 `13명 / 실제 고용 300 / 10일 토지 / 2구역 / COW 8 / SHEEP 8 / CARROT 6 / MELON 16 / STRAWBERRY 20`으로 같았다. 하지만 720턴 액션 해시는 4종이라 “완전 고정 스크립트”가 아니라 “고정 경제 골격”까지만 증거가 있다.
5. 공식 엔진 코드와 공식 README가 CARE 보너스에서 충돌한다. 현재 핀된 코드 `4f6e2763e2232605aacbade443715a9e2c9ef401`는 fed+cared day당 `+1`, README는 `+2`라고 적는다. 전략 계산은 코드 `+1`을 기준으로 해야 하고, 최소 단위 환경 테스트로 고정해야 한다.
6. 현재 공개 Code 14개 중 독립적인 수치 실험이 가장 잘 적힌 건 Barnyard Economist와 Scenario-Aware notebook이다. 다만 둘 다 저자 notebook 내부 주장이고 이 조사에서 재실행하지 않았다. “LB 950”, “8-0” 같은 숫자는 후보 생성 근거이지 채택 근거가 아니다.
7. GitHub 검색에서 현재 공식 엔진 외 직접 쓸 만한 공개 구현은 적었다. `niits/kaggriculture`는 실행 산출물이 있지만 5 seeds·내부 상대군이고 보상 규모도 현재 공개 상위권과 멀다. `krobus`는 전략보다 리플레이 검증 도구로 유용하다.

## 1. 증거 등급과 해석 규칙

| 등급 | 뜻 | 이 문서에서의 예 |
|---|---|---|
| A | 공식 원본/실행 산출물 | 공식 엔진 소스, Kaggle leaderboard API, raw episode JSON, 로컬 benchmark CSV |
| B | 공개 구현 소스 + 재현 가능한 설명 | Kaggle notebook source, GitHub agent code |
| C | 저자 보고 수치, 이번 조사에서 미재현 | notebook markdown의 win/score 주장 |
| D | 커뮤니티 관찰/일화 | Discussion의 좌석·RNG 관찰 |

- `reward`는 raw episode의 최종 bank와 일치하는 실제 게임 결과다.
- `rating`은 각 episode 전후의 `initialScore → updatedScore`다. 라이브 점수와 시간대가 다르면 별도 스냅샷으로 취급했다.
- `실제 고용`은 `farm.hands` 상태의 양의 증가분 합이다. 반복 `HIRE` 주문 시도 수와 다르다.
- `실제 작물`은 `(좌표, planted_day, crop)`의 최초 출현을 센 값이다. 단순 PLANT 명령 수가 아니다.
- `동물 max`는 관측 상태의 동물별 PASTURE 최대 개수다. 빈 PASTURE는 제외했다.
- 리플레이 표본은 22 episodes, 상위 6팀 관측 31행이다. 전체 ladder의 확률 표본이 아니며 상대·시간·submission이 상관돼 있다.

## 2. 라이브 상위권 스냅샷

공식 leaderboard API/CLI, 2026-07-31 23:06:02 KST. URL: <https://www.kaggle.com/competitions/kaggriculture/leaderboard>

| 순위 | 팀 | team id | 조사한 active best submission | 라이브 점수 |
|---:|---|---:|---:|---:|
| 1 | RuiKimura4 | 16623798 | 55129098 | 1322.2 |
| 2 | smlcr | 16621709 | 55134690 | 1283.1 |
| 3 | Raiden.B | 16621355 | 55134549 | 1281.2 |
| 4 | Victor @ Tufa Labs | 16621497 | 55136535 | 1256.3 |
| 5 | Max Manushin | 16622835 | 55124664 | 1253.8 |
| 6 | Danilo_Malbashich | 16622990 | 55129067 | 1227.3 |

주의: 같은 날 09:37 UTC에 갱신된 `georgymamarin/kaggriculture-episodes`의 teams snapshot은 Max 1277.7, Rui 1263.6 순이었다. 14:06 UTC live snapshot은 Rui 1322.2, Max 1253.8이다. 순위와 평점은 빠르게 움직인다.

## 3. 상위 6팀 공개 리플레이 비교

### 3.1 팀별 관측 요약

`bank`는 day 5/10/15/20/25/29/final의 표본 중앙값이다. 작물·동물은 표본별 실제 관측의 중앙값이다.

| 팀 | n / 좌석(0,1) | reward min/med/max | 피크 인원 / 실제고용 med | 토지 첫날→구역 | 실제 작물 med | 동물 max med | bank med (d5,d10,d15,d20,d25,d29,final) |
|---|---:|---:|---:|---|---|---|---|
| RuiKimura4 | 5 / 3,2 | 81,343 / 115,085 / 120,662 | 13 / 300 | 10→2 | C6 M16 S20 | COW8 SHEEP8 | 1,250 / 4,209 / 17,940 / 40,976 / 79,020 / 105,568 / 115,085 |
| smlcr | 6 / 4,2 | 112,956 / 115,369.5 / 124,449 | 11 / 282 | 6–7→3 | C8.5 M16 S42.5 T0 W33.5 | COW6 SHEEP3 | 504 / 1,061 / 19,562.5 / 43,557 / 79,111 / 106,089.5 / 115,369.5 |
| Raiden.B | 5 / 3,2 | 103,462 / 114,386 / 126,022 | 14 / 324 | 11→3 | M23 S34 T10 W18 | COW8 SHEEP8 | 15 / 70 / 3,322 / 15,380 / 65,882 / 104,382 / 114,386 |
| Victor @ Tufa Labs | 6 / 2,4 | 66,255 / 130,264.5 / 165,388 | 15 / 323.5 | 0→4 | C13 M40 S33 | COW15 SHEEP5 | 326 / 161 / 25.5 / 15,004.5 / 60,895 / 102,927.5 / 130,264.5 |
| Max Manushin | 5 / 2,3 | 29,357 / 60,906 / 97,520 | 13 / 238 | 10→2 | C14 M30 W24 | seat0 COW12/S16; seat1 COW22/S6 | 156 / 339 / 3,740 / 23,225 / 51,065 / 58,124 / 60,906 |
| Danilo_Malbashich | 4 / 2,2 | 102,526 / 105,655 / 108,889 | 13 / 324 | 11→3 | C48.5 M21 S16 T5 W79 | COW9 SHEEP8 | 327.5 / 124.5 / 8,175 / 22,075.5 / 56,566.5 / 90,751 / 105,655 |

### 3.2 팀별 메커니즘·효과·실패모드·반증 실험

이 여섯 카드는 아래 raw episode family 전체를 retained source로 본다. 권위는 A(공식 replay 원본), 성능 인과 해석은 관찰 수준이다.

#### R-1 RuiKimura4 / submission 55129098

- 정확한 메커니즘 관측: 5/5에서 13인, 300 실제 고용, day 10 두 번째 구역, COW8/SHEEP8, C6/M16/S20, 종료 FERTILIZER6·WOOL3. 경제 골격이 좌석·상대에 무관하게 같았다.
- 기대 효과: 운영 복잡도를 제한하면서 melon/strawberry와 milk/wool/fertilizer를 함께 현금화해 시장 한 자원 포화를 줄인다.
- 실패모드: final에 fertilizer/wool을 들고 끝나고, reward가 81k–121k로 상대/시장 충격을 그대로 받는다. 동일 골격이 메타 변화에 둔감할 수 있다.
- 반증 실험: 같은 seed를 양 좌석, 저공급/고공급/가축 spam 상대 3종으로 돌린 뒤 상태 특징뿐 아니라 720턴 action hash·시장 매도곡선을 비교한다. 상대를 바꿔도 특징과 행동이 모두 같아야 “고정 스크립트”라고 부를 수 있다.

#### R-2 smlcr / submission 55134690

- 정확한 메커니즘 관측: 11인, 281–282 실제 고용, day 6–7에 3구역, 9개 안팎 가축, strawberry/wheat 중심이지만 작물 조합이 게임별로 크게 달랐다. 6/6 final carry가 0이었다.
- 기대 효과: 빠른 토지와 완전 청산, 작물 비중 적응으로 시장 수요를 따라간다.
- 실패모드: 6게임 중 seat1은 2개뿐이고, 동일 상대가 반복된다. 많은 밀 매매가 실제 성공 거래인지 주문 재시도인지 raw action만으로는 분리되지 않았다.
- 반증 실험: 20 paired seeds × 양 좌석에서 opponent supply를 crop별로 고정하고, 성공 주문 로그/실제 inventory delta로 작물 전환 임계값과 terminal liquidation 성공률을 측정한다.

#### R-3 Raiden.B / submission 55134549

- 정확한 메커니즘 관측: 14인, day 11→3구역, 13–18 동물 pasture, crop mix가 M19–32/S18–52/T1–33/W16–29로 바뀐다. 표본 중앙 final carry는 FERTILIZER14·WOOL12 등 0이 아니다.
- 기대 효과: specialty crop과 동물 구성을 시장/판에 맞춰 바꾸고 fertilizer를 실제 생산에 투입한다.
- 실패모드: 매우 낮은 d5/d10 bank(중앙 15/70), 종료 재고 누수, game별 가축/작물 변동 원인이 상대인지 seed인지 불분명하다.
- 반증 실험: paired seed에서 기존 정책 vs last-48-turn 강제 청산을 비교하고, bank·운반 중 재고·미수확량을 분해한다. 동시에 상대 supply만 바꿔 crop/animal 선택의 민감도를 회귀한다.

#### R-4 Victor @ Tufa Labs / submission 55136535

- 정확한 메커니즘 관측: 6/6에서 day 0에 4구역, 15인, day 11부터 동물, 중앙 COW15/SHEEP5. CARROT13/MELON40은 안정적이고 strawberry가 9–61로 바뀐다. final carry는 5/6이 0, 최신 게임만 fertilizer16이다.
- 기대 효과: 전 구역을 즉시 확보하고 후반 생산량을 크게 키워, 조건이 맞을 때 150k+ bank를 만든다.
- 실패모드: d15 bank 중앙 25.5까지 자본이 잠기고 reward 66k–165k로 가장 크게 흔들린다. 상대 가격 압박이나 이동 병목에 취약할 가능성이 높다.
- 반증 실험: `BUY_LAND day0`를 day3/day6로 지연한 ablation, premium glut slope stress, 양 좌석 paired seeds를 각각 30개 이상 돌린다. 파산 근접 턴, invalid order, d15 liquidity, final bank의 lower decile을 주지표로 둔다.

#### R-5 Max Manushin / submission 55124664

- 정확한 메커니즘 관측: 13인·238 실제 고용·day10→2구역은 5/5 동일. seat0 두 게임은 COW12/SHEEP16·final COW6, seat1 세 게임은 COW22/SHEEP6·final 0이었다. crop은 C14/M29–31/W21–27.
- 기대 효과: 좌석별 공간/동선에 맞춘 가축 구성과 대량 wheat 공급으로 동물 생산을 밀어붙인다.
- 실패모드: seat와 animal mix가 완전히 공선이라 의도된 좌석 정책인지 우연인지 아직 모른다. reward 29k–98k, 두 seat0 게임에서 COW6가 미배치로 남았다. 반복 대량 SELL 주문은 10-order cap을 낭비할 수 있다.
- 반증 실험: 같은 20 seeds를 seat swap하고 상대를 고정한다. 구매 animal과 성공 배치 animal을 따로 세며, order acceptance/invalid/no-op 비율과 final unplaced animal을 기록한다.

#### R-6 Danilo_Malbashich / submission 55129067

- 정확한 메커니즘 관측: 4/4에서 13인, day11→3구역, COW9/SHEEP8, M21/S16/T5가 고정에 가깝고 carrot/wheat를 많이 재배했다. final에는 fertilizer 7–17, milk12, wheat10–16, wool14–18이 남았다.
- 기대 효과: 많은 crop cycles와 17개 가축으로 시장 한쪽에 덜 의존하는 안정 수익을 낸다. 표본 reward 범위가 102.5k–108.9k로 좁았다.
- 실패모드: 종료 재고가 일관되게 남아 bank metric을 직접 손해 본다. 좁은 reward 범위는 4게임이라는 작은 표본 때문일 수 있다.
- 반증 실험: 마지막 72/48/24턴 별 liquidation planner를 붙인 ablation을 paired seeds로 돌리고, 청산 증가분과 기존 생산 차질을 함께 본다.

### 3.3 직접 맞대결 표본

| episode | seat0 vs seat1 | reward | 해석 한계 |
|---:|---|---:|---|
| 89145303 | Rui vs smlcr | 120,662–114,726 | Rui 승 |
| 89142306 | smlcr vs Rui | 112,956–117,603 | Rui 승 |
| 89138818 | smlcr vs Rui | 115,610–106,787 | smlcr 승; 같은 좌석 배치에서도 결과 반전 |
| 89147298 | smlcr vs Victor | 115,129–106,165 | smlcr 승 |
| 89145796 | Victor vs Raiden | 94,799–120,095 | Raiden 승 |
| 89145290 | Raiden vs Victor | 114,386–66,255 | Raiden 승; seat swap 2게임 모두 Raiden 승 |
| 89133857 | Raiden vs smlcr | 103,462–116,109 | smlcr 승 |
| 89119601 | Rui vs Max | 81,343–51,826 | Rui 승 |
| 89140809 | smlcr vs Danilo | 124,449–107,084 | smlcr 승 |

이건 1–3게임짜리 head-to-head다. 특히 Rui↔smlcr처럼 동일 상대에서도 승패가 바뀌므로 상대전적을 안정적인 우열로 승격하지 않는다.

### 3.4 episode별 action/economy 관측

표기: `ep(s)`는 episode와 seat, rating은 episode 전→후, bank는 `d10/d20/final`, `C/H/L`은 피크 인원/실제 고용/토지 첫날→구역, `A`는 동물 max, `P`는 실제 작물. action hash는 720턴 action JSON SHA256 앞 12자리다. 전체 raw hash는 다음 절에 있다.

| 팀 | ep(s) | rating | reward | action hash | bank d10/d20/final | C/H/L | A | P | final carry |
|---|---|---:|---:|---|---|---|---|---|---|
| Rui | 89119601(0) | 1238.0→1263.6 | 81,343 | 4c65d73016f9 | 4,162/39,211/81,343 | 13/300/10→2 | C8 S8 | C6 M16 S20 | F6 Wl3 |
| Rui | 89138818(1) | 1294.7→1275.4 | 106,787 | 1d3f9548e077 | 4,405/37,782/106,787 | 13/300/10→2 | C8 S8 | C6 M16 S20 | F6 Wl3 |
| Rui | 89142306(1) | 1275.4→1293.5 | 117,603 | bf407b2e20a9 | 4,209/40,976/117,603 | 13/300/10→2 | C8 S8 | C6 M16 S20 | F6 Wl3 |
| Rui | 89143795(0) | 1293.5→1308.7 | 115,085 | 0811a777a58b | 4,191/41,133/115,085 | 13/300/10→2 | C8 S8 | C6 M16 S20 | F6 Wl3 |
| Rui | 89145303(0) | 1308.7→1322.2 | 120,662 | bf407b2e20a9 | 4,345/42,778/120,662 | 13/300/10→2 | C8 S8 | C6 M16 S20 | F6 Wl3 |
| smlcr | 89133857(1) | 1222.4→1243.7 | 116,109 | cc9cefc08a60 | 366/44,129/116,109 | 11/281/7→3 | C7 S2 | C13 M15 S47 W22 | 0 |
| smlcr | 89138818(0) | 1264.3→1286.3 | 115,610 | 898697a88009 | 958/41,599/115,610 | 11/282/6→3 | C6 S3 | C10 M17 S42 W30 | 0 |
| smlcr | 89140809(0) | 1286.3→1302.2 | 124,449 | b1761b7bbf4c | 775/48,589/124,449 | 11/281/7→3 | C7 S2 | C5 M19 S43 W36 | 0 |
| smlcr | 89142306(0) | 1302.2→1283.0 | 112,956 | 73f0e9b30988 | 1,199/40,943/112,956 | 11/282/6→3 | C6 S3 | C10 M13 S39 W54 | 0 |
| smlcr | 89145303(1) | 1283.0→1267.8 | 114,726 | b0455999031b | 1,495/42,985/114,726 | 11/282/6→3 | C6 S3 | C7 M19 S30 T4 W66 | 0 |
| smlcr | 89147298(0) | 1267.8→1283.1 | 115,129 | 39ddf2a4dbe3 | 1,164/46,979/115,129 | 11/282/6→3 | C4 S5 | C3 M13 S50 W31 | 0 |
| Raiden | 89133857(0) | 1203.4→1182.7 | 103,462 | fb146fecd76b | 125/14,668/103,462 | 14/322/11→3 | C5 S8 | M23 S34 T10 W18 | E6 F13 W1 Wl12 |
| Raiden | 89134343(0) | 1182.7→1200.8 | 108,388 | 09fc0a53c4a1 | 70/2,948/108,388 | 14/314/11→3 | C14 S4 | M19 S52 T1 W16 | F14 Mi11 S1 Wl3 |
| Raiden | 89144303(1) | 1236.5→1250.5 | 126,022 | 7200aa0b4d6c | 79/15,380/126,022 | 14/328/11→3 | C10 S8 | M32 S36 T1 W29 | F15 Mi3 W2 Wl15 |
| Raiden | 89145290(0) | 1250.5→1267.3 | 114,386 | 0dfc51cfc351 | 50/22,585/114,386 | 14/328/11→3 | C7 S11 | M20 S18 T33 W26 | F12 Mi6 W3 Wl8 |
| Raiden | 89145796(1) | 1267.3→1281.2 | 120,095 | 143957a2632c | 28/18,089/120,095 | 14/324/11→3 | C8 S10 | M23 S32 T12 W18 | F14 M5 W1 Wl16 |
| Victor | 89145290(1) | 1260.1→1237.4 | 66,255 | 4b6a7e4bba6a | 161/601/66,255 | 15/318/0→4 | C15 S5 | C13 M29 S9 | 0 |
| Victor | 89145796(0) | 1237.4→1218.9 | 94,799 | 5e914cc7608d | 161/8,154/94,799 | 15/320/0→4 | C15 S5 | C13 M39 S9 | 0 |
| Victor | 89146796(1) | 1234.5→1251.6 | 165,388 | bf2c7da91d83 | 161/19,986/165,388 | 15/335/0→4 | C15 S5 | C13 M40 S61 | 0 |
| Victor | 89147287(0) | 1251.6→1261.4 | 154,704 | 4559b4a25620 | 161/23,478/154,704 | 15/333/0→4 | C10 S10 | C13 M40 S60 | 0 |
| Victor | 89147298(1) | 1261.4→1245.4 | 106,165 | dceda004ca7f | 116/13,593/106,165 | 15/315/0→4 | C15 S5 | C13 M40 S13 | 0 |
| Victor | 89151337(1) | 1245.4→1256.3 | 154,364 | 9d1c8bc54fdd | 143/16,416/154,364 | 15/327/0→4 | C15 S5 | C13 M40 S53 | F16 |
| Max | 89075437(0) | 1271.5→1284.6 | 96,309 | 93f3a0d00976 | 137/23,225/96,309 | 13/238/10→2 | C12 S16 | C14 M30 W27 | COW6 |
| Max | 89076404(1) | 1256.7→1269.4 | 97,520 | 2b19b4be2c5d | 543/26,602/97,520 | 13/238/10→2 | C22 S6 | C14 M30 W21 | 0 |
| Max | 89089846(0) | 1284.2→1297.1 | 29,357 | 1979116c84ee | 128/15,580/29,357 | 13/238/10→2 | C12 S16 | C14 M29 W26 | COW6 |
| Max | 89119601(1) | 1297.1→1277.7 | 51,826 | d28db572f0c0 | 570/23,834/51,826 | 13/238/10→2 | C22 S6 | C14 M30 W21 | 0 |
| Max | 89142305(1) | 1277.7→1253.9 | 60,906 | aeab11b6a3db | 339/15,476/60,906 | 13/238/10→2 | C22 S6 | C14 M31 W24 | 0 |
| Danilo | 89113213(1) | 1169.0→1180.1 | 104,226 | f5ce72d53615 | 118/23,209/104,226 | 13/325/11→3 | C9 S8 | C49 M21 S16 T5 W78 | F7 Mi12 W10 Wl14 |
| Danilo | 89123989(0) | 1226.0→1239.3 | 108,889 | e41c75290976 | 138/20,942/108,889 | 13/324/11→3 | C9 S8 | C48 M21 S16 T5 W80 | F17 Mi12 W14 Wl17 |
| Danilo | 89140809(1) | 1239.3→1227.2 | 107,084 | dbbd5a98e876 | 127/24,256/107,084 | 13/324/11→3 | C9 S8 | C48 M21 S16 T5 W71 | F17 Mi12 W11 Wl18 |
| Danilo | 89147303(0) | 1215.4→1227.4 | 102,526 | 9008f4cc1a85 | 122/16,711/102,526 | 13/324/11→3 | C9 S8 | C49 M21 S16 T5 W80 | F9 Mi12 W16 Wl15 |

약어: C=carrot 또는 cow(열 문맥), M=melon, S=strawberry 또는 sheep, T=tomato, W=wheat, F=fertilizer, Mi=milk, Wl=wool, E=egg.

### 3.5 raw episode source manifest

모두 Kaggle 공식 public episode payload다. `configuration.seed`는 scrub되어 `None`이고, 원 seed는 raw JSON의 `info.seed`에서 읽었다. hash는 내려받은 JSON bytes의 SHA256다.

| episode / raw URL | seed | 종료 UTC | 회수 UTC | bytes | SHA256 | 팀 |
|---|---:|---|---|---:|---|---|
| [89075437](https://www.kaggleusercontent.com/episodes/89075437.json) | 281981887 | 03:26:02 | 14:14:29 | 25,362,192 | `beb4fe5cbde354014faa131a32179d93c23ef315b71e77eb4488f9588a86304e` | Max vs Raiden |
| [89076404](https://www.kaggleusercontent.com/episodes/89076404.json) | 415365662 | 03:34:15 | 14:14:28 | 23,446,279 | `e26d4ce3e539102db5c6689bb5f1db6caae7f7858b08b91035db747f3a5ccf8b` | Danilo vs Max |
| [89089846](https://www.kaggleusercontent.com/episodes/89089846.json) | 468802595 | 05:26:17 | 14:14:27 | 23,508,223 | `1aa2b15d1c7af2528f5fa5e0aee96628418e7d7c309a9fd492076763643873fd` | Max vs Victor |
| [89113213](https://www.kaggleusercontent.com/episodes/89113213.json) | 210057754 | 08:37:46 | 14:14:30 | 24,596,125 | `e2cea22c8554a7e3229a59d1582f652b8b205c2d56876be3e422e6fdb192d7f7` | Howon vs Danilo |
| [89119601](https://www.kaggleusercontent.com/episodes/89119601.json) | 988212155 | 09:29:52 | 14:14:25 | 19,882,722 | `a27e6041d51452ebcc57c2da88d38e059a9137a663279e8246d5439d33006600` | Rui vs Max |
| [89123989](https://www.kaggleusercontent.com/episodes/89123989.json) | 1972514372 | 10:06:10 | 14:14:31 | 26,236,346 | `44190d921486a341b34fb2d02aa377c67adaa57cd26f7c47014a645a00a4a0bf` | Danilo vs smlcr |
| [89133857](https://www.kaggleusercontent.com/episodes/89133857.json) | 1407839729 | 11:26:22 | 14:14:25 | 26,427,994 | `ccfb39ad6daef967c8e5487822b176d0792828b790582eed65432af84c55c183` | Raiden vs smlcr |
| [89134343](https://www.kaggleusercontent.com/episodes/89134343.json) | 1714520255 | 11:30:27 | 14:14:32 | 23,968,411 | `97ab30979f444fa1df01a750b4d4b091568263f9527bed84d0c463bc12e6cca7` | Raiden vs ayutin |
| [89138818](https://www.kaggleusercontent.com/episodes/89138818.json) | 1519608725 | 12:06:15 | 14:14:21 | 22,068,371 | `fa25ea7747ffb08427e10165d9d1d032ab3b9c7fdd9183a7804af180e7c9e19f` | smlcr vs Rui |
| [89140809](https://www.kaggleusercontent.com/episodes/89140809.json) | 1588005946 | 12:22:03 | 14:14:26 | 26,528,953 | `b248d00f91d72dc1067675dd1a4038c23384baea111f042d23869c1c09ca21ea` | smlcr vs Danilo |
| [89142305](https://www.kaggleusercontent.com/episodes/89142305.json) | 414385762 | 12:34:16 | 14:14:35 | 19,784,706 | `bd5f51ef021c1312dffdb63337be428a1e04064fbcc9d91c9df674938d0b01e2` | ayutin vs Max |
| [89142306](https://www.kaggleusercontent.com/episodes/89142306.json) | 1652737459 | 12:34:03 | 14:14:21 | 22,093,215 | `ff0e552b1762ae12924b0a66fa737fffe1fb66dd229628063e7a24daac6018bd` | smlcr vs Rui |
| [89143795](https://www.kaggleusercontent.com/episodes/89143795.json) | 728836876 | 12:46:29 | 14:14:34 | 21,861,236 | `a9de6d8fbf0c093ac7b0c9db377378d9ab2004fc0bf2c29ad5584d0a8ab65bc1` | Rui vs smlcr(old sub) |
| [89144303](https://www.kaggleusercontent.com/episodes/89144303.json) | 384546671 | 12:50:01 | 14:14:32 | 26,000,816 | `45e09430cadd8dd892e602160712ac3ab2ae56792857ae659af393c1b86c31f6` | Avikumar vs Raiden |
| [89145290](https://www.kaggleusercontent.com/episodes/89145290.json) | 84868333 | 12:58:06 | 14:14:25 | 22,019,772 | `513eaabcd1ca470eebeb22cd5058977c0d8c3aef111a608036804eee76acb10e` | Raiden vs Victor |
| [89145303](https://www.kaggleusercontent.com/episodes/89145303.json) | 585247399 | 12:58:11 | 14:14:21 | 21,984,911 | `389209be7727758193c294fed9c4a756bb8064a3c4614cd307fbeffd0eb44386` | Rui vs smlcr |
| [89145796](https://www.kaggleusercontent.com/episodes/89145796.json) | 799057898 | 13:02:03 | 14:14:23 | 23,659,684 | `120946631a4111aaab032181ef1de1cbdf1999c261bdbc93dc6e7d63b0e9c217` | Victor vs Raiden |
| [89146796](https://www.kaggleusercontent.com/episodes/89146796.json) | 1070739682 | 13:10:17 | 14:14:34 | 27,198,664 | `b28ff1cb4a013528af1c50013b1b8e44411e7dde21581a55fa5d8cfb65451eb4` | Max(new sub) vs Victor |
| [89147287](https://www.kaggleusercontent.com/episodes/89147287.json) | 317957257 | 13:14:09 | 14:14:32 | 27,720,339 | `e76dd790c54c76ddef8e18d786434a3ec200821f16f8f7c3197c2f966a660e34` | Victor vs yw8837 |
| [89147298](https://www.kaggleusercontent.com/episodes/89147298.json) | 1384913829 | 13:14:20 | 14:14:21 | 24,013,914 | `dfa56fedffaac3e935eac39f28ce9ac76fb896072678865c081da3853f6df629` | smlcr vs Victor |
| [89147303](https://www.kaggleusercontent.com/episodes/89147303.json) | 1891174512 | 13:14:01 | 14:14:29 | 23,338,361 | `eb85ebd390fd326a0851b19d8a355bfd7b31cdeab13d9cd4760f454d0fc99972` | Danilo vs RuleCraft |
| [89151337](https://www.kaggleusercontent.com/episodes/89151337.json) | 2106003461 | 13:46:33 | 14:14:35 | 26,891,115 | `be36673c016291a84b7faa23b9c3e4c37dd44a3c58606517c4c65d1e097fb05c` | Lucien vs Victor |

## 4. Kaggle 공개 Code 전수 목록(현재 검색 결과 14개)

공식 CLI `kaggle kernels list --competition kaggriculture --page-size 20 --sort-by dateCreated --format json` 결과가 14개였고, 각 notebook source를 읽기 전용 API로 받아 hash했다. 이는 2026-07-31 접근 시점의 공개 검색 결과이지 삭제·비공개·검색 누락 notebook까지 포함한 역사적 전수는 아니다.

| ref / URL | votes | version | notebook source SHA12 | code SHA12 | 판정 |
|---|---:|---:|---|---|---|
| [prvsiyan/kaggriculture-frontier-lab-high-score-visuals](https://www.kaggle.com/code/prvsiyan/kaggriculture-frontier-lab-high-score-visuals) | 0 | 3 | `6d1466929ee6` | `2a7414832130` | retained: board-adaptive 가축 route 후보 |
| [guruprasaathas111/kagriculture-gudiebook](https://www.kaggle.com/code/guruprasaathas111/kagriculture-gudiebook) | 1 | 1 | `eaa6d5127c38` | `56ca48006284` | retained family: landrush 계열, 런타임 의존성 위험 |
| [pilkwang/kaggriculture-scenario-aware-economic-policy](https://www.kaggle.com/code/pilkwang/kaggriculture-scenario-aware-economic-policy) | 7 | 6 | `51ff56aecc79` | `f86d3b8fa848` | retained: 가장 상세한 failure ledger |
| [romantamrazov/kaggriculture-hamburger](https://www.kaggle.com/code/romantamrazov/kaggriculture-hamburger) | 17 | 6 | `d4abc5993751` | `9e1fecbc3c53` | retained: 환경 이중모델/probe |
| [romanrozen/strong-statr-baseline-agent-lb-950](https://www.kaggle.com/code/romanrozen/strong-statr-baseline-agent-lb-950) | 11 | 1 | `b526f8419207` | `82f9706efb02` | retained: value-per-action + 시장곡선 |
| [chaitanyajamble/kaggriculture](https://www.kaggle.com/code/chaitanyajamble/kaggriculture) | 6 | 4 | `d347fa804ea0` | `449883cbc959` | retained family: guidebook와 높은 코드 중첩 |
| [pavloivanin/kaggriculture-baseline](https://www.kaggle.com/code/pavloivanin/kaggriculture-baseline) | 6 | 4 | `3335ea70f53c` | `398908d27e0a` | retained family: Harvest Pulse와 높은 중첩 |
| [mpwolke/doomed-kaggleculture-harvest](https://www.kaggle.com/code/mpwolke/doomed-kaggleculture-harvest) | 9 | 2 | `2ca5d7902a21` | `d7ea547dafd5` | screened negative: 약한 starter/tutorial |
| [georgymamarin/kaggriculture-daily-replays-the-live-meta-report](https://www.kaggle.com/code/georgymamarin/kaggriculture-daily-replays-the-live-meta-report) | 3 | 12 | `2c21c6b84fb9` | `e7d52bc1b2bd` | retained: replay 관측 보고서 |
| [georgymamarin/kaggriculture-visualized-what-every-crop-pays](https://www.kaggle.com/code/georgymamarin/kaggriculture-visualized-what-every-crop-pays) | 8 | 9 | `5ce7fa729305` | `85ba186cfde4` | retained: 시장/작물 시각화, 정책은 아님 |
| [alexandergremyakov/harvest-pulse-adaptive-landrush-baseline](https://www.kaggle.com/code/alexandergremyakov/harvest-pulse-adaptive-landrush-baseline) | 17 | 1 | `0b49296181ab` | `58094dc18fce` | retained family: Pavlo 계열 |
| [dheerajkannaujiya/start-with-basic-simple](https://www.kaggle.com/code/dheerajkannaujiya/start-with-basic-simple) | 9 | 2 | `df639821db39` | `09127b79860c` | screened baseline: 단일 farmer grid scan |
| [ektarr/diversified-scheduler-baseline-kaggriculture](https://www.kaggle.com/code/ektarr/diversified-scheduler-baseline-kaggriculture) | 14 | 1 | `e1b4928471f2` | `831264908786` | retained: static diversification 비교군 |
| [bovard/kaggriculture-getting-started](https://www.kaggle.com/code/bovard/kaggriculture-getting-started) | 21 | 4 | `adcdc666cfc6` | `4b35047a1e97` | retained baseline: 공식 host tutorial |

7-token code shingle Jaccard로 본 큰 중첩은 guidebook↔chaitanya `0.600`, pavlo↔Harvest Pulse `0.518`이었다. 구현 계보 가능성은 높지만 Kaggle의 공식 “fork” 관계를 증명하지는 않는다.

### 4.1 retained Code source cards

#### K-1 Barnyard Economist / `strong-statr-baseline-agent-lb-950`

- 권위: B(공개 코드), notebook의 성능 숫자는 C. 접근일 2026-07-31.
- 정확한 메커니즘: tile별 value-per-action layout, `가치 - 거리` 기반 greedy 작업 배정, 엔진과 같은 piecewise market curve, reservation price, sell scheduling. CARE bonus를 `+1`로 계산해 현재 코드와 맞는다.
- 저자 보고 기대 효과: public melon loop보다 평균 bank `47,300 vs 25,700`, 6 seeds 6승; 4 seeds seat1 `47,112 vs 25,723`; self-play 약 `35,041/34,959`; 약 1 ms. 이번 조사에서는 재실행하지 않았다.
- 실패모드: 상대/public tile 무시, town shop 무시, reservation 고정, fertilizer는 팔지만 사용 안 함, one-turn greedy, melon 동시 수확·shed 병목.
- 반증 실험: 공식 핀 엔진에서 최소 30 holdout seeds × 양 좌석 × 4 상대군. 동일 market calculator를 엔진 quote와 property test하고, reservation/town/opponent-aware ablation의 lower-decile bank를 본다.

#### K-2 Scenario-Aware Economic Policy

- 권위: B/C. 코드와 실험 설계는 공개됐지만 결과는 notebook 내부 산출물이다.
- 정확한 메커니즘: terminal bank만 목적, phase/horizon별 feed floor, bounded melon + 수요형 specialty crop + geese, 전역 value-distance matching, market/town/opponent supply 관측, terminal conversion.
- 저자 보고 기대 효과: seeds 217/317/733 양 좌석 starter 상대; reference seeds 3000–3003 양 좌석에서 Barnyard `8-0`, 평균 `45,504 vs 27,588`; FarmBurger `58,186/36,067`; Adaptive Landrush `53,664/20,545`; Diversified `50,780/19,560`. seed1009 holdout도 적었다. 이번 조사 미재현.
- 실패모드: rival harvest 지연, goose 11 cap, `planted_day=0` truthiness bug, greedy blocking, Manhattan 우회 무시, 1-day market forecast, inventory-0 sentinel, fertilizer 미사용, order-dependent DROP, sale cash discount, silent PASS fallback.
- 반증 실험: notebook이 적은 seed를 그대로 재실행한 뒤 완전 분리 holdout 50 seeds를 추가한다. 각 known bug를 하나씩 고친 ablation과 invalid/no-op/action latency를 함께 기록한다.

#### K-3 Hamburger

- 권위: B/C.
- 정확한 메커니즘: fertilizer 판매를 허용하는 exact model과 거부하는 conservative model을 동시에 두고, 1회 fertilizer sell probe로 환경을 판별한다. robust score는 두 모델 결과의 최솟값을 사용한다.
- 저자 보고 기대 효과: conservative에서 10 cows/11 hands가 예비 최적, permissive 11 cows는 100k 이상 가능, 12 cows는 care/feed 압박. 이번 조사 미재현.
- 실패모드: 현재 공식 코드는 `SELL FERTILIZER`를 허용한다. conservative branch가 필요한 현상은 엔진 차이보다 로그·submission packaging 문제일 수 있고, probe 자체가 돈/주문 슬롯을 쓴다.
- 반증 실험: official local env와 Kaggle raw replay에서 동일 probe의 inventory/price/cash delta를 비교한다. exact-only, dual-probe, conservative-only를 paired seeds로 돌려 probe cost와 오판율을 분리한다.

#### K-4 Frontier Lab

- 권위: B/C.
- 정확한 메커니즘: 공개 board를 읽고 cow route와 sheep counter route를 선택하는 opponent/board-adaptive 가축 전략, 공식 local env 1.32.2 cross-play를 주장한다.
- 기대 효과: 상대가 만든 시장 공급에 따라 동물 포트폴리오를 바꾼다.
- 실패모드: 추출된 notebook markdown에 cross-play 숫자가 없어 효과 크기를 검증할 수 없고, board signal과 market cause가 섞일 수 있다.
- 반증 실험: 동일 seed/동일 board에서 상대 action만 counterfactual replay하는 건 불가능하므로, 통제된 supply-bot 3종과 paired seeds를 사용한다. route 선택 로그와 사전 정의 threshold를 저장한다.

#### K-5 Diversified Scheduler

- 권위: B.
- 정확한 메커니즘: 초기 5×5를 대략 melon 60%, carrot 12%, wheat 12%, tomato 8%, 나머지 strawberry로 채우고 7 hands, unique greedy task, shed sell, day29 liquidation을 쓴다.
- 기대 효과: melon-only보다 가격 포화와 단일 수확 실패를 줄이는 정적 비교군이다.
- 실패모드: 가격/상대/phase에 따라 배치를 바꾸지 않고, greedy assignment와 day29 일괄청산이 병목을 만든다.
- 반증 실험: 동일 scheduler에서 crop mix만 고정/market-aware로 바꿔 30 seeds 양 좌석 비교. final carry와 각 crop의 realized unit price를 본다.

#### K-6 Landrush family

- 출처: [guidebook](https://www.kaggle.com/code/guruprasaathas111/kagriculture-gudiebook), [chaitanya](https://www.kaggle.com/code/chaitanyajamble/kaggriculture), [Pavlo baseline](https://www.kaggle.com/code/pavloivanin/kaggriculture-baseline), [Harvest Pulse](https://www.kaggle.com/code/alexandergremyakov/harvest-pulse-adaptive-landrush-baseline). 권위 B.
- 정확한 메커니즘: guidebook/chaitanya는 13 melon, 4 carrot, 4 wheat, 2 tomato, 2 strawberry, 7 hands, day11 NE land+15 wheat, 거리/priority greedy, product별 sell throttle, day29 청산. Pavlo/Harvest Pulse도 13/4/4/2/2, 7 hands, day11 landrush, melon sell cap, final liquidation 골격이 매우 비슷하다.
- 기대 효과: 단순하고 제출 가능한 고정 확장 baseline.
- 실패모드: 시장·상대 적응이 약하고 토지/가축/인력 규모가 현재 상위 리플레이보다 작다. guidebook submission은 `numpy/pandas/kagglehub`를 import해 제출 runtime 의존성 위험이 있다. notebook 설명의 “adaptive”보다 실제 code overlap이 크다.
- 반증 실험: source를 독립 submission zip으로 검증하고, 20 paired seeds에서 동일 family 간 action trace/hash·reward를 비교한다. import 없는 chaitanya 변형을 packaging control로 둔다.

#### K-7 Replay reports / crop visualization

- 출처: [Daily Replays report](https://www.kaggle.com/code/georgymamarin/kaggriculture-daily-replays-the-live-meta-report), [What Every Crop Pays](https://www.kaggle.com/code/georgymamarin/kaggriculture-visualized-what-every-crop-pays). 권위 B, 전략 성능 증거는 아님.
- 정확한 메커니즘: public episode crawl을 feature table로 바꾸고 rating/은행/작물/인력 패턴과 시장 수익을 시각화한다.
- 기대 효과: 후보 전략 생성과 drift 감지.
- 실패모드: submission당 best game 중심 peak sketch, crawl은 census가 아니고 최신 submission 지연, 적은 h2h, validation 제외, 상관을 인과처럼 읽기 쉽다.
- 반증 실험: daily official index의 episode id와 coverage를 대조하고, 팀/시드 cluster bootstrap과 시간 분할 holdout으로 집계 안정성을 검증한다.

#### K-8 Getting Started

- 권위: B(competition host tutorial).
- 정확한 메커니즘: melon-maxxer형 최소 동작 agent와 submission 형식을 설명한다.
- 기대 효과: API/행동 형식 sanity baseline.
- 실패모드: 현재 상위권의 가축·토지·시장/상대 적응을 다루지 않는다. 높은 votes를 경쟁력으로 해석하면 안 된다.
- 반증 실험: 모든 후보가 starter를 안정적으로 이기는지 packaging smoke와 짧은 regression 상대군으로만 사용한다.

## 5. Kaggle Discussions와 Datasets

### 5.1 Discussion 검색 결과 3개

`kaggle competitions topics list kaggriculture --sort-by new --format json` 결과가 3개였다. 본문은 `topic-messages` 공식 CLI로 읽었다.

#### D-1 Daily Top Episodes Dataset

- URL: <https://www.kaggle.com/competitions/kaggriculture/discussion/731215>, 권위 A(competition host 공지).
- 정확한 메커니즘: 매일 agent 평균 rating 순으로 episode를 모아 최대 20GB 공개하고, imitation/behavior cloning/RL/statistics용 dataset/index로 배포한다.
- 기대 효과: 상위권 정책의 상태-행동 분포를 직접 학습/분석한다.
- 실패모드: top-rating sampling이라 exploration과 하위권 실패가 과소대표되고, 하루 snapshot이 빠른 meta drift를 놓친다.
- 반증 실험: 날짜별·rating decile별 holdout, 팀 중복 제거 split, policy clone의 unseen-team/unseen-date 성능을 본다.

#### D-2 Seat swap thread

- URL: <https://www.kaggle.com/competitions/kaggriculture/discussion/731152>, 권위 D.
- 정확한 관찰 주장: 한 사용자가 6 seeds 양 좌석 starter 실험에서 bot bank는 같고, market quote는 seat 선점 효과가 없으며, weeds RNG draw 순서로 board는 달라지고 seed replay는 deterministic하다고 보고했다.
- 기대 효과: paired-seat 평가 설계와 market 처리 순서 가설을 만든다.
- 실패모드: 작은 표본·커뮤니티 일화다. code를 읽지 않는 bot의 bank 동률을 일반 정책의 seat invariance로 확대할 수 없다.
- 반증 실험: 공식 엔진에서 100 seeds 양 좌석, state/action/market quote/weed spawn hash를 저장한다. player order만 바꾸고 precommit market inventory가 같은지 단위 테스트한다.

#### D-3 Getting started + Discord

- URL: <https://www.kaggle.com/competitions/kaggriculture/discussion/730708>, 권위 A(competition host).
- 메커니즘/효과: 공식 시작 자료와 public Discord 경로를 제공한다.
- 실패모드: Discord는 공식적으로 지속 모니터되지 않으며 전략 주장의 영속성·검색성이 낮다.
- 반증/운영: 중요한 규칙 질문은 forum/공식 source로 재확인하고 Discord 단독 주장은 채택하지 않는다.

### 5.2 Dataset 검색 결과

`kaggle datasets list -s kaggriculture --page-size 20 --sort-by updated --format json`은 3개, 오타 `kagriculture` 검색은 0개였다.

| dataset / URL | snapshot 사실 | 권위·용도 |
|---|---|---|
| [georgymamarin/kaggriculture-episodes](https://www.kaggle.com/datasets/georgymamarin/kaggriculture-episodes) | 98,790,567 bytes, downloads 74, votes 12, usability 1.0, updated 09:37:35 UTC | B; public replay crawl + features |
| [kaggle/kaggriculture-episodes-index](https://www.kaggle.com/datasets/kaggle/kaggriculture-episodes-index) | index CSV 317 bytes | A; 날짜→공식 daily dataset 라우팅 |
| [kaggle/kaggriculture-episodes-2026-07-30](https://www.kaggle.com/datasets/kaggle/kaggriculture-episodes-2026-07-30) | catalog compressed size 314,465,842 bytes | A; 2026-07-30 raw episodes |

#### DS-1 공식 daily index

- 권위: A. index row는 `episode_count=864`, raw `total_bytes=13,639,221,377`, `top_avg_score=1152.418623`, `median_avg_score=669.750471`를 기록한다.
- 정확한 메커니즘/기대 효과: 날짜별 immutable-ish raw episode bundle로 재현 가능한 replay corpus를 만든다.
- 실패모드: 하루 단위 top sampling, catalog 압축 크기와 raw total bytes가 달라 저장비 추정 오류가 생길 수 있다.
- 반증 실험: index id count와 dataset file pagination count, 각 JSON hash/episode id, 재다운로드 hash를 대조한다.

#### DS-2 Georgy replay dataset

- 권위: B. files는 `agents.csv`, `episodes.csv`, `episode_features.csv`, `replays.parquet`, `teams.csv`, scraper/feature code 등이다.
- 직접 분석한 snapshot: episodes 1,285 = public 1,196 + validation 89, submissions 255, teams 95, feature rows 2,570. 시간 범위 2026-07-30 17:10:38Z–2026-07-31 05:20:46Z.
- rating≥1100 관측행 116(10 teams/14 subs): final money 중앙 85,996.5, peak crew 12, 실제 hires feature 261, first land day 10, planted tiles 76.5. plant share C17.0/M26.1/S13.4/T3.6/W39.9%.
- rating 700–900 관측행 696: final 35,400.5, crew 8, hires 203, first land 10, tiles 129, share C27.6/M21.9/S6.5/T4.0/W40.0%.
- 기대 효과: 상위권이 더 많은 crew·hires와 더 적은 planted tiles를 쓰는 후보 가설을 준다.
- 실패모드: 관측 상관, 반복 팀/게임, feature의 plant count는 동물을 담지 않음, `elbow` 같은 파생값은 final value와 기계적으로 연결된다. Spearman crew .686/hires .704를 인과 효과로 읽으면 안 된다.
- 반증 실험: 팀 단위 split·시간 holdout·submission cluster bootstrap 후, 실제 정책 ablation으로 crew/land/animal 각각의 인과를 검증한다.

## 6. 공식 엔진 소스와 규칙 변경

### E-1 current official engine

- URL: [kaggriculture.py @ pinned commit](https://github.com/Kaggle/kaggle-environments/blob/4f6e2763e2232605aacbade443715a9e2c9ef401/kaggle_environments/envs/kaggriculture/kaggriculture.py)
- 권위: A. 로컬 핀 commit `4f6e2763e2232605aacbade443715a9e2c9ef401`, worktree clean을 확인했다.
- 파일 증거: `kaggriculture.py` 39,523 bytes, SHA256 `b6da1554674c03931ef03d3499d035d7e10894047faecd3a8bcc471127734e5d`; README 22,262 bytes, SHA256 `74b6bce7be801f0f09a843516b8f8f5909c508ae5e2f24dd8c84233da94cce24`.
- 정확한 메커니즘:
  - 양 player의 market order는 같은 precommit inventory를 기준으로 unit quote를 계산한 뒤 commit된다. 먼저 처리된 seat가 같은 턴의 더 좋은 첫 가격을 독점하지 않는다.
  - HIRE/BUY_LAND는 player order로 atomic 처리되고, market orders는 턴당 최대 10개다.
  - SELL price는 $1 floor를 가지며 floor sale은 더 이상 유효 supply를 밀지 않는다.
  - `BUY_PRODUCT`는 wheat/fertilizer만 허용되고, buy→sell round-trip은 무차익으로 설계됐다.
  - 동물 pasture는 매일 `fertilizer_available=True`로 갱신돼 매일 수집 가능하다.
  - seed는 agent observation에서 숨기지만 replay `info.seed`에 보존된다.
- 기대 효과: 전략·simulator·replay parser의 유일한 규칙 기준점이다.
- 실패모드: 아래 CARE처럼 README/commit 설명과 실행 코드가 어긋날 수 있다. Kaggle service의 실제 deployed version이 로컬 핀과 달라질 가능성도 별도 검증해야 한다.
- 반증 실험: 주요 transition을 one-step golden test로 만들고 raw replay 한 게임의 state delta와 local env를 seed/action replay해 hash 비교한다.

### E-2 CARE 보너스 충돌

- 코드 원문 위치: `kaggriculture.py:799`는 fed+cared day에 `pending_care_bonus + 1`.
- README 원문 위치: line 69는 같은 상황을 `+2`라고 설명한다.
- 변경 이력: [commit 8317e5f](https://github.com/Kaggle/kaggle-environments/commit/8317e5f7d038c7fad92dc1b2e1ddb3236bb95cc5)는 `+2`로 상향했다고 적지만 current code는 `+1`이다.
- 기대 영향: care ROI, cow/sheep 수, worker allocation을 두 배 가까이 오판할 수 있다.
- 실패모드: 문서/PR 제목만 보고 수익 모델을 만들면 backtest와 실제 engine이 갈린다.
- 반증 실험: pasture 1개를 여러 날 feed+care하고 production tick 전후 `pending_care_bonus/yield_units`를 local env와 raw replay에서 측정한다. 결과가 current code와 다르면 deployed parity 이슈로 격상한다.

### E-3 전략에 직접 영향 주는 공식 변경 이력

| commit / PR | 날짜 UTC | 변경 | 검증 포인트 |
|---|---|---|---|
| [2819d493 / #1364](https://github.com/Kaggle/kaggle-environments/pull/1364) | 07-24 | stale animal 가격/비용 문서 수정 | 문서도 다시 stale할 수 있음 |
| [abfc0e58 / #1242](https://github.com/Kaggle/kaggle-environments/commit/abfc0e58bc3b836ee00a41dfb8b60d95d698a6e1) | 06-12 | hidden seed resolver, replay에 seed 보존 | paired replay 재현 |
| [8452d21e / #1199](https://github.com/Kaggle/kaggle-environments/pull/1199) | 06-02 | premium glut crash slope ×4, cow cost 400 | melon/milk/wool 대량판매 리스크 |
| [4245df40 / #1145](https://github.com/Kaggle/kaggle-environments/commit/4245df40e536648e45b5c8448577341402a58ed6) | 05-21 | 시작금 3000, town 느리게, hire mult 1 | 구 baseline 수치 폐기 |
| [1e140565 / #1142](https://github.com/Kaggle/kaggle-environments/pull/1142) | 05-21 | DROP 추가 | day30/terminal carry |
| [1aaf9aa4 / #1135](https://github.com/Kaggle/kaggle-environments/pull/1135) | 05-20 | wheat/fertilizer만 buy, no-arbitrage | market model |
| [fdda4705 / #1112](https://github.com/Kaggle/kaggle-environments/pull/1112) | 05-19 | Fibonacci hire cost | crew target/일별 재고용 |
| [958c9eaa / #1108](https://github.com/Kaggle/kaggle-environments/pull/1108) | 05-18 | resource별 piecewise market shape | exact price calculator |
| [6bd846e8 / #1092](https://github.com/Kaggle/kaggle-environments/commit/6bd846e84b14168a0124ac3d242124b87c0c7820) | 05-12 | market order cap 10 등 | 반복 주문 손실 |

공식 저장소에서 Kaggriculture 관련 현재 open Issue는 검색되지 않았다. 검색된 관련 항목은 위 PR들과 과거 closed fix 위주였다. “issue가 없다”는 버그가 없다는 뜻이 아니다. CARE 문서 충돌처럼 source audit가 여전히 필요하다.

## 7. GitHub 구현·fork·commit·issue 조사

`gh search repos kaggriculture --limit 100`은 인증된 환경에서 19 hits(공개 18 + 이 프로젝트의 비공개 1)를 돌려줬다. exact-name 구현 검색에서 `isFork=true`로 표시된 공개 repo는 없었고, 아래 주요 repo의 fork count는 검색 시 0이었다. `niits/kaggriculture`의 forks endpoint도 비어 있었다. 이건 GitHub 전체의 역사적 fork 부재를 증명하지 않고, 현재 검색에서 발견하지 못했다는 뜻이다.

| repo | latest commit (UTC) | 구현/검증 상태 | issues/PRs 판정 |
|---|---|---|---|
| [niits/kaggriculture](https://github.com/niits/kaggriculture) | `3c89b816e634653fcde40918edae5f65ff356f84` 07-31 09:16 | 7 agents + 140-match benchmark | 발견된 open issue/PR 없음 |
| [rooklift/krobus](https://github.com/rooklift/krobus) | `35d889f0670ac288dc6172eb491716f127402852` 07-31 14:12 | Electron replay viewer | 전략 성능 검증 없음 |
| [sota1111/kaggriculture-claude](https://github.com/sota1111/kaggriculture-claude) | `39d46d3cad48451d6a3ad28ae058bee299308902` 07-31 07:57 | 단순 wheat agent + packaging CI | gameplay test 없음 |
| [sota1111/kaggriculture-gpt](https://github.com/sota1111/kaggriculture-gpt) | `4f6e594ad2377820dfcca5bc6c58aa3d4edbb6c3` 07-31 07:57 | 위와 동일 계열 | gameplay test 없음 |
| [jcdumlao14/Kaggriculture-AI-Agent](https://github.com/jcdumlao14/Kaggriculture-AI-Agent) | `ef2442a7ea4c5e82177f79305cfbb2bc9a4098fc` 07-31 09:15 | modular planner, pathfinding | 제출 packaging/성과 미검증 |
| [yuki-a4/kaggriculture](https://github.com/yuki-a4/kaggriculture) | `6b41e6341f05f78091a28246ccca7475c51ee112` 07-31 13:52 | docs/scaffold 중심 | agent source 근거 부족 |
| [liamnewsam/kaggriculture_competition](https://github.com/liamnewsam/kaggriculture_competition) | `53a046829adba09e6642be64f93a33c9733eb2da` 07-30 22:16 | `main.py` 0 bytes | 제외 |
| [ShaunTheKing/kaggriculture-tools](https://github.com/ShaunTheKing/kaggriculture-tools) | empty repo | 코드 없음 | 제외 |

### G-1 niits benchmark suite

- 권위: B, 로컬 commit과 산출물은 A 수준 실행 증거. 접근일 2026-07-31.
- 증거 hash: `agent_summary.csv` SHA256 `5f6623929b27ccfeb06eab3d91e64902002771f170241f424d7519fd8b6c099d`; `episodes.csv` `d12fef29867143cf2c7ec3f40c1545e5823a4ec157e4080594c16cafe9a11085`; `system_performance.json` `cfff9edc2f916baf01bd925cb48bbdf4659c77204761ccc1c270dd142d46b915`.
- 정확한 메커니즘: wheat_only/roi_crop/market_tracker/many_hands/animal_heavy/balanced/pro_tier 7종, seeds 10000–10004, 720 steps, unique pairing을 round parity로 좌석 교대. many_hands는 tomato 25/hands5, animal_heavy는 goose/cow/sheep과 hands3, 공통 market tracker는 scarcity와 reservation을 쓴다.
- 실행 결과: 140 matches, 100,800 env steps, 642.54 s, decision mean 0.134 ms/p95 0.372 ms. competition 30 games/agent에서 many_hands와 pro_tier win rate 0.667, animal_heavy 0.567. 평균 reward는 many_hands 1,815.23, animal_heavy 1,353.97, pro_tier 1,323.83.
- 기대 효과: 빠른 회귀 suite와 전략 archetype 비교.
- 실패모드: 5 seeds, 내부 상대군, 5 rounds라 seat가 3/2로 완전 균형이 아니고 holdout이 없다. `net worth proxy`는 terminal bank metric이 아니며 reward 규모도 현재 public top replay와 멀다.
- 반증 실험: official top-replay-derived opponent를 추가하고 50 train/50 holdout paired seeds, 완전한 seat swap, terminal bank를 primary로 다시 돌린다.

### G-2 krobus replay viewer

- 권위: B(도구 코드), 전략 성능 증거 아님.
- 정확한 메커니즘: raw replay의 seat0 shared state와 seat별 private state를 합쳐 money, tiles, units, prices, equilibrium, town shops, market actions, shed/seeds/inventory를 표시한다.
- 기대 효과: 정책 실패를 turn-level로 눈으로 찾고 raw schema drift를 탐지한다.
- 실패모드: 빠른 UI 커밋 대비 parser test/parity 증거가 없고, 잘못된 seat/private merge가 그럴듯한 오진을 만든다.
- 반증 실험: 이 문서의 22 raw hash를 fixture로 두고, parser 출력과 직접 JSON path 집계를 property test한다. 양 seat private inventory를 교차 검증한다.

### G-3 simple GitHub baselines / negative evidence

- 권위: B.
- 정확한 메커니즘: sota 두 repo는 한 tile에서 wheat 판매→seed1 구매→plant/water/harvest를 반복하고 이동이 없다. CI는 submission shape/package만 검증한다. jcdumlao planner는 harvest/sell/water/feed/fertilizer/buy wheat/plant 중 한 task를 고르지만 seed/animal/land/hire task와 독립 gameplay evidence가 부족하고 committed `.venv`가 있다.
- 기대 효과: packaging smoke와 API shape 예제.
- 실패모드: “CI green”을 경쟁력으로 오인할 수 있다. sota current public team score는 약 370.8 snapshot으로 상위와 멀었다.
- 반증 실험: packaging test와 gameplay regression을 분리하고 starter/niits/public-derived 상대에 20 paired seeds를 의무화한다.

### G-4 older mock-simulator repo

- 출처: GitHub 검색의 older capstone `deepeshumrao` 계열. 권위 B이나 current-rule relevance가 낮아 전략 후보에서는 제외했다.
- 정확한 메커니즘/효과: 66 tests와 contract/parity test 아이디어가 있다.
- 실패모드: 시작 cash 100과 단순 crop model인 mock simulator이며 저자도 실제 게임과 차이를 명시한다.
- 반증 실험: current official transition golden tests를 통과하지 못하면 숫자 성과를 모두 폐기하고 테스트 구조만 참고한다.

## 8. 바로 실험할 가치가 있는 가설 순위

| 우선 | 가설/변경 | 공개 증거 | 기대 효과 | 가장 위험한 실패 | 최소 반증 실험 / 폐기 기준 |
|---:|---|---|---|---|---|
| P0 | engine parity + CARE `+1` 고정 | E-1/E-2 | 모든 ROI 계산 오차 제거 | deployed env가 local pin과 다름 | one-step animal/market/land/hire golden tests + raw replay action replay. state hash 불일치면 전략 실험 중단 |
| P1 | terminal liquidation planner | smlcr 6/6 carry0, Rui/Raiden/Danilo carry 존재 | bank 직접 증가 | 너무 일찍 생산 중단 | 기존 vs 72/48/24-turn liquidation, 50 paired seeds. median만 오르고 lower decile이 악화되면 폐기 |
| P2 | success-aware market order queue | Max의 반복 대량 SELL, cap10 공식 규칙 | no-op/invalid 감소, 주문 슬롯 회수 | quote/commit timing 오해 | order별 accepted/state delta logger. invalid/no-op 비율 50% 이상 감소 없이 bank 개선 없으면 폐기 |
| P3 | liquidity-aware land timing | Victor day0→4구역, d15 25.5, reward 큰 분산 | tail risk 감소 | 후반 생산량 손실 | day0/day3/day6 land ablation × premium-glut opponents. final lower decile과 d15 liquidity 둘 다 개선 못 하면 폐기 |
| P4 | market-aware crop/animal portfolio | smlcr/Raiden/Victor의 game별 mix 변화 | 공급 충격 대응 | 관측 변동이 단순 seed noise | crop/animal별 통제 supply bot, 30 paired seeds. 선택이 공급 방향과 단조 관계 없으면 adaptive claim 폐기 |
| P5 | global job matching + detour cost | Scenario/Barnyard와 상위권 큰 crew | worker idle/동선 감소 | 계산량·충돌·greedy blocking | greedy vs Hungarian/min-cost, same economic plan. completed tasks/action과 p95 latency, final bank 동시 측정 |
| P6 | seat-specific animal plan 검증 | Max 표본 seat0 12C/16S, seat1 22C/6S | spawn/동선 비대칭 활용 | 2/3게임의 우연한 공선성 | 같은 20 seeds 양 좌석 고정 상대. seat coefficient가 유지되지 않으면 좌석 규칙 제거 |
| P7 | replay behavior prior | 공식 daily dataset + 상위 22 raw | 좋은 phase/규모 prior | covariate shift, top-sampling bias | unseen date/team holdout; clone 단독이 아니라 rule policy prior로만 ablation |

실험 평가는 평균만 보지 말고 `median / lower 10% / invalid·no-op / timeout / final carry / seat delta`를 함께 저장해야 한다. ladder rating은 상대 pool과 시간에 따라 움직이므로 local paired-bank가 1차, public rating은 2차다.

## 9. coverage gaps와 다음 수집 우선순위

### 확인하지 못한 것

1. 검색 이후의 leaderboard와 새 submission. snapshot은 2026-07-31 14:06 UTC에 고정돼 있다.
2. 비공개 Code, validation action payload, 삭제된 notebook, arbitrary-name GitHub repo, Discord 내부 전략. 역사적 전체를 exhaustive하다고 주장하지 않는다.
3. 공식 2026-07-30 dataset 13.6GB 전체. index/catalog과 Georgy small CSV, 선택 raw 22개만 읽었다.
4. 공개 notebook의 reported benchmark 재실행. 코드/주장/known failure만 추출했다.
5. top6 각 submission의 무작위 표본. public episode 목록의 최신·맞대결·양 좌석을 의도적으로 고른 표본이라 selection bias가 있다.
6. raw action order의 실제 체결/실패 전수 분류. 상태 기반 실제 hires/land/plants는 분리했지만 SELL/BUY 주문 성공률은 후속 parser가 필요하다.
7. GitHub formal fork lineage. 현재 검색 결과에 fork가 없었을 뿐 code copy, detached fork, renamed repo는 놓칠 수 있다.
8. Kaggle competition data access 규칙을 우회하지 않았다. 공개 API/공개 dataset/공개 episode만 사용했다.

### 수집 우선순위

1. 매일 공식 index를 고정하고 live top10 active submission별 public episode를 최소 양 좌석 10개씩 hash 저장.
2. episode metadata에 `submissionId/teamId/initialScore/updatedScore/create/end`, raw에 `seed/action/state`를 묶은 immutable manifest 생성.
3. 실제 market order acceptance를 state delta로 복원하고 `attempted vs executed quantity`, order-cap drop, $1-floor sale을 분리.
4. 같은 team의 submission 변경 시 action-feature drift와 score drift를 함께 기록. team 단위만 보면 새/구 정책이 섞인다.
5. 공식 엔진 commit이 바뀔 때 source hash와 transition golden test를 다시 실행. 특히 CARE mismatch의 upstream fix 여부를 감시.
6. GitHub는 `kaggriculture`, env import path, Kaggle competition URL, `BUY_ANIMAL/BUILD_PASTURE` code search를 함께 써서 arbitrary repo를 보완.

## 10. 실행한 query/source manifest

### 환경/권한 확인

```text
agent-reach doctor
  GitHub: gh CLI OK
  web/exa: OK
gh auth status
  authenticated
kaggle --version
  Kaggle API 2.2.4
```

Insane Search로 discussion 731215 URL을 먼저 시도했지만 Kaggle generic shell HTML만 받은 `weak_ok`라 근거에서 제외했다. 이후 공식 Kaggle `topic-messages` API가 실제 본문을 반환해 그 결과만 사용했다.

### Kaggle Code

```powershell
kaggle kernels list --competition kaggriculture --page-size 20 --sort-by dateCreated --format json
# 결과: public kernels 14
```

각 ref는 Kaggle low-level `ApiGetKernelRequest`/`get_kernel`로 source blob을 메모리에서 읽고 notebook source와 합친 code의 SHA256을 계산했다. 파일로 내려쓰지 않았다.

### Discussions

```powershell
kaggle competitions topics list kaggriculture --sort-by new --format json
# 결과: topics 3 (731215, 731152, 730708)
kaggle competitions topic-messages kaggriculture 731215 -n -1 -s old --format json
kaggle competitions topic-messages kaggriculture 731152 -n -1 -s old --format json
kaggle competitions topic-messages kaggriculture 730708 -n -1 -s old --format json
```

### Datasets

```powershell
kaggle datasets list -s kaggriculture --page-size 20 --sort-by updated --format json
# 결과: datasets 3
kaggle datasets list -s kagriculture --page-size 20 --sort-by updated --format json
# 결과: 0
```

공식 index CSV, Georgy dataset의 small CSV/source files는 public signed URL/API로 메모리에서 읽었다. full parquet와 13.6GB daily bundle은 받지 않았다.

### Leaderboard/submission/episode

```powershell
kaggle competitions leaderboard kaggriculture --show --page-size 200 --format json
# 2026-07-31T14:06:02Z snapshot
$teamIds = 16623798,16621709,16621355,16621497,16622835,16622990
foreach ($id in $teamIds) { kaggle competitions submissions kaggriculture --team-id $id --page-size 100 --format json }
$submissionIds = 55129098,55134690,55134549,55136535,55124664,55129067
foreach ($id in $submissionIds) { kaggle competitions episodes kaggriculture --submission-id $id --page-size 100 --format json }
```

episode metadata는 public `POST https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes`, raw는 `GET https://www.kaggleusercontent.com/episodes/{episode_id}.json`을 사용했다. 22개 raw 모두 HTTP 200, JSON parse 성공, bytes와 SHA256을 위 manifest에 기록했다.

### GitHub repo/fork/commit/issue/code

```powershell
gh search repos kaggriculture --limit 100 --json fullName,isPrivate,isFork,updatedAt,url,forksCount,openIssuesCount
gh search repos 'kaggriculture fork:true' --limit 100 --json fullName,isFork,updatedAt,url
gh search code kaggriculture --limit 100 --json repository,path,url
gh search issues kaggriculture --include-prs --limit 100 --json number,title,url,state,repository,isPullRequest
gh api repos/<repo>/commits?per_page=1
gh api repos/niits/kaggriculture/forks
gh api 'repos/Kaggle/kaggle-environments/commits?path=kaggle_environments/envs/kaggriculture&per_page=30'
```

검색 결과에서 현재 직접 관련된 GitHub issue는 없고 공식 Kaggriculture PR/commit이 주로 나왔다. 주요 repo 최신 commit은 7절에 고정했다.

### 로컬 원본 검증

```powershell
git -C references/kaggle-environments status --short
git -C references/niits-kaggriculture status --short
# 둘 다 출력 없음(clean)
Get-FileHash -Algorithm SHA256 <official engine/readme/niits artifacts>
```

## 11. 보수적 채택 기준

- raw replay 사실과 공식 engine transition은 바로 회귀 테스트 근거로 쓴다.
- 공개 notebook의 아이디어는 후보로만 가져오고, 수치는 local pinned env에서 재현될 때까지 C등급으로 둔다.
- 상위팀 한 게임의 행동을 일반 규칙으로 복사하지 않는다. 최소 양 좌석·여러 seeds·여러 supply 상대에서 유지되는 특징만 prior로 쓴다.
- score가 오르더라도 timeout/invalid/no-op/final carry/lower decile이 악화되면 production 후보로 올리지 않는다.
- upstream code hash가 바뀌면 이전 benchmark를 같은 규칙의 결과로 섞지 않는다.
