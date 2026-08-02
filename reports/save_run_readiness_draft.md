# Fa_01 / Fa_02 single Save & Run readiness draft

Status: **LOCAL PREFLIGHT PLAN ONLY - EXTERNAL SAVE & RUN, SUBMISSION, PUBLICATION, AND API MUTATION ARE FORBIDDEN IN THIS DRAFT.**

Prepared against Git HEAD `4a997eb931f84c49d72b33316497a6d93637750d` on 2026-08-01.
The Fa_02 source and related evaluation files were dirty while this was written, so every planned
production source/archive hash below is deliberately `PENDING`. Do not substitute an intermediate
worktree hash.

## Save & Run is not a competition submission

- `kaggle kernels push -p <run-directory>` creates or updates a private Kaggle Code notebook and
  runs it. In this plan, a fresh slug and exactly one accepted push must produce one Save & Run.
- It does **not** enter the emitted `.tar.gz` in the Kaggriculture competition.
- No command beginning with `kaggle competitions submit` is permitted during this workflow. A
  later competition submission is a separate external mutation and needs the user's explicit
  submit instruction after Save & Run output verification.
- No browser action is needed for this plan.

## Existing ground truth and collision risks

Read from the local ledgers, original kernel metadata/logs, champion manifest, dist files, and a
read-only Kaggle kernel listing:

- Historical kernel `yw8837/fa-01-overflow-safe-inventory` already exists. Local records identify
  Version 2 as `COMPLETE`; both downloaded `output_v1` and `output_v2` archives hash to
  `1B52522D0CD55536F1C45B73F5FC5A37A27CF924A218FA009D1D1786B72F53D1`.
- The historical artifact is also competition submission ref `55142935`, confirmed as the user's
  manual Kaggle UI action. A new Save & Run must not be described as a submission.
- The official competition-filtered read-only listing returned exactly two refs:
  `yw8837/kaggriculture-strong-expansion-baseline` and
  `yw8837/fa-01-overflow-safe-inventory`. The proposed fresh refs below were absent. Because the
  count was below the requested page size of 200, that snapshot was not truncated.
- `dist/Fa_02 - Horizon-Aware Crop Rotation.tar.gz` already exists locally with SHA-256
  `DD3ABEB21A31AFDA56430ADB3555CB4A7CEBBFB24A33FFEC52447CBF30D59850`, but local records say it
  had no Save & Run or submission. The new BG1 filename must remain different and the old file must
  not be overwritten.
- `dist/final_day_labor.tar.gz` and `dist/formal_champion.tar.gz` are byte-identical
  (`59281C6434D6D48C429DDC7950266A1083454978A0425D143480E9BB75559670`). Filename uniqueness is
  therefore not evidence of artifact uniqueness.
- `dist/manifest.json` currently lists only `overflow_drop`; it is not a complete dist inventory
  and must not be used alone for duplicate prevention.
- `resolve_current_champion()` reads only `artifacts/champion/manifest.json:current_champion` and
  verifies its source/artifact SHA-256. Rejected history cannot be packaged through that resolver.
  Fa_02 must pass audit and promotion and become the exact registered production identity before
  its production package can use this gate. Fa_01 likewise needs its exact requested output path
  bound into the final frozen packaging record; the current manifest points to
  `dist/formal_champion.tar.gz`, not the numbered filename below.

Focused local test evidence at drafting time:

```text
uv run pytest tests/test_package.py tests/test_save_run.py -q
....                                                                     [100%]
4 passed in 0.07s
```

## Fixed identities — do not improvise names at push time

| Field | Fa_01 | Fa_02 |
|---|---|---|
| Lineage | `final_day_labor` | `BG1_rescue_greedy` |
| Frozen source path | `artifacts/candidates/final_day_labor/main.py` | `experiments/source_snapshots/fa02_rescue_greedy/BG1.py` |
| Artifact filename | `Fa_01 - Final-Day Labor.tar.gz` | `Fa_02 - Rescue-Greedy Allocation.tar.gz` |
| Kaggle title | `Fa_01 - Final-Day Labor` | `Fa_02 - Rescue-Greedy Allocation` |
| Fresh kernel id | `yw8837/fa-01-final-day-labor` | `yw8837/fa-02-rescue-greedy-allocation` |
| Local run directory | `kaggle_runs/Fa_01 - Final-Day Labor` | `kaggle_runs/Fa_02 - Rescue-Greedy Allocation` |
| Expected first accepted version | `1` | `1` |
| Final source SHA-256 | `PENDING` | `PENDING` |
| Final archive SHA-256 | `PENDING` | `PENDING` |
| Final archive bytes | `PENDING` | `PENDING` |

Both filenames satisfy the enforced pattern
`^Fa_\d{2} - [A-Za-z0-9][A-Za-z0-9 _-]*\.tar\.gz$`.

Do not reuse `yw8837/fa-01-overflow-safe-inventory`. Updating that slug would create another
version under the rejected historical agent and destroy the one-run identity proof. Do not rename
an archive after wrapper generation: artifact filename, notebook filename, title, slug, receipt,
download path, and ledger row must all agree before the push.

## Mandatory gates before either wrapper is built

All boxes are blocking and must be evaluated separately for Fa_01 and Fa_02.

- [ ] Independent auditor returned PASS for the exact frozen candidate, evidence, and packaging
  identity. User authorization alone does not replace this gate.
- [ ] The candidate has a frozen commit and no unexplained dirty file in its source, builder,
  packaging, Save & Run, manifest, tests, or evidence chain.
- [ ] The final promotion record names this exact identity, source path, source SHA-256, artifact
  path, and archive SHA-256. For Fa_02, `current_champion` must actually be BG1 after promotion;
  a draft/closed candidate is not eligible.
- [ ] Required candidate tests, official simulator smoke, runtime/schema gate, deterministic
  rebuild, and package tests pass against the frozen commit.
- [ ] The exact artifact filename and run directory do not already exist. If either exists, stop
  and audit it; never overwrite it to make the checklist pass.
- [ ] The planned archive hash is absent from every prior Save & Run/publication/submission hash
  in `submissions/ledger.jsonl`, `publications/ledger.jsonl`, original downloaded kernel outputs,
  and submission inventories. Also assert Fa_01 and Fa_02 hashes differ from each other.
- [ ] The proposed kernel id is absent from a complete `--mine` listing immediately before push.
  If the listing contains 200 rows, stop and paginate; a single full first page is then not proof.
- [ ] A pre-push receipt records UTC, Git HEAD, exact dirty inventory, source/archive hashes and
  bytes, artifact member/payload hash, metadata/notebook hashes, fresh-slug listing evidence, user
  authority, and independent-auditor PASS.

## Exact local preflight — run once per spec, sequentially

Run the Fa_01 block and finish its post-run verification before starting Fa_02. Replace only the
spec block; do not edit the common commands.

Fa_01 spec:

```powershell
$spec = @{
  Sequence = 'Fa_01'
  Identity = 'final_day_labor'
  Source = 'artifacts/candidates/final_day_labor/main.py'
  Artifact = 'dist/Fa_01 - Final-Day Labor.tar.gz'
  Title = 'Fa_01 - Final-Day Labor'
  KernelId = 'yw8837/fa-01-final-day-labor'
  RunDir = 'kaggle_runs/Fa_01 - Final-Day Labor'
}
```

Fa_02 spec:

```powershell
$spec = @{
  Sequence = 'Fa_02'
  Identity = 'BG1_rescue_greedy'
  Source = 'experiments/source_snapshots/fa02_rescue_greedy/BG1.py'
  Artifact = 'dist/Fa_02 - Rescue-Greedy Allocation.tar.gz'
  Title = 'Fa_02 - Rescue-Greedy Allocation'
  KernelId = 'yw8837/fa-02-rescue-greedy-allocation'
  RunDir = 'kaggle_runs/Fa_02 - Rescue-Greedy Allocation'
}
```

### 1. Freeze and resolve the registered identity

```powershell
$receiptUtc = [DateTime]::UtcNow.ToString('o')
$gitHead = git rev-parse HEAD
$dirtyInventory = @(git status --porcelain=v1)
$sourceHash = (Get-FileHash -LiteralPath $spec.Source -Algorithm SHA256).Hash

if (Test-Path -LiteralPath $spec.Artifact) { throw "artifact path already exists: $($spec.Artifact)" }
if (Test-Path -LiteralPath $spec.RunDir) { throw "run directory already exists: $($spec.RunDir)" }

uv run python -c "from pathlib import Path; from kaggriculture_lab.candidates.package import resolve_current_champion; r=resolve_current_champion(Path('artifacts/champion/manifest.json'), Path('.')); print(r['identity'], r['source_sha256'], r['artifact_sha256'])"
uv run pytest tests/test_package.py tests/test_save_run.py -q
```

Abort unless the resolver identity is the candidate's final registered production identity and its
hashes match the independent-audit handoff. With the current manifest, this check resolves
`final_day_labor`; it must **not** be treated as a BG1 pass.

### 2. Build the exact numbered artifact once and validate it

```powershell
uv run python -c "import json; from pathlib import Path; from kaggriculture_lab.candidates.package import package; print(json.dumps(package(Path(r'$($spec.Source)'), Path(r'$($spec.Artifact)'))))"

$artifactHash = (Get-FileHash -LiteralPath $spec.Artifact -Algorithm SHA256).Hash
$artifactBytes = (Get-Item -LiteralPath $spec.Artifact).Length
$env:KG_PREFLIGHT_SOURCE = (Resolve-Path -LiteralPath $spec.Source).Path
$env:KG_PREFLIGHT_ARTIFACT = (Resolve-Path -LiteralPath $spec.Artifact).Path
uv run python -c "import hashlib,os,tarfile; from pathlib import Path; s=Path(os.environ['KG_PREFLIGHT_SOURCE']).read_bytes(); a=Path(os.environ['KG_PREFLIGHT_ARTIFACT']); t=tarfile.open(a,'r:gz'); assert t.getnames()==['main.py']; p=t.extractfile('main.py').read(); assert p==s; compile(p,'main.py','exec'); print(hashlib.sha256(s).hexdigest().upper(), hashlib.sha256(a.read_bytes()).hexdigest().upper(), a.stat().st_size, t.getnames())"
```

Run the deterministic build a second time to a temporary, differently named local file and require
the same hash. This is a local build check, not a second Save & Run. Do not change the production
artifact after this point.

### 3. Reject duplicate uploaded bytes

```powershell
$knownUploadHashes = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($ledgerPath in @('submissions/ledger.jsonl', 'publications/ledger.jsonl')) {
  Get-Content -LiteralPath $ledgerPath | ForEach-Object {
    $row = $_ | ConvertFrom-Json
    foreach ($field in @('artifact_sha256', 'local_artifact_sha256', 'downloaded_output_sha256', 'local_matching_filename_artifact_sha256')) {
      if (($row.PSObject.Properties.Name -contains $field) -and ($row.$field -match '^[A-Fa-f0-9]{64}$')) {
        [void]$knownUploadHashes.Add($row.$field)
      }
    }
  }
}
if ($knownUploadHashes.Contains($artifactHash)) { throw "duplicate prior upload hash: $artifactHash" }
```

Also hash every original downloaded kernel output under `kaggle_runs/` and compare it to
`$artifactHash`; this covers a Save & Run that may be missing from a ledger. For the second agent,
also assert its hash is not the first agent's final hash.

### 4. Prove the slug is fresh locally and on Kaggle

```powershell
$localKernelIds = @(
  Get-ChildItem -Path kaggle_runs -Recurse -Filter kernel-metadata.json | ForEach-Object {
    (Get-Content -LiteralPath $_.FullName -Raw | ConvertFrom-Json).id
  }
)
if ($localKernelIds -contains $spec.KernelId) { throw "local kernel id collision: $($spec.KernelId)" }

$mine = @(kaggle kernels list --mine --page-size 200 --format json | ConvertFrom-Json)
if ($mine.Count -ge 200) { throw 'kernel inventory may be paginated; collect every page before continuing' }
if ($mine.ref -contains $spec.KernelId) { throw "remote kernel id collision: $($spec.KernelId)" }
```

Do not use `kaggle kernels status <new-slug>` failure as sole nonexistence proof: the CLI's access
error is ambiguous for a missing versus inaccessible private slug. The complete owned-kernel
inventory plus local metadata inventory are the collision gates.

### 5. Generate and locally execute the byte-preserving wrapper

```powershell
uv run kg-prepare-save-run --artifact "$($spec.Artifact)" --output-dir "$($spec.RunDir)" --kernel-id "$($spec.KernelId)" --title "$($spec.Title)" --competition kaggriculture

$metadataPath = Join-Path $spec.RunDir 'kernel-metadata.json'
$notebookPath = Join-Path $spec.RunDir "$($spec.Title).ipynb"
$metadata = Get-Content -LiteralPath $metadataPath -Raw | ConvertFrom-Json
if ($metadata.id -ne $spec.KernelId) { throw 'kernel id mismatch' }
if ($metadata.title -ne $spec.Title) { throw 'kernel title mismatch' }
if ($metadata.code_file -ne "$($spec.Title).ipynb") { throw 'code_file mismatch' }
if ($metadata.is_private -ne $true) { throw 'kernel must be private' }
if ($metadata.enable_internet -ne $false) { throw 'internet must be disabled' }
if (@($metadata.competition_sources).Count -ne 1 -or $metadata.competition_sources[0] -ne 'kaggriculture') { throw 'competition source mismatch' }

$localCheckDir = Join-Path ([IO.Path]::GetTempPath()) ('kg-save-run-' + [Guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $localCheckDir -ErrorAction Stop | Out-Null
$env:KG_PREFLIGHT_NOTEBOOK = (Resolve-Path -LiteralPath $notebookPath).Path
Push-Location $localCheckDir
try {
  uv run python -c "import json,os; from pathlib import Path; n=json.loads(Path(os.environ['KG_PREFLIGHT_NOTEBOOK']).read_text(encoding='utf-8')); exec(compile(''.join(n['cells'][1]['source']),'emit-verified-artifact','exec'))"
} finally {
  Pop-Location
}
$localEmitted = Join-Path $localCheckDir ([IO.Path]::GetFileName($spec.Artifact))
if ((Get-FileHash -LiteralPath $localEmitted -Algorithm SHA256).Hash -ne $artifactHash) { throw 'local wrapper output hash mismatch' }
```

Before any external action, hash the notebook and metadata, save the pre-push receipt, and rerun
steps 3 and 4. Any change invalidates the receipt and returns the candidate to audit.

## The one external mutation — HOLD until separately released

Only after every gate above passes and the independent auditor releases this exact receipt:

```powershell
kaggle kernels push -p "$($spec.RunDir)" 2>&1 | Tee-Object -FilePath (Join-Path $spec.RunDir 'push_receipt.txt')
```

This command is permitted **exactly once per fresh slug**. Never rerun it merely because the client
times out or returns unclear output: the server may already have accepted the version. First inspect
the owned-kernel list, status, and logs. A retry is eligible only after original evidence proves no
kernel/version/run was created and the auditor explicitly releases the same frozen receipt again.

Fresh slug absence immediately before one accepted push is the version-collision proof and implies
expected Version 1. Capture the push stdout because current `kernels list`/`status` output does not
reliably expose a version number. Do not claim a numeric version from status alone.

## Post-run verification — reads/download only, never a second push

Use these commands after the one push; rerun `status`, not `push`, while waiting:

```powershell
kaggle kernels status "$($spec.KernelId)"
kaggle kernels logs "$($spec.KernelId)" | Tee-Object -FilePath (Join-Path $spec.RunDir 'latest.log')
kaggle kernels files "$($spec.KernelId)" --format json | Tee-Object -FilePath (Join-Path $spec.RunDir 'latest_files.json')

$downloadDir = Join-Path $spec.RunDir 'output_v1'
if (Test-Path -LiteralPath $downloadDir) { throw "download directory already exists: $downloadDir" }
New-Item -ItemType Directory -Path $downloadDir -ErrorAction Stop | Out-Null
kaggle kernels output "$($spec.KernelId)" -p "$downloadDir" --force

$downloadedArtifact = Join-Path $downloadDir ([IO.Path]::GetFileName($spec.Artifact))
$downloadedHash = (Get-FileHash -LiteralPath $downloadedArtifact -Algorithm SHA256).Hash
if ($downloadedHash -ne $artifactHash) { throw "Kaggle output hash mismatch: $downloadedHash" }

$logHits = @(Select-String -Path (Join-Path $spec.RunDir 'latest.log') -Pattern 'Traceback|KernelWorkerStatus.ERROR|Exception|failed' -CaseSensitive:$false)
if ($logHits.Count -ne 0) { $logHits; throw 'error context found in Kaggle log' }
```

Acceptance requires all of the following:

- status output is exactly `KernelWorkerStatus.COMPLETE`;
- the log's JSON receipt reports the exact artifact filename, local SHA-256, byte count, and
  `members: ["main.py"]`;
- the downloaded artifact SHA-256 equals the frozen local archive SHA-256;
- opening the downloaded archive again shows only root `main.py`, whose bytes equal the frozen
  source;
- the post-push owned-kernel list contains the exact new ref once;
- no competition submission was created;
- an append-only Save & Run ledger row records source/archive/notebook/metadata hashes, fresh slug,
  expected Version 1 provenance, `COMPLETE`, downloaded hash, UTC, and `submitted:false`.

Do not rely on `kaggle kernels files` byte size as the content proof. In the existing Fa_01 check it
reported `924` while the downloaded archive and both local original outputs were `4,894` bytes;
only the downloaded artifact SHA-256 and member/payload comparison close the gate.

## Final HOLD conditions

Do not run either push while any of these remains true:

- final source/archive/notebook/metadata hash is `PENDING`;
- the independent auditor has not passed the exact frozen handoff;
- Fa_02 is still a draft/closed candidate rather than the registered production identity;
- the packaging resolver points at another identity or output path;
- a slug, filename, output directory, or uploaded artifact hash collides;
- Fa_01 post-run verification is incomplete when preparing Fa_02;
- the next requested action is a competition submission rather than private Save & Run.
