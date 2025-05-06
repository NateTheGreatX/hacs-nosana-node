# Nosana Node Integration
A Home Assistant integration to monitor Nosana nodes using a Solana address.

## Installation
1. Install via HACS.
2. Add the integration in Home Assistant.
3. Enter your Nosana node’s Solana address.

## Sensors
- Node Uptime
- Node State
- Node Version
- Node Country
- Network Ping (ms)
- Download Speed (Mbps)
- Upload Speed (Mbps)
- Disk Size (GB)
- RAM Size (MB)
- CPU Logical Cores
- GPU Memory Total (MB)
- CUDA Driver Version

## Configuration
- **Solana Address**: The address of your Nosana node.
- **Update Interval**: Polling frequency (default: 5 minutes).