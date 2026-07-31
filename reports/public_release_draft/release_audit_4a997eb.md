# Public release audit at `4a997eb`

Status: **USER PUBLICATION AUTHORIZATION GRANTED; LOCAL PACKAGE SAFE; ACTUAL PUBLISH HOLD PENDING INDEPENDENT AUDITOR PASS.**

The user explicitly authorized the public-code workflow. This report still does not perform or
authorize the final publish action by itself: Discussion and Kaggle Code publication remain on
hold until the independent auditor passes this frozen release bundle. Save & Run, competition
submission, commit, and push are outside this draft.

## Identity and separation

- Public source: `artifacts/candidates/public_expansion_baseline/main.py`
- Source bytes: 16,365
- Source SHA-256: `BD32AEFDC00B1F0A41746EBACC4FCBF0AFF32AC061363179F15371B9ACE9A5C0`
- Formal private comparator: `artifacts/candidates/final_day_labor/main.py`
- Comparator SHA-256: `112AF9EC28030B53CE852927CEE986834F18F0245F3A88FB2E06F423291C9F8B`

The public policy deliberately omits the private final-day labor repair and uses a different,
weaker fixed herd/labor mix. The source diff is small (36 changed lines including the public
header), so this is a strength-separated public baseline, not a secrecy-separated architecture.
Do not describe it as a simplified copy of a current leaderboard agent.

An additional read-only diagnostic used seeds `29000-29007`, both seats, only to check the release
gap. The public baseline scored 1-15 with zero failures against the formal comparator, match score
0.0625 and mean margin -8,735.0625. Seat records were 0-8 and 1-7. This supports material local
separation; it does not estimate either agent's Kaggle rating.

## Exact public archive

Fixed public filename:

`Kaggriculture - Strong Expansion Baseline.tar.gz`

Use the already verified bytes of `dist/public/public_expansion_baseline.tar.gz`; renaming the
outer file does not change its content hash.

- Archive bytes: 4,685
- Archive SHA-256: `967A899A2BE149FF676B025E955AEDE2C42C0720C0A868428770A9B818F1144D`
- Sole member: root `main.py`
- Member size/SHA-256: 16,365 / `BD32AEFDC00B1F0A41746EBACC4FCBF0AFF32AC061363179F15371B9ACE9A5C0`
- Tar metadata: regular file, mode `0644`, uid/gid `0`, empty owner/group names, mtime `0`
- Verified: archived payload is byte-identical to the audited source.

The public artifact is intentionally unnumbered so private production submissions retain the
`Fa_01`, `Fa_02`, ... sequence without collision.

## Fixed publication identity and order

Publish the Discussion first, followed by the Kaggle Code artifact after the same audit gate:

1. Discussion: `Kaggriculture Baseline Guide | Expansion Agent & Reproducible Evaluation`
2. Kaggle Code: `Kaggriculture Agent | Strong Expansion Baseline`

Do not add an unverified rating, leaderboard band, or fixed-hand count to either title.

The existing Version 1 identity is verified from local original records:

- Slug: `yw8837/kaggriculture-strong-expansion-baseline`
- Version: `1`
- Visibility/status: `public` / `COMPLETE`
- Recorded title: `Kaggriculture | Strong Expansion Baseline`
- URL: `https://www.kaggle.com/code/yw8837/kaggriculture-strong-expansion-baseline`
- Competition submission: `false`
- Evidence: `publications/ledger.jsonl`,
  `kaggle_runs/public-expansion-baseline/kernel-metadata.json`, and
  `reports/public_expansion_baseline.md`

## Allowlist and mandatory exclusions

Archive allowlist: **root `main.py` only**.

Never include any of the following in the archive, notebook source, README, or Discussion:

- `artifacts/candidates/final_day_labor/`, `cow_tilt/`, or any other private candidate;
- `experiments/source_snapshots/`, Fa seed registries, scenario configs, thresholds, or raw results;
- `src/kaggriculture_lab/candidates/market_mpc.py`, `task_bundle.py`, or `rescue_greedy.py`;
- private opponent snapshots, downloaded public-opponent source, replay corpora, or `references/`;
- champion manifests, audit correspondence, submission inventories, API responses, or ledger internals;
- `.git/`, `.kaggle/`, environment files, usernames, tokens, credentials, or local absolute paths;
- tests, runtime profiles, private hashes, private ratings, unverified leaderboard claims, and package
  build machinery.

The audited `main.py` imports only `collections.deque`. A targeted text scan found no Fa seed,
private-candidate, opponent-source, credential, GitHub, or API-token material. Uses of the variable
name `private` refer only to the official game observation field.

## License risk

No repository `LICENSE`, SPDX header, or explicit license statement was found for this source.
The source is internally generated campaign code rather than either frozen public-opponent file,
and no private opponent bytes are present. Nevertheless, absent an explicit license, downstream
reuse rights are unclear.

- Kaggle-only publication can retain the current all-rights-reserved default if desired.
- Before a public GitHub release, the owner should explicitly choose a license; do not assign MIT,
  Apache-2.0, or another license without that decision.
- The tar must remain `main.py` only. Put any chosen license in the notebook/README or add only a
  comment header after rebuilding and rehashing the package.

## Release decision

The source and existing archive pass the local content-safety check. User publication authorization
is recorded as granted. Actual Discussion and Kaggle Code publication remains on hold solely until
the independent auditor returns PASS for this frozen release bundle; this draft does not publish,
commit, push, Save & Run, or submit anything.
