# Query and collector log — 2026-08-10

This log is append-only. Search snippets are discovery metadata, not proof unless a retained source row states otherwise.

| Collector | Exact query or command | Outcome | Retention decision |
|---|---|---|---|
| Agent-Reach | `C:\\Users\\최용우\\Documents\\Codex\\2026-07-31\\kaggriculture-3-github\\work\\campaign_3000\\.venv\\Scripts\\python.exe -m agent_reach.cli doctor --json` | `ModuleNotFoundError: No module named 'agent_reach'` | Failed collector; recorded so absence is not misreported as a search. |
| Agent-Reach fallback | `python -m agent_reach.cli doctor --json` | PowerShell: `python` command not found. | Failed collector; no retry requiring installation or approval. |
| Insane Search availability | `bash -lc "python3 --version && test -d '/mnt/c/Users/최용우/.agents/skills/insane-search/engine'"` | WSL `CreateInstance/E_ACCESS_DENIED`; `python3 -m engine` was not callable. | Failed collector; no setup/install or approval prompt attempted. |
| Official Kaggle CLI | `uvx --from kaggle kaggle competitions list -s kaggriculture` | Failed before network call: uv cache initialisation error 183 at the user cache. | Failed collector; no cache repair or external mutation attempted. |
| Kaggle direct pages | `https://www.kaggle.com/competitions/kaggriculture`, `/models` | Web collector: `text/html`, zero indexed lines. `/code` and `/discussion` marked unsafe/non-retryable. | Inventory count not asserted. |
| Kaggle v1 API attempts | `/api/v1/competitions/list?search=kaggriculture`; `/api/v1/kernels/list?searchQuery=Kaggriculture`; `/api/v1/models/list?search=kaggriculture` | Web collector marked all unsafe/non-retryable. | Inventory count not asserted. |
| Web search | `site:kaggle.com/competitions/kaggriculture Kaggriculture official` | No decision-grade Kaggriculture result returned. | Not retained as a mechanism. |
| Web search | `site:kaggle.com/code Kaggriculture "Kaggriculture" 2026` | No decision-grade Kaggriculture Code result returned. | Not treated as zero Code. |
| Web search | `site:kaggle.com/discussions Kaggriculture 2026` | No decision-grade competition-specific discussion returned. | Not treated as zero Discussion. |
| Web search | `site:kaggle.com/models "Kaggriculture"` | No decision-grade Models result returned. | Not treated as zero Models. |
| Web search | `Kaggle Kore 2022 official competition GitHub environment`; `Kaggle Lux AI Challenge official competition GitHub rules`; `Kaggle Hungry Geese official competition GitHub kaggle environments`; `site:github.com/Kaggle/kaggle-environments kaggriculture OR kore OR hungry_geese` | Retained official Kaggle Environments repository, Lux AI primary paper/site, and Hungry Geese research as bounded methodology evidence. | Mapped in S03–S05. |
| Korean web search | `카글 Kaggriculture Hungry Geese 전략` | Keyword collision: real-goose husbandry/biology pages; no direct game source. | Rejected, recorded in S06. |

## External source capture notes

- Kaggle Environments GitHub README: <https://github.com/Kaggle/kaggle-environments>. Discovery capture described agent observation→action, repeated evaluation, and invalid/timeout/error categories.
- Lux AI primary paper: <https://openreview.net/pdf?id=7t8kWYbOcj>; official project site: <https://www.lux-ai.org/>. Retained only for the rule-based vs learned/opponent-adaptive boundary.
- Hungry Geese study: <https://arxiv.org/abs/2109.01954>. Retained only for stochastic-evaluation caution, not for an economic policy.
- Existing previously captured Kaito v22 page: <https://www.kaggle.com/code/kaitofukami/44-46-strict-future-top-30-v22-price-impact>. Its page claim is paired with the exact local `NO_GO`, never substituted for it.
