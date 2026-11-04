# Changelog

## 0.1.17
- Fix: resolve `UnboundLocalError` in coordinator follow-up jobs refresh by using `datetime.utcnow()` directly instead of the local variable `now` which was not yet assigned when the status-change scheduling block runs.

## 0.1.16
- Add job type sensor for the currently running job (deployer-based):
  - New sensor `NosanaNodeJobTypeSensor` (`sensor.nosana_node_<node>_job_type`) reports the job type of the running job.
  - If the running job's deployer (`project`) is in the general deployments list, the state is `"General"`.
  - If the running job belongs to any other deployer, the state is `"Deployment Manager"`.
  - If the node is idle, queued, or the job is finished, the state is `"Idle"`.
- Expose `project`, `type`, `jobStatus`, and `state` on the coordinator's `latest_job` payload so sensors can determine job type.
- Persist `project` and `type` on stored job records (for fallback/latest-job computations from the HA Store).
- Add configurable `general_deployments` list (defaults to `["JBksZBRkyjPYnqmnxheMr4t1WP88gAwGX6SUz3HuPkfT"]`) in `const.py`.
- Schedule a follow-up jobs API refresh ~60s after a `Queued -> Running` status transition to pick up newly started jobs.

## 0.1.15
- Bug fix: support the new nested dashboard `/node/info` payload shape (`{"state": "RUNNING_JOB", "info": {...}}`).
  - Running nodes with `state: "RUNNING_JOB"` now correctly report `Running` (previously fell through to `Offline`).
  - Status reads now fall back to nested `info.state` when top-level state is absent.
  - Nested `info` fields (`version`, `country`, `system_environment`, `protocol`) are flattened to top level for sensors.
- Coordinator info polling now runs at **1s** on success and progressive backoff (**5s → 10s → 20s → 40s → capped at 60s**) on failure, resetting to 1s on recovery.

## 0.1.13
- Throttle jobs API via TTL: fetch at most every 15 minutes, similar to markets TTL logic, and recompute totals from Store between fetches.
- Fetch jobs immediately when node status changes (Offline/Queued/Running), to keep earnings up to date without hitting rate limits.
- Earnings totals count only finalized jobs (`timeEnd > 0`); running jobs are not accrued into totals.
- Default entity picture path updated to HACS-served `/hacsfiles/hacs-nosana-node/logomark.svg` with optional `/local/...` fallback.

## 0.1.11
- Add earnings aggregation using Home Assistant Storage (Store):
  - Fetch recent jobs (limit 10) and persist per-node job records in `storage/nosana_node/node-<address>.jobs.json`.
  - Compute totals (USD) including ephemeral accrual for running jobs.
  - Expose new sensor: `earnings_usd_total`.
- Reinforce status normalization: `/node/info` failures -> `Offline`; `OTHER`/`RUNNING` -> `Running`; `QUEUED` -> `Queued`.
- Device triggers: ensure triggers appear for the Status sensor (Running/Queued/Offline).
- Logo: entity picture now defaults to HACS-served path `/hacsfiles/hacs-nosana-node/logomark.svg` to avoid `/local` 404s; optional `/local/nosana_node/logomark.svg` still supported if copied to `www/`.

## 0.1.10
- Normalize `status` across sensors:
  - Info fetch failure or 500 → `Offline`.
  - `state: OTHER` → `Running`.
  - `state: QUEUED` → `Queued`.
  - Unknown non-offline states → `Running`.
- Ensure `status`, `nodeStatus`, and `state` keys are always present for automations.
- Minor: confirm HACS logo config uses `hacs.json` → `logo: "logomark.svg"`; for Home Assistant entity pictures, place the logo in `www/` and reference via `/local/...`.

## 0.1.9
- Default node `status` to `"Offline"` when `/node/info` fails or returns an invalid payload.
- Improve coordinator resilience: continue updating `specs` and `market` data even if `info_url` errors.

## 0.1.5

- Fix: Cap job runtime earnings calculation at job timeout value.

## 0.1.4
- Fixed `ValueError` for non-numeric sensors by removing `state_class="measurement"` for `status`, `system_environment`, `nvml_version`, `gpu_name`, `market_address`, and `state`.

## 0.1.3
- Added new primary endpoint `https://dashboard.k8s.prd.nos.ci/api/nodes/<solana_address>/specs` for node specifications.
- Set `state` to `"offline"` if `/node/info` endpoint fails.
- Fixed `ImportError` for `DATA_GIGABYTES` and `DATA_MEGABYTES` by using `UnitOfInformation.GIGABYTES` and `UnitOfInformation.MEGABYTES`.
- Fixed `NameError` in `coordinator.py` by adding `import re` for Solana address validation.
- Added sensors for benchmark metrics from `https://dashboard.k8s.prd.nos.ci/api/benchmarks/generic-benchmark-data`:
  - Storage to CPU Bandwidth
  - CPU to GPU Bandwidth
  - System Read/Write Speed
  - RAM Read/Write Speed
  - Internet Download Speed
  - Internet Upload Speed
- Added sensors from `/specs` endpoint:
  - Node Status
  - Node Country
  - RAM Size
  - Disk Space
  - CPU Model
  - CPU Logical Cores
  - CPU Physical Cores
  - Node Version
  - System Environment
  - GPU Memory Total
  - CUDA Version
  - NVML Version
  - Network Ping
  - Download Speed
  - Upload Speed
  - GPU Name
  - Market Address
  - GPU Major Version
  - GPU Minor Version

## 0.1.2
- Fixed missing `async_setup_entry` in `__init__.py` causing setup failure.
- Fixed deprecated `self.config_entry` in `config_flow.py` for 2025.12 compatibility.