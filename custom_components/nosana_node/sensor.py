from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import PERCENTAGE, UnitOfInformation
from .const import DOMAIN, CONF_SOLANA_ADDRESS

SENSOR_TYPES = [
    # Existing sensors (node info API)
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
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="ram_mb",
        name="RAM Size",
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
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
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="cuda_driver_version",
        name="CUDA Driver Version",
        state_class="measurement",
    ),
    # New sensors (benchmark API)
    SensorEntityDescription(
        key="storage_to_cpu_bandwidth_mbps",
        name="Storage to CPU Bandwidth",
        native_unit_of_measurement="Mbps",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="cpu_to_gpu_bandwidth_mbps",
        name="CPU to GPU Bandwidth",
        native_unit_of_measurement="Mbps",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="system_read_write_speed",
        name="System Read/Write Speed",
        native_unit_of_measurement="MB/s",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="ram_read_write_speed",
        name="RAM Read/Write Speed",
        native_unit_of_measurement="MB/s",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="internet_speed_download",
        name="Internet Download Speed",
        native_unit_of_measurement="Mbps",
        state_class="measurement",
    ),
    SensorEntityDescription(
        key="internet_speed_upload",
        name="Internet Upload Speed",
        native_unit_of_measurement="Mbps",
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
        # Node info data
        node_info = self.coordinator.data.get("node_info", {}) if self.coordinator.data else {}
        node_info_data = node_info.get("info", {})
        network = node_info_data.get("network", {})
        gpus = node_info_data.get("gpus", {}).get("devices", [{}])[0]

        # Benchmark data
        benchmark = self.coordinator.data.get("benchmark", {}) if self.coordinator.data else {}
        metrics = benchmark.get("metrics", {})

        # Existing sensors (node info)
        if self.entity_description.key == "uptime":
            return node_info.get("uptime")
        elif self.entity_description.key == "state":
            return node_info.get("state")
        elif self.entity_description.key == "version":
            return node_info_data.get("version")
        elif self.entity_description.key == "country":
            return node_info_data.get("country")
        elif self.entity_description.key == "ping_ms":
            return network.get("ping_ms")
        elif self.entity_description.key == "download_mbps":
            return network.get("download_mbps")
        elif self.entity_description.key == "upload_mbps":
            return network.get("upload_mbps")
        elif self.entity_description.key == "disk_gb":
            return node_info_data.get("disk_gb")
        elif self.entity_description.key == "ram_mb":
            return node_info_data.get("ram_mb")
        elif self.entity_description.key == "cpu_logical_cores":
            return node_info_data.get("cpu", {}).get("logical_cores")
        elif self.entity_description.key == "gpu_memory_total_mb":
            return gpus.get("memory", {}).get("total_mb")
        elif self.entity_description.key == "cuda_driver_version":
            return node_info_data.get("gpus", {}).get("cuda_driver_version")
        # New sensors (benchmark)
        elif self.entity_description.key == "storage_to_cpu_bandwidth_mbps":
            return metrics.get("storageToCpuBandwidthMbps")
        elif self.entity_description.key == "cpu_to_gpu_bandwidth_mbps":
            return metrics.get("cpuToGpuBandwidthMbps")
        elif self.entity_description.key == "system_read_write_speed":
            return metrics.get("systemReadWriteSpeed")
        elif self.entity_description.key == "ram_read_write_speed":
            return metrics.get("ramReadWriteSpeed")
        elif self.entity_description.key == "internet_speed_download":
            return metrics.get("internetSpeedDownload")
        elif self.entity_description.key == "internet_speed_upload":
            return metrics.get("internetSpeedUpload")
        return None

    @property
    def extra_state_attributes(self):
        """Return additional attributes."""
        node_info = self.coordinator.data.get("node_info", {}) if self.coordinator.data else {}
        node_info_data = node_info.get("info", {})
        gpus = node_info_data.get("gpus", {}).get("devices", [{}])[0]
        benchmark = self.coordinator.data.get("benchmark", {}) if self.coordinator.data else {}
        attributes = {}

        if self.entity_description.key == "uptime":
            attributes["node_address"] = node_info.get("node")
        elif self.entity_description.key == "cpu_logical_cores":
            attributes["cpu_model"] = node_info_data.get("cpu", {}).get("model")
            attributes["physical_cores"] = node_info_data.get("cpu", {}).get("physical_cores")
        elif self.entity_description.key == "gpu_memory_total_mb":
            attributes["gpu_name"] = gpus.get("name")
            attributes["gpu_uuid"] = gpus.get("uuid")
        elif self.entity_description.key in [
            "storage_to_cpu_bandwidth_mbps",
            "cpu_to_gpu_bandwidth_mbps",
            "system_read_write_speed",
            "ram_read_write_speed",
            "internet_speed_download",
            "internet_speed_upload"
        ]:
            attributes["bench_version"] = benchmark.get("benchVersion")
            attributes["gpu_address"] = benchmark.get("gpu")
        return attributes

    @property
    def available(self):
        """Return if sensor is available."""
        return self.coordinator.last_update_success