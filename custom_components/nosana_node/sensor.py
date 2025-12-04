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
        NosanaNodeUptimeSensor(coordinator, entry.title, node_address),
        NosanaNodeVersionSensor(coordinator, entry.title, node_address),
        NosanaNodeCountrySensor(coordinator, entry.title, node_address),
        NosanaNodePingSensor(coordinator, entry.title, node_address),
        NosanaNodeDownloadSensor(coordinator, entry.title, node_address),
        NosanaNodeUploadSensor(coordinator, entry.title, node_address),
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
    """Sensor for the node 'state' (Queued/Running)."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "status")
        self._attr_icon = "mdi:server"

    @property
    def state(self) -> StateType:
        if self.coordinator.data is None:
            return None
        state = self.coordinator.data.get("state")
        return "Queued" if state == "QUEUED" else "Running"

    @property
    def entity_picture(self) -> Optional[str]:
        """Return a path to the integration image for UI display.

        Try HACS common locations and a local /local path. This doesn't
        verify the URL exists; the frontend will handle missing images.
        """
        # HACS installs community files to /hacsfiles/<repository>/ or /community/<repository>/ depending on HACS version.
        # Using both common prefixes improves compatibility.
        repo_name = "NateTheGreatX/hacs-nosana-node"
        candidates = [
            f"/hacsfiles/{repo_name.split('/')[-1]}/logomark.svg",
            f"/community/{repo_name.split('/')[-1]}/logomark.svg",
            # Local fallback if the user put the file under config/www/nosana_node/
            "/local/nosana_node/logomark.svg",
            # Raw GitHub fallback (may be blocked by CORS), uses raw.githubusercontent.com on the default branch main
            f"https://raw.githubusercontent.com/{repo_name}/main/logomark.svg",
        ]
        return candidates[0]


class NosanaNodeUptimeSensor(_BaseNosanaSensor):
    """Sensor for the node uptime (seconds)."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "uptime")
        self._attr_native_unit_of_measurement = "s"
        self._attr_icon = "mdi:clock-outline"
        # Mark as a measurement so HA knows this is a numeric measurement
        self._attr_state_class = SensorStateClass.MEASUREMENT
        # Use the duration device class for uptime
        self._attr_device_class = SensorDeviceClass.DURATION

    @property
    def state(self) -> Optional[float]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("uptime")


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
    """Sensor for the node ping in milliseconds."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "ping_ms")
        self._attr_native_unit_of_measurement = "ms"
        self._attr_icon = "mdi:speedometer"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[float]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("info", {}).get("network", {}).get("ping_ms")


class NosanaNodeDownloadSensor(_BaseNosanaSensor):
    """Sensor for the node download bandwidth in Mbps."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "download_mbps")
        self._attr_native_unit_of_measurement = "Mbps"
        self._attr_icon = "mdi:download"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[float]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("info", {}).get("network", {}).get("download_mbps")


class NosanaNodeUploadSensor(_BaseNosanaSensor):
    """Sensor for the node upload bandwidth in Mbps."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        super().__init__(coordinator, name, node_address, "upload_mbps")
        self._attr_native_unit_of_measurement = "Mbps"
        self._attr_icon = "mdi:upload"
        self._attr_state_class = SensorStateClass.MEASUREMENT

    @property
    def state(self) -> Optional[float]:
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.get("info", {}).get("network", {}).get("upload_mbps")


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
