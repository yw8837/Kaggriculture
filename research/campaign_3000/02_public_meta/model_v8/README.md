# Kaggriculture DQN Weights v8 evidence

This directory records a read-only investigation of the single model returned by the
official Kaggle text search used by this campaign:
`saitejabandaruin/kaggriculture-dqn-weights`.

The population boundary has **not** changed: Kaggle exposes model text search but no
official competition filter, so one analyzed hit is not a claim that Kaggriculture has
exactly one public model.

## Reproduction

```powershell
$env:PYTHONUTF8='1'
uvx kaggle models get saitejabandaruin/kaggriculture-dqn-weights
uvx kaggle models instances versions files saitejabandaruin/kaggriculture-dqn-weights/PyTorch/pytorch-v1/8 --format json
uvx kaggle models instances versions download saitejabandaruin/kaggriculture-dqn-weights/PyTorch/pytorch-v1/8 -p dist/model-v8-download --untar -f
.\.venv\Scripts\python.exe research/campaign_3000/02_public_meta/model_v8/build_model_v8_evidence.py --download-dir dist/model-v8-download
.\.venv\Scripts\python.exe research/campaign_3000/02_public_meta/model_v8/verify_model_v8.py --download-dir dist/model-v8-download
```

`inspect_checkpoint.py` uses only ZIP parsing and `pickletools` opcode inspection. It
does not import PyTorch, unpickle the checkpoint, instantiate a class, or execute model
code. The large banner and raw checkpoint stay in ignored `dist/`; their exact byte
counts and hashes are pinned in `file_inventory_v8.json`. Normalized LF text copies of
the small upstream README and metadata are preserved here; raw-byte hashes stay separate.

## Disposition

The checkpoint is not usable as a competition agent from the published material:

- the README and API usage advertise a 10→256→128→4 network;
- the checkpoint actually contains only `fc1` 10→64 and `fc2` 64→4 parameters;
- the published module names do not match the checkpoint keys;
- no 10-feature encoder, four-action mapping, reward/training receipt, or conversion
  from four indices to Kaggriculture's composite farmer/hands/market action is supplied.

This is a falsifiable `UNUSABLE_WITH_PUBLISHED_INTERFACE` result, not a claim that the
weights contain no learned signal. The disposition may be revisited only if an exact
compatible network, encoder, four-index action mapping, and evaluation provenance are
published and hash-pinned.
