# 도구 실행 증거와 미확인 범위

## 실제 사용한 도구

### Agent-Reach 1.5.0

doctor JSON을 실제 실행했다.

- GitHub: OK, gh CLI.
- Exa search: OK, mcporter endpoint.
- generic web: OK, Jina Reader.
- YouTube/Bilibili search/V2EX/RSS: OK.
- Twitter: warning, 검색 backend 없음.
- Reddit/Facebook/Instagram/Xiaohongshu/LinkedIn: unavailable/off.

마지막 check-update 출력:

- current version: v1.5.0
- already latest

Exa는 1차 Halite/Lux/Kore/Hungry Geese 검색까지 성공했고 이후 free endpoint가 HTTP 429를 반환했다. 이후 결과를 Exa 성공처럼 표현하지 않고 official web, Crossref, GitHub CLI, Jina로 전환했다. 전체 쿼리와 실패는 query_log.jsonl Q001–Q028에 보존했다.

### Insane Search

로컬 skill 디렉터리에는 engine, references, tests, SKILL.md만 있었고 setup/setup.sh는 없었다. 특정 차단 URL인 Kore 1위 writeup에만 다음 route를 실행했다.

- python3 -m engine URL --trace --json
- 결과: HTTP 200, weak_ok, curl_cffi safari, body length 5,867이라고 보고했지만 text extraction은 비어 있었다.
- 판정: Q010 REPRO_FAILED. 이 결과를 내용 근거로 쓰지 않았다.
- 뒤의 Jina 재시도 Q028에서 실제 7,514-byte 본문과 SHA-256 2A0EC854EFFF34ED8DDB5E12152C9491D12358F483232BBAC447F924849EE6F6를 회수해 그 별도 bytes만 C10 근거로 썼다.

### Context7

mcporter에서 context7 tool 2개가 healthy임을 확인하고 실제 호출했다.

1. resolve-library-id: SciPy → /websites/scipy_doc_scipy, reputation High, benchmark 80.06.
2. query-docs: scipy.optimize.linear_sum_assignment.

공식 문서에서 확인한 사항:

- rectangular cost matrix 지원
- maximize boolean option
- modified Jonker–Volgenant with no initialization
- 작은 차원만큼 완전 assignment하고 row/column index를 반환

직접 내려받은 문서 HTML: 30,608 bytes, SHA-256 B40A69DADCC5AD747296C76AB7229BD12A18E893CE32F6D7D28FA65662175F45.

### Serena

mcporter에서 Serena 23 tools가 healthy임을 확인했다. 초기 project language가 비어 있어 symbol call이 실패했고, 생성된 .serena/project.yml의 language를 Python으로 설정한 뒤 재호출했다.

실제 성공 호출:

- get_symbols_overview: src/kaggriculture_lab/candidates/market_mpc.py
- find_symbol include_body: build_source

확인한 symbol:

- constants VALID_MODES, _MARKET_HELPERS, _HERD_HELPERS
- functions _replace_once, _inject_helpers, _ensure_math_import, build_source, build_file

build_source body는 A0 exact, A1 self-sale/funded-day29/buy-product, A2 herd target, A4 combined를 생성한다. 이 때문에 Kag_02가 기존 A1/A2/A4와 겹치면 새 외부 가설이 아니라는 local collision을 기록했다.

주의: Serena activation이 workspace root에 untracked .serena/를 만들었다. 이는 조사 evidence를 만들기 위한 tool state이고 campaign output이 아니며, 부모 task에 별도 dirty-inventory로 보고해야 한다.

### GitHub CLI / raw GitHub

검색 후 각 repository의 owner, default head commit, license metadata, README raw bytes/hash를 고정했다. 13개 repository가 source_inventory C01–C13/T01–T02에 기록돼 있다. license null은 공개라는 이유로 재사용 허가로 해석하지 않았다.

### Web / Crossref / direct PDF

