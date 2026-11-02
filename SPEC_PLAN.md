# Nosana Node Integration — Endpoint Migration & Sensor Update Spec

Goal
----
Replace a deprecated node-info endpoint and update sensors to rely on stable dashboard APIs while preserving backward compatibility and minimizing disruption for existing users.

Checklist (implementation plan)
--------------------------------
- [ ] Confirm which endpoint(s) are deprecated in production (coordinate with API owners).
- [ ] Add a clear feature-flag and detection path in the coordinator to prefer the new endpoint with a safe fallback to the old endpoint.
- [ ] Update `NosanaNodeCoordinator` to support the new endpoint URL(s) and resilient parsing of returned payload shapes.
- [ ] Update sensor data mappings in `sensor.py` where keys/nesting differ from the old endpoint.
- [ ] Add unit tests for coordinator behavior against sample responses (new/old/malformed/offline).
- [ ] Add integration tests or run manual tests to validate sensors after migration.
- [ ] Add a config entry migration or optional toggle so existing installs keep working until they opt-in.
- [ ] Update README and changelog with the migration details.

API endpoints the integration currently uses
-------------------------------------------
These were discovered in `custom_components/nosana_node/coordinator.py`:

1) GET https://{node_address}.node.k8s.prd.nos.ci/node/info
   - Currently assigned to `self.info_url`.
   - Purpose: primary node-level status and info (state/status/nodeStatus, uptime, info.version/model/country, network ping/download/upload). Also used as fallback source for `marketAddress`.

2) GET https://dashboard.k8s.prd.nos.ci/api/nodes/{node_address}/metrics
   - Assigned to `self.specs_url` (should be updated to `metrics_url` or reuse the attribute name but point to `/metrics`).
   - Purpose: hardware and runtime metrics (ram_gb, disk_gb, cpu.*, gpu.*, package_version, model-specific telemetry such as `<model>_tokens_per_second_mean`) and `marketAddress` at the top level.

3) GET https://dashboard.k8s.prd.nos.ci/api/markets
   - Assigned to `self.markets_url` (cached).
   - Purpose: list of markets to resolve market name, type, slug, and reward fields (NOS / USD reward fields).

4) GET https://dashboard.k8s.prd.nos.ci/api/jobs?limit=10&offset=0&node={node_address}
   - `self.jobs_url_base` + query params.
   - Purpose: earnings aggregation, runtime accounting, and extracting llm-benchmark results (model_id, tokens_per_second.mean).

