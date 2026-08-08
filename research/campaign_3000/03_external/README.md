# Campaign 3000 external-methods inventory

이 폴더는 내부 하위 연구자의 외부 자료 조사 결과다. 독립감사 보고서가 아니고, 구현·seed-open·SaveRun·제출·공개 권한도 아니다.

## 핵심 결론

1. Kag_01: bounded contention assignment.
   - Halite 상위권의 polynomial joint assignment를 가져오되, 기존 B1/B2/B4 global bitmask DP NO-GO와 겹치지 않게 rare contention state로 제한한다.
2. Kag_02: short-horizon robust market MPC.
   - MPC/robust optimization/Kore의 horizon ledger를 가져오되, 기존 A1/A2/A4 self-market/herd NO-GO와 겹치지 않게 frozen scenario set과 execute-first-action-only로 제한한다.
3. MCTS/RHEA/full RL/opponent expert gate는 현재 production pair가 아니다. offline diagnostic 또는 backlog다.

## 파일

- query_log.jsonl: 영어/한국어 1차·2차 검색, 성공·429·추출실패·회수 이력 28개.
- source_inventory.jsonl: URL/DOI/commit/hash/bytes/authority/license/메커니즘/적용·비적용/최소 delta/반증 35개.
- competition_cases.md: 종료 대회 상위 솔루션과 교차 패턴.
- paper_mechanisms.md: assignment, MPC, robustness, MCTS, bandit, ensemble, RL의 적용 경계.
- hypothesis_cards.json: Kag_01/Kag_02 production 가설과 backlog/defer 카드.
- tool_and_coverage_evidence.md: Agent-Reach, Insane Search, Context7, Serena, gh, Naver, web의 실제 사용 증거와 미확인 범위.
- manifest.json: 위 파일의 SHA-256/bytes와 JSON 검증 결과. manifest 자체는 self-hash하지 않는다.

## 강한 제한

- 3000점·메달·top-3 보장은 없다.
- 상위 Kaggriculture 공개 코드/LB/replay와의 최종 중복 검사는 sibling inventory handoff와 결합해야 한다.
- 1차 public-meta 교차에서 Kag_02의 broad robust-market/price-impact/future-gate 표방은 이미 다수 공개 코드와 겹쳤다. exact finite scenario set + first-action-only가 없으면 새 가설로 인정하지 않는다.
- Kag_01의 task-assignment/router broad collision도 확인됐지만 exact scarce-resource polynomial matching은 아직 미확인이다.
- license 미표시 repository 코드는 복사하지 않는다.
- fresh strength evidence 없이 외부 아이디어를 성능 주장으로 승격하지 않는다.
