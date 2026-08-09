# Private SaveRun post-run receipts

This directory records the two externally completed, independently rechecked private
Save & Run operations that followed the frozen `b13eeb2` package build.

- `Kag_01` version 1 is the strict-development-PASS private candidate.
- `Kag_02` version 1 remains exploratory and non-promotion; its strict development verdict
  is still `NO_GO`.
- Both remote workers were `COMPLETE`, private, internet-disabled, and their downloaded
  archives were byte-exact with the approved local archives.
- No competition submission was created. The independent read-only snapshot still contained
  exactly 22 historical submissions.
- No second push, confirmation/robustness run, Discussion publication, public Code push, or
  competition submission is authorized by this receipt.

`research/campaign_3000/06_candidates/lifecycle.json` remains the immutable development-close
ledger. Its `external_actions: HOLD` means there is no *additional* external-action authority;
this directory separately records the two already authorized and completed SaveRuns.