Why migration is needed
----------------------
- The per-node subdomain node-info endpoint (https://{node}.node.k8s.prd.nos.ci/node/info) appears to be deprecated or scheduled for removal. The dashboard API already exposes node-related data under `dashboard.k8s.prd.nos.ci` and is a preferable single-domain source.
- Moving to a dashboard-hosted node-info endpoint (or relying on `specs` + `markets`) reduces DNS/subdomain management and simplifies TLS/certificate handling.

Proposed replacement strategies (pick one)
----------------------------------------
Strategy A — Preferred: Add first-class dashboard node-info endpoint
- Use a new endpoint (example):
  - GET https://dashboard.k8s.prd.nos.ci/api/nodes/{node_address}/info
- Benefits: single host, likely stable schema, easier to authenticate and firewall.
- Implementation: coordinator tries this endpoint first; if HTTP 404/410 or other error indicating deprecation, fall back to the old per-node subdomain only for backward compatibility.

Strategy B — Minimal change: keep using old `node/info` only for status but derive other values from `specs` and `markets`.
- Only required if the new `info` endpoint is not available and the per-node host remains available for state.

Strategy C — Remove the old endpoint entirely (breaking change)
- Only for major-version bump. Add migration doc and automation to help users update their nodes.

Data mapping (fields → sensors)
--------------------------------
- Node info (new/old):
  - state/status/nodeStatus -> `NosanaNodeStatusSensor` (normalize into Running/Queued/Offline)
  - uptime -> REMOVED (dashboard /metrics does not provide uptime)
  - info.version -> `NosanaNodeVersionSensor` and `device_info.sw_version`
  - info.model -> `device_info.model`
  - info.country -> `NosanaNodeCountrySensor`
  - info.network.* -> REMOVED (network sensors: ping_ms/download_mbps/upload_mbps are no longer available)
  - marketAddress (if present) -> used to match against `/api/markets`

- Metrics (dashboard):
-  - `metrics.ram_gb` -> `NosanaNodeRamSensor` (integration expects MB; multiply GB→MB, recommended factor: 1024)
-  - `metrics.disk_gb` -> `NosanaNodeDiskSensor` (GB — pass through)
-  - `metrics.cpu.cpu_model` -> `NosanaNodeCpuSensor` (string)
-  - `metrics.cpu.logical_cores` -> `NosanaNodeLogicalCoresSensor`
-  - `metrics.cpu.physical_cores` -> `NosanaNodePhysicalCoresSensor`
-  - `metrics.gpu.devices` -> `NosanaNodeGpuModelSensor` (take first device.name) and `NosanaNodeMemoryGpuSensor` (vram_total_mb)
-  - `metrics.package_version` -> copy into `info.version` or `specs.packageVersion` so `NosanaNodeVersionSensor` continues to work
-  - `marketAddress` (top-level) -> used to match against `/api/markets`
-  - model-specific keys like `<model>_tokens_per_second_mean` under `metrics` -> can be scanned and normalized into the same `earnings["benchmark"]` shape used by the benchmark sensor: `{"model_id": <model>, "tokens_per_second_mean": <value>}`

- Markets (dashboard):
  - match market by keys: `address`, `marketAddress`, `market_address`, `id`
  - name/title: `name`, `marketName`, `title` → `NosanaNodeMarketSensor`
  - type/category → `NosanaNodeMarketTypeSensor`
  - nos_reward_per_second / rewardPerSecond → `NosanaNodeMarketNosRewardSensor`
  - usd_reward_per_hour / rewardPerHourUsd → `NosanaNodeMarketUsdRewardSensor`

- Jobs (dashboard):
  - `jobs` list → per-job fields: `id`, `timeStart`, `timeEnd`, `timeout`, `usdRewardPerHour`, `jobResult.opStates` for llm-benchmark
  - earnings aggregation computed from finalized jobs → `NosanaNodeEarningsUsdSensor`
  - benchmark tokens/sec and model_id extracted into `NosanaNodeBenchmarkTokensPerSecondSensor`

Implementation details & code changes
-----------------------------------
1) Coordinator: add support for the new `/metrics` endpoint and normalization logic; keep the older endpoints as fallbacks.
   - Replace or add `self.metrics_url = f"https://dashboard.k8s.prd.nos.ci/api/nodes/{node_address}/metrics"` (update usage where `self.specs_url` was used).
   - Update `_async_update_data` to fetch the `metrics_url` (HTTP 200 → parse) and normalize the returned JSON into the existing `specs` shape the sensors expect. If the `metrics` endpoint returns an unexpected schema or HTTP errors, fall back to the previous `/specs` or per-node endpoints if still available.
   - Normalization must at minimum perform these transformations:
     - specs["ram"] = int(metrics.get("ram_gb") * 1024)  # MB (guard against missing/invalid values)
     - specs["diskSpace"] = metrics.get("disk_gb")
     - specs["cpu"] = metrics.get("cpu", {}).get("cpu_model")
     - specs["logicalCores"] = metrics.get("cpu", {}).get("logical_cores")
     - specs["physicalCores"] = metrics.get("cpu", {}).get("physical_cores")
     - specs["gpus"] = [{"gpu": d.get("name")} for d in metrics.get("gpu", {}).get("devices", [])]
     - specs["memoryGPU"] = metrics.get("gpu", {}).get("devices", [{}])[0].get("vram_total_mb")
     - specs["packageVersion"] = metrics.get("package_version") or resp.get("package_version")
     - specs["marketAddress"] = resp.get("marketAddress") or metrics.get("market_address")
   - Also scan `metrics` for keys matching the regex `_tokens_per_second_mean` and convert the best candidate into `earnings["benchmark"] = {"model_id": <parsed>, "tokens_per_second_mean": <value>}` when job-based benchmark info is not available.
   - Keep existing timeouts and overall error handling.

2) Config / Feature flag:
   - Add a config entry option `use_dashboard_info` (default: true) stored in `entry.data` so new installs use dashboard endpoint by default. For existing installs, preserve their current behavior unless they opt in (or use autodetect logic described above).
   - If adding a config flow change is heavy, implement autodetect behavior on first successful coordinator run and save detection result to the Store or to `entry.options`.

