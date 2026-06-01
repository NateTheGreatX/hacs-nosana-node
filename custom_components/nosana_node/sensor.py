# custom_components/nosana_node/sensor.py
"""Sensor platform for Nosana Node integration.

This module exposes multiple SensorEntity classes that read from the
NosanaNodeCoordinator and present discrete sensors for Home Assistant.
"""
from typing import List, Optional

from homeassistant.components.sensor import SensorEntity, SensorStateClass, SensorDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, CONF_NODE_ADDRESS
from .coordinator import NosanaNodeCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nosana Node sensors from a config entry."""
    coordinator: NosanaNodeCoordinator = hass.data[DOMAIN][entry.entry_id]
    node_address = entry.data[CONF_NODE_ADDRESS]

    sensors: List[SensorEntity] = [
        NosanaNodeStatusSensor(coordinator, entry.title, node_address),
        NosanaNodeVersionSensor(coordinator, entry.title, node_address),
        NosanaNodeCountrySensor(coordinator, entry.title, node_address),
        # network sensors restored from dashboard /metrics
        NosanaNodePingSensor(coordinator, entry.title, node_address),
        NosanaNodeDownloadSensor(coordinator, entry.title, node_address),
        NosanaNodeUploadSensor(coordinator, entry.title, node_address),
        NosanaNodeCountrySensor(coordinator, entry.title, node_address),
        # new sensors from specs / markets
        NosanaNodeMarketSensor(coordinator, entry.title, node_address),
        NosanaNodeMarketAddressSensor(coordinator, entry.title, node_address),
        NosanaNodeMarketTypeSensor(coordinator, entry.title, node_address),
        NosanaNodeMarketNosRewardSensor(coordinator, entry.title, node_address),
        NosanaNodeMarketUsdRewardSensor(coordinator, entry.title, node_address),
        NosanaNodeRamSensor(coordinator, entry.title, node_address),
        NosanaNodeDiskSensor(coordinator, entry.title, node_address),
        NosanaNodeCpuSensor(coordinator, entry.title, node_address),
        NosanaNodeLogicalCoresSensor(coordinator, entry.title, node_address),
        NosanaNodePhysicalCoresSensor(coordinator, entry.title, node_address),
        NosanaNodeGpuModelSensor(coordinator, entry.title, node_address),
        NosanaNodeMemoryGpuSensor(coordinator, entry.title, node_address),
        # earnings sensors (aggregated via HA Store)
        NosanaNodeEarningsUsdSensor(coordinator, entry.title, node_address),
        NosanaNodeBenchmarkTokensPerSecondSensor(coordinator, entry.title, node_address),
        NosanaNodeJobTimeoutHoursSensor(coordinator, entry.title, node_address),
        NosanaNodeJobTimeLeftHoursSensor(coordinator, entry.title, node_address),
    ]

    async_add_entities(sensors)


class _BaseNosanaSensor(CoordinatorEntity, SensorEntity):
    """Base class for Nosana Node sensors."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str, suffix: str):
        super().__init__(coordinator)
        self._node_address = node_address
        # Use a human-friendly display name by title-casing the suffix (replace underscores with spaces)
        display_suffix = suffix.replace("_", " ").title()
        self._attr_name = f"{name} {display_suffix}"
        # Keep the unique id stable by using the raw suffix form (lower/underscored)
        self._attr_unique_id = f"nosana_node_{node_address[:8]}_{suffix.replace(' ', '_').lower()}"
        # Keep the device name (based on the config entry title) so device_info can use it
        self._device_name = name

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None

    @property
    def device_info(self) -> dict:
        """Return device information for device registry grouping.

        The device is identified by (DOMAIN, node_address) so multiple entities
        created for the same node are grouped under one device entry.
        """
        info = {
            "identifiers": {("nosana_node", self._node_address)},
            "name": self._device_name,
            "manufacturer": "Nosana",
            "model": "Nosana Node",
        }
        # Add software version/model if coordinator has data
        if self.coordinator.data:
            model = self.coordinator.data.get("info", {}).get("model")
            version = self.coordinator.data.get("info", {}).get("version")
            if model:
                info["model"] = model
            if version:
                info["sw_version"] = version
        return info


class NosanaNodeStatusSensor(_BaseNosanaSensor):
    """Sensor for the node 'state' with explicit mapping.

    Mapping:
    - OTHER -> Running
    - QUEUED -> Queued
    - RUNNING -> Running
    - OFFLINE/ERROR/missing -> Offline
    """

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "status")
        self._attr_icon = "mdi:server"

    @property
    def state(self) -> StateType:
        if self.coordinator.data is None:
            return None
        state = self.coordinator.data.get("state")
        if not isinstance(state, str) or not state.strip():
            return "Offline"
        s = state.strip().upper()
        if s in {"OFFLINE", "ERROR"}:
            return "Offline"
        if s == "QUEUED":
            return "Queued"
        if s in {"RUNNING", "OTHER"}:
            return "Running"
        # Fallback for any other unexpected value -> Offline
        return "Offline"

    @property
    def entity_picture(self) -> Optional[str]:
        """Return a path to the integration image for UI display.

        Prefer a local /local path per HA docs (place file under config/www/...).
        """
        return "/local/nosana_node/logomark.svg"


