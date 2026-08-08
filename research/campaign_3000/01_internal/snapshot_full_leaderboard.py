from __future__ import annotations

import csv
import hashlib
import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ARCHIVE = ROOT / "kaggriculture.zip"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest().upper()


def main() -> None:
    archive_raw = ARCHIVE.read_bytes()
    with zipfile.ZipFile(ARCHIVE) as bundle:
        names = bundle.namelist()
        if len(names) != 1:
            raise ValueError(f"expected one member, got {names}")
        member_name = names[0]
        member_raw = bundle.read(member_name)
    rows = list(csv.DictReader(io.StringIO(member_raw.decode("utf-8-sig"))))
    our = [row for row in rows if row["TeamId"] == "16630689"]
    if len(our) != 1:
        raise ValueError(f"expected one account row, got {len(our)}")
    payload = {
        "schema_version": 1,
        "observed_at_utc": datetime.now(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z"),
        "source_command": "kaggle competitions leaderboard kaggriculture --download --path research/campaign_3000/01_internal -q",
        "source_url": "https://www.kaggle.com/competitions/kaggriculture/leaderboard",
        "population_rows": len(rows),
        "archive": {
            "path": ARCHIVE.relative_to(Path.cwd()).as_posix(),
            "bytes": len(archive_raw),
            "sha256": sha256(archive_raw),
        },
        "member": {"name": member_name, "bytes": len(member_raw), "sha256": sha256(member_raw)},
        "our_team": our[0],
        "top25": rows[:25],
    }
    output = ROOT / "leaderboard_full_snapshot.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    raw = output.read_bytes()
    print(json.dumps({"path": output.as_posix(), "bytes": len(raw), "sha256": sha256(raw), "our_team": our[0]}))


if __name__ == "__main__":
    main()
