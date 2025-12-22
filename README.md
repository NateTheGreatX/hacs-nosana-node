# Nosana Node Home Assistant Integration

This integration allows you to monitor the status and specifications of a Nosana node in Home Assistant. It exposes multiple sensor entities for node state, hardware specs, network stats, market/reward information, queue position, and aggregated earnings by polling the Nosana APIs.

Version: 0.1.11

## Features
- Configurable via Home Assistant's UI.
- Node status sensor: shows "Queued" or "Running" (falls back to "Offline" if the `/node/info` endpoint fails).
- Separate sensors for network and hardware metrics (so each value updates independently):
  - status
  - uptime (seconds)
  - version
  - country
  - ping_ms, download_mbps, upload_mbps
  - specs: ram (MB), disk_space (GB), cpu, logical_cores, physical_cores, gpu_model, memory_gpu (MB)
  - market info: market name, market address, market type, nos_reward_per_second, usd_reward_per_hour
  - earnings: earnings_usd_total (USD)
- All sensors are grouped under a single device for the node in Integrations → Devices.
- Entity picture support:
  - HACS store/integration logo: defined via `hacs.json` using `"logo": "logomark.svg"` at the repo root (HACS displays this in the store).
  - Home Assistant entity picture: place the logo file under `config/www/nosana_node/logomark.svg` and it will be referenced via `/local/nosana_node/logomark.svg`.
- Coordinator reuses Home Assistant's HTTP session and polls every 30 seconds (markets endpoint is cached and polled at most every 5 minutes by default).

## Queue position (on-chain)
The queue position sensor attempts to fetch the node's position from the on-chain market queue using the Solana RPC API. This requires additional Python packages which are optional and only needed if you want this sensor to work:

- `solana`
- `solders`
- `borsh-construct`

If these packages are available (installed automatically when installing via HACS because they are listed in `manifest.json`), the integration will query Solana for the queue position. If not installed the sensor will remain unavailable and the integration still functions for the other sensors.

## Earnings aggregation (jobs API)
- The coordinator queries `https://dashboard.k8s.prd.nos.ci/api/jobs?limit=10&offset=0&node=<node>` on each update and maintains a small per-node store under Home Assistant Storage: `storage/nosana_node/node-<address>.jobs.json`.
- Jobs with `timeEnd == 0` are treated as running; their earnings accrue ephemerally using the current time but are only saved as finalized when `timeEnd > 0`.
- Sensor exposes the total: `earnings_usd_total`.

## Installation

### Via HACS (recommended)
1. Open HACS in Home Assistant.
2. Go to **Integrations** > **Explore & Download Repositories**.
3. Search for "Nosana Node" or add the repository: `https://github.com/NateTheGreatX/hacs-nosana-node`.
4. Click **Download** and install the integration.
5. Restart Home Assistant.

When installed via HACS, the repository `logomark.svg` is used as the store/integration logo. For entity pictures in HA, use `/local/...` and ensure the file is in `www/`.

### Manual Installation
1. Copy the `custom_components/nosana_node/` folder to your Home Assistant configuration directory (e.g., `~/.homeassistant/custom_components/nosana_node/`).
2. (Optional) Copy `logomark.svg` to `config/www/nosana_node/logomark.svg` if you want the entity picture available locally.
3. Restart Home Assistant.

## Configuration
1. Go to **Settings** > **Devices & Services** > **Add Integration**.
2. Search for and select **Nosana Node**.
3. Enter your Solana node address (e.g., `67qvHLKGmM62RLevcGRde1aWhEPU3njDiemvX6RZEX6i`).
4. Optionally, set a custom name (defaults to "Nosana Node <first_8_chars>").
5. Submit to create the sensors and device.

In the Integrations → Devices view you will find a device named after the config entry title; all sensors for that node appear under that device.

## Usage
- **Lovelace Card** (example showing a few sensors):
  ```yaml
  type: entities
  entities:
    - entity: sensor.nosana_node_67qvHLKG_status
      name: Nosana Node Status
    - entity: sensor.nosana_node_67qvHLKG_earnings_usd_total
      name: Earnings (USD)
    - entity: sensor.nosana_node_67qvHLKG_ping_ms
      name: Ping (ms)
    - entity: sensor.nosana_node_67qvHLKG_market
      name: Market
  ```

- **Automation**:
  ```yaml
  alias: Notify if Nosana Node is Running
  trigger:
    platform: state
    entity_id: sensor.nosana_node_67qvHLKG_status
    to: "Running"
  action:
    service: notify.notify
    data:
      message: "Nosana node is now running!"
  ```

## Notes & Troubleshooting
- Ensure the Nosana API endpoints (`/node/info` and the dashboard `/api/*`) are reachable from your Home Assistant instance. Test with `curl` or a browser from the machine running Home Assistant.
- The coordinator logs warnings if the optional `specs` or `markets` endpoints fail; a failure to fetch `/node/info` will cause the integration to mark the entry as `Offline`.
- If fields appear as `unknown` or sensors are `unavailable`, check logs for fetch errors and ensure the configured node address is correct.

## Development & Contributing
- The coordinator uses Home Assistant's shared aiohttp session for efficient HTTP connections and polls every 30 seconds. To limit traffic to the markets endpoint the integration caches markets for 5 minutes by default.
- If you add or change sensors, remember to bump the version in `custom_components/nosana_node/manifest.json`.

## Changelog
- 0.1.11: Add earnings aggregation sensors; improve device triggers; logo guidance.
- 0.1.10: Normalize status and offline handling.
- 0.1.8: Add queue position sensor (on-chain, optional), improve markets caching, bump version.
- 0.1.7: Added specs and market sensors (RAM, disk, CPU, cores, GPU, market rewards and type), device grouping, entity picture support, and coordinator improvements.
- 0.1.6: Initial release (node status + attributes).

## License
MIT License