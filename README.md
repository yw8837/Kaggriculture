# Kaggle Kaggriculture Simulation — Bronze Medal 🥉

[![Kaggle Bronze Medal](https://img.shields.io/badge/Kaggle-Bronze%20Medal%20(Top%205.5%25)-CD7F32?logo=kaggle&logoColor=white)](https://www.kaggle.com/competitions/kaggriculture/leaderboard)
[![Final Rank](https://img.shields.io/badge/Rank-557%20%2F%2010%2C148%20Teams-blue)](https://www.kaggle.com/competitions/kaggriculture/leaderboard)
[![Final Score](https://img.shields.io/badge/Score-4498.3-green)](https://www.kaggle.com/competitions/kaggriculture/leaderboard)
[![Environment](https://img.shields.io/badge/Environment-kaggle--environments%201.32.7-orange)](https://github.com/Kaggle/kaggle-environments)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)

Official team repository and research summary for **Team Taeyang** in the Kaggle [Kaggriculture Simulation Competition](https://www.kaggle.com/competitions/kaggriculture).

---

## 🏆 Competition Highlights

| Metric | Official Result |
|---|---|
| **Final Standing** | **557th** / 10,148 teams (**Bronze Medal 🥉**) |
| **Final Score** | **4498.3** (Private Leaderboard) |
| **Team Name** | **Taeyang** ([TaeyanG4](https://github.com/TaeyanG4), [yw8837](https://github.com/yw8837)) |
| **Winning Submission** | `c1200` (Submission ID: `56722176`, verified byte-identical to `c1064`) |
| **Research Horizon** | ~1,100 candidate agents (`c001`–`c1068`, `o001`–`o403`), 20+ Kaggle submissions |
| **Validation League** | Paired fixed-panel local engine running **200,000+ simulation matches** |

---

## 🌾 Competition Overview

Kaggriculture is a 2-player economic resource management simulation game spanning **720 turns** on Kaggle Environments. Two agents manage farm expansion, labor allocation, crop rotation, animal husbandry (cows & sheep), and depot market delivery under dynamic demand clocks and liquidity constraints.

Key challenges:
- Non-linear resource dependencies: Seeds, water, labor, feed buffers, and cash flow.
- Terminal cash maximization vs. mid-game capital expansion.
- Opponent awareness and supply-chain congestion in shared markets.

---

## 🧠 Core Methodology & Architecture

### 1. Strategy-Meta Dataset & Fingerprinting
We transformed daily CC0 replay episodes into 48-column strategic fingerprint vectors (`kaggriculture_meta`). This pipeline quantified macro-trends in the Kaggle pool:
- Expansion speed vs. liquidity risk thresholds across public champions (Kaito v27, Özer v37, Guru Prasaath Master Engine V2).
- Market price collapse curves for high-yield crops (carrots and tomatoes).

### 2. Tiered Heuristic & Optimizer Hierarchy
Across 1,100 iterations, we avoided ungrounded end-to-end RL drift and engineered disciplined state-machine optimizers:
- **Router Layer (`c100` series)**: Context-aware dispatch based on opening hand and opponent aggressiveness.
- **Supply Chain Guardrails (`c120`–`c139`)**: Terminal prefix safety, livestock margin buffers, and liquidity-aware crop rotation.
- **Native Survival & Recovery (`c1000`–`c1200`)**: Autonomous disaster recovery routines for drought or unexpected market price drops.

### 3. Paired Fixed-Panel Validation League
To prevent leaderboard overfitting and variance traps:
- Every candidate agent was benchmarked locally across fixed seed suites against strong historical baselines.
- Zero data leakage policy: Hypotheses and evaluation criteria were locked before local tournament runs.

---

## 🔗 Provenance & Full Research Repositories

- **Kaggle Leaderboard**: [Kaggle Kaggriculture Leaderboard](https://www.kaggle.com/competitions/kaggriculture/leaderboard)
- **Deep Research & League Runner Repository**: [TaeyanG4/kaggriculture-strategy-meta](https://github.com/TaeyanG4/kaggriculture-strategy-meta)  
  *(Contains full historical logs, 200k match league runners, and strategy fingerprint extraction pipelines)*
- **Team Post-Mortem & Retrospective**: Comprehensive analysis of Top 10 solutions vs. final `c1200` behavior.

---

## 🛠️ Local Development & Reproduction

```bash
# Clone the repository
git clone https://github.com/yw8837/Kaggriculture.git
cd Kaggriculture

# Sync dependencies with uv
uv sync --python 3.12

# Run local validation tests
uv run pytest
```

---

## 📜 License & Acknowledgments

This project is licensed under the Apache 2.0 License. Base public notebook agents and environment bindings are credited to their respective open-source Kaggle contributors (Kaito Fukami, Ahmed Berat Özer, Guru Prasaath S).
