# Campaign 3000 development results

This directory is the tracked, byte-exact closure evidence for the two authorized local
development runs. Each slot manifest pins exactly six original files by path, byte count, and
SHA-256. The production validator reparses every raw row, recomputes the development gate, and
requires typed JSON equality with the tracked `gate.json`.

- `Kag_01`: 128 games, strict `PASS`, lifecycle `CONSUMED_PASS`.
- `Kag_02`: 128 games, strict `NO_GO`, lifecycle `CONSUMED_NO_GO`.
- `Kag_01` confirmation/robustness remain `CLOSED`; `Kag_02` later pools are
  `RETIRED_UNUSED`. All external actions remain `HOLD`.

The exact subprocess stderr byte streams were not saved. The observed OpenSpiel startup noise was
benign, but this bundle makes no immutable zero-stderr claim and the 256 fresh games were not
rerun.

## Privacy boundary

The byte-exact receipts and reports contain the local Windows workspace path and username. The
repository is private, and these files must stay private. They are forbidden from every Kaggle
archive, notebook, Discussion, public Code payload, or other publication. Release tests scan the
actual private/public upload payloads for `10_results`, `C:\\Users\\`, and the local username.

`DEVELOPMENT_CLOSED` is an evidence state, not an independent-auditor release. The separate auditor
task must inspect the frozen close commit and issue a new exact verdict before any Save & Run or
publication. No post-run auditor receipt is claimed in this directory.
