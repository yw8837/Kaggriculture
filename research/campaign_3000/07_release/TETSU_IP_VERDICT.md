# Tetsu v16 IP / provenance verdict

Evidence cutoff: 2026-08-09 KST (live retrieval `2026-08-08T18:53:47Z`).

Verdict: `CONDITIONAL_PASS_PRIVATE_SAVERUN_ONLY`. This is an evidence-backed
release gate, not legal advice and not authorization to call Kaggle. The exact
Tetsu bytes may enter `Kag_01` only while every condition below remains true.

## Exact artifact identity

- Kaggle ref: `tetsutani/adaptive-farming-strategy-for-kaggriculture`
- Official page: <https://www.kaggle.com/code/tetsutani/adaptive-farming-strategy-for-kaggriculture>
- Kaggle kernel id: `129434690`
- Current API version: `16`; `isPrivate=false`
- API notebook source SHA-256: `81DA966E92F9889836E22142FD7A60CEBEAEE81CB3C52661AA286AC8C727BAF9`
- Exact extracted `main.py`: `dist/campaign_3000_public_agents/tetsutani__adaptive-farming-strategy-for-kaggriculture.py`
- Exact `main.py` SHA-256: `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`
- Extraction: notebook cell 14, `WRITEFILE_MAIN_PY`, recorded in
  `dist/campaign_3000_public_agents/manifest.json`.
- Live page capture digest: 5,128 UTF-8 bytes,
  `56128BD9BBD09F0F4D48A19E3304690570F23776045A045665124F351432D55F`.
  The page states Apache 2.0 and links to
  <http://www.apache.org/licenses/LICENSE-2.0>.

The Kaggle SDK returned v16 and the notebook source hash above on the evidence
cutoff. That source hash equals the locally archived v16 notebook hash. The
Apache statement is page-level. Treating the exact cell-14 artifact as covered
by it is a documented mapping inference supported by the exact source and
extraction hashes; it is not an artifact-embedded SPDX declaration.

## Required derivative lineage

The embedded 9,297-byte Base85 route is byte-identical across these exact
artifacts, SHA-256
`EDC3163ED477B6F9EF70FA8F7A212A4F8179C4FA281008D400EDF6EE488906C2`:

- Tetsu v16: main SHA-256
  `997E6BFC5234534E246E945BC61C87858EBF997AB85B0A5C9427DD4ED710F1B6`.
- Boatlee v4, `boatlee/84-84-base-public-holdout-v14-clone-preemption`,
  <https://www.kaggle.com/code/boatlee/84-84-base-public-holdout-v14-clone-preemption>,
  kernel id `130060645`, notebook source SHA-256
  `9AB82FD86A9F3BE300EC4EE2AE2A6A9BDABC5A1232926ED57A5E3B645DDA11E0`,
  extracted-agent SHA-256
  `A7F827B9438885B34B7FD5BF8165458A72F8BB83031A288DD4640F21ADE3294B`.
- Flex v42, `flexonafft/kaggriculture-adaptive-replay-agent`,
  <https://www.kaggle.com/code/flexonafft/kaggriculture-adaptive-replay-agent>,
  kernel id `129367546`, notebook source SHA-256
  `25D06F9006C0A6A6185E5A9D5D92AA27592818096C0E9E76CEED8A0BEE854A51`,
  extracted-agent SHA-256
  `3C41010DE37114C082D481E4A4C3E42CA5148E826A140E2AA02964ACA8636DD8`.

Boatlee and Flex differ only by Boatlee's six-line explanatory docstring in
the inspected runtime body. Boatlee's notice says the field/labor route is
shared by Kakuteki and mrgrishninsb, and that the runtime preserves public V23
actor-local weed repair, nonlinear price-impact SELL ordering, and frontier
terminal cleanup. Tetsu retains that route and extends the future-sale search
to ordered horizons 3 -> 2 -> 1 with exact repayment. It must not be described
as clean-room or independently authored.

At the live cutoff, the Boatlee and Flex official pages also displayed Apache
2.0. Their captured page digests were respectively
`C68675A3B91A9BC257B2C683D1206B640C92D915843F608FB80D4FE18812D8AF`
(4,308 bytes) and
`25A6D44854B9FBB06FEC60B849A643A71A45AF7F652638F78D1289DFFF27C1E0`
(3,327 bytes). This strengthens the lineage audit but does not erase the
attribution duty.

## Score boundary

The live Tetsu page linked `2703.1 V15` (`scriptVersionId=341037424`). That is
not evidence for v16. No public score is claimed for the exact v16 payload.
Local engine-screen results are consumed-seed, non-promotion evidence only.

## Blocking release conditions

1. `main.py` must remain byte-exact at `997E...F1B6`; any edit reopens review.
2. The archive must contain the complete Apache-2.0 `LICENSE` text.
3. `ATTRIBUTION.md` must preserve the Tetsu, Boatlee, Flex, Kakuteki,
   mrgrishninsb, public V23, and frontier-cleanup lineage above, including exact
   refs, versions, notebook/source hashes, agent hashes, and common-route hash.
4. Notebook metadata must set `is_private=true` and `enable_internet=false`.
5. The wrapper may only emit the prebuilt payload; it may not submit, publish,
   access the network, rebuild, or alter the agent.
6. Pre-push verification must confirm archive members and hashes, compile
   `main.py`, prove deterministic rebuilds, and show no external action was run.
7. Any mismatch, missing notice, later license contradiction, or attempt to use
   the v15 score as a v16 score changes this verdict to `HOLD`.

## Rules basis and claim type

- Verified official rule URL:
  <https://www.kaggle.com/competitions/kaggriculture/rules>.
- The captured rules response states that public Competition Code shared in a
  competition notebook is deemed licensed under an OSI-approved license that
  does not limit commercial use, and that open-source code used for a
  submission must meet that standard.
- The same rules list winner license `CC-BY 4.0` and Competition Data access/use
  `Apache 2.0`; neither label by itself is the Tetsu artifact license.
- The direct artifact-license evidence is the notebook page's Apache-2.0
  statement. The exact-byte coverage conclusion is the mapping inference
  described above.

