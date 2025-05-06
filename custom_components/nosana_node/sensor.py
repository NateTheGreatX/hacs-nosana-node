from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.const import UnitOfInformation
from .const import DOMAIN, CONF_SOLANA_ADDRESS

SENSOR_TYPES = [
    # Sensors from /specs (primary)
    SensorEntityDescription(
        key="status",
        name="Node Status",
        state_class=None,  # Non-numeric (e.g., "PREMIUM")
    ),
    SensorEntityDescription(
        key="country",
        name="Node Country",
        state_class=None,  # Non-numeric (e.g., "US")
    ),
    SensorEntityDescription(
        key="ram_mb",
        name="RAM Size",
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="disk_space_gb",
        name="Disk Space",
        native_unit_of_measurement=UnitOfInformation.GIGABYTES,
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="cpu",
        name="CPU Model",
        state_class=None,  # Non-numeric (e.g., "Intel(R) Core(TM) i5-3470")
    ),
    SensorEntityDescription(
        key="logical_cores",
        name="CPU Logical Cores",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="physical_cores",
        name="CPU Physical Cores",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="node_version",
        name="Node Version",
        state_class=None,  # Non-numeric (e.g., "1.0.37")
    ),
    SensorEntityDescription(
        key="system_environment",
        name="System Environment",
        state_class=None,  # Non-numeric (e.g., "5.4.0-215-generic")
    ),
    SensorEntityDescription(
        key="memory_gpu_mb",
        name="GPU Memory Total",
        native_unit_of_measurement=UnitOfInformation.MEGABYTES,
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="cuda_version",
        name="CUDA Version",
        state_class=None,  # Non-numeric (e.g., "12.9")
    ),
    SensorEntityDescription(
        key="nvml_version",
        name="NVML Version",
        state_class=None,  # Non-numeric (e.g., "575.51.02")
    ),
    SensorEntityDescription(
        key="ping_ms",
        name="Network Ping",
        native_unit_of_measurement="ms",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="download_mbps",
        name="Download Speed",
        native_unit_of_measurement="Mbps",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="upload_mbps",
        name="Upload Speed",
        native_unit_of_measurement="Mbps",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="gpu_name",
        name="GPU Name",
        state_class=None,  # Non-numeric (e.g., "NVIDIA GeForce RTX 5080")
    ),
    SensorEntityDescription(
        key="market_address",
        name="Market Address",
        state_class=None,  # Non-numeric (Solana address)
    ),
    SensorEntityDescription(
        key="major_version_gpu",
        name="GPU Major Version",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="minor_version_gpu",
        name="GPU Minor Version",
        state_class="measurement",  # Numeric
    ),
    # Sensor from /node/info
    SensorEntityDescription(
        key="state",
        name="Node State",
        state_class=None,  # Non-numeric (e.g., "offline", "OTHER")
    ),
    # Sensors from /benchmarks
    SensorEntityDescription(
        key="storage_to_cpu_bandwidth_mbps",
        name="Storage to CPU Bandwidth",
        native_unit_of_measurement="Mbps",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="cpu_to_gpu_bandwidth_mbps",
        name="CPU to GPU Bandwidth",
        native_unit_of_measurement="Mbps",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="system_read_write_speed",
        name="System Read/Write Speed",
        native_unit_of_measurement="MB/s",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="ram_read_write_speed",
        name="RAM Read/Write Speed",
        native_unit_of_measurement="MB/s",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="internet_speed_download",
        name="Internet Download Speed",
        native_unit_of_measurement="Mbps",
        state_class="measurement",  # Numeric
    ),
    SensorEntityDescription(
        key="internet_speed_upload",
        name="Internet Upload Speed",
        native_unit_of_measurement="Mbps",
        state_class="measurement",  # Numeric
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
            configuration_url="https://dashboard.k8s.prd.nos.ci",
        )

    @property
    def native_value(self):
        """Return the sensor value."""
        # Specs data (primary)
        specs = self.coordinator.data.get("specs", {}) if self.coordinator.data else {}
        bandwidth = specs.get("bandwidth", {})
        gpus = specs.get("gpus", [{}])[0]

        # Node info data (for state)
        node_info = self.coordinator.data.get("node_info", {}) if self.coordinator.data else {}

        # Benchmark data
        benchmark = self.coordinator.data.get("benchmark", {}) if self.coordinator.data else {}
        metrics = benchmark.get("metrics", {})

        # Sensors from /specs
        if self.entity_description.key == "status":
            return specs.get("status")
        elif self.entity_description.key == "country":
            return specs.get("country")
        elif self.entity_description.key == "ram_mb":
            return specs.get("ram")
        elif self.entity_description.key == "disk_space_gb":
            return specs.get("diskSpace")
        elif self.entity_description.key == "cpu":
            return specs.get("cpu")
        elif self.entity_description.key == "logical_cores":
            return specs.get("logicalCores")
        elif self.entity_description.key == "physical_cores":
            return specs.get("physicalCores")
        elif self.entity_description.key == "node_version":
            return specs.get("nodeVersion")
        elif self.entity_description.key == "system_environment":
            return specs.get("systemEnvironment")
        elif self.entity_description.key == "memory_gpu_mb":
            return specs.get("memoryGPU")
        elif self.entity_description.key == "cuda_version":
            return specs.get("cudaVersion")
        elif self.entity_description.key == "nvml_version":
            return specs.get("nvmlVersion")
        elif self.entity_description.key == "ping_ms":
            return bandwidth.get("ping")
        elif self.entity_description.key == "download_mbps":
            return bandwidth.get("download")
        elif self.entity_description.key == "upload_mbps":
            return bandwidth.get("upload")
        elif self.entity_description.key == "gpu_name":
            return gpus.get("gpu")
        elif self.entity_description.key == "market_address":
            return specs.get("marketAddress")
        elif self.entity_description.key == "major_version_gpu":
            return specs.get("majorVersionGPU")
        elif self.entity_description.key == "minor_version_gpu":
            return specs.get("minorVersionGPU")
        # Sensor from /node/info
        elif self.entity_description.key == "state":
            return node_info.get("state", "offline")
        # Sensors from /benchmarks
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
        specs = self.coordinator.data.get("specs", {}) if self.coordinator.data else {}
        node_info = self.coordinator.data.get("node_info", {}) if self.coordinator.data else {}
        benchmark = self.coordinator.data.get("benchmark", {}) if self.coordinator.data else {}
        attributes = {}

        if self.entity_description.key == "state":
            attributes["node_address"] = specs.get("nodeAddress")
        elif self.entity_description.key in ["logical_cores", "physical_cores"]:
            attributes["cpu_model"] = specs.get("cpu")
        elif self.entity_description.key == "memory_gpu_mb":
            attributes["gpu_name"] = specs.get("gpus", [{}])[0].get("gpu")
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