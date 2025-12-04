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

    @property
    def available(self) -> bool:
        return self.coordinator.data is not None


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
