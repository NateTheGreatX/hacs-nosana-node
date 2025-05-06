# Nosana Node Integration

A Home Assistant integration to monitor Nosana nodes using a Solana address.

## Features
- Fetches node specifications from `https://dashboard.k8s.prd.nos.ci/api/nodes/<solana_address>/specs` (primary).
- Fetches state from `https://<solana_address>.node.k8s.prd.nos.ci/node/info` (sets state to "offline" if unavailable).
- Fetches benchmark metrics from `https://dashboard.k8s.prd.nos.ci/api/benchmarks/generic-benchmark-data`.
- Sensors for node specs, state, and performance metrics.

## Installation
1. Install HACS in Home Assistant.
2. Add this repository as a custom repository in HACS (type: Integration).
3. Install the "Nosana Node" integration.
4. Add the integration via `Settings > Devices & Services > Add Integration`.
5. Enter your Nosana node’s Solana address.

## Configuration
- **Solana Address**: The address of your Nosana node (e.g., `67qvHLKGmM62RLevcGRde1aWhEPU3njDiemvX6RZEX6i`).
- **Update Interval**: Polling frequency in seconds (default: 300).

## Sensors
- Node State (online/offline)
- Node Status (e.g., PREMIUM)
- Node Country
- RAM Size (MB)
- Disk Space (GB)
- CPU Model
- CPU Logical Cores
- CPU Physical Cores
- Node Version
- System Environment
- GPU Memory Total (MB)
- CUDA Version
- NVML Version
- Network Ping (ms)
- Download Speed (Mbps)
- Upload Speed (Mbps)
- GPU Name
- Market Address
- GPU Major Version
- GPU Minor Version
- Storage to CPU Bandwidth (Mbps)
- CPU to GPU Bandwidth (Mbps)
- System Read/Write Speed (MB/s)
- RAM Read/Write Speed (MB/s)
- Internet Download Speed (Mbps)
- Internet Upload Speed (Mbps)

## Support
Report issues at [GitHub Issues](https://github.com/NateTheGreatX/hacs-nosana-node/issues).