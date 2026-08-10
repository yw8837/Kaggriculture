---
name: kaggriculture-campaign-cycle
description: Kaggriculture의 기본 전수조사와 사용자가 지정한 이전 제출물 분석을 다음 Kag_XX 설계·평가에 누락 없이 연결한다.
triggers:
  - Kaggriculture 다음 후보 만들어
  - 이전 제출물 분석하고 다음 Kag_XX 설계해
  - 기본 체크리스트대로 조사 분석 적용해
---

# Kaggriculture campaign cycle

## The insight

조사량이 많아도 현재 모집단, 사용자가 지정한 이전 제출물, 실제 후보 delta 사이의 연결표가
없으면 다음 후보는 근거 없는 새 가설이 된다. 제출 번호는 계속 증가하므로 분석 대상을 Kag_01/02로
고정하면 즉시 stale instruction이 된다.

## Recognition pattern

- 사용자가 다음 `Kag_XX` 후보를 요청한다.
- “이전 제출물 A/B를 분석하고 다음 것을 만들어”라고 한다.
- Code/Discussion/LB 조사 자료는 많지만 실제 후보 선택 이유가 추적되지 않는다.

## Workflow

1. `CAMPAIGN_DIRECTIVE.md`의 mandatory baseline checklist를 로드한다.
2. 이번 사이클의 새 후보 번호와 사용자가 지정한 이전 제출물 목록을 exact하게 기록한다.
3. 현재 시점의 우리 제출물, LB 1~25, Code, Discussion, Models, 외부 연구를 provenance와 함께
   갱신한다.
4. 지정된 이전 제출물만 full-population facts와 sampled replay facts를 분리해 분석한다.
5. 각 후보마다 `source -> finding -> defect -> delta -> metric -> risk -> falsifier -> fresh lane`
   한 행을 작성한다.
6. 연결된 한 가설만 구현·동결하고 fresh paired both-seat 평가를 수행한다.
7. exact 이전 control을 strict하게 이기지 못하면 폐기하거나 재설계한다.
8. 모든 체크리스트 row와 QA가 PASS인 경우에만 완료라고 보고한다.

## Success criteria

- 분석 대상이 사용자 지정 목록과 정확히 같다.
- 모집단·표본·미확인이 분리되어 있다.
- 조사 근거에서 코드 delta와 반증 평가까지 역추적된다.
- 다음 후보가 지정된 이전 champion보다 낫다는 fresh evidence가 있다.
- 부분 결과를 완료로 부르지 않는다.

## Pitfalls

- Kag_01/02를 영구 분석 대상으로 고정하지 않는다.
- 최신 점수와 특정 version/source를 근거 없이 연결하지 않는다.
- aggregate mean으로 상대별 붕괴를 가리지 않는다.
- public research inventory를 전부 실행·재현한 것으로 과장하지 않는다.
- 독립감사 전 내부 review를 독립 PASS라고 부르지 않는다.
