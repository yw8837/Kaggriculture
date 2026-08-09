# Kaggriculture public release draft: fixed trace plus safe selling

Status: **local draft only; no upload, publication, browser action, Save & Run, or competition
submission has been performed.**

This directory is a self-contained, audit-ready public Kaggle Code plus Discussion release. The
public agent is byte-identical to the audited Fa04 G1 source, SHA-256
`81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922`. It does not contain the
Kag_01/Tetsu, Kag_02/Kaito, or Ray production bytes.

## Selected titles

- Kaggle Code: **Kaggriculture Agent | Fixed Trace + Safe Selling**
- Discussion: **Kaggriculture Strategy | Replay Agents, Sell Guards & Engine Drift**

The exact alternatives and selection rationale are in `titles.json`. Both selected titles
front-load `Kaggriculture`, state the search intent and mechanism, and avoid a score claim.

## Why this stays below the private agents

The exact designated Kag_01 and Kag_02 sources each beat this public source in all 16 local games
under `kaggle-environments==1.32.6` (eight consumed seeds, both seats). Across the wider five-agent
screen, the public source lost all 80 games. All games were valid and had no recorded runner or
hidden-abnormal-status failure.

This is exact local head-to-head separation. It is not promotion evidence or a ladder-rating
estimate because the seeds were consumed development seeds and the opponent set was selected.
The comparison is bound to the exact designated private source hashes. The final local-only private
archives are also pinned in the release evidence: Kag_01
`184F687C474933A7215DB97E8C5A5F823AE79233EEA42D04B70EABC001BF9E16` and Kag_02
`37EA53D3046E3D1DA914F8A89C6F4BB02E240E1BB85857BDA149273FC4DD974C`. This does not claim that
either private archive was uploaded or submitted. Their final local notebook, metadata, and
disabled prepush hashes are bound in `release_manifest.json` and `external_action_payload.json`.

## Score claim versus remote evidence

- Score claim for this exact release: **none**.
- Expected Kaggle rating: **unknown**.
- Remote evidence: an API snapshot associated submission `55171193` and filename
  `Fa_04 - Frontier Trace Guard.tar.gz` with `1317.1`.
- Provenance limit: Kaggle does not expose the historical uploaded archive bytes, and no local
  same-named archive was available. Therefore `1317.1` is not attributed to this exact public
  source and is absent from the public title, notebook narrative, and Discussion.

## Engine 1.32.6 lesson carried into the release

The saved same-cell diagnostic compared 20 games under 1.32.2 and 1.32.6. All 20 final reward
tuples changed and 16 of 20 win/tie/loss outcomes changed. The only resolved default configuration
change was `townCenterSellInterval: 12 -> 24`. The notebook therefore teaches version pinning,
resolved-config capture, both-seat pairing, and strict separation between local evidence and a
remote score.

## Release contents

- `public_source/main.py`: exact allowlisted G1 source.
- `artifact/kaggriculture_fixed_trace_safety_baseline.tar.gz`: deterministic root archive with
  `main.py`, the full Apache-2.0 `LICENSE`, and exact `NOTICE.md`.
- `kaggle_code_draft/*.ipynb`: deterministic, output-free public notebook.
- `kaggle_code_draft/kernel-metadata.json`: public metadata draft; never pushed by the builder.
- `discussion_draft.md`: publication-ready educational Discussion body.
- `evidence/*.json`: exact hash-pinned engine 1.32.6 evidence and private local-package manifest.
- `external_action_payload.json`: disabled, exact external-action handoff and receipt contract.
- `release_manifest.json` and `SHA256SUMS`: provenance, evidence boundaries, and exact hashes.
- `LICENSE` and `NOTICE.md`: Apache-2.0 license and upstream attribution.

The companion Discussion links the already-public reactive
[Strong Expansion Baseline](https://www.kaggle.com/code/yw8837/kaggriculture-strong-expansion-baseline)
so readers can compare an open-loop trace with a shorter reactive policy.

## Deterministic local rebuild

From the campaign project root:

```powershell
python research/campaign_3000/08_public_release/build_release.py build
python -m pytest -q research/campaign_3000/08_public_release/test_release.py
python -m ruff check research/campaign_3000/08_public_release
```

`bootstrap` is the maintainer-only refresh step that reads outside this directory: it accepts only
the hash-pinned G1 source, Apache license, engine evidence, and private package identity manifest.
The default `build` command uses only the self-contained copies. The builder has no network or
Kaggle client code.

## Publication hold

`external_action_payload.json` is deliberately disabled. A later publisher must obtain fresh,
exact authorization, rerun the leak/hash audit, publish the Discussion first, push public Code
second without a competition submission, and capture all remote receipts listed in that payload.
