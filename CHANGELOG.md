# Changelog

## 0.1.11
- Add earnings aggregation using Home Assistant Storage (Store):
  - Fetch recent jobs (limit 10) and persist per-node job records in `storage/nosana_node/node-<address>.jobs.json`.
  - Compute totals (USD) including ephemeral accrual for running jobs.
  - Expose new sensor: `earnings_usd_total`.
- Reinforce status normalization: `/node/info` failures -> `Offline`; `OTHER`/`RUNNING` -> `Running`; `QUEUED` -> `Queued`.
- Device triggers: ensure triggers appear for the Status sensor (Running/Queued/Offline).
- Logo: prefer placing `logomark.svg` under `config/www/nosana_node/` and use `/local/nosana_node/logomark.svg` for entity pictures. HACS store logo remains configured via `hacs.json`.

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