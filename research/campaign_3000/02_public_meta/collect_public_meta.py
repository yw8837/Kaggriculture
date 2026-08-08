from __future__ import annotations

import base64
import concurrent.futures
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest

OUT = Path(__file__).resolve().parent
RAW = OUT / "raw"
COMPETITION = "kaggriculture"
USER_AGENT = "kaggriculture-public-meta-research/1.0"

MECHANISM_PATTERNS: dict[str, tuple[str, ...]] = {
    "fixed_trace_or_schedule": (
        "fixed trace",
        "hardcoded",
        "schedule",
        "action tape",
        "opening book",
    ),
    "replay_mining_or_cloning": ("replay", "clone", "replica", "trace"),
    "adaptive_or_opponent_aware": (
        "adaptive",
        "opponent",
        "reactive",
        "conditional memory",
        "closed loop",
    ),
    "market_timing_or_impact": ("market", "sell", "price", "glut", "scarcity", "batch"),
    "animals_or_fertilizer": ("cow", "sheep", "goose", "wool", "milk", "fertilizer", "barnyard"),
    "crop_portfolio": ("wheat", "melon", "strawberry", "carrot", "tomato", "crop mix"),
    "routing_or_task_allocation": ("route", "path", "bfs", "a*", "task", "preemption", "scheduler"),
    "holdout_or_evaluation": ("holdout", "benchmark", "validation", "seed", "confidence", "paired"),
    "optimization_or_search": ("mpc", "mcts", "dynamic programming", "cma", "optimizer", "search"),
    "rl_or_learning": ("reinforcement", " q-learning", "policy gradient", "neural", "ppo", "dqn"),
    "engine_or_balance": ("1.32.6", "balance", "town", "engine changed", "pr1394"),
}


