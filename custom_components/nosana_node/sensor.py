from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import DATA_GIGABYTES, DATA_MEGABYTES, PERCENTAGE, UnitOfInformation
from .const import DOMAIN

SENSOR_TYPES = [
    SensorEntityDescription(
        key="uptime",
        name="Node Uptime",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="state",
        name="Node State",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="version",
        name="Node Version",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="country",
        name="Node Country",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="ping_ms",
        name="Network Ping",
        native_unit_of_measurement="ms",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="download_mbps",
        name="Download Speed",
        native_unit_of_measurement="Mbps",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="upload_mbps",
        name="Upload Speed",
        native_unit_of_measurement="Mbps",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="disk_gb",
        name="Disk Size",
        native_unit_of_measurement=DATA_GIGABYTES,
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="ram_mb",
        name="RAM Size",
        native_unit_of_measurement=DATA_MEGABYTES,
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="cpu_logical_cores",
        name="CPU Logical Cores",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="gpu_memory_total_mb",
        name="GPU Memory Total",
        native_unit_of_measurement=DATA_MEGABYTES,
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="cuda_driver_version",
        name="CUDA Driver Version",
        state_class="measurement",
    ),
]


async def async_setup_entry(hass, config_entry, async_add_entities):
    """Set up the sensor platform."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities = [
        NosanaNodeSensor(coordinator, config_entry, description)
        for description in SENSOR_TYPES
    ]
    async_add_entities(entities)


class NosanaNodeSensor(SensorEntity):
    """Representation of a Nosana Node sensor."""

    def __init__(self, coordinator, config_entry, description):
        """Initialize the sensor."""
        super().__init__()
        self.coordinator = coordinator
        self.entity_description = description
        self._attr_unique_id = f"{config_entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"Nosana Node {config_entry.data[CONF_SOLANA_ADDRESS][:8]}",
            manufacturer="Nosana",
            model="Node",
        )

    @property
    def native_value(self):
        """Return the sensor value."""
        data = self.coordinator.data.get("info", {})
        network = data.get("network", {})
        gpus = data.get("gpus", {}).get("devices", [{}])[0]

        if self.entity_description.key == "uptime":
            return self.coordinator.data.get("uptime")
        elif self.entity_description.key == "state":
            return self.coordinator.data.get("state")
        elif self.entity_description.key == "version":
            return data.get("version")
        elif self.entity_description.key == "country":
            return data.get("country")
        elif self.entity_description.key == "ping_ms":
            return network.get("ping_ms")
        elif self.entity_description.key == "download_mbps":
            return network.get("download_mbps")
        elif self.entity_description.key == "upload_mbps":
            return network.get("upload_mbps")
        elif self.entity_description.key == "disk_gb":
            return data.get("disk_gb")
        elif self.entity_description.key == "ram_mb":
            return data.get("ram_mb")
        elif self.entity_description.key == "cpu_logical_cores":
            return data.get("cpu", {}).get("logical_cores")
        elif self.entity_description.key == "gpu_memory_total_mb":
            return gpus.get("memory", {}).get("total_mb")
        elif self.entity_description.key == "cuda_driver_version":
            return data.get("gpus", {}).get("cuda_driver_version")
        return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        data = self.coordinator.data.get("info", {})
        gpus = data.get("gpus", {}).get("devices", [{}])[0]
        attributes = {}

        if self.entity_description.key == "uptime":
            attributes["node_address"] = self.coordinator.data.get("node")
        elif self.entity_description.key == "cpu_logical_cores":
            attributes["cpu_model"] = data.get("cpu", {}).get("model")
            attributes["physical_cores"] = data.get("cpu", {}).get("physical_cores")
        elif self.entity_description.key == "gpu_memory_total_mb":
            attributes["gpu_name"] = gpus.get("name")
            attributes["gpu_uuid"] = gpus.get("uuid")
        return attributes

    @property
    def available(self):
        """Return if sensor is available."""
        return self.coordinator.last_update_success