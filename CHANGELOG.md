# Changelog

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