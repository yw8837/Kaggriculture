# Kaggriculture 최신 공개 메타 재스냅샷 — 2026-07-31

- 이전 기준점: 2026-07-31 14:06:02 UTC
- 새 leaderboard 조회: 2026-07-31 14:54:20 UTC / 23:54:20 KST
- 새 episode window: 이전 기준점 이후 종료된 공개 episode 47개, 마지막 종료 14:54:25 UTC
- raw 보존: `references/top-replays-refresh/`, JSON 70개, 1,491,664,905 bytes
- 구성: 새 47 + 좌석 coverage backfill 8 + smlcr 새 submission의 cutoff 이전 9 + smlcr 구 submission baseline 6
- 접근 방식: Kaggle 공식 leaderboard/team-submissions/ListEpisodes/replay 및 `kaggleusercontent.com` 공개 raw. 접근일 2026-07-31.
- 금지사항 준수: Kaggle submit/SaveRun, 게시, commit/push, production/Fa 수정은 하지 않았다.

## 0. 결론

1. smlcr의 1406.8 급등은 cutoff 이후 갑자기 정책이 변해서가 아니라, `55138375`로 교체된 직후부터 나타난 새 골격의 연속 승리로 보인다. 이 submission의 확보 가능한 21개 public episode는 21승, rating `600→1406.8`이었다.
2. smlcr 구 submission 대비 새 submission은 피크 인원 `11→13`, 실제 hires 중앙 `282→323`, 토지 첫 확장 중앙 `day6→day7`, 동물 `COW6/SHEEP3→대략 5/5`, wheat SELL 주문량 중앙 `719→971`, BUY_PRODUCT wheat `563→795`로 바뀌었다. 전 게임 final carry는 0이었다.
3. smlcr 새 submission의 21개 action SHA256는 전부 달랐다. 즉 경제 골격은 고정적이지만 raw action trace는 state/상대/seed에 따라 바뀐다. “완전 고정 스크립트”라고 부르면 과장이다.
4. cutoff 이후 smlcr는 현재 상위권 상대에게도 공개 표본상 전승했다: Rui 4회, Victor best 2회, Raiden 1회, Danilo 2회, Max best 1회. 다만 ladder가 승리 episode를 더 잘 노출하는 구조인지까지 배제한 확률 표본은 아니다.
5. Victor의 최신 submission `55139846`은 양 좌석 4게임 모두 reward 3,000, 피크 인원 1, hires 0, market action 0, 동일 PASS action hash였다. public score 258.6으로, packaging/agent 실행 실패에 가까운 명확한 negative regression이다. leaderboard best는 이전 `55136535`의 1225.1이다.
6. 신규 RuleCraft best `55137664`는 4게임 양 좌석, 3승, 13인/day10→2구역/COW8/SHEEP8/C6-M16-S20의 고정 골격이다. Rui와 상태 특징이 닮았지만 실제 hires 288, BUY_ANIMAL 주문과 종료 미배치 COW가 달라 동일 정책이라고 단정할 수 없다.
7. Lucien best `55138198`은 9게임 6승, 13인/day6→3구역/딸기 중심/완전 청산이었다. 최신 `55140228`은 공개 3게임 모두 seat0·3승뿐이라 양 좌석 일반화가 불가능하다.
8. Max 최신 `55139381`은 새 window에서 14게임 양 좌석 균형, 13승, `14인/day8→3구역`, reward `38,088–135,960`이었다. rating은 `600→1173.8`까지 올랐지만 leaderboard best 1195.2에는 아직 못 미쳤다.

## 1. 14:54 UTC leaderboard top10

공식 URL: <https://www.kaggle.com/competitions/kaggriculture/leaderboard>

| rank | team / team id | live score | latest submission / score | leaderboard-best active submission / score |
|---:|---|---:|---|---|
| 1 | smlcr / 16621709 | 1406.8 | 55138375 / 1406.8 | 55138375 / 1406.8 |
| 2 | Raiden.B / 16621355 | 1279.2 | 55134549 / 1279.2 | 55134549 / 1279.2 |
| 3 | RuiKimura4 / 16623798 | 1270.0 | 55129098 / 1270.0 | 55129098 / 1270.0 |
| 4 | Danilo_Malbashich / 16622990 | 1226.8 | 55137510 / 1171.9 | 55129067 / 1226.8 |
| 5 | Victor @ Tufa Labs / 16621497 | 1225.1 | 55139846 / 258.6 | 55136535 / 1225.1 |
| 6 | RuleCraft / 16627472 | 1217.7 | 55137664 / 1217.7 | 55137664 / 1217.7 |
| 7 | Lucien de Rubempre / 16630675 | 1210.3 | 55140228 / 931.8 | 55138198 / 1210.3 |
| 8 | Max Manushin / 16622835 | 1195.2 | 55139381 / 1173.7 | 55125574 / 1195.2 |
| 9 | Ali / 16622509 | 1187.7 | 55129923 / 1187.7 | 55129923 / 1187.7 |
| 10 | ayutin tin / 16623645 | 1179.5 | 55133690 / 1123.6 | 55132876 / 1179.5 |

14:06 UTC와 비교 가능한 이전 top6 변화:

| team | 이전 rank/score | 현재 rank/score | score delta |
|---|---:|---:|---:|
| smlcr | 2 / 1283.1 | 1 / 1406.8 | +123.7 |
| Raiden.B | 3 / 1281.2 | 2 / 1279.2 | -2.0 |
| RuiKimura4 | 1 / 1322.2 | 3 / 1270.0 | -52.2 |
| Danilo | 6 / 1227.3 | 4 / 1226.8 | -0.5 |
| Victor | 4 / 1256.3 | 5 / 1225.1 | -31.2 |
| Max | 5 / 1253.8 | 8 / 1195.2 | -58.6 |

rating은 상대 pool과 새 episode에 따라 연속 갱신된다. 같은 submission의 team-submissions 표시와 마지막 episode `updatedScore`가 0.1 정도 다른 건 표시 반올림으로 본다.

## 2. 수집과 feature 정의

### 2.1 새 window

- `endTime > 2026-07-31T14:06:02.517Z`인 top10 active-submission 관련 public episode를 dedupe했다.
- 결과는 47 episodes다. public ListEpisodes가 반환한 agent별 submission/team/reward/rating을 사용했다.
- 이 47개는 모두 공식 `kaggle competitions replay <episode_id>`로 raw 저장했다.
- 현재 top10 best의 양 좌석이 새 window에서 비는 경우 8개 이전 episode를 backfill했다.
- smlcr 정책 교체 전후 비교를 위해 new-submission cutoff 이전 9개와 old-submission 6개를 추가했다.

### 2.2 action/economic features

- action hash: 720개 action dict를 key-sort한 compact JSON의 SHA256.
- 실제 hires: `farm.hands` 상태의 양의 증가분 합. 반복 HIRE 주문 시도와 분리했다.
- first land/max quadrants: `unlocked_quadrants` 실제 상태 변화.
- 실제 plant: `(row,col,planted_day,crop)` 최초 출현 수.
- herd max: 동물별 PASTURE의 episode 내 최대 동시 개수.
- final carry: 마지막 observation의 shed + 모든 worker inventory. seed는 제외.
- market count/quantity: agent가 발행한 주문이다. 실제 체결 수량과 동일하다고 가정하지 않는다.
- reward/final bank: raw state의 마지막 money와 일치했다.

## 3. smlcr 급등 전후

### 3.1 세 구간 비교

| 구간 | n / seats(0,1) | rating span | W-L | reward min/med/max | action hash | crew / hires med | land→q | plants med | herd med | final carry |
|---|---:|---:|---:|---:|---|---|---|---|---|---|
| old `55134690` | 7 / 4,3 | 1222.4→1302.2 | 5-2 | 112,956 / 115,129 / 124,449 | 7/7 unique | 11 / 282 | day6–7→3 | C10 M15 S43 W36 | COW6 S3 | 0 |
| new `55138375`, cutoff 전 | 9 / 4,5 | 600→1205.5 | 9-0 | 99,549 / 128,955 / 150,981 | 9/9 unique | 13 / 323 | day7→3 | C11 M16 S37 W26 | COW5 S5 | 0 |
| new `55138375`, cutoff 후 | 12 / 5,7 | 1205.5→1406.8 | 12-0 | 95,732 / 115,336 / 134,968 | 12/12 unique | 13 / 323 | day7→3 | C9.5 M16.5 S37.5 W44 | COW4 S4.5 | 0 |

### 3.2 market/economy 변화

중앙값. `SELL qty`와 `BUY_PRODUCT qty`는 주문량이라 체결량을 과대계상할 수 있다.

| 구간 | HIRE orders | BUY_PRODUCT orders | SELL orders | wheat BUY qty | wheat SELL qty | fertilizer SELL qty | bank d5/d10/d15/d20/d25/d29/final |
|---|---:|---:|---:|---:|---:|---:|---|
| old | 284 | 293 | 535 | 563 | 719 | 171 | 504 / 1,157 / 19,892 / 44,129 / 78,976 / 106,086 / 115,129 |
| new pre | 323 | 368 | 598 | 878 | 955 | 214 | 285 / 893 / 21,146 / 44,587 / 82,849 / 120,946 / 128,955 |
| new post | 323 | 339 | 575.5 | 760.5 | 971 | 207.5 | 274 / 857.5 / 19,256.5 / 43,839.5 / 79,228.5 / 104,604 / 115,336 |

해석:

- rating 급등 후에 경제 골격이 또 바뀐 증거는 없다. new pre/post 모두 13인, day7 확장, 3구역, carry0이다.
- old→new에서 인력과 wheat throughput이 커지고 cow/sheep 비중이 균형화됐다.
- new post의 final bank 중앙이 pre보다 낮은 건 정책 퇴화보다 상대 rating 상승과 top-team 대전 비중 증가로 설명 가능한 관찰이다. 인과는 분리 못 했다.
- new post에서 wheat plant 중앙이 26→44, wheat BUY 주문량이 878→760.5로 바뀌었다. 내부 생산으로 구매를 일부 대체했을 가능성이 있지만, 상대·seed composition 차이가 섞여 있다.

### 3.3 new submission 21-game trajectory

`Ahash`는 action SHA256 앞 16자리. `L/Q`는 first land day/max quadrants. plants/animals는 실제 상태 feature다.

| episode | window | seat | rating | reward-opponent | opponent | Ahash | crew/hires | L/Q | plants | herd | carry |
|---:|---|---:|---:|---:|---|---|---|---|---|---|---|
| 89149303 | pre | 1 | 600→673.6 | 150981-23703 | Chirapathleo | `0fc99a1f5ebdaa15` | 13/319 | 7/3 | C47 M18 S32 W27 | C10 S2 | 0 |
| 89149800 | pre | 0 | 673.6→764.0 | 119966-12206 | yuto083 | `d71433e2a4c12741` | 13/322 | 7/3 | C47 M11 S37 W26 | C5 S5 | 0 |
| 89150321 | pre | 1 | 764.0→903.8 | 128955-71836 | Mominul | `032764945b65584d` | 13/323 | 7/3 | C10 M12 S48 W21 | C3 S9 | 0 |
| 89150817 | pre | 1 | 903.8→987.1 | 141955-56769 | datnt114 | `5a2c5bd068614af3` | 13/323 | 7/3 | C8 M19 S34 T5 W40 | C7 S5 | 0 |
| 89151315 | pre | 1 | 987.1→1049.9 | 138789-71218 | Waffle | `0429cbfa675f0988` | 13/322 | 7/3 | C9 M12 S51 T3 W7 | C5 S7 | 0 |
| 89151811 | pre | 0 | 1049.9→1097.5 | 136137-75567 | BOBQWERA | `b9ed9f58900cc0b5` | 13/323 | 7/3 | C11 M25 S41 W26 | C4 S8 | 0 |
| 89152313 | pre | 1 | 1097.5→1139.4 | 122298-65235 | Peng Wang | `92125b580af9ae18` | 13/322 | 7/3 | C21 M14 S30 T17 W19 | C8 S4 | 0 |
| 89152814 | pre | 0 | 1139.4→1170.2 | 121558-86275 | yw8837 | `462f752eb5db51b5` | 13/323 | 7/3 | C26 M16 S42 W25 | C9 S2 | 0 |
| 89153321 | pre | 0 | 1170.2→1205.5 | 99549-61811 | Avikumar | `89cd4f2d28f4738a` | 13/323 | 7/3 | C5 M22 S37 W47 | C2 S8 | 0 |
| 89153832 | new | 1 | 1205.5→1222.8 | 115755-81765 | Tony Li | `232567e28b8dc3f0` | 13/322 | 7/3 | C16 M14 S30 W72 | C4 S6 | 0 |
| 89154333 | new | 1 | 1222.8→1247.6 | 134968-105637 | Danilo new | `e2604a4cd04684d1` | 13/323 | 7/3 | C4 M18 S39 W33 | C4 S8 | 0 |
| 89154838 | new | 0 | 1247.6→1272.0 | 114917-95076 | Danilo best | `3f09d1ca7a72f003` | 13/323 | 7/3 | C7 M15 S38 W44 | C4 S5 | 0 |
| 89155333 | new | 0 | 1272.0→1290.7 | 102276-62392 | Max best | `80f9fd09de723d18` | 13/323 | 7/3 | C18 M22 S31 W49 | C10 S2 | 0 |
| 89155838 | new | 0 | 1290.7→1312.2 | 124560-82783 | Raiden best | `586cb94aee9797b9` | 13/323 | 7/3 | C10 M18 S38 W28 | C7 S4 | 0 |
| 89156343 | new | 1 | 1312.2→1329.1 | 112028-102764 | Victor best | `1fe4c7eb658990f4` | 13/323 | 7/3 | C14 M11 S34 W63 | C8 S4 | 0 |
| 89156876 | new | 1 | 1329.1→1348.1 | 113476-99792 | Rui best | `35fa3e08750c7fa1` | 13/323 | 7/3 | C9 M18 S32 W62 | C3 S8 | 0 |
| 89156867 | new | 1 | 1348.1→1364.0 | 113602-110330 | Rui best | `9bf6607bb9c63534` | 13/322 | 7/3 | C11 M14 S37 W44 | C4 S8 | 0 |
| 89157383 | new | 0 | 1364.0→1377.5 | 95732-89554 | Rui best | `813915d56748acda` | 13/323 | 7/3 | C8 M19 S43 W35 | C3 S4 | 0 |
| 89157901 | new | 0 | 1377.5→1389.1 | 116267-104506 | Rui best | `e06807c69b5a9ab6` | 13/323 | 7/3 | C8 M15 S46 W31 | C9 S2 | 0 |
| 89158412 | new | 1 | 1389.1→1399.3 | 115872-106414 | Rui best | `201203793aacf1bb` | 13/322 | 7/3 | C7 M18 S31 W69 | C4 S8 | 0 |
| 89158919 | new | 1 | 1399.3→1406.8 | 128599-114221 | Victor best | `0e026d77cd8fb000` | 13/322 | 7/3 | C24 M14 S42 W29 | C10 S2 | 0 |

21연승은 강한 신호지만 독립 Bernoulli 표본이 아니다. 상대 선정·rating update·public episode 노출은 상관돼 있고, 동일 submission/시간대의 연속 게임이다.

## 4. current top10 policy snapshots

표본은 이 refresh가 의도적으로 모은 latest/best/양좌석 game이지 무작위 표본이 아니다. `Ahash uniq`는 표본 내 서로 다른 action trace 수다.

| team/submission | n/seats | W-L | reward min/med/max | Ahash uniq | crew/hires | land→q | plants med | herd med | final carry med |
|---|---:|---:|---:|---:|---|---|---|---|---|
| smlcr new 55138375 | 21 / 9,12 | 21-0 | 95,732 / 119,966 / 150,981 | 21 | 13/323 | 7→3 | C10 M16 S37 W33 | C5 S5 | 0 |
| smlcr old 55134690 | 7 / 4,3 | 5-2 | 112,956 / 115,129 / 124,449 | 7 | 11/282 | 6–7→3 | C10 M15 S43 W36 | C6 S3 | 0 |
| Raiden best 55134549 | 4 / 2,2 | 2-2 | 82,783 / 108,924 / 133,971 | 4 | 14/324.5 | 11→3 | M21 S35.5 T13 W17.5 | C6 S7.5 | F12.5 등 |
| Rui best 55129098 | 8 / 4,4 | 2-6 | 89,554 / 106,600.5 / 120,662 | 6 | 13/300 | 10→2 | C6 M16 S20 | C8 S8 | F6 Wl3 |
| Danilo best 55129067 | 3 / 1,2 | 1-2 | 95,076 / 107,084 / 111,989 | 3 | 13/324 | 11→3 | C48 M21 S16 T7 W71 | C9 S8 | F17 Mi12 등 |
| Danilo latest 55137510 | 3 / 2,1 | 1-2 | 73,669 / 100,491 / 105,637 | 3 | 13/323 | 11→3 | C39 M23 S17 T4 W85 | C9 S7 | F11 Mi8 등 |
| Victor best 55136535 | 6 / 3,3 | 1-5 | 66,255 / 104,464.5 / 154,364 | 6 | 15/322.5 | 0→4 | C13 M39.5 S27.5 | C12.5 S7.5 | 중앙 0 |
| Victor latest 55139846 | 4 / 2,2 | 0-4 | 3,000 / 3,000 / 3,000 | 1 | 1/0 | 없음→1 | 없음 | 없음 | 0 |
| RuleCraft best 55137664 | 4 / 2,2 | 3-1 | 89,575 / 97,951.5 / 105,499 | 4 | 13/288 | 10→2 | C6 M16 S20 | C8 S8 | COW4.5, Wl1 |
| Lucien best 55138198 | 9 / 5,4 | 6-3 | 75,049 / 99,697 / 106,304 | 9 | 13/320 | 6→3 | C5 M17 S40 W24 | C7 S2 | 0 |
| Lucien latest 55140228 | 3 / 3,0 | 3-0 | 100,743 / 101,367 / 106,801 | 3 | 13/322 | 6→3 | C5 M19 S43 W30 | C4 S5 | 0 |
| Max best 55125574 | 3 / 1,2 | 1-2 | 62,392 / 80,806 / 93,368 | 3 | 13/238 | 10→2 | C14 M30 W26 | C22 S6 | 0 |
| Max latest 55139381 | 14 / 7,7 | 13-1 | 38,088 / 75,014.5 / 135,960 | 14 | 14/294 | 8→3 | C14 M28.5 W17 | 주로 C22 S6 | 중앙 0 |
| Ali best 55129923 | 4 / 2,2 | 3-1 | 56,992 / 86,517 / 128,448 | 4 | 13/248 | 10→2 | C27 M21.5 W20.5 | C12 S16 | F4 Mi3 |
| ayutin best 55132876 | 2 / 1,1 | 0-2 | 78,574 / 85,770.5 / 92,967 | 2 | 14/335 | 8→3 | C8.5 M21.5 S2 W29.5 | C11 S7 | 0 |
| ayutin latest 55133690 | 2 / 1,1 | 0-2 | 55,910 / 62,544 / 69,178 | 2 | 14/350 | 8→3 | C7.5 M20.5 S6.5 W24 | C11 S7 | 0 |

### 4.1 중요한 상대별 결과

