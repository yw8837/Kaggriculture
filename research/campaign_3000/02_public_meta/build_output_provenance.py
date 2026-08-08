"""Join downloaded output receipts to the exact current Code inventory rows."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def main() -> None:
    code = {
        row["ref"]: row
        for row in (
            json.loads(line)
            for line in (ROOT / "code_inventory.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    }
    outputs = [
        json.loads(line)
        for line in (ROOT / "kernel_output_manifest.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rows = []
    for output in outputs:
        inventory = code[output["ref"]]
        rows.append(
            {
                "ref": output["ref"],
                "kernel_id": inventory["id"],
                "current_version": inventory["version"],
                "current_source_sha256": inventory["source_sha256"],
                "current_source_bytes": inventory["source_bytes"],
                "page_best_score": inventory["best_score"],
                "page_best_score_version": inventory["best_score_version"],
                "license_name": inventory["license_name"],
                "license_url": inventory["license_url"],
                "code_inventory_retrieved_at_utc": inventory["retrieved_at_utc"],
                "output_started_at_utc": output["started_at_utc"],
                "output_finished_at_utc": output["finished_at_utc"],
                "output_file_count": len(output["files"]),
                "output_files_contract_sha256": hashlib.sha256(
                    _canonical(output["files"])
                ).hexdigest().upper(),
                "output_download_receipt_sha256": hashlib.sha256(_canonical(output)).hexdigest().upper(),
                "execution_status": "OUTPUT_DOWNLOADED_STATIC_ONLY_NOT_AGENT_EXECUTED",
            }
        )
    (ROOT / "kernel_output_provenance.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    print(json.dumps({"rows": len(rows)}, sort_keys=True))


if __name__ == "__main__":
    main()
