"""Map public Kaggriculture literal action tapes to replay-observed farm hashes.

This is a static, read-only analyzer. It never executes public notebook code.
"""

from __future__ import annotations

import ast
import base64
import gzip
import hashlib
import io
import json
import tarfile
import zipfile
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from kaggle.api.kaggle_api_extended import KaggleApi
from kagglesdk.kernels.types.kernels_api_service import ApiGetKernelRequest

ROOT = Path(__file__).resolve().parent
DOMINANT_FARM_SHA256 = "FC37F8688680DA949DB44C9444DCB9541488B4E10D9F432CC42648D6423F1B26"
MAX_DECODED_BYTES = 8_000_000


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest().upper()


def _farm_only(action: Any) -> Any:
    if not isinstance(action, dict):
        return action
    return {"farmer": action.get("farmer"), "hands": action.get("hands")}


def _farm_hash(actions: list[Any]) -> str:
    return _sha([_farm_only(action) for action in actions])


def _code_text(source: str) -> str:
    try:
        notebook = json.loads(source)
    except json.JSONDecodeError:
        return source
    if not isinstance(notebook, dict) or not isinstance(notebook.get("cells"), list):
        return source
    chunks: list[str] = []
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        raw = cell.get("source", "")
        chunks.append("".join(raw) if isinstance(raw, list) else str(raw))
    return "\n\n".join(chunks)


def _looks_like_actions(value: Any) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) not in {719, 720}:
        return False
    mappings = [x for x in value if isinstance(x, dict)]
    if len(mappings) < 600:
        return False
    return any(set(x).intersection({"farmer", "hands", "market"}) for x in mappings)


def _walk_values(value: Any, label: str) -> Iterator[tuple[str, list[Any]]]:
    if _looks_like_actions(value):
        yield label, list(value)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _walk_values(item, f"{label}.{key}")
    elif isinstance(value, (list, tuple)) and len(value) < 2000:
        for index, item in enumerate(value):
            yield from _walk_values(item, f"{label}[{index}]")


def _decode_archives(blob: bytes, label: str) -> Iterator[tuple[str, str]]:
    if len(blob) > MAX_DECODED_BYTES:
        return
    candidates: list[tuple[str, bytes]] = [(label, blob)]
    try:
        candidates.append((f"{label}:gzip", gzip.decompress(blob)))
    except (OSError, EOFError):
        pass
    for candidate_label, candidate in candidates:
        if len(candidate) > MAX_DECODED_BYTES:
            continue
        try:
            text = candidate.decode("utf-8")
        except UnicodeDecodeError:
            text = ""
        if text and ("SCHEDULE" in text or "farmer" in text or "market" in text):
            yield candidate_label, text
        try:
            with tarfile.open(fileobj=io.BytesIO(candidate), mode="r:*") as archive:
                for member in archive.getmembers():
                    if not member.isfile() or member.size > MAX_DECODED_BYTES:
                        continue
                    handle = archive.extractfile(member)
                    data = handle.read() if handle else b""
                    try:
                        yield f"{candidate_label}:{member.name}", data.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
        except (tarfile.TarError, OSError):
            pass
        try:
            with zipfile.ZipFile(io.BytesIO(candidate)) as archive:
                for member in archive.infolist():
                    if member.file_size > MAX_DECODED_BYTES:
                        continue
                    try:
                        yield f"{candidate_label}:{member.filename}", archive.read(member).decode("utf-8")
                    except UnicodeDecodeError:
                        continue
        except (zipfile.BadZipFile, OSError):
            pass


def _nested_sources(tree: ast.AST) -> Iterator[tuple[str, str]]:
    seen: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = node.value
        if len(text) >= 500 and text not in seen and (
            "SCHEDULE" in text or "farmer" in text or "market" in text
        ):
            seen.add(text)
            yield "string_constant", text
        compact = "".join(text.split())
        if len(compact) < 1000 or len(compact) % 4:
            continue
        try:
            decoded = base64.b64decode(compact, validate=True)
        except (ValueError, base64.binascii.Error):
            continue
        for label, nested in _decode_archives(decoded, "base64_constant"):
            if nested not in seen:
                seen.add(nested)
                yield label, nested


def _literal_tapes(source: str) -> list[dict[str, Any]]:
    queue: list[tuple[str, str]] = [("kernel", _code_text(source))]
    seen_sources: set[str] = set()
    rows: list[dict[str, Any]] = []
    while queue:
        source_label, text = queue.pop()
        text_sha = hashlib.sha256(text.encode("utf-8")).hexdigest().upper()
        if text_sha in seen_sources:
            continue
        seen_sources.add(text_sha)
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            value_node = node.value
            if value_node is None:
                continue
            try:
                value = ast.literal_eval(value_node)
            except (ValueError, TypeError, MemoryError, RecursionError):
                continue
            names = (
                [ast.unparse(target) for target in node.targets]
                if isinstance(node, ast.Assign)
                else [ast.unparse(node.target)]
            )
            label = f"{source_label}:{'|'.join(names)}"
            for tape_label, actions in _walk_values(value, label):
                variants = {
                    "literal": _farm_hash(actions),
                    "prepend_none": _farm_hash([None, *actions]),
                    "append_none": _farm_hash([*actions, None]),
                }
                rows.append(
                    {
                        "label": tape_label,
                        "length": len(actions),
                        "farm_hash_variants": variants,
                        "dominant_match_variants": sorted(
                            key for key, digest in variants.items() if digest == DOMINANT_FARM_SHA256
                        ),
                    }
                )
        queue.extend(_nested_sources(tree))
    unique: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in rows:
        key = (row["label"], row["length"], row["farm_hash_variants"]["literal"])
        unique[key] = row
    return list(unique.values())


def _get_source(ref: str) -> str:
    owner, slug = ref.split("/", 1)
    api = KaggleApi()
    api.authenticate()
    request = ApiGetKernelRequest()
    request.user_name = owner
    request.kernel_slug = slug
    with api.build_kaggle_client() as client:
        response = client.kernels.kernels_api_client.get_kernel(request)
    return response.blob.source


def _scan(ref: str) -> dict[str, Any]:
    try:
        source = _get_source(ref)
        return {
            "ref": ref,
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest().upper(),
            "literal_tapes": _literal_tapes(source),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001 - inventory records per-ref API failure.
        return {"ref": ref, "source_sha256": None, "literal_tapes": [], "error": repr(exc)}


def main() -> None:
    inventory = [
        json.loads(line)
        for line in (ROOT / "code_inventory.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    refs = [row["ref"] for row in inventory]
    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(_scan, ref): ref for ref in refs}
        for future in as_completed(futures):
            results.append(future.result())
    results.sort(key=lambda row: row["ref"])
    (ROOT / "tape_lineage.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in results),
        encoding="utf-8",
    )
    matches = [
        {"ref": row["ref"], "tape": tape}
        for row in results
        for tape in row["literal_tapes"]
        if tape["dominant_match_variants"]
    ]
    print(
        json.dumps(
            {
                "refs": len(results),
                "failed": sum(row["error"] is not None for row in results),
                "literal_tapes": sum(len(row["literal_tapes"]) for row in results),
                "dominant_matches": matches,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
