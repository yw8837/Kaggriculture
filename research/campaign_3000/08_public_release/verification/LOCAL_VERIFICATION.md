# Local public-release verification receipt

Date: 2026-08-09 KST. Scope: `research/campaign_3000/08_public_release/**` only.

No Kaggle call, upload, Code push, Discussion publication, browser action, Save & Run, competition
submission, commit, or push was performed.

## Focused tests and Ruff

```text
> .\.venv\Scripts\python.exe -m pytest -q -p no:cacheprovider research\campaign_3000\08_public_release\test_release.py
..........                                                               [100%]
10 passed

> .\.venv\Scripts\python.exe -m ruff check research\campaign_3000\08_public_release
All checks passed!
```

The tests recheck the original engine-summary/comparison hashes, exact G1 byte identity, Python
compile, executable notebook guard probe, output-free/public notebook metadata, full embedded
license and notice, deterministic archive metadata, final private release manifest/spec plus
notebook/prepush pins, private-source separation records, disabled external actions, score-claim
boundary, public-copy leak markers, title selection, and every entry in `SHA256SUMS`. It also
enforces the fixed Discussion-first, public-Code-second order.

## Two-build byte identity

Two consecutive self-contained `build` runs compared 20 files and returned zero hash drift:

```text
artifact/kaggriculture_fixed_trace_safety_baseline.tar.gz  2730084026B6C0EA68D1D54FF469E1B80D9ABF9BEF43285B15366CF13CF8ACCB
external_action_payload.json                              18951EA710C788E050EA29600B2A97AD27ADEBBD0F4B4D1FC19152FD7837099D
kaggle_code_draft/kaggriculture-fixed-trace-safety-baseline.ipynb  F24F4939C8EC591D5794C650923E583658F0BE05E47FA7A6F049D53664F74153
kaggle_code_draft/kernel-metadata.json                    A6550E25FE46FBB82E6722AA73D1458F1850D2B621ABCADC34F286EDAC0FFC7F
public_source/main.py                                     81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922
release_manifest.json                                     582357B41C64D5D03960FB9AC01FADA1C2444AA8B23EAAD71971AF480E955078
```

The archive member list was exactly `['main.py']`, and its payload hash matched the public source.

## Secret and external-action scan

```text
public_secret_hits= {'private_key': [], 'aws_key': [], 'github_token': [], 'slack_token': [], 'bearer': []}
metadata_is_private= False
metadata_enable_internet= False
external_calls_performed= []
enabled_actions= [False, False]
archive_members= ['main.py']
```

The scan covered the public notebook, kernel metadata, Discussion, title file, notice, and archive
payload. It is a focused pattern scan, not a universal proof that no conceivable secret format
exists.