# Uptime and network sensors removed — the dashboard /metrics endpoint no longer provides
# uptime or network fields (ping_ms/download_mbps/upload_mbps). They were removed from setup
# and the implementation to avoid exposing unavailable values.


class NosanaNodeVersionSensor(_BaseNosanaSensor):
    """Sensor for the node software version."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "version")
        self._attr_icon = "mdi:tag"

    @property
    def state(self) -> StateType:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("info", {}).get("version")


class NosanaNodeCountrySensor(_BaseNosanaSensor):
    """Sensor for the node country."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "country")
        self._attr_icon = "mdi:map-marker"

    @property
    def state(self) -> StateType:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("info", {}).get("country")


class NosanaNodePingSensor(_BaseNosanaSensor):
    """Sensor for the network ping in milliseconds."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "ping_ms")
        self._attr_icon = "mdi:network-latency"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "ms"

    @property
    def state(self) -> Optional[int]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("ping_ms")


class NosanaNodeDownloadSensor(_BaseNosanaSensor):
    """Sensor for the network download speed in Mbps."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "download_mbps")
        self._attr_icon = "mdi:download"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "Mbps"

    @property
    def state(self) -> Optional[int]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("download_mbps")


class NosanaNodeUploadSensor(_BaseNosanaSensor):
    """Sensor for the network upload speed in Mbps."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "upload_mbps")
        self._attr_icon = "mdi:upload"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "Mbps"

    @property
    def state(self) -> Optional[int]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("upload_mbps")


# network-related sensors removed


# New sensors from specs/markets
class NosanaNodeMarketSensor(_BaseNosanaSensor):
    """Sensor for the market name determined from specs/markets endpoints."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "market")
        self._attr_icon = "mdi:store"

    @property
    def state(self) -> Optional[str]:
        if self.coordinator.data is None:
            return None
        # market_name is populated by the coordinator
        return self.coordinator.data.get("market", {}).get("name")


class NosanaNodeMarketAddressSensor(_BaseNosanaSensor):
    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "market_address")
        self._attr_icon = "mdi:map-marker"

    @property
    def state(self) -> Optional[str]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("market", {}).get("address")


class NosanaNodeMarketTypeSensor(_BaseNosanaSensor):
    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "market_type")
        self._attr_icon = "mdi:shape"

    @property
    def state(self) -> Optional[str]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("market", {}).get("type")


class NosanaNodeMarketNosRewardSensor(_BaseNosanaSensor):
    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "nos_reward_per_second")
        self._attr_icon = "mdi:currency-usd"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[float]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("market", {}).get("nos_reward_per_second")


class NosanaNodeMarketUsdRewardSensor(_BaseNosanaSensor):
    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "usd_reward_per_hour")
        self._attr_icon = "mdi:currency-usd"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "USD/h"

    @property
    def state(self) -> Optional[float]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("market", {}).get("usd_reward_per_hour")


class NosanaNodeRamSensor(_BaseNosanaSensor):
    """Sensor for the node RAM in MB."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "ram")
        self._attr_native_unit_of_measurement = "MB"
        self._attr_icon = "mdi:memory"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[int]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("ram")


class NosanaNodeDiskSensor(_BaseNosanaSensor):
    """Sensor for the node disk space in GB."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "disk_space")
        self._attr_native_unit_of_measurement = "GB"
        self._attr_icon = "mdi:harddisk"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[int]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("diskSpace")


class NosanaNodeCpuSensor(_BaseNosanaSensor):
    """Sensor for the CPU model string."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "cpu")
        self._attr_icon = "mdi:cpu-64-bit"

    @property
    def state(self) -> Optional[str]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("cpu")


class NosanaNodeLogicalCoresSensor(_BaseNosanaSensor):
    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "logical_cores")
        self._attr_icon = "mdi:chip"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "cores"

    @property
    def state(self) -> Optional[int]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("logicalCores")


class NosanaNodePhysicalCoresSensor(_BaseNosanaSensor):
    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "physical_cores")
        self._attr_icon = "mdi:chip"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "cores"

    @property
    def state(self) -> Optional[int]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("physicalCores")


class NosanaNodeGpuModelSensor(_BaseNosanaSensor):
    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "gpu_model")
        self._attr_icon = "mdi:gpu"

    @property
    def state(self) -> Optional[str]:
        if self.coordinator.data is None:
            return None
        gpus = self.coordinator.data.get("specs", {}).get("gpus") or []
        if not isinstance(gpus, list) or not gpus:
            return None
        first = gpus[0]
        return first.get("gpu") if isinstance(first, dict) else None


class NosanaNodeMemoryGpuSensor(_BaseNosanaSensor):
    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "memory_gpu")
        self._attr_native_unit_of_measurement = "MB"
        self._attr_icon = "mdi:memory"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[float]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("specs", {}).get("memoryGPU")


class NosanaNodeEarningsUsdSensor(_BaseNosanaSensor):
    """Total USD earned (aggregated from jobs via HA Store)."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "earnings_usd_total")
        self._attr_icon = "mdi:currency-usd"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = "USD"

    @property
    def state(self) -> Optional[float]:
        if self.coordinator.data is None:
            return None
        return (self.coordinator.data.get("earnings") or {}).get("usd_total")


