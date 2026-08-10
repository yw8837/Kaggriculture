# Autoresearch mission: Kag_03/Kag_04 direct Kag_01 improvement

- Mission: produce two bounded observable-state candidates and retain only a
  candidate that beats exact Kag_01/Tetsu v16 in the paired direct diagnostic.
- Controls: exact Tetsu v16, both seats, historical already-consumed seeds
  50000-50015. This diagnostic cannot support promotion or seed opening.
- Candidate A: actor-local weed repair only.
- Candidate B: safe late-inventory liquidation only.
- Evaluator: `evaluate_diagnostic.py` produces JSON with required `pass` and
  numeric `score`.
- Start: 2026-08-10T03:10:00Z.
- Max runtime: 90 minutes.
- Stop: both candidates pass, max runtime is reached, the user cancels, or a
  safety/integrity invariant fails.
- All six catalog-declared fresh ranges and all Kaggle mutations remain forbidden.

Every experiment must append one evaluation JSON and one decision-log entry.
No result from this mission may be called independent audit evidence.