- smlcr new vs Rui best: 4-0, reward margins `+13,684 / +3,272 / +6,178 / +9,458`.
- smlcr new vs Victor best: 2-0, margins `+9,264 / +14,378`.
- smlcr new vs Danilo new/best, Raiden best, Max best: 각각 승리.
- Raiden best vs smlcr new는 82,783–124,560 패배, Lucien best에는 133,971–103,910 승리.
- RuleCraft best는 ayutin, Lucien, 55137568 상대 승리; Max best에 91,278–93,368 패배.
- Lucien best는 RuleCraft와 1-2, Raiden에 패배. 최신 Lucien 3승은 모두 낮은 초기 rating 상대이며 seat0뿐이다.
- Max latest는 14게임 중 Yaroslav Tanko 상대 38,088–53,250 한 번만 졌다. 다만 상대 다수가 600–1100대였다.

### 4.2 market order 관측

- smlcr는 3절에 별도 기록했다.
- Max latest 중앙: HIRE 294, BUY_LAND 2, BUY_PRODUCT 594, SELL 1,792 orders; wheat BUY qty 3,376.5, wheat SELL qty 14,697.5. 주문 재시도가 매우 많아 체결/실패 분리가 우선이다.
- Ali best 중앙: HIRE 248, BUY_PRODUCT 634, SELL 829; day10 2구역, final fertilizer/milk가 남는다.
- ayutin best/latest는 SELL order 중앙 776/802, final carry0. latest는 hires 350으로 늘었지만 이 두-game 표본 성적은 둘 다 패배다.
- RuleCraft는 Rui와 비슷한 crop/herd 골격이지만 실제 hires 288 vs Rui 300, BUY_ANIMAL 주문 중앙 12, final 미배치 COW가 있다. action/source 동일성 증거는 없다.

## 5. 실패모드와 반증 실험

| 관찰 | 가장 위험한 해석 오류 | 최소 반증 실험 |
|---|---|---|
| smlcr 21연승 | public selection/초기 약한 상대를 무시하고 절대 강도로 해석 | 동일 opponent suite, 30 paired seeds, 양 좌석. old/new submission 골격을 재구현해 bank lower-decile 비교 |
| smlcr wheat 주문 증가 | 주문량을 실제 체결량으로 해석 | inventory/market delta로 accepted qty, cap-drop, no-op를 turn별 복원 |
| Victor latest all PASS | 전략 의도라고 해석 | agent logs/packaging smoke에서 callable/return schema/timeout 확인. 정상 action 1개도 없으면 submission regression 확정 |
| RuleCraft≈Rui | 상태 특징 유사성을 코드 동일성으로 해석 | 동일 seed/상대에서 full action hash와 state-conditional decision 비교; 공개 source 없이는 계보 주장 금지 |
| Lucien latest 3-0 | 양 좌석·상위 상대에도 강하다고 일반화 | seat1 공개 game 확보 후 top10 5종과 paired-seat 20 seeds |
| Max latest 13-1 | 낮은 상대 rating composition 무시 | top5 공급 archetype 상대와 동일 seeds. order success ratio와 low-tail bank 측정 |

## 6. 공개 관측 한계

1. 새 47개는 leaderboard 스케줄이 생성한 연속 public episode다. 독립·균등·무작위 표본이 아니다.
2. validation episode는 raw action 비교에서 제외했다. private/validation 정책 성능은 모른다.
3. top10별 n이 다르고 상대 난이도가 크게 다르다. 승률을 팀 간 직접 비교하면 안 된다.
4. `initialScore/updatedScore`는 해당 시점 ladder 상태다. report의 live team score와 정확히 같은 시각이 아니다.
5. action hash가 다르다는 건 trace가 다르다는 뜻뿐이다. 코드/알고리즘이 다르다는 증거는 아니다.
6. market 주문량은 요청량이다. 자금 부족, order cap, silent no-op, quote/commit 처리로 실제 체결이 달라질 수 있다.
7. Lucien latest는 seat0 3개뿐이다. Victor latest는 실패 제출로 보여 전략 메타 표본에서 분리해야 한다.
8. Ali best와 일부 좌석은 cutoff 이전 backfill이다. 새 window 집계와 섞지 않았다.
9. snapshot 후에도 새 episode가 계속 생겼다. 이 문서는 leaderboard 14:54:20 UTC와 episode 14:54:25 UTC에서 고정했다.

## 7. 우선 수집/실험 순서

1. smlcr new와 old를 모사한 opponent 두 개를 만들고, 동일 50 seeds 양 좌석에서 차이를 분해한다.
2. market order parser에 `requested / accepted / cash delta / inventory delta / cap-dropped`를 추가한다.
3. Victor `55139846`의 public agent logs를 읽기 전용으로 확인해 exception/timeout/empty action을 구분한다.
4. Lucien `55140228` seat1 public episode가 생길 때까지 snapshot을 추가하고, best/new submission drift를 분리한다.
5. RuleCraft와 Rui의 full action/state conditional similarity를 동일 seeds에서 비교하되, source lineage 주장은 보류한다.
6. 매 snapshot마다 raw bytes SHA256, episode metadata, leaderboard timestamp를 함께 고정한다.

## 8. raw source manifest

모든 SHA256는 로컬에 저장한 공식 replay JSON bytes 기준이다. class `new`만 14:06 UTC 이후 47개이며 나머지는 비교/좌석 보강이다.