3) Sensors: keep sensors unchanged where possible.
   - Because coordinator will normalize the incoming payload to the same keys (`info`, `specs`, `market`, `earnings`), the sensors should not need code changes.
   - If the new node-info payload uses different nesting for `network` fields or renames keys, ensure normalization code maps those names into the same keys the sensors expect.

4) Job fetching and markets caching: keep behavior but validate schema differences (e.g., `jobs` response shape).

5) Logging & telemetry: add debug logs that indicate which endpoint was used for this update and whether a fallback occurred:
   - e.g., _LOGGER.debug("Using dashboard_info_url for node %s", node_address)
   - e.g., _LOGGER.warning("Dashboard info endpoint returned 404; falling back to per-node info URL")

6) Tests:
   - Add unit tests that mock aiohttp responses for:
     - new dashboard info 200 response (expected schema)
     - new dashboard info 200 response with alternate keys
     - new dashboard info 404/410 leading to fallback to old endpoint
     - old endpoint 200 response
     - overall coordinator update flow with markets/jobs responses
   - Validate sensors continue to read the expected normalized fields.

Backward compatibility & rollout
--------------------------------
- Implement a safe rollout: attempt new endpoint first with fallback to old if anything fails. This ensures older nodes (still reporting to subdomain) remain supported.
- Add a config option or automatic detection to prefer old endpoint only if necessary; do not remove the old code path without a major version change and explicit migration documentation.

Edge cases and error handling
-----------------------------
- New endpoint returns unexpected schema: normalize with defensive getters and fall back to previous behavior if critical fields are missing.
- New endpoint rate limits / 429: honor Retry-After if present and use the existing markets/jobs caching TTLs to reduce load.
- Jobs endpoint changes format for llm-benchmark: update _extract_llm_benchmark to be defensive and try multiple shapes.

Example normalization strategy (pseudocode)
-----------------------------------------
1. Attempt GET dashboard_info_url
2. If 200: parse JSON to `raw_info`
   - Build `info_out` object with keys expected by sensors:
     - info_out["state"] = raw_info.get("state") or raw_info.get("status") or raw_info.get("nodeStatus")
     - info_out["uptime"] = raw_info.get("uptime") or raw_info.get("uptime_seconds")
     - info_out["info"] = raw_info.get("info") or raw_info (if the dashboard nests differently)
3. If 404/410 or parse error: attempt old `self.info_url` as fallback

Acceptance criteria
-------------------
- Coordinator update succeeds and the same set of sensors report correct values when using the new dashboard endpoint.
- If the new endpoint fails, the integration falls back to the old endpoint without throwing unhandled exceptions and preserves existing sensor values.
- Tests validate both new and fallback behaviors.

Manual test plan
----------------
1. Configure an instance with a test node address and run Home Assistant in dev mode.
2. Mock the dashboard new endpoint to return a sample expected JSON; verify sensors update.
3. Return 404 from the dashboard endpoint and provide a valid old endpoint response; verify fallback and log message.
4. Provide malformed JSON; verify coordinator logs and sets node Offline where appropriate.

Sample test HTTP payloads (representative)
------------------------------------------
New dashboard info (example):

{
  "nodeId": "abcd",
  "state": "RUNNING",
  "uptime": 3600,
  "info": { "version": "1.2.3", "model": "x86-1", "country": "US" },
  "network": { "ping_ms": 10, "download_mbps": 500, "upload_mbps": 200 },
  "marketAddress": "market-xyz"
}

Old per-node info (current):

{
  "state": "OTHER",
  "uptime": 3600,
  "version": "1.2.3",
  "model": "x86-1",
  "country": "US",
  "network": { "ping_ms": 10, "download_mbps": 500, "upload_mbps": 200 }
}

Next steps I can take for you
----------------------------
- I can implement the coordinator changes that add `dashboard_info_url` and normalization with safe fallback, and run tests.
- Or I can produce a focused patch and tests only for the `_async_update_data` path and the normalization logic.

Tell me which you'd like me to do next: implement the code changes and tests now, or only produce the spec file and hand off to your team.