class NosanaNodeBenchmarkTokensPerSecondSensor(_BaseNosanaSensor):
    """Latest LLM benchmark tokens/sec (mean) with model_id attribute.

    Keeps the last known value when new data is unavailable (e.g., job not finalized yet).
    """

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "benchmark_tokens_per_second")
        self._attr_icon = "mdi:chart-line"
        self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_native_unit_of_measurement = "tokens/s"
        self._last_value: Optional[float] = None
        self._last_model_id: Optional[str] = None

    @property
    def state(self) -> Optional[float]:
        data = self.coordinator.data or {}
        bench = (data.get("earnings") or {}).get("benchmark") or {}
        val = bench.get("tokens_per_second_mean")
        if isinstance(val, (int, float)):
            self._last_value = float(val)
            # update cached model id if present
            mid = bench.get("model_id")
            if isinstance(mid, str):
                self._last_model_id = mid
            return self._last_value
        # No new finalized benchmark → keep last known value
        return self._last_value

    @property
    def extra_state_attributes(self) -> dict:
        data = self.coordinator.data or {}
        bench = (data.get("earnings") or {}).get("benchmark") or {}
        model_id = bench.get("model_id")
        if isinstance(model_id, str):
            self._last_model_id = model_id
        return {"model_id": self._last_model_id} if isinstance(self._last_model_id, str) else {}


class NosanaNodeJobTimeoutHoursSensor(_BaseNosanaSensor):
    """Job timeout in hours. 0 if the latest job is finished or missing."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "job_timeout_hours")
        self._attr_icon = "mdi:timer-sand"
        self._attr_native_unit_of_measurement = "h"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[float]:
        data = self.coordinator.data or {}
        latest = (data.get("earnings") or {}).get("latest_job") or {}
        try:
            time_end = int(latest.get("timeEnd", 0) or 0)
            if time_end > 0:
                return 0.0

            # timeout may be stored in seconds (typical) or milliseconds in some APIs.
            timeout_raw = int(latest.get("timeout", 0) or 0)
            if timeout_raw <= 0:
                return 0.0

            # Heuristic: if timeout looks like milliseconds (very large), convert to seconds
            if timeout_raw > 1_000_000_000:
                timeout_seconds = timeout_raw / 1000.0
            else:
                timeout_seconds = float(timeout_raw)

            return round(timeout_seconds / 3600.0, 6)
        except Exception:
            return 0.0


class NosanaNodeJobTimeLeftHoursSensor(_BaseNosanaSensor):
    """Time left (hours) for the latest running job. 0 if finished or no timeout."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "job_time_left_hours")
        self._attr_icon = "mdi:timer"
        self._attr_native_unit_of_measurement = "h"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[float]:
        from datetime import datetime, timezone
        data = self.coordinator.data or {}
        latest = (data.get("earnings") or {}).get("latest_job") or {}
        try:
            time_end = int(latest.get("timeEnd", 0) or 0)
            if time_end > 0:
                return 0.0

            time_start_raw = int(latest.get("timeStart", 0) or 0)
            timeout_raw = int(latest.get("timeout", 0) or 0)
            if time_start_raw <= 0 or timeout_raw <= 0:
                return 0.0

            # Heuristic: detect if timeStart is in milliseconds
            if time_start_raw > 1_000_000_000_000:
                time_start = int(time_start_raw / 1000)
            else:
                time_start = time_start_raw

            # timeout likely in seconds; if extremely large assume ms
            if timeout_raw > 1_000_000_000:
                timeout_seconds = timeout_raw / 1000.0
            else:
                timeout_seconds = float(timeout_raw)

            now_ts = int(datetime.now(timezone.utc).timestamp())
            expire_at = int(time_start + int(timeout_seconds))
            left = max(0, expire_at - now_ts)
            return round(float(left) / 3600.0, 6)
        except Exception:
            return 0.0

    @property
    def extra_state_attributes(self) -> dict:
        # Expose the raw latest_job for debugging convenience
        data = self.coordinator.data or {}
        latest = (data.get("earnings") or {}).get("latest_job")
        return {"latest_job": latest} if isinstance(latest, dict) else {}
