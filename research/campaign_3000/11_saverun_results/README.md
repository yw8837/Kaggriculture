# Private SaveRun post-run receipts

This directory records the two externally completed, independently rechecked private
Save & Run operations that followed the frozen `b13eeb2` package build.

- `Kag_01` version 1 is the strict-development-PASS private candidate.
- `Kag_02` version 1 remains exploratory and non-promotion; its strict development verdict
  is still `NO_GO`.
- Both remote workers were `COMPLETE`, private, internet-disabled, and their downloaded
  archives were byte-exact with the approved local archives.
- `auditor_deliveries.json` preserves the complete final-message text for the one-time release,
  postrun `COMPLETE_VERIFIED`, and later publication `HOLD`, together with the main task's recorded
  auditor thread/host/turn/item identity and exact UTF-8 text SHA-256. Full `read_thread` envelopes
  were not retained, so the file does not claim cryptographic provider attestation beyond those
  recorded delivery identities.
- No competition submission was created. The independent read-only snapshot still contained
  exactly 22 historical submissions.
- No second push, confirmation/robustness run, Discussion publication, public Code push, or
  competition submission is authorized by this receipt.

`research/campaign_3000/06_candidates/lifecycle.json` remains the immutable development-close
ledger. Its `external_actions: HOLD` means there is no *additional* external-action authority;
this directory separately records the two already authorized and completed SaveRuns.

The two August 8 timestamps are retained only as
`locally_observed_push_or_complete_time_utc`. Their raw Kaggle GetKernel envelopes were not saved,
and a later independent read returned a different mutable `lastRunTime`; consequently these values
are not presented as authoritative live GetKernel `lastRunTime` fields.

The latest independently delivered publication verdict is explicitly `HOLD` for both Discussion
and public Code. Recording it here grants no publication authority.
