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
license and notice, deterministic three-member archive metadata, executable notebook packaging,
final private release manifest/spec plus
notebook/prepush pins, private-source separation records, disabled external actions, score-claim
boundary, public-copy leak markers, title selection, and every entry in `SHA256SUMS`. It also
enforces the fixed Discussion-first, public-Code-second order.

## Two-build byte identity

Two consecutive self-contained `build` runs compared 20 files and returned zero hash drift:

```text
artifact/kaggriculture_fixed_trace_safety_baseline.tar.gz  5DBD64463878A52ED7C47C8D60BCA3AE9FAC7E29B775E7FADB08F0CC7670A8B6
external_action_payload.json                              CA4ECDBB22ED0CB2DAE183A24DFDCF8D6362C3EE7DFCC8AB61CFE93E26F33D14
kaggle_code_draft/kaggriculture-fixed-trace-safety-baseline.ipynb  802C785A6882E14574E6EB612ED9C5BE60412E9B51A14CA13A51ECCB8B7EC641
kaggle_code_draft/kernel-metadata.json                    A6550E25FE46FBB82E6722AA73D1458F1850D2B621ABCADC34F286EDAC0FFC7F
public_source/main.py                                     81159A18DF3CD1A5CAABE5EDBBA0A597561775F77A49465FA39DF6802A706922
release_manifest.json                                     855A4E297305AA2B3F6BB6B816DA7F1140AEEEB15903C80197576A52054EBA72
```

The archive member list was exactly `['main.py', 'LICENSE', 'NOTICE.md']`. Every member used
mode `0644`, uid/gid/mtime `0`, empty uname/gname, and byte-exact source/license/notice payloads.

## Secret and external-action scan

```text
public_secret_hits= {'private_key': [], 'aws_key': [], 'github_token': [], 'slack_token': [], 'bearer': []}
metadata_is_private= False
metadata_enable_internet= False
external_calls_performed= []
enabled_actions= [False, False]
archive_members= ['main.py', 'LICENSE', 'NOTICE.md']
```

The scan covered the public notebook, kernel metadata, Discussion, title file, notice, and archive
payload. It is a focused pattern scan, not a universal proof that no conceivable secret format
exists.
