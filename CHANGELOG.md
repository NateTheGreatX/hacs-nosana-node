# Changelog

## 0.1.3
- Fixed `ImportError` for `DATA_GIGABYTES` and `DATA_MEGABYTES` by using `UnitOfInformation.GIGABYTES` and `UnitOfInformation.MEGABYTES`.
- Added sensors for benchmark metrics from `https://dashboard.k8s.prd.nos.ci/api/benchmarks/generic-benchmark-data`:
  - Storage to CPU Bandwidth
  - CPU to GPU Bandwidth
  - System Read/Write Speed
  - RAM Read/Write Speed
  - Internet Download Speed
  - Internet Upload Speed

## 0.1.2
- Fixed missing `async_setup_entry` in `__init__.py` causing setup failure.
- Fixed deprecated `self.config_entry` in `config_flow.py` for 2025.12 compatibility.