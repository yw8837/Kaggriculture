# Fa A/B frozen development evidence — 2026-08-01 KST

**Verdict: NO-GO for every new challenger. Sealed-strength and robustness pools remain closed.**

This is production-task evidence for review by the structurally separate auditor. It is not an
auditor-issued or auditor-approved report.

## Frozen boundary and claims

- Frozen implementation commit: `995359f25c96b44c2521cc211227ec1b0cd2272f`
- Remote branch: `agent/fa-ab-development-freeze`
- Draft PR: `https://github.com/yw8837/Kaggriculture/pull/1`
- Every raw report records that frozen Git head, candidate/opponent start/end hashes, a start
  receipt hash, both seats, normalized requested configuration, actual environment configuration,
  resolved hidden seed, and `sources_unchanged_during_run=true`.
- A1 claims only self-order exact pricing; it does not claim hidden opponent interleaving is exact.
- A2 is a visible-state nominal herd chooser, not an economic oracle.
- B1/B2 use a top-18-pruned exact DP, not an exact assignment over every generated task.
- A 1200+ ladder rating/top-3 strength was a target, never a verified claim.

Development config SHA-256:
`A72967570D0D825A9DB5745A57353AB389C70BFD5531F366B63D4B3E539C0B74`.
At-freeze seed registry SHA-256:
`384086676174BF7FE61E818C0A2217015FBE98394952AD253A2E443F543613F3`.
Post-development seed registry SHA-256:
`1261F8E6D034B7BBABDE636A6DF8A2EAFF1C12461443D3DE86A6BFFB9FF99319`.
Scenario config SHA-256:
`3BCB18188C1618236EF90F92F09D6D20DDF7178ADE625DC47D1A48ADAB7A16F2`.

## Preregistered development result

Each completed mode used 16 registered seeds, four opponents, and both seats: 128 games. The
direct subset is 32 games against `final_day_labor`. Selection required zero failures, direct
score >= 0.55, direct mean margin >= 0, and overall score >= 0.70.

| Mode | Games/fail | Overall score | Overall margin | Direct W-L | Direct score | Direct margin | Sum elapsed s | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| A0 control | 128/0 | 0.875000 | +44,896.48 | 16-16 | 0.50000 | 0.00 | 1,033.8 | control |
| A1 exact self market | 128/0 | 0.851562 | +43,310.16 | 13-19 | 0.40625 | -1,197.59 | 1,312.1 | NO-GO |
| A2 adaptive herd | 128/0 | 0.835938 | +43,270.92 | 11-21 | 0.34375 | -2,957.41 | 1,249.3 | NO-GO |
| A4 combined | 128/0 | 0.773438 | +40,519.03 | 3-29 | 0.09375 | -4,671.31 | 1,266.5 | NO-GO |
| B0 control | 128/0 | 0.875000 | +45,135.67 | 16-16 | 0.50000 | 0.00 | 1,034.1 | control |
| B1 global DP | 128/0 | 0.882812 | +45,631.72 | 17-15 | 0.53125 | -70.88 | 9,865.0 | NO-GO |
| B2 deadline DP | 128/0 | 0.890625 | +45,377.36 | 18-14 | 0.56250 | -169.81 | 8,169.3 | NO-GO |

B4's full 128-game matrix was not opened. Its one-replay 720-call hard runtime check already
failed: p50 34.5223 ms, p95 160.4761 ms, p99 189.8814 ms, maximum 254.4447 ms, invalid outputs 0.
The active runtime safety gate is maximum 100 ms. Running another roughly 30–40 minute matrix
could not repair that hard failure. B1 also failed runtime (p95 157.4655 ms, max 242.3382 ms),
and B2 failed runtime (p95 111.8131 ms, max 158.1921 ms).

## Immutable raw hashes

| Evidence | SHA-256 |
|---|---|
| A0 raw / receipt | `54EFB1E52AFC643DF1B911E249F236F7051546BDDCF9B727CEDB93146C14540A` / `9F5F32DBBA4BA2B3E2A7E98CB6B993CFF8CA224C0204A0FB8AD45D43A73D7D95` |
| A1 raw / receipt | `841FE5E5B0A1EC384B6B89FCB6A06BE99E265EFBAE8D7A2011ADD29997A0DDCA` / `9136D5FB5F845200D7368F0668AC2FFE4051819B560607EB1ECE4099A01BF4F2` |
| A2 raw / receipt | `E1F95C6723CA23F2C5EFD2269812156829DB00839F848D1AD6F46797A8ED7009` / `EC5D58F3B4A1F011EDF09637AEEEA588C212CB0E0521E36261FB7D8E7A0DE813` |
| A4 raw / receipt | `E066E00E59EF8CCF8B8E4F0A5D6B9E0A9D458D727E9A1828925C2F82635494F7` / `A1301601A74562776288EA07DDF4204A51316365647F52BF18A4D07A541FB7B0` |
| B0 raw / receipt | `82F5D89EA9E21D303F54E1B3E6F52818E9D6A12D7279DA54C55C718FD514EAEF` / `73BEC7086D1A9E03479531B7F983C53149713C1513962DD9F3B41E604F53E67D` |
| B1 raw / receipt | `3B9BE6A6865CE7C229A5F77D962920E5DB5B8D58E9E8C6E0F969F48B3670B524` / `353F35CDEC34C31EF31D8798AEF7E165F2FD59CBE49B1BA2F994C85C6972BA66` |
| B2 raw / receipt | `4BBAAA81ADDFD581EF69E3F2B887A679589A612DB10373E1F730530658C69647` / `DE0A66E9EC1247BDE398EBB1D2F1C58D97E4EDE5FE5469F01406610DA4C2F9E6` |
| B1 / B2 / B4 runtime | `D6127F39D5B9B6EFEFF410CA4874EC1BD33EC642B51C88381D863A2258ACEB63` / `3CE81CC6D517F93B29774BE6F1CA2AADD10F8B8EF654810FA09405C967CC2F07` / `05AFF707A12B3A0702CAFBF07731A2666B9FE5BC5868F6A905E4802CDD81E5E0` |

## Scenario and remediation proof

- The focused runner test intercepts the exact configuration passed to `make()` and verifies its
  row hash. Another focused test constructs the official environment for every registered
  `marketParams`/town-demand override, verifies the interpreter clears the visible seed, and
  verifies the resolved seed is retained in `env.info` and raw rows.
- The champion resolver packages only `current_champion=final_day_labor`, verifies the source hash,
  deterministically rebuilds the artifact, and verifies artifact SHA-256
  `59281C6434D6D48C429DDC7950266A1083454978A0425D143480E9BB75559670`.
- The complete API snapshot preserves 2 submissions x (18 PUBLIC + 1 VALIDATION) = 38 COMPLETE
  episodes and is hash-registered in the append-only submission ledger.
- Project `AGENTS.md` remains deliberately unchanged under the global no-mid-session-edit rule;
  the stale 403 statement and next-session correction are explicit in the current-state document.

## Requested auditor decision

1. Verify F6–F9 remediation and this development provenance.
2. Keep all registered sealed-strength/robustness pools closed; no challenger is eligible.
3. Approve or reject this next boundary proposal:
   - Fa_01 safety axis: retain `final_day_labor` as the private candidate, then evaluate it on a
     fresh auditor-approved confirmation pool because every A challenger regressed.
   - Fa_02 challenger: replace exponential global DP with one bounded greedy change that only
     prioritizes officially rescuable second-miss WATER/FEED tasks; require a new auditor-approved
     development/confirmation pool because B development seeds are consumed.
