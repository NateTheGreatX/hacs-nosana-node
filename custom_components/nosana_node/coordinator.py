import aiohttp
import asyncio
from datetime import timedelta
import logging
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from .const import DOMAIN, CONF_SOLANA_ADDRESS, CONF_UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class NosanaNodeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Nosana Node API data."""

    def __init__(self, hass, config_entry):
        """Initialize and validate Solana address."""
        address = config_entry.data[CONF_SOLANA_ADDRESS]
        if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address):
            _LOGGER.error(f"Invalid Solana address: {address}")
            raise ValueError("Invalid Solana address")

        self.config_entry = config_entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=config_entry.data[CONF_UPDATE_INTERVAL]),
        )

    async def _async_update_data(self):
        """Fetch data from both Nosana APIs."""
        try:
            address = self.config_entry.data[CONF_SOLANA_ADDRESS]
            node_info_url = f"https://{address}.node.k8s.prd.nos.ci/node/info"
            benchmark_url = f"https://dashboard.k8s.prd.nos.ci/api/benchmarks/generic-benchmark-data?node={address}"

            async with aiohttp.ClientSession() as session:
                # Fetch node info
                node_info_task = session.get(node_info_url)
                benchmark_task = session.get(benchmark_url)

                # Execute both requests concurrently
                node_info_response, benchmark_response = await asyncio.gather(
                    node_info_task,
                    benchmark_task,
                    return_exceptions=True
                )

                # Process node info response
                node_info_data = {}
                if isinstance(node_info_response, aiohttp.ClientResponse):
                    node_info_response.raise_for_status()
                    node_info_data = await node_info_response.json()
                else:
                    _LOGGER.warning("Failed to fetch node info data")

                # Process benchmark response
                benchmark_data = {}
                if isinstance(benchmark_response, aiohttp.ClientResponse):
                    benchmark_response.raise_for_status()
                    benchmark_response_data = await benchmark_response.json()
                    # Extract first item from data array (if available)
                    benchmark_data = benchmark_response_data.get("data", [{}])[0] if benchmark_response_data.get(
                        "data") else {}
                else:
                    _LOGGER.warning("Failed to fetch benchmark data")

                # Combine data
                return {
                    "node_info": node_info_data,
                    "benchmark": benchmark_data
                }
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error fetching data: {err}")
            raise UpdateFailed(f"Error fetching data: {err}")