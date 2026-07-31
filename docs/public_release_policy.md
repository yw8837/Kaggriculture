# Public release policy

The private record repository contains production research and must remain private.

- Production filenames follow `Fa_XX - Short Description.tar.gz`.
- The two initial unnumbered submissions are baseline probes and do not consume the Fa sequence.
- Save & Run is the default stopping point. Submission requires an explicit user instruction.
- Public notebooks and Discussions use a separately packaged `Fa_XX_public` ablation that is
  measurably weaker than the active private champion.
- Public material must say that it is a strong public baseline, not the current private champion.
- Before publication, verify the public artifact locally, quantify its gap from the champion,
  scan it for private strategy/code, and obtain explicit user approval for the exact release.

## Rolling release gate

Public strength may rise only after the private ladder strength is stable. A release candidate
must satisfy all of the following before publication:

- It is at least one production generation behind both active private agents.
- It loses at least 60% of a 96-game paired, both-seat comparison against the private champion.
- The private rating lead over the intended public rating band is at least 100 points in three
  consecutive snapshots, and each active private agent has at least ten completed public games.
- It has zero local failures and passes the same runtime, packaging, and secret-leak checks as a
  production artifact.
- Its notebook and Discussion describe it as a public baseline with known limitations, never as
  the current best private agent.

The first intended public band is approximately 1050 while private agents target a stable 1150+
band. Later public bands can move upward only after the private floor moves upward first.
