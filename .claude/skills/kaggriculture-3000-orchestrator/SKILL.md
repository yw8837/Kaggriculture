---
name: kaggriculture-3000-orchestrator
description: "Kaggriculture 3000+ 목표의 LB·replay·공개 메타·외부 연구, 후보 구현, QA, 재실행·업데이트·보완을 조율한다. Kaggriculture 전략/리플레이/상위권/후보 빌드 요청이면 사용한다."
---

# Kaggriculture 3000+ Orchestrator

## 실행 모드

Codex 다중 에이전트 기반 하이브리드 팬아웃/팬인이다. 현재 런타임에는 Harness 문서의 Claude `TeamCreate`와 `opus`가 없으므로, 동일 역할을 `spawn_agent`/메시지/공유 파일로 수행하고 이 제한을 증거에 남긴다.

## 에이전트

| 내부 에이전트 | 역할 | 출력 |
|---|---|---|
| lb-replay-analyst | 우리 제출/LB 1~25/replay | `01_internal/` |
| public-meta-researcher | Code/Discussion/Models/GitHub | `02_public_meta/` |
| external-methods-researcher | 종료 대회/논문/공식/해커톤 | `03_external/` |
| qa-integrator | 경계 계약/증거 QA | `90_internal_qa/` |

별도 task `019fb8b8-7758-7860-9304-39eb4f06c65c`만 독립감사자다.

## 단계

1. `research/campaign_3000/00_scope.md`에 목표, 조회 UTC, authority, 모집단, 쿼리군을 동결한다.
2. 앞의 세 조사자를 병렬 실행한다. 원본 URL/ID/hash/조회 UTC 없는 사실은 채택하지 않는다.
3. 리더가 원본을 표본 재검증하고 `04_synthesis/mechanism_backlog.json`으로 통합한다.
4. 한 후보=한 제한된 가설로 구현한다. 기존 champion과 최소 delta를 고정한다.
5. dev→validation→sealed/robustness 순으로 실행하고 raw/receipt/gate/hash를 보존한다.
6. UltraQA는 최대 5회 반복하며 test/lint/simulator/package 경계를 검증한다.
7. QA 내부 판정 후 exact clean freeze를 별도 독립감사 task에 넘긴다.
8. 독립감사 PASS가 온 exact payload만 user authority 범위 내에서 업로드한다. competition submit은 사용자가 정확히 제출을 지시할 때만 한다.

## 오류 처리

- 특정 플랫폼이 차단되면 Insane Search 체인을 사용하고 실패 원문을 남긴다.
- 비공개/삭제/로그인 필요 자료는 `UNVERIFIED`로 유지한다.
- seed 누수나 freeze 불일치가 발견되면 해당 pool을 폐기하고 새 disjoint pool을 등록한다.
- 조사자 과반이 실패해도 수집 범위를 축소해 전수조사라고 부르지 않는다.

## 테스트 시나리오

- 정상: 3개 조사 inventory와 query log가 생성되고 후보가 sealed gate와 QA를 통과한 뒤 감사 handoff 생성.
- 오류: Kaggle 동적 항목 일부 조회 실패 시 raw 오류와 미확인 필드를 보존하고 후보 근거에서 제외.