| class | episode / raw URL | seed | bytes | SHA256 | teams |
|---|---|---:|---:|---|---|
| seat-backfill | [89119595](https://www.kaggleusercontent.com/episodes/89119595.json) | 937013395 | 23,142,376 | `23e40b5c9eff86641b726b5aa1c67ff1d94b9c71ddcc3a45f77a84c1e18a130b` | smlcr vs Ali |
| seat-backfill | [89126474](https://www.kaggleusercontent.com/episodes/89126474.json) | 946609462 | 19,275,345 | `d301f261c3e905001b76b07464f6655b5b683df196c17b2b9b03fea8dd6cd9aa` | ayutin tin vs Ali |
| smlcr-old | [89133857](https://www.kaggleusercontent.com/episodes/89133857.json) | 1407839729 | 26,427,994 | `ccfb39ad6daef967c8e5487822b176d0792828b790582eed65432af84c55c183` | Raiden.B vs smlcr |
| smlcr-old | [89138818](https://www.kaggleusercontent.com/episodes/89138818.json) | 1519608725 | 22,068,371 | `fa25ea7747ffb08427e10165d9d1d032ab3b9c7fdd9183a7804af180e7c9e19f` | smlcr vs RuiKimura4 |
| smlcr-old | [89140809](https://www.kaggleusercontent.com/episodes/89140809.json) | 1588005946 | 26,528,953 | `b248d00f91d72dc1067675dd1a4038c23384baea111f042d23869c1c09ca21ea` | smlcr vs Danilo_Malbashich |
| smlcr-old | [89142306](https://www.kaggleusercontent.com/episodes/89142306.json) | 1652737459 | 22,093,215 | `ff0e552b1762ae12924b0a66fa737fffe1fb66dd229628063e7a24daac6018bd` | smlcr vs RuiKimura4 |
| seat-backfill | [89143301](https://www.kaggleusercontent.com/episodes/89143301.json) | 1634611797 | 19,751,721 | `1aa0945158e2f5fb421f322975843b9413ef807763f6ca8b2aacbaeecf1f8a80` | Ali vs RuleCraft |
| seat-backfill | [89145290](https://www.kaggleusercontent.com/episodes/89145290.json) | 84868333 | 22,019,772 | `513eaabcd1ca470eebeb22cd5058977c0d8c3aef111a608036804eee76acb10e` | Raiden.B vs Victor @ Tufa Labs |
| seat-backfill | [89145302](https://www.kaggleusercontent.com/episodes/89145302.json) | 337517845 | 17,003,612 | `0d980beee108deb786aa8255423fb7861a9e4f4a6cb36ca8aa2316d50ff42d63` | Ali vs cocoaAI |
| smlcr-old | [89145303](https://www.kaggleusercontent.com/episodes/89145303.json) | 585247399 | 21,984,911 | `389209be7727758193c294fed9c4a756bb8064a3c4614cd307fbeffd0eb44386` | RuiKimura4 vs smlcr |
| smlcr-old | [89147298](https://www.kaggleusercontent.com/episodes/89147298.json) | 1384913829 | 24,013,914 | `dfa56fedffaac3e935eac39f28ce9ac76fb896072678865c081da3853f6df629` | smlcr vs Victor @ Tufa Labs |
| smlcr-new-pre | [89149303](https://www.kaggleusercontent.com/episodes/89149303.json) | 764186302 | 19,764,389 | `790a1b4da8f72d49082210ab4e915b4d6da839d31650b0a26f0004fb2c67821d` | Chirapathleo Saelim vs smlcr |
| smlcr-new-pre | [89149800](https://www.kaggleusercontent.com/episodes/89149800.json) | 1896692745 | 20,685,008 | `59b08642820d5b3392f55652a90b6de311e178d61afc965a39742cd55c93565e` | smlcr vs yuto083 |
| smlcr-new-pre | [89150321](https://www.kaggleusercontent.com/episodes/89150321.json) | 1297799492 | 21,086,838 | `bcc0669fa77833344c7912ba287aaa301d25ffeebb9f236f638fecd72ea94961` | Mominul Islam Hemal vs smlcr |
| smlcr-new-pre | [89150817](https://www.kaggleusercontent.com/episodes/89150817.json) | 361340106 | 19,890,111 | `dbca6e10b330f67955ae7864fdb3fbea9c4e00f7bb6c1a8ba7a60b4a73f0b371` | datnt114 vs smlcr |
| smlcr-new-pre | [89151315](https://www.kaggleusercontent.com/episodes/89151315.json) | 1683945425 | 26,663,352 | `943306ac82ea77cfaaa5d8ecbb61d93a471f335b8b306dbfb154b9c540afd7fe` | Waffle vs smlcr |
| seat-backfill | [89151337](https://www.kaggleusercontent.com/episodes/89151337.json) | 2106003461 | 26,891,115 | `be36673c016291a84b7faa23b9c3e4c37dd44a3c58606517c4c65d1e097fb05c` | Lucien de Rubempre vs Victor @ Tufa Labs |
| smlcr-new-pre | [89151811](https://www.kaggleusercontent.com/episodes/89151811.json) | 363197531 | 24,495,149 | `2cb3f2a3baa0e34b9c23c0ec9e6ab984289d46cf08c0c577bc23e5afb6cbef66` | smlcr vs BOBQWERA |
| smlcr-new-pre | [89152313](https://www.kaggleusercontent.com/episodes/89152313.json) | 1748557165 | 26,438,964 | `08011e908b2fcffb3fbafe49230c9bf66cbb60a7e399b1babd0cc844ca5785ea` | Peng Wang vs smlcr |
| seat-backfill | [89152331](https://www.kaggleusercontent.com/episodes/89152331.json) | 1952493362 | 23,280,939 | `361c8fdabe1699d0aacb68a596ca3988c212492db44812734d7ed1d60ebf04a6` | RuleCraft vs Danilo_Malbashich |
| smlcr-new-pre | [89152814](https://www.kaggleusercontent.com/episodes/89152814.json) | 2017787869 | 23,358,000 | `dfc39b7b3bceff867afaa44ef9049c62d8c66926f8223438edadfb5119fa8ea2` | smlcr vs yw8837 |
| seat-backfill | [89152833](https://www.kaggleusercontent.com/episodes/89152833.json) | 1442263148 | 23,114,405 | `e4dd9ea062d874092f50fcf9dde81d9f43626441f1eaf793b78fe20038e9cf5e` | Danilo_Malbashich vs ayutin tin |
| smlcr-new-pre | [89153321](https://www.kaggleusercontent.com/episodes/89153321.json) | 1573035878 | 26,121,272 | `e86379f2bbb4f6f4a040afcf12e7f5143c5ba6990116627090890f1f743e5564` | smlcr vs Avikumar93801 |
| new | [89153832](https://www.kaggleusercontent.com/episodes/89153832.json) | 958426204 | 23,271,219 | `985feb01631fc6be7646bd38024522a33ec0be03e5f7eb76671e99bbb5c81c19` | Tony Li vs smlcr |
| new | [89153835](https://www.kaggleusercontent.com/episodes/89153835.json) | 721397152 | 19,534,451 | `89e63d8a1273f53c50169587a339240f15c88b4667bfd0fefe022dddefe2e012` | Vlad Kochetov vs Lucien de Rubempre |
| new | [89153848](https://www.kaggleusercontent.com/episodes/89153848.json) | 742296373 | 18,387,939 | `d67ebc87f7f8360d2c161c5b69d8c3cb85d44444185568de1eb86f740f3ab77a` | ayutin tin vs RuleCraft |
| new | [89154333](https://www.kaggleusercontent.com/episodes/89154333.json) | 1874221559 | 26,775,831 | `ac204eb96953ae06b21d063327457158c7cbdc525d141ef56bcee36e70459871` | Danilo_Malbashich vs smlcr |
| new | [89154335](https://www.kaggleusercontent.com/episodes/89154335.json) | 1226948591 | 19,800,120 | `573b376ebbc938d09296ce286f99eb4a4278351f77228943b3b3d8e342e83e6c` | Lucien de Rubempre vs Juste Me |
| new | [89154341](https://www.kaggleusercontent.com/episodes/89154341.json) | 819991804 | 22,292,009 | `5af96baca089c79978a1e240ad2ec05629cb6c87395b4a2ed387f94367b6017e` | Raiden.B vs RuleCraft |
| new | [89154821](https://www.kaggleusercontent.com/episodes/89154821.json) | 117909443 | 16,523,647 | `7b87b1adc10544c2b8e87df84ee093c480760cafe892840fa8a4fc5ccfba6433` | chunluran vs Max Manushin |
| new | [89154838](https://www.kaggleusercontent.com/episodes/89154838.json) | 505438700 | 26,644,252 | `81ce254d89c631fb0e279bea0957e130dac32b28081e1b9c0341b08bc79d9fa2` | smlcr vs Danilo_Malbashich |
| new | [89154840](https://www.kaggleusercontent.com/episodes/89154840.json) | 671061261 | 25,986,066 | `d3820c50e7f302414e73653f0159c3a7eb986e0a979b6cc335b9c2f2f6a9baf9` | Danilo_Malbashich vs Lucien de Rubempre |
| new | [89155317](https://www.kaggleusercontent.com/episodes/89155317.json) | 1294866071 | 23,587,464 | `3370c7336544e085bf7f360db59077a17859ac6e2cce69be0e841588ffc7353f` | AdamJonesJohnson vs Max Manushin |
| new | [89155319](https://www.kaggleusercontent.com/episodes/89155319.json) | 1243482701 | 24,758,247 | `389be0fa79b37304a4e620d646308f455adb79f5a0a5256888472aae5785180b` | Roman Rozen vs Max Manushin |
| new | [89155333](https://www.kaggleusercontent.com/episodes/89155333.json) | 351785906 | 23,215,436 | `a371f20d88f5fd0cbaa4656b655a269451672a06cd56314d1fef99dca3e637a2` | smlcr vs Max Manushin |
| new | [89155339](https://www.kaggleusercontent.com/episodes/89155339.json) | 559747922 | 18,386,408 | `832cd5f972098d7f82d4f7838b67dfaf1dba8b91c0d1b65a4b2a99d23a647384` | cocoaAI vs Lucien de Rubempre |
| new | [89155828](https://www.kaggleusercontent.com/episodes/89155828.json) | 866325928 | 21,668,748 | `3ab560c2f50b711363c876dbf682efde2378202507af4347bce1af41595db700` | William Morley vs Max Manushin |
| new | [89155829](https://www.kaggleusercontent.com/episodes/89155829.json) | 407538344 | 20,363,940 | `1c2c749e65c41c8f4b3ad444905e1650fc7957085437b58a5abef34e49e119a2` | Max Manushin vs Emre Cirak |
| new | [89155838](https://www.kaggleusercontent.com/episodes/89155838.json) | 253069190 | 26,430,256 | `9ebf67e8b25506f3ed9a765d5e2131137b5a7839d461a8a6e73a8d26215d5abc` | smlcr vs Raiden.B |
| new | [89155850](https://www.kaggleusercontent.com/episodes/89155850.json) | 1388285811 | 20,507,843 | `a0c081ad92de4da2720ec570c7c17cdb74a58d7668618c4458c9a26d088b427e` | Lucien de Rubempre vs ayutin tin |
| new | [89156337](https://www.kaggleusercontent.com/episodes/89156337.json) | 959669198 | 18,091,399 | `ee8488168816e4965921d32e18df66c1c3630f1f531538a256276864367f4798` | Max Manushin vs Mominul Islam Hemal |
| new | [89156343](https://www.kaggleusercontent.com/episodes/89156343.json) | 1533360308 | 27,958,318 | `e5317695c86dce1963c901e70c924884ae1dede45b9e6181a4589c9f8e5a0405` | Victor @ Tufa Labs vs smlcr |
| new | [89156352](https://www.kaggleusercontent.com/episodes/89156352.json) | 350472932 | 21,739,120 | `6a3e3f035acffc73ff293d0150db9fe4293327813c77435e09cdd00b2238c564` | Max Manushin vs Lucien de Rubempre |
| new | [89156359](https://www.kaggleusercontent.com/episodes/89156359.json) | 1997852471 | 19,921,722 | `57a6b85e9b673cf42190a481da3306bad2a2001e57beb012ed28b7296bf8b16a` | RuleCraft vs Max Manushin |
| new | [89156360](https://www.kaggleusercontent.com/episodes/89156360.json) | 457792283 | 25,936,067 | `c592416f7e4d3604982bd2dd0da794ebc41481f66d75c63be31f318eee985912` | Victor @ Tufa Labs vs smlcr |
| new | [89156857](https://www.kaggleusercontent.com/episodes/89156857.json) | 838033947 | 18,720,848 | `0e27575f429d406f82f46f3e6a031a24d8b2109153c609f41e44d912cd8c343c` | Juste Me vs Max Manushin |
| new | [89156867](https://www.kaggleusercontent.com/episodes/89156867.json) | 1857097461 | 22,223,788 | `c1c5db42942c722992931d706610fac198a03eb2db1ef55f0462ae184f7f4f9b` | RuiKimura4 vs smlcr |
| new | [89156872](https://www.kaggleusercontent.com/episodes/89156872.json) | 1392666505 | 20,731,528 | `bb6f45008995e118ef9b5ed0cc00a5daad63a6ab0cacde53fc65d6a703101b16` | Lucien de Rubempre vs RuleCraft |
| new | [89156876](https://www.kaggleusercontent.com/episodes/89156876.json) | 1076750056 | 22,263,603 | `2a399660a14fc23a614e820fd27d77f095adffc46e77e75529cae85bda5e53d0` | RuiKimura4 vs smlcr |
| new | [89157366](https://www.kaggleusercontent.com/episodes/89157366.json) | 1394775678 | 8,938,491 | `fb21924c1395ec48a687008ffd956bc9b7d34e906fa4df7a97f91049e20d1e1b` | Raunak Dey vs Victor @ Tufa Labs |
| new | [89157373](https://www.kaggleusercontent.com/episodes/89157373.json) | 78071736 | 19,548,880 | `1285aa87a074b590896a8769dfbe13b64d47c4fddc833a118848c6bea733eb16` | Max Manushin vs Ali |
| new | [89157379](https://www.kaggleusercontent.com/episodes/89157379.json) | 1550985666 | 20,380,766 | `a198f19f1417e683ec8eb87573deed6f6b2c8dbbaf3c206f872586343e70f796` | Max Manushin vs Alexander Gremyakov |
| new | [89157383](https://www.kaggleusercontent.com/episodes/89157383.json) | 1964995189 | 22,875,015 | `c3e4f9050d01c85992076c633ff942276d302d0b6c718bff536c8ac9ed95e073` | smlcr vs RuiKimura4 |
| new | [89157388](https://www.kaggleusercontent.com/episodes/89157388.json) | 1930813204 | 21,545,023 | `3e58599329f662efda3ac4b37bac8799516a9ccef7c242a2f3dafca5257e14d5` | Lucien de Rubempre vs RuleCraft |
| new | [89157393](https://www.kaggleusercontent.com/episodes/89157393.json) | 923876253 | 20,630,662 | `ee331a97a3d3ab631b6a58d094a84f06ac23b19af4d833266be378125e7d3005` | RuleCraft vs Lucien de Rubempre |
| new | [89157884](https://www.kaggleusercontent.com/episodes/89157884.json) | 1580364777 | 4,594,959 | `890754744dac3bd7f87972b51d41edb4b728b31ec87f5e41343e9cebe7381e65` | masatoshi hiraki vs Victor @ Tufa Labs |
| new | [89157891](https://www.kaggleusercontent.com/episodes/89157891.json) | 1336223045 | 19,507,273 | `bb22be084945df2716120a7bc9585f2c835b85eaf7e23f1b8f5cc569f548d0bc` | Yaroslav Tanko vs Max Manushin |
| new | [89157901](https://www.kaggleusercontent.com/episodes/89157901.json) | 686097825 | 22,992,887 | `e20b0099755e77e7f2f508e042a0aeb0078eb87b0eaf3f40d9ad31f796eb1ebc` | smlcr vs RuiKimura4 |
| new | [89157906](https://www.kaggleusercontent.com/episodes/89157906.json) | 1782775013 | 26,048,195 | `46aee68faed8690bfec40fe293811f4872ab09e012db39861d7d4161090bda70` | Lucien de Rubempre vs Raiden.B |
| new | [89158397](https://www.kaggleusercontent.com/episodes/89158397.json) | 1697975851 | 4,583,736 | `957da1190ddb9b744b19dfb83819af9443c9d1275e8a72d4b8666c5ae7f2aca4` | Victor @ Tufa Labs vs Bovard Doerschuk-Tiberi |
| new | [89158403](https://www.kaggleusercontent.com/episodes/89158403.json) | 1876057574 | 20,031,898 | `0b90d8f208e597fbc95d1a2d669c9f79b0034ba1b8810417b5f30d64e00a80d7` | Max Manushin vs Vlad Kochetov |
| new | [89158412](https://www.kaggleusercontent.com/episodes/89158412.json) | 1847499921 | 22,392,571 | `7ea11050978343b03d2b65b0db3981e8479c2ab11416004b955be58123ffe51b` | RuiKimura4 vs smlcr |
| new | [89158890](https://www.kaggleusercontent.com/episodes/89158890.json) | 24982111 | 19,807,599 | `907c4440b6fd894585762154cd80f2d84455091ec7abce994487d968f4ec33c7` | Lucien de Rubempre vs Erwin Huizenga |
| new | [89158908](https://www.kaggleusercontent.com/episodes/89158908.json) | 1583310193 | 8,514,421 | `b3111e3b5cc4f9054cb6294c1c04961ad82a30a2ba41053efe772c2e2c11917d` | Victor @ Tufa Labs vs Aditya Mishra |
| new | [89158913](https://www.kaggleusercontent.com/episodes/89158913.json) | 765226851 | 18,217,609 | `58b018c121a91eab9aa33edaafbc78d40cf635040c0e1570532fe7a73acc6597` | Max Manushin vs Pomiro |
| new | [89158919](https://www.kaggleusercontent.com/episodes/89158919.json) | 845198715 | 25,057,295 | `fb0566cc75f8a873bf95b2f5e7352107b9e860e4c97c51a88e1a2832bd49fe3e` | Victor @ Tufa Labs vs smlcr |
| new | [89159396](https://www.kaggleusercontent.com/episodes/89159396.json) | 1334982527 | 23,942,634 | `41bec4a4edd496c19bc13a59790a92fe7d63e2e28ef2117ea75972f75672877b` | Lucien de Rubempre vs Raggriculture |
| new | [89159423](https://www.kaggleusercontent.com/episodes/89159423.json) | 1453644070 | 19,969,103 | `eeef4c65d8ea89349942f4e3e24046a3348137ec0fba53c694ccfb1fd9bef6de` | ayutin tin vs Max Manushin |
| new | [89159899](https://www.kaggleusercontent.com/episodes/89159899.json) | 1581766169 | 21,357,922 | `4f621119ad9ed2d678645ba26f4fc6586b62be3d76432c58fc99ac44d4e58dd6` | Lucien de Rubempre vs Shivangoudaa |
| new | [89159926](https://www.kaggleusercontent.com/episodes/89159926.json) | 140706480 | 18,907,971 | `5c6fbaddf7cb4fe1c50484286a6b0b72ec8e92f4a2611661045a738d611c05cc` | Max Manushin vs KO Ho Tin |

## 9. 새 window 47개 episode/submission/rating manifest

형식은 `team/submission: reward, initialScore→updatedScore`다. 종료 시각은 UTC. 이 표는 이전 14:06:02 UTC snapshot 이후만 담는다.

| end UTC | episode | seat0 | seat1 |
|---|---:|---|---|
| 14:06:28 | 89153835 | Vlad/55133558: 92525, 1064.1→1055.6 | Lucien/55138198: 99697, 1148.6→1168.8 |
| 14:06:31 | 89153832 | Tony Li/55137102: 81765, 1057.7→1047.6 | smlcr/55138375: 115755, 1205.5→1222.8 |
| 14:06:31 | 89153848 | ayutin/55132876: 78574, 1204.2→1191.3 | RuleCraft/55137664: 89575, 1187.2→1205.8 |
| 14:10:05 | 89154341 | Raiden/55133215: 104519, 1127.1→1114.0 | RuleCraft/55135596: 105611, 1201.7→1213.0 |
| 14:10:09 | 89154335 | Lucien/55138198: 98307, 1168.8→1190.0 | Juste Me/55134838: 87223, 1120.2→1108.0 |
| 14:10:11 | 89154333 | Danilo/55137510: 105637, 1186.2→1172.0 | smlcr/55138375: 134968, 1222.8→1247.6 |
| 14:14:05 | 89154821 | chunluran/55133770: 24617, 532.3→513.6 | Max/55139381: 90639, 600→686.7 |
| 14:14:32 | 89154838 | smlcr/55138375: 114917, 1247.6→1272.0 | Danilo/55129067: 95076, 1227.4→1215.9 |
| 14:14:34 | 89154840 | Danilo/55129067: 111989, 1215.9→1226.8 | Lucien/55138198: 106304, 1190.0→1168.5 |
| 14:18:27 | 89155317 | AdamJonesJohnson/55139401: 58872, 600→525.2 | Max/55139381: 68648, 686.7→750.7 |
| 14:18:29 | 89155333 | smlcr/55138375: 102276, 1272.0→1290.7 | Max/55125574: 62392, 1201.3→1194.4 |
| 14:18:34 | 89155319 | Roman Rozen/55131333: 44350, 812.9→797.9 | Max/55139381: 123712, 750.7→848.3 |
| 14:18:36 | 89155339 | cocoaAI/55130970: 65693, 1126.9→1114.2 | Lucien/55138198: 75049, 1168.5→1187.2 |
| 14:22:10 | 89155838 | smlcr/55138375: 124560, 1290.7→1312.2 | Raiden/55134549: 82783, 1281.2→1267.0 |
| 14:22:12 | 89155828 | William Morley/55134278: 57414, 819.0→802.4 | Max/55139381: 135960, 848.3→912.4 |
| 14:22:26 | 89155850 | Lucien/55138198: 101070, 1187.2→1208.0 | ayutin/55132876: 92967, 1191.3→1179.5 |
| 14:22:30 | 89155829 | Max/55139381: 88780, 912.4→964.5 | Emre/55139152: 43467, 900.0→847.9 |
| 14:26:23 | 89156337 | Max/55139381: 77374, 964.5→1016.3 | Mominul/55133422: 45941, 963.2→949.6 |
| 14:26:23 | 89156359 | RuleCraft/55137664: 91278, 1205.8→1188.5 | Max/55125574: 93368, 1194.4→1203.6 |
| 14:26:28 | 89156352 | Max/55125574: 80806, 1203.6→1195.2 | Lucien/55138198: 89134, 1208.0→1226.9 |
| 14:26:34 | 89156343 | Victor/55136535: 102764, 1256.3→1244.3 | smlcr/55138375: 112028, 1312.2→1329.1 |
| 14:26:37 | 89156360 | Victor/55136535: 97375, 1244.3→1232.0 | smlcr/55134690: 114306, 1283.1→1296.2 |
| 14:30:07 | 89156876 | Rui/55129098: 99792, 1322.2→1308.5 | smlcr/55138375: 113476, 1329.1→1348.1 |
| 14:30:26 | 89156867 | Rui/55129098: 110330, 1308.5→1296.8 | smlcr/55138375: 113602, 1348.1→1364.0 |
| 14:30:31 | 89156857 | Juste Me/55134286: 71903, 1047.5→1030.6 | Max/55139381: 83631, 1016.3→1065.1 |
| 14:30:35 | 89156872 | Lucien/55138198: 100942, 1226.9→1206.9 | RuleCraft/55137664: 104625, 1188.5→1205.9 |
| 14:34:05 | 89157379 | Max/55139381: 66291, 1065.1→1093.2 | Alexander/55138990: 49047, 982.8→958.5 |
| 14:34:11 | 89157373 | Max/55139381: 88183, 1093.2→1123.0 | Ali/55126439: 45597, 1040.7→1033.8 |
| 14:34:25 | 89157393 | RuleCraft/55137664: 105499, 1205.9→1217.8 | 55137568: 98626, 1150.5→1136.8 |
| 14:34:31 | 89157388 | Lucien/55138198: 99252, 1206.9→1223.9 | RuleCraft/55135596: 97655, 1213.0→1198.4 |
| 14:34:31 | 89157383 | smlcr/55138375: 95732, 1364.0→1377.5 | Rui/55129098: 89554, 1296.8→1286.7 |
| 14:34:51 | 89157366 | Raunak/55116223: 49161, 652.1→660.0 | Victor/55139846: 3000, 600→507.1 |
| 14:38:17 | 89157884 | masatoshi/55131149: 3764, 412.6→454.6 | Victor/55139846: 3000, 507.1→393.4 |
| 14:38:25 | 89157901 | smlcr/55138375: 116267, 1377.5→1389.1 | Rui/55129098: 104506, 1286.7→1277.9 |
| 14:38:31 | 89157891 | Yaroslav/55137848: 53250, 1107.6→1124.8 | Max/55139381: 38088, 1123.0→1089.9 |
| 14:38:34 | 89157906 | Lucien/55138198: 103910, 1223.9→1210.4 | Raiden/55134549: 133971, 1267.0→1279.2 |
| 14:42:09 | 89158403 | Max/55139381: 72655, 1089.9→1113.5 | Vlad/55134116: 65185, 1035.6→1022.7 |
| 14:42:12 | 89158397 | Victor/55139846: 3000, 393.4→322.3 | Bovard/55119357: 6099, 444.8→454.1 |
| 14:42:12 | 89158412 | Rui/55129098: 106414, 1277.9→1270.1 | smlcr/55138375: 115872, 1389.1→1399.3 |
| 14:45:59 | 89158908 | Victor/55139846: 3000, 322.3→258.7 | Aditya/55138539: 16658, 340.4→374.9 |
| 14:46:28 | 89158890 | Lucien/55140228: 101367, 600→712.5 | Erwin/55119776: 26582, 615.4→608.1 |
| 14:46:33 | 89158919 | Victor/55136535: 114221, 1232.0→1225.1 | smlcr/55138375: 128599, 1399.3→1406.8 |
| 14:46:48 | 89158913 | Max/55139381: 53954, 1113.5→1134.3 | Pomiro/55135016: 21842, 1048.4→1036.2 |
| 14:50:12 | 89159396 | Lucien/55140228: 106801, 712.5→837.8 | Raggriculture/55133209: 58547, 826.2→807.5 |
| 14:50:25 | 89159423 | ayutin/55133690: 55910, 1138.5→1123.6 | Max/55139381: 67599, 1134.3→1159.0 |
| 14:54:11 | 89159899 | Lucien/55140228: 100743, 837.8→931.8 | Shivangoudaa/55123200: 61913, 880.6→872.0 |
| 14:54:25 | 89159926 | Max/55139381: 70668, 1159.0→1173.8 | KO Ho Tin/55134973: 56174, 1048.6→1038.5 |

## 10. 실행 manifest

```powershell
kaggle competitions leaderboard kaggriculture --show --page-size 200 --format json
kaggle competitions team-submissions <top10 team id> --format json
kaggle competitions episodes <active submission id> --format json
kaggle competitions replay <episode id> -p references/top-replays-refresh -q
```

episode metadata는 공개 `POST https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes`, raw source는 위 manifest의 `https://www.kaggleusercontent.com/episodes/{id}.json`이다. API가 짧은 구간에 HTTP 429를 반환한 호출은 기다린 뒤 읽기 전용으로 재시도했다. 원본을 우회하거나 비공개 데이터에 접근하지 않았다.
