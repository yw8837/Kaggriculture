---
name: kaggriculture-3000-orchestrator
description: "Kaggriculture 조사, 이전 제출물 분석, Kag_XX 후보 설계·평가·업로드 요청이면 반드시 기본 체크리스트부터 실행하고 증거를 단계별로 연결한다."
---

# Kaggriculture campaign orchestrator

## 시작 계약

1. `CAMPAIGN_DIRECTIVE.md`, `PROJECT_BRIEF.md`, `WORKFLOW.md`를 전부 읽는다.
2. 사용자가 이번 사이클에 지정한 이전 제출물 목록을 그대로 기록한다. 목록을 추정하거나
   Kag_01/02로 고정하지 않는다.
3. 새 후보 번호, 현재 UTC cutoff, 허용된 외부 action을 기록한다.

## 실행 순서

1. `lb-replay-analyst`: 우리 제출물과 LB 1~25, episode/replay를 현재 cutoff로 수집·분석한다.
2. `public-meta-researcher`: Code, Discussion, Models, GitHub 모집단과 메커니즘을 조사한다.
3. `external-methods-researcher`: 종료 봇 대회, 해커톤, 논문, 공식 문서, 영문·국문 외부 자료를
   조사하고 적용 가능한 단일 가설과 반증 조건을 만든다.
4. 지정된 이전 제출물을 exact artifact/API/episode/replay에 결속하고 양 좌석·상대별·경제·행동·
   runtime·실패를 분석한다.
5. `source -> finding -> defect -> delta -> metric -> risk -> falsifier -> fresh lane` 연결표를 만든다.
6. 연결표가 있는 단일 가설만 구현한다. 개발 전에 source/builder/runner/engine/opponent/scenario/
   seed/receipt/gate를 동결한다.
7. fresh paired both-seat 평가, 상대별 결과, 불확실성, worst case, runtime/invalid, 실제 발동·인과
   witness를 검증한다.
8. UltraQA로 테스트·lint·manifest·clean reproduction을 최대 5회 반복 검증한다.
9. subordinate QA 결과와 별도로, final frozen evidence만 독립감사 task에 전달한다.

## 완료 규칙

- 각 체크리스트 항목은 `PASS`, `PARTIAL`, `UNVERIFIED`, `NOT_APPLICABLE` 중 하나와 원본 증거를
  가져야 한다.
- 필요한 항목이 모두 `PASS`일 때만 “완료”라고 한다.
- 지정된 이전 제출물보다 좋아야 하는 후보는 exact direct lane에서 strict win과 positive mean
  margin을 모두 충족해야 한다. confirmation/robustness는 development PASS 뒤 별도 fresh 설계다.
- 공개 게시, Save & Run, competition submit은 서로 다른 action이다. 현재 사용자가 명시한 범위만
  실행한다.

## 도구 기록

Harness, UltraQA, Autoresearch, Agent-Reach, Insane Search, Context7, Serena, Learner/Skillify,
memory consolidation, Self-improve의 실제 사용 여부를 각각 기록한다. 파일을 읽은 것만으로
`USED`라고 쓰지 않는다. Self-improve의 mandatory trust gate를 우회하지 않는다.

## 오류 처리

- 막힌 source는 다른 route로 계속 조사하되 실패 원문과 미확인 범위를 보존한다.
- 일부 결과가 없어도 나머지 안전한 조사·분석은 계속한다.
- 기존 증거를 덮어쓰지 않고 새 cutoff 디렉터리에 append한다.
- 내부 에이전트를 독립감사자로 부르지 않는다.

## 테스트 시나리오

- 정상: 사용자가 `Kag_05/06`, 이전 제출물 `Kag_03/04`를 지정하면 03/04만 추가 분석하고 전체
  기본 체크리스트 후 05/06을 설계한다.
- 오류: 사용자가 이전 제출물을 지정하지 않았으면 오래된 01/02를 자동 재사용하지 않고, 기본
  조사와 현재 상태 inventory만 수행하며 분석 대상은 `UNSPECIFIED`로 남긴다.