기술 질문의 메커니즘 근거는 공식 문서·원 저장소·동료심사 논문만 사용했다. Crossref JSON 또는 primary PDF의 bytes/SHA를 고정했다. 핵심 목록은 P01–P16이다.

### Naver 한국어 검색

한국어 query 5개를 curl_cffi/Naver로 실제 실행했다. 응답은 HTTP 200이었지만 대부분 secondary/noisy였고 영어 primary를 대체하는 새 원본은 0개였다. 응답 byte 수와 0-retained 판정은 Q018–Q022에 남겼다. “한국어도 검색했다”와 “한국어 1차 자료에서 새 메커니즘을 얻었다”를 구분한다.

## 이 lane에서 사용하지 않은 사용자 지정 skill

이 lane은 외부 메서드 inventory 전담이라 harness, ultraqa, self-improve, autoresearch, learner, skillify, consolidate-memory를 실행하지 않았다. 그 skill의 실제 사용 증거는 각 담당 lane 또는 root가 별도로 내야 한다. 이 문서는 그 도구가 사용됐다고 대리 주장하지 않는다.

## source coverage

- source_inventory.jsonl: 35개 원본/로컬 음성대조군.
- query_log.jsonl: 28개 query/route event, 성공·429·실패·재회수 모두 포함.
- 종료 대회 직접 사례: Halite, Lux, Hungry Geese, Kore, Google AI Challenge; Fighting Game AI/GVGAI는 논문 근거.
- 방법: MPC, MCTS/DUCT, POMCP, MRTA/assignment, CBS, robust optimization/DP, UCB/EXP3, specialized experts, RHEA, AlphaZero/self-play.

## 미확인·제한

1. 인터넷 전체 전수조사가 아니다. query manifest에 정의한 모집단만 조사했다.
2. Kaggle Kore 1위 코드는 별도 license를 확인하지 못했다. writeup 메커니즘만 사용한다.
3. license가 null인 GitHub repository는 코드 복사·배포 근거가 아니다.
4. Twitter/Reddit/LinkedIn 등 Agent-Reach 비활성 플랫폼은 이 lane에서 조사하지 못했다.
5. Exa 429 뒤의 query는 Exa 결과가 아니다.
6. Naver 결과는 새 retained primary source가 0개다.
7. public_meta_inventory의 18:03–18:08Z page-claim inventory와 1차 교차했다. Kag_02의 broad robust-market/price-impact/future-gate 표방은 여러 공개 코드와 명백히 겹친다. bounded finite scenario set, first-action-only, exact fallback을 코드로 증명하지 못하면 novelty가 없다. Kag_01도 task assignment/router라는 broad collision은 있으나 2400+ 소스에서 exact scarce-resource polynomial matching은 아직 UNKNOWN_PENDING_SOURCE_CROSSCHECK다. 공개 코드 자체는 아직 실행하지 않았으므로 page score/claim과 재현을 구분한다. LB replay lane 교차는 여전히 대기다.
8. Kag_01/Kag_02는 가설 카드일 뿐 구현·seed-open·SaveRun·제출·공개 승인이 아니다.
9. 외부 원본은 3000점/메달/top-3를 보장하지 않는다. strength claim은 official simulator fresh evidence만 가능하다.

## diminishing-return 판정

2차 query는 DUCT/RHEA/OR-Tools 근거를 보강했지만 production 후보 축은 바꾸지 못했다. 새 source 5개가 추가됐으나, 즉시 적용 가능한 새 독립 delta는 0개였다. 그러므로 현재 외부조사의 합리적 stop point는 다음이다.

- Kag_01 bounded contention assignment
- Kag_02 short-horizon robust market MPC
- opponent archetype/MCTS/RHEA/RL은 backlog 또는 offline diagnostic

이후 조사는 public/LB replay lane에서 발견되는 구체적인 실패 패턴이 위 두 가설을 반박하거나 새로운 gap을 만들 때 재개한다.
