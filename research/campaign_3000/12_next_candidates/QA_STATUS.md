# Kag_03 / Kag_04 QA status

This is a local construction checkpoint, not an execution or release verdict.

## Completed without opening seeds

- Kag_03 builder pins the exact Kag_01 control SHA and emits only a SELL-order permutation overlay.
- Static adversarial checks cover control-prefix equality, forbidden observation fields, forbidden-field metamorphism, non-market equality, control-object immutability, legal fallback, and runner-compatible metrics hooks.
- Kag_04 source is a materialized implementation-freeze input: `kag_04/main.py`, 31,455 bytes, SHA-256 `797E2BFE...DA20F191`. Its only recorded delta is exact Tetsu `COW2/SHEEP2 -> COW1/SHEEP3`; seed authority remains CLOSED.
- JSON parsing and Python compilation passed for all 18 Kag_03/Kag_04 planning, source, test, and receipt files.
- Focused pytest passed after exact source/environment pin hardening: `34 passed in 0.64s` across Kag_03, Kag_04, and the shared development gate/catalog tests. The sandbox-safe run used the bundled Python 3.12 runtime, the existing `.venv` site-packages, and a repo-local `--basetemp`.
- Ruff passed for both builders, both candidate test files, and the shared reservation/gate tooling.
- The bundled Python runtime materialized and compiled Kag_03, verified one legal SELL permutation with exact farmer/hands and control-object preservation, and verified the runner-compatible metrics hook. Frozen input source: `9034026D...A186FE36`, 33,206 bytes.
- Final source-materialization reservation adapter result: `all_pools_collision_free=true`, 1,696 observed input seeds, observed digest `B918500D...D98446FD`, evidence-file digest `62482780...A19F2A39`, 397 scanned text files, 202 seed-bearing files, and 483 enumerated files.
- The development-only plan records the exact engine/configuration, runner, two candidates, five opponent paths/hashes/bytes, default scenario, both seats, exact runner commands, and runner-started/raw/gate receipt paths. The gate rejects self-consistent candidate/opponent swaps and typed environment-mapping mutations. It does not authorize either command.
- A development PASS now requires beating the direct Kag_01/Tetsu v16 lane on both strict conditions: match score `> 0.50` and mean margin `> 0.0`. Equality or non-inferiority is `DEVELOPMENT_NO_GO`; no result guarantees a 3000 score.

## Still required before any seed-opening handoff

1. Repeat `seed_reservation.py::validate` only if a later freeze input changes. It excludes only the three declared reservation-derived files.
2. Make a clean two-stage S/E freeze with runner, opponent, gate, environment, source, and test hashes.
3. Obtain an independent-auditor exact OPEN authority before any development seed.

No OS approval prompt, network action, fresh seed, SaveRun, upload, or competition submission was used for this checkpoint.
