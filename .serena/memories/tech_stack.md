# Tech Stack
- Python >=3.12,<3.13; UTF-8; Windows PowerShell host.
- uv and uv_build; project virtualenv .venv.
- Runtime pin: kaggle-environments==1.32.6; numpy, pandas, pyarrow. Historical 1.32.2 evidence stays immutable and must not be relabeled current.
- Dev gates: pytest >=8.4 and Ruff >=0.16; target py312; line length 100.
- Kaggle CLI handles read-only inventory and separately audited private kernel pushes.
