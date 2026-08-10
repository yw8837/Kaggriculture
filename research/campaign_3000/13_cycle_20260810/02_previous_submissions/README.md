# Kag_01 / Kag_02 previous-submission comparison

This is an append-only, evidence-bound comparison prepared on 2026-08-10 for
the next-candidate cycle.  It does not run an episode, upload, Save & Run,
submit, or publish anything.

The primary result is in [comparison.md](comparison.md); pinned input hashes
are in [evidence_manifest.json](evidence_manifest.json).

## Status at this capture

- `Kag_01` is an exact Tetsu v16 local-development control and had a strict
  local `PASS`; its private version-1 Save & Run archive was later reported
  byte-equal to the approved archive.
- `Kag_02` is the exact Kaito v22 local-development candidate and had a strict
  local `NO_GO`; its private version-1 Save & Run was runtime-verified but is
  explicitly non-promotion.
- Neither item is a competition submission, so neither has a competition
  rating/time series or Kaggle episode/replay population attributable to its
  archive.

## Current-official-data boundary

One read-only current Kaggle CLI request was attempted during this capture.
It failed before the API client initialized because `uvx` could not initialize
`C:\\Users\\최용우\\AppData\\Local\\uv\\cache` (`os error 183`).  No Kaggle
response, episode metadata, replay payload, leaderboard, or submission row was
received; no retry or privilege escalation was made.  Consequently, all
official data cited here are frozen local captures with their cutoff times,
never labelled current.

The preserved public replay corpus contains 89 other episodes (44 sampled
account submissions and 45 sampled top-25 episodes), not Kag_01/Kag_02.  Its
719-action alignment rule is retained as an analysis contract, but it cannot
produce an action comparison for these two private Save & Runs.