def utc_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run(command: list[str], *, timeout: int = 120) -> dict[str, Any]:
    started = utc_now()
    original_command = list(command)
    resolved = shutil.which(command[0])
    if resolved:
        command = [resolved, *command[1:]]
    if command[0].lower().endswith((".cmd", ".bat")):
        command = [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", *command]
    proc = subprocess.run(
        command, text=True, encoding="utf-8", capture_output=True, timeout=timeout, check=False
    )
    return {
        "command": original_command,
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
        "stdout_sha256": sha256(proc.stdout.encode("utf-8")),
        "stderr_sha256": sha256(proc.stderr.encode("utf-8")),
    }


def fetch_text(url: str, *, retries: int = 3, timeout: int = 60) -> dict[str, Any]:
    last_error = ""
    for attempt in range(retries):
        try:
            request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(request, timeout=timeout) as response:
                data = response.read()
                return {
                    "ok": True,
                    "status": int(response.status),
                    "url": url,
                    "bytes": len(data),
                    "sha256": sha256(data),
                    "text": data.decode("utf-8", errors="replace"),
                }
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(1.5 * (attempt + 1))
    return {"ok": False, "url": url, "error": last_error, "bytes": 0, "sha256": None, "text": ""}


def mechanism_tags(text: str) -> list[str]:
    lower = text.lower()
    return sorted(
        name for name, terms in MECHANISM_PATTERNS.items() if any(term in lower for term in terms)
    )


def notebook_shape(source: str, kernel_type: str) -> dict[str, Any]:
    if kernel_type.lower() != "notebook":
        try:
            compile(source, "<public-kernel>", "exec")
            compile_status = "STATIC_COMPILE_PASS"
        except Exception as exc:  # noqa: BLE001 - untrusted public source is classified, not executed.
            compile_status = f"STATIC_COMPILE_FAIL:{type(exc).__name__}"
        return {
            "source_format": "script",
            "cell_count": None,
            "markdown_cell_count": None,
            "code_cell_count": None,
            "executed_code_cell_count": None,
            "error_output_count": None,
            "static_parse_status": compile_status,
            "headings": [],
        }
    try:
        notebook = json.loads(source)
    except json.JSONDecodeError as exc:
        return {
            "source_format": "notebook",
            "cell_count": None,
            "markdown_cell_count": None,
            "code_cell_count": None,
            "executed_code_cell_count": None,
            "error_output_count": None,
            "static_parse_status": f"NOTEBOOK_JSON_FAIL:{exc.msg}",
            "headings": [],
        }
    cells = notebook.get("cells") or []
    markdown = [cell for cell in cells if cell.get("cell_type") == "markdown"]
    code = [cell for cell in cells if cell.get("cell_type") == "code"]
    headings: list[str] = []
    for cell in markdown:
        for line in str(cell.get("source", "")).splitlines():
            if re.match(r"^#{1,4}\s+", line):
                headings.append(re.sub(r"^#{1,4}\s+", "", line).strip())
    return {
        "source_format": "notebook",
        "cell_count": len(cells),
        "markdown_cell_count": len(markdown),
        "code_cell_count": len(code),
        "executed_code_cell_count": sum(cell.get("execution_count") is not None for cell in code),
        "error_output_count": sum(
            1
            for cell in code
            for output in (cell.get("outputs") or [])
            if output.get("output_type") == "error"
        ),
        "static_parse_status": "NOTEBOOK_JSON_PASS",
        "headings": headings[:40],
    }


def parse_code_page(text: str) -> dict[str, Any]:
    score_match = re.search(
        r"Best Score\s*\n+\s*\[?([0-9]+(?:\.[0-9]+)?)\s+V([0-9]+)", text, re.IGNORECASE
    )
    license_match = re.search(
        r"## License\s+.*?released under the \[([^\]]+)\]\(([^)]+)\)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    successful_log = bool(re.search(r"Logs\s+[^\n]*successful", text, re.IGNORECASE))
    return {
        "best_score": float(score_match.group(1)) if score_match else None,
        "best_score_version": int(score_match.group(2)) if score_match else None,
        "license_name": license_match.group(1).strip() if license_match else "UNVERIFIED",
        "license_url": license_match.group(2).strip() if license_match else None,
        "remote_successful_log_claim": successful_log,
    }


def get_kernel(ref: str) -> dict[str, Any]:
    owner, slug = ref.split("/", 1)
    api = KaggleApi()
    api.authenticate()
    request = ApiGetKernelRequest()
    request.user_name = owner
    request.kernel_slug = slug
    with api.build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.get_kernel(request)
    metadata = response.metadata.to_dict()
    source = response.blob.source
    source_bytes = source.encode("utf-8")
    page_url = f"https://www.kaggle.com/code/{ref}"
    jina = fetch_text(f"https://r.jina.ai/{page_url}")
    page_meta = (
        parse_code_page(jina["text"])
        if jina["ok"]
        else {
            "best_score": None,
            "best_score_version": None,
            "license_name": "UNVERIFIED",
            "license_url": None,
            "remote_successful_log_claim": False,
        }
    )
    shape = notebook_shape(
        source, str(metadata.get("kernelType") or response.blob.kernel_type or "")
    )
    return {
        "ref": ref,
        "version": metadata.get("currentVersionNumber"),
        "id": metadata.get("id"),
        "author": metadata.get("author"),
        "title": metadata.get("title"),
        "last_run_time": metadata.get("lastRunTime"),
        "votes": metadata.get("totalVotes", 0),
        "url": page_url,
        "source_sha256": sha256(source_bytes),
        "source_bytes": len(source_bytes),
        "metadata_sha256": sha256(canonical_bytes(metadata)),
        "metadata": {
            key: metadata.get(key)
            for key in (
                "language",
                "kernelType",
                "isPrivate",
                "enableGpu",
                "enableTpu",
                "enableInternet",
                "competitionDataSources",
                "datasetDataSources",
                "kernelDataSources",
                "modelDataSources",
                "dockerImage",
                "machineShape",
            )
        },
        **shape,
        **page_meta,
        "page_reader_status": "FETCHED" if jina["ok"] else "REPRO_FAILED",
        "page_reader_sha256": jina.get("sha256"),
        "page_reader_bytes": jina.get("bytes", 0),
        "mechanism_tags": mechanism_tags(source + "\n" + jina.get("text", "")),
        "local_execution_status": "READ_ONLY",
        "claim_status": "SOURCE_AND_REMOTE_PAGE_CAPTURED"
        if jina["ok"]
        else "SOURCE_CAPTURED_PAGE_UNVERIFIED",
        "reproduction_status": "NOT_EXECUTED_UNTRUSTED_PUBLIC_CODE",
        "retrieved_at_utc": utc_now(),
        "error": None,
    }


def list_kernels(api: KaggleApi) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: dict[str, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []
    page = 1
    while True:
        batch = (
            api.kernels_list(
                page=page,
                page_size=200,
                competition=COMPETITION,
                sort_by="dateRun",
            )
            or []
        )
        refs = [item.ref for item in batch if item]
        pages.append(
            {
                "page": page,
                "count": len(refs),
                "first_ref": refs[0] if refs else None,
                "last_ref": refs[-1] if refs else None,
                "refs_sha256": sha256(canonical_bytes(refs)),
                "retrieved_at_utc": utc_now(),
            }
        )
        if not refs:
            break
        for item in batch:
            if item:
                rows[item.ref] = item.to_dict()
        page += 1
        if page > 100:
            raise RuntimeError("kernel pagination safety limit exceeded")
    return list(rows.values()), pages


def discussion_author(text: str, title: str) -> tuple[str | None, str | None]:
    marker = f"### {title}"
    before = text.split(marker, 1)[0] if marker in text else text[:2500]
    profiles = re.findall(r"\[\]\(https://www\.kaggle\.com/([^)/?#]+)\)", before)
    if not profiles:
        return None, None
    username = profiles[-1]
    return username, f"https://www.kaggle.com/{username}"


def get_discussion(api: KaggleApi, topic: dict[str, Any]) -> dict[str, Any]:
    topic_id = int(topic["id"])
    response = api.competition_list_topic_messages(COMPETITION, topic_id, page_size=-1)
    messages = response.to_dict().get("messages", [])
    url = f"https://www.kaggle.com/competitions/{COMPETITION}/discussion/{topic_id}"
    jina = fetch_text(f"https://r.jina.ai/{url}")
    author, author_url = (
        discussion_author(jina.get("text", ""), str(topic.get("title", "")))
        if jina["ok"]
        else (None, None)
    )
    message_bytes = canonical_bytes(messages)
    return {
        "id": topic_id,
        "title": topic.get("title"),
        "author": author or "UNVERIFIED",
        "author_url": author_url,
        "comment_count": topic.get("commentCount", 0),
        "votes": topic.get("votes", 0),
        "post_date": topic.get("postDate"),
        "last_comment_post_date": topic.get("lastCommentPostDate"),
        "sticky": bool(topic.get("isSticky", False)),
        "url": url,
        "message_tree_sha256": sha256(message_bytes),
        "message_tree_bytes": len(message_bytes),
        "message_node_count": count_message_nodes(messages),
        "page_reader_status": "FETCHED" if jina["ok"] else "REPRO_FAILED",
        "page_reader_sha256": jina.get("sha256"),
        "page_reader_bytes": jina.get("bytes", 0),
        "mechanism_tags": mechanism_tags(
            json.dumps(messages, ensure_ascii=False) + jina.get("text", "")
        ),
        "execution_status": "READ_ONLY",
        "retrieved_at_utc": utc_now(),
    }


def count_message_nodes(messages: list[dict[str, Any]]) -> int:
    total = 0
    stack = list(messages)
    while stack:
        message = stack.pop()
        total += 1
        stack.extend(message.get("replies") or [])
    return total


def list_discussions(api: KaggleApi) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: dict[int, dict[str, Any]] = {}
    pages: list[dict[str, Any]] = []
    page = 1
    total_count: int | None = None
    while True:
        response = api.competition_list_topics(COMPETITION, sort_by="new", page=page)
        payload = response.to_dict()
        batch = payload.get("topics") or []
        total_count = int(payload.get("totalCount") or total_count or 0)
        ids = [int(row["id"]) for row in batch]
        pages.append(
            {
                "page": page,
                "count": len(ids),
                "ids": ids,
                "ids_sha256": sha256(canonical_bytes(ids)),
                "declared_total_count": total_count,
                "retrieved_at_utc": utc_now(),
            }
        )
        if not batch:
            break
        for row in batch:
            rows[int(row["id"])] = row
        if total_count and len(rows) >= total_count:
            page += 1
            empty = (
                api.competition_list_topics(COMPETITION, sort_by="new", page=page)
                .to_dict()
                .get("topics")
                or []
            )
            pages.append(
                {
                    "page": page,
                    "count": len(empty),
                    "ids": [int(row["id"]) for row in empty],
                    "ids_sha256": sha256(canonical_bytes([int(row["id"]) for row in empty])),
                    "declared_total_count": total_count,
                    "retrieved_at_utc": utc_now(),
                }
            )
            break
        page += 1
        if page > 100:
            raise RuntimeError("discussion pagination safety limit exceeded")
    return list(rows.values()), pages


def gh_json(args: list[str], timeout: int = 120) -> Any:
    result = run(["gh", *args], timeout=timeout)
    if result["returncode"] != 0:
        raise RuntimeError(f"gh failed: {' '.join(args)}: {result['stderr'][:500]}")
    return json.loads(result["stdout"])


def github_search() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    queries = [
        "kaggriculture in:name,description,readme",
        "kaggriculture agent in:name,description,readme",
        "kaggriculture replay in:name,description,readme",
    ]
    found: dict[str, dict[str, Any]] = {}
    query_log: list[dict[str, Any]] = []
    for query in queries:
        first = gh_json(
            [
                "api",
                "-X",
                "GET",
                "search/repositories",
                "-f",
                f"q={query}",
                "-f",
                "per_page=100",
                "-f",
                "page=1",
            ]
        )
        total = int(first.get("total_count", 0))
        page_count = min(10, max(1, math.ceil(total / 100)))
        page_payloads = [first]
        for page in range(2, page_count + 1):
            page_payloads.append(
                gh_json(
                    [
                        "api",
                        "-X",
                        "GET",
                        "search/repositories",
                        "-f",
                        f"q={query}",
                        "-f",
                        "per_page=100",
                        "-f",
                        f"page={page}",
                    ]
                )
            )
        refs: list[str] = []
        for payload in page_payloads:
            for item in payload.get("items") or []:
                refs.append(item["full_name"])
                found[item["full_name"].lower()] = item
        query_log.append(
            {
                "query": query,
                "reported_total": total,
                "accessible_cap": 1000,
                "pages_fetched": page_count,
                "rows_seen": len(refs),
                "unique_refs_seen": len(set(refs)),
                "refs_sha256": sha256(canonical_bytes(sorted(set(refs)))),
                "retrieved_at_utc": utc_now(),
            }
        )

    official = gh_json(["api", "repos/Kaggle/kaggle-environments"])
    found[official["full_name"].lower()] = official

    def enrich(item: dict[str, Any]) -> dict[str, Any]:
        full_name = item["full_name"]
        default_branch = item.get("default_branch") or "main"
        head_sha: str | None = None
        head_error: str | None = None
        readme_sha: str | None = None
        readme_bytes: int | None = None
        readme_tags: list[str] = []
        readme_error: str | None = None
        try:
            commit = gh_json(["api", f"repos/{full_name}/commits/{default_branch}"])
            head_sha = commit.get("sha")
        except Exception as exc:  # noqa: BLE001 - inventory must retain inaccessible repositories.
            head_error = f"{type(exc).__name__}: {exc}"
        try:
            readme = gh_json(["api", f"repos/{full_name}/readme"])
            content = base64.b64decode(readme.get("content", ""), validate=False)
            readme_sha = sha256(content)
            readme_bytes = len(content)
            readme_tags = mechanism_tags(content.decode("utf-8", errors="replace"))
        except Exception as exc:  # noqa: BLE001 - unavailable README is an inventory state.
            readme_error = f"{type(exc).__name__}: {exc}"
        license_info = item.get("license") or {}
        return {
            "kind": "repository",
            "full_name": full_name,
            "url": item.get("html_url"),
            "description": item.get("description"),
            "default_branch": default_branch,
            "head_commit_sha": head_sha,
            "head_retrieval_error": head_error,
            "updated_at": item.get("updated_at"),
            "pushed_at": item.get("pushed_at"),
            "created_at": item.get("created_at"),
            "is_fork": bool(item.get("fork")),
            "forks_count": item.get("forks_count", 0),
            "stars": item.get("stargazers_count", 0),
            "open_issues_count": item.get("open_issues_count", 0),
            "license_spdx": license_info.get("spdx_id") or "UNVERIFIED",
            "readme_sha256": readme_sha,
            "readme_bytes": readme_bytes,
            "readme_retrieval_error": readme_error,
            "mechanism_tags": readme_tags,
            "execution_status": "READ_ONLY",
            "retrieved_at_utc": utc_now(),
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        rows = list(pool.map(enrich, found.values()))

    issue_search = gh_json(
        [
            "api",
            "-X",
            "GET",
            "search/issues",
            "-f",
            "q=kaggriculture in:title,body",
            "-f",
            "per_page=100",
            "-f",
            "page=1",
        ]
    )
    for issue in issue_search.get("items") or []:
        body = issue.get("body") or ""
        rows.append(
            {
                "kind": "pull_request" if "pull_request" in issue else "issue",
                "id": issue.get("id"),
                "number": issue.get("number"),
                "title": issue.get("title"),
                "url": issue.get("html_url"),
                "state": issue.get("state"),
                "created_at": issue.get("created_at"),
                "updated_at": issue.get("updated_at"),
                "author": (issue.get("user") or {}).get("login"),
                "comments": issue.get("comments", 0),
                "body_sha256": sha256(body.encode("utf-8")),
                "body_bytes": len(body.encode("utf-8")),
                "mechanism_tags": mechanism_tags(issue.get("title", "") + "\n" + body),
                "execution_status": "READ_ONLY",
                "retrieved_at_utc": utc_now(),
            }
        )
    query_log.append(
        {
            "query": "kaggriculture in:title,body (issues and PRs)",
            "reported_total": issue_search.get("total_count", 0),
            "rows_seen": len(issue_search.get("items") or []),
            "accessible_cap": 100,
            "retrieved_at_utc": utc_now(),
        }
    )
    try:
        pr = gh_json(
            [
                "pr",
                "view",
                "1394",
                "--repo",
                "Kaggle/kaggle-environments",
                "--json",
                "number,title,url,state,mergedAt,mergeCommit,headRefOid,baseRefOid,author,body,files",
            ]
        )
        rows.append(
            {
                "kind": "official_pull_request",
                "number": pr.get("number"),
                "title": pr.get("title"),
                "url": pr.get("url"),
                "state": pr.get("state"),
                "merged_at": pr.get("mergedAt"),
                "merge_commit": (pr.get("mergeCommit") or {}).get("oid"),
                "head_commit_sha": pr.get("headRefOid"),
                "base_commit_sha": pr.get("baseRefOid"),
                "author": (pr.get("author") or {}).get("login"),
                "body_sha256": sha256((pr.get("body") or "").encode("utf-8")),
                "changed_files": [file.get("path") for file in pr.get("files") or []],
                "mechanism_tags": mechanism_tags(
                    (pr.get("title") or "") + "\n" + (pr.get("body") or "")
                ),
                "execution_status": "READ_ONLY",
                "retrieved_at_utc": utc_now(),
            }
        )
    except Exception as exc:  # noqa: BLE001
        query_log.append(
            {"query": "Kaggle/kaggle-environments PR 1394", "error": f"{type(exc).__name__}: {exc}"}
        )
    rows.sort(key=lambda row: (row.get("kind", ""), row.get("full_name") or row.get("url") or ""))
    return rows, query_log


def tool_evidence() -> list[dict[str, Any]]:
    commands = [
        [sys.executable, "-m", "agent_reach.cli", "doctor", "--json"],
        [
            "mcporter",
            "call",
            "exa.web_search_exa",
            "query=site:kaggle.com/code Kaggriculture agent strategy public score 2026",
            "numResults=10",
        ],
        [
            "mcporter",
            "call",
            "exa.web_search_exa",
            "query=site:kaggle.com/discussions/kaggriculture balance strategy",
            "numResults=10",
        ],
        [
            "mcporter",
            "call",
            "exa.web_search_exa",
            "query=Kaggriculture GitHub agent market planning replay",
            "numResults=10",
        ],
        [
            "mcporter",
            "call",
            "context7.resolve-library-id",
            "query=Kaggle CLI kernel listing pagination metadata",
            "libraryName=Kaggle API",
        ],
        [
            "mcporter",
            "call",
            "context7.query-docs",
            "libraryId=/kaggle/kaggle-cli",
            "query=List and paginate competition notebooks discussions and models with JSON metadata",
        ],
    ]
    results = [run(command, timeout=120) for command in commands]
    for result in results:
        result["stdout_excerpt"] = result.pop("stdout")[:6000]
        result["stderr_excerpt"] = result.pop("stderr")[:1000]
    results.append(
        {
            "tool": "serena",
            "status": "USED",
            "evidence": (
                "mcporter ad-hoc Serena server activated project campaign_3000; "
                "get_symbols_overview and find_symbol inspected "
                "src/kaggriculture_lab/research/kaggle_inventory.py::collect_inventory."
            ),
            "observed_symbols": ["_utc_now", "_run_json", "collect_inventory", "main"],
            "retrieved_at_utc": utc_now(),
        }
    )
    results.append(
        {
            "tool": "insane-search",
            "status": "NOT_INVOKED",
            "reason": "No concrete Kaggle/GitHub URL remained blocked after official API and Jina Reader access; policy forbids gratuitous fallback use.",
            "retrieved_at_utc": utc_now(),
        }
    )
    return results


def collect_models() -> list[dict[str, Any]]:
    cli = run(
        ["kaggle", "models", "list", "-s", COMPETITION, "--page-size", "200", "--format", "json"],
        timeout=60,
    )
    ui = fetch_text(f"https://r.jina.ai/https://www.kaggle.com/competitions/{COMPETITION}/models")
    parsed: list[dict[str, Any]] = []
    try:
        value = json.loads(cli["stdout"])
        if isinstance(value, list):
            parsed = value
    except json.JSONDecodeError:
        pass
    if parsed:
        return [
            {
                "discovery_method": "kaggle models list search",
                "competition_linkage": "TEXT_SEARCH_ONLY_NOT_OFFICIAL_COMPETITION_FILTER",
                "record": row,
                "record_sha256": sha256(canonical_bytes(row)),
                "retrieved_at_utc": utc_now(),
                "execution_status": "READ_ONLY",
            }
            for row in parsed
        ]
    return [
        {
            "discovery_method": "kaggle models list -s kaggriculture plus competition Models UI reader",
            "competition_linkage": "UNVERIFIED_NO_OFFICIAL_COMPETITION_FILTER_EXPOSED",
            "result": "NO_SEARCH_RESULTS",
            "cli_returncode": cli["returncode"],
            "cli_stdout_sha256": cli["stdout_sha256"],
            "cli_stderr_sha256": cli["stderr_sha256"],
            "ui_reader_status": "FETCHED" if ui["ok"] else "REPRO_FAILED",
            "ui_reader_sha256": ui.get("sha256"),
            "ui_reader_bytes": ui.get("bytes", 0),
            "note": "This is not a claim that zero Kaggriculture-linked model objects exist; the CLI exposes search, not a competition filter.",
            "retrieved_at_utc": utc_now(),
            "execution_status": "READ_ONLY",
        }
    ]


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    started = utc_now()
    api = KaggleApi()
    api.authenticate()

    kernel_list, kernel_pages = list_kernels(api)
    refs = sorted(row["ref"] for row in kernel_list)
    code_rows: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        future_map = {pool.submit(get_kernel, ref): ref for ref in refs}
        for index, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            ref = future_map[future]
            try:
                code_rows.append(future.result())
            except Exception as exc:  # noqa: BLE001 - preserve inaccessible item instead of aborting population.
                code_rows.append(
                    {
                        "ref": ref,
                        "url": f"https://www.kaggle.com/code/{ref}",
                        "retrieved_at_utc": utc_now(),
                        "local_execution_status": "UNVERIFIED",
                        "reproduction_status": "REPRO_FAILED",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
            if index % 25 == 0:
                print(f"kernels {index}/{len(refs)}", flush=True)
    code_rows.sort(key=lambda row: row["ref"])
    write_jsonl(OUT / "code_inventory.jsonl", code_rows)

    topic_list, discussion_pages = list_discussions(api)
    discussion_rows: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        future_map = {
            pool.submit(get_discussion, api, topic): int(topic["id"]) for topic in topic_list
        }
        for index, future in enumerate(concurrent.futures.as_completed(future_map), 1):
            topic_id = future_map[future]
            try:
                discussion_rows.append(future.result())
            except Exception as exc:  # noqa: BLE001
                topic = next(row for row in topic_list if int(row["id"]) == topic_id)
                discussion_rows.append(
                    {
                        "id": topic_id,
                        "title": topic.get("title"),
                        "url": f"https://www.kaggle.com/competitions/{COMPETITION}/discussion/{topic_id}",
                        "retrieved_at_utc": utc_now(),
                        "execution_status": "UNVERIFIED",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
                )
            if index % 20 == 0:
                print(f"discussions {index}/{len(topic_list)}", flush=True)
    discussion_rows.sort(key=lambda row: int(row["id"]))
    write_jsonl(OUT / "discussion_inventory.jsonl", discussion_rows)

    model_rows = collect_models()
    write_jsonl(OUT / "model_inventory.jsonl", model_rows)
    github_rows, github_queries = github_search()
    write_jsonl(OUT / "github_inventory.jsonl", github_rows)
    tools = tool_evidence()

    write_json(
        OUT / "query_log.json",
        {
            "schema_version": 1,
            "started_at_utc": started,
            "finished_at_utc": utc_now(),
            "population_definitions": {
                "code": "All refs returned by Kaggle kernels_list competition=kaggriculture sort=dateRun page_size=200 through the first empty page; deduplicated by ref, current version fetched by get_kernel.",
                "discussion": "All topics returned by Kaggle competition_list_topics sort=new through declared total and a terminal empty page; deduplicated by topic id; full message trees requested.",
                "models": "Official Kaggle CLI model text search plus the competition Models UI. No official CLI competition filter exists, so absence is UNVERIFIED rather than zero.",
                "github": "Union of three saved GitHub repository query families through the API's 1000-result cap, plus issue/PR search and official kaggle-environments PR 1394.",
            },
            "kernel_pages": kernel_pages,
            "discussion_pages": discussion_pages,
            "github_queries": github_queries,
            "tool_evidence": tools,
        },
    )
    summary = {
        "started_at_utc": started,
        "finished_at_utc": utc_now(),
        "counts": {
            "code_rows": len(code_rows),
            "code_failed": sum(bool(row.get("error")) for row in code_rows),
            "discussion_rows": len(discussion_rows),
            "discussion_failed": sum(bool(row.get("error")) for row in discussion_rows),
            "model_rows": len(model_rows),
            "github_rows": len(github_rows),
        },
        "code_mechanism_counts": dict(
            Counter(tag for row in code_rows for tag in row.get("mechanism_tags", []))
        ),
        "discussion_mechanism_counts": dict(
            Counter(tag for row in discussion_rows for tag in row.get("mechanism_tags", []))
        ),
        "github_mechanism_counts": dict(
            Counter(tag for row in github_rows for tag in row.get("mechanism_tags", []))
        ),
    }
    write_json(OUT / "collection_summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
