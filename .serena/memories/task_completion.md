# Task Completion Gate
- Run focused tests, full pytest, and Ruff; retain immutable outputs and SHA-256.
- Deterministically rebuild packages; verify member order, byte-identical source, compile, secret/path scan, metadata, and embedded payload.
- Freeze clean implementation then evidence commit; local HEAD must equal origin with exact dirty inventory.
- Separate auditor task 019fb8b8-7758-7860-9304-39eb4f06c65c must PASS exact HEAD and payload; later byte changes void PASS.
- Private Save and Run needs exact release and downloaded-output equality after COMPLETE. Competition submit needs explicit user command.