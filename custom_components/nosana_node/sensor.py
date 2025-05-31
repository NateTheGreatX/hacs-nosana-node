# custom_components/nosana_node/sensor.py
"""Sensor platform for Nosana Node integration."""
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType

from .const import DOMAIN, CONF_NODE_ADDRESS
from .coordinator import NosanaNodeCoordinator


async def async_setup_entry(
        hass: HomeAssistant,
        entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Nosana Node sensor from a config entry."""
    coordinator: NosanaNodeCoordinator = hass.data[DOMAIN][entry.entry_id]
    node_address = entry.data[CONF_NODE_ADDRESS]

    async_add_entities([
        NosanaNodeSensor(coordinator, entry.title, node_address)
    ])


class NosanaNodeSensor(SensorEntity):
    """Representation of a Nosana Node sensor."""

    def __init__(self, coordinator: NosanaNodeCoordinator, name: str, node_address: str):
        """Initialize the sensor."""
        super().__init__()
        self.coordinator = coordinator
        self._node_address = node_address
        self._attr_name = name
        self._attr_unique_id = f"nosana_node_{node_address[:8]}_node_status"
        self._attr_icon = "mdi:server"
        self._attr_entity_id = f"sensor.nosana_node_{node_address[:8]}_node_status"

    @property
    def state(self) -> StateType:
        """Return the state of the sensor."""
        if self.coordinator.data is None:
            return None
        state = self.coordinator.data.get("state")
        return "Queued" if state == "QUEUED" else "Running"

    @property
    def extra_state_attributes(self):
        """Return the state attributes."""
        if self.coordinator.data is None:
            return {}
        return {
            "node_address": self._node_address,
            "uptime": self.coordinator.data.get("uptime"),
            "version": self.coordinator.data.get("info", {}).get("version"),
            "country": self.coordinator.data.get("info", {}).get("country"),
            "ping_ms": self.coordinator.data.get("info", {}).get("network", {}).get("ping_ms"),
            "download_mbps": self.coordinator.data.get("info", {}).get("network", {}).get("download_mbps"),
            "upload_mbps": self.coordinator.data.get("info", {}).get("network", {}).get("upload_mbps"),
        }

    @property
    def available(self) -> bool:
        """Return if the sensor is available."""
        return self.coordinator.data is not None