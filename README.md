# Nosana Node Home Assistant Integration

This integration allows you to monitor the status and specifications of a Nosana node in Home Assistant. It exposes multiple sensor entities for node state, hardware specs, network stats, market/reward information, aggregated earnings, and LLM benchmark metrics by polling the Nosana APIs.

Version: 0.1.14

## Features
- Configurable via Home Assistant's UI.
- Node status sensor: shows "Queued" or "Running" (falls back to "Offline" if the `/node/info` endpoint fails).
- Separate sensors for network and hardware metrics:
  - status
  - uptime (seconds)
  - version
  - country
  - ping_ms, download_mbps, upload_mbps
  - specs: ram (MB), disk_space (GB), cpu, logical_cores, physical_cores, gpu_model, memory_gpu (MB)
  - market info: market name, market address, market type, nos_reward_per_second, usd_reward_per_hour
  - earnings: earnings_usd_total (USD)
  - LLM benchmark: benchmark_tokens_per_second (tokens/s, mean) with `model_id` attribute
- All sensors are grouped under a single device for the node in Integrations → Devices.
- Entity picture support:
  - Default (HACS): entity picture points to `/hacsfiles/hacs-nosana-node/logomark.svg` which HACS serves automatically when installed via HACS.
  - Optional local: copy the file to `config/www/nosana_node/logomark.svg` and use `/local/nosana_node/logomark.svg` if you prefer managing it yourself.
- Coordinator uses Home Assistant's shared HTTP session and updates every 30 seconds for info/specs/markets. Jobs API is throttled with a 15-minute TTL and also fetched immediately on status changes to avoid rate limits while keeping earnings/benchmarks fresh.

## Earnings aggregation (jobs API)
- The coordinator queries `https://dashboard.k8s.prd.nos.ci/api/jobs?limit=10&offset=0&node=<node>` and maintains a per-node store under Home Assistant Storage: `storage/nosana_node/node-<address>.jobs.json`.
- Only finalized jobs (`timeEnd > 0`) are counted toward totals.
- The Store includes per-job records with `runtime_seconds`, `earned_usd`, and (when available) `benchmark` extracted from `jobResult.opStates` (`operationId == "llm-benchmark"`).
- Sensors expose totals (`earnings_usd_total`) and the latest benchmark tokens/sec mean along with the `model_id`.

## Installation

### Via HACS (recommended)
1. Open HACS in Home Assistant.
2. Go to **Integrations** > **Explore & Download Repositories**.
3. Search for "Nosana Node" or add the repository: `https://github.com/NateTheGreatX/hacs-nosana-node`.
4. Click **Download** and install the integration.
5. Restart Home Assistant.

When installed via HACS, the repository `logomark.svg` is used as the store/integration logo and served from `/hacsfiles/hacs-nosana-node/logomark.svg`. For entity pictures via `/local/...`, ensure the file is in `www/`.

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
- **Lovelace Card** (example):
  ```yaml
  type: entities
  entities:
    - entity: sensor.nosana_node_67qvHLKG_status
      name: Nosana Node Status
    - entity: sensor.nosana_node_67qvHLKG_earnings_usd_total
      name: Earnings (USD)
    - entity: sensor.nosana_node_67qvHLKG_benchmark_tokens_per_second
      name: LLM Tokens/sec (mean)
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
- Ensure the Nosana API endpoints (`/node/info` and the dashboard `/api/*`) are reachable from your Home Assistant instance.
- Jobs API is throttled with a 15-minute TTL and fetched immediately on status changes to reduce 429 rate-limit errors.
- If the entity picture returns 404 under `/hacsfiles/`, try a hard refresh (Cmd+Shift+R). If installed manually (not via HACS), copy the SVG under `www/` and use the `/local/` path instead.
- If sensors are `unavailable`, check logs for fetch errors and ensure the configured node address is correct.

## Development & Contributing
- The coordinator uses Home Assistant's shared aiohttp session for efficient HTTP connections and polls every 30 seconds; markets are cached (5-minute TTL).
- If you add or change sensors, remember to bump the version in `custom_components/nosana_node/manifest.json` and update the changelog.

## Changelog
- 0.1.13: Add jobs TTL with status-change-triggered fetch; finalized-only earnings; LLM benchmark tokens/sec sensor; default entity picture to `/hacsfiles/...`.
- 0.1.11: Initial earnings aggregation sensor; device triggers; logo guidance.
- 0.1.10: Normalize status and offline handling.

## License
MIT License