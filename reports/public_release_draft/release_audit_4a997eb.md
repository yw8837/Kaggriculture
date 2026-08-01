# Public release safety review

Status: **LOCAL UPDATE PREPARED; NO EXTERNAL ACTION; PUBLISH HOLD REMAINS.**

This review covers only the public baseline source, explanatory notebook, Discussion draft, and
deterministic package. It does not publish, push, Save & Run, or submit anything.

## Public identity

- Code title: **Kaggriculture Agent | Early Expansion & Mixed-Farm Baseline**
- Discussion title: **Kaggriculture Agent Guide | Expansion Strategy & Both-Seat Evaluation**
- Public source bytes: 16,365
- Public source SHA-256: `BD32AEFDC00B1F0A41746EBACC4FCBF0AFF32AC061363179F15371B9ACE9A5C0`
- Public archive bytes: 4,685
- Public archive SHA-256: `967A899A2BE149FF676B025E955AEDE2C42C0720C0A868428770A9B818F1144D`
- Archive member allowlist: root `main.py` only

The public source and archive behavior are unchanged. The notebook update adds explanation,
evaluation guidance, and package verification only.

## Public-content allowlist

- the exact public `main.py` source;
- the two public checksums above;
- descriptions of behavior visible in that source;
- general both-seat evaluation methodology;
- honest limitations and license status;
- deterministic packaging code and its generated verification output.

## Mandatory exclusions

Do not include unpublished agent code or strategy, internal experiments, reserved evaluation
inputs, non-public performance results, internal repository provenance, credentials, account
secrets, or audit correspondence in any public cell, output, attachment, README, or Discussion.

The notebook archive must remain root `main.py` only. Generated notebook outputs must be scanned
again before any later publication action.

## License status

No standalone reuse license has been selected. The public text states this directly and does not
grant a license on the owner's behalf.

## Decision

The local explanatory update is ready for focused tests and an independent content review. Actual
publication remains disabled until the recorded release gate is satisfied.
