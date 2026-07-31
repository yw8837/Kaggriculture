# Portfolio case study — working draft

## Challenge

Build a competitive autonomous agent for Kaggriculture, a 720-turn simultaneous farming economy,
with a long-term final top-three target. The key process constraint is to avoid repeating a previous
campaign's leaderboard overfitting and unverifiable claims.

## What was built

- A pinned Python environment and exact official-simulator test gate
- A both-seat paired evaluation harness with clustered uncertainty
- Public-agent extraction and top-replay trajectory analysis
- Immutable experiment, submission, publication, and audit records
- Deterministic one-file packaging with source/archive SHA-256 identity
- Private Kaggle Save & Run verification and a private GitHub evidence repository
- An independent adversarial audit lane with no edit, publish, submit, or Git authority

## Demonstrated outcomes

- Official environment tests and project tests reproduce locally.
- Two initial unnumbered competition submissions completed; their ratings remain volatile early-field
  signals, not stable strength estimates.
- A public Discussion and readable Code notebook were released in the requested order; Kaggle output
  bytes match the local frozen artifact.
- Fa_01 reached private Save & Run with exact hash equality, then was honestly rejected when a later
  preregistered sealed gate failed.

## Engineering lesson

A bot campaign needs stronger evidence hygiene than a normal model leaderboard. A candidate can have
a positive point estimate and still fail promotion when the lower confidence bound, worst case, or a
preregistered threshold fails. Preserving that negative result is more valuable than retrofitting a
gate around it.

## Status

This is an active campaign. Stable 1200-level strength and final top-three placement are not yet
demonstrated and must not be presented as achieved portfolio results.
