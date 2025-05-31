# custom_components/nosana_node/coordinator.py
"""Data coordinator for Nosana Node integration."""
import logging
from datetime import timedelta

import aiohttp
import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

class NosanaNodeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Nosana node data."""

    def __init__(self, hass, node_address):
        """Initialize the coordinator."""
        self.node_address = node_address
        self.api_url = f"https://{node_address}.node.k8s.prd.nos.ci/node/info"
        super().__init__(
            hass,
            _LOGGER,
            name="Nosana Node",
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self):
        """Fetch data from Nosana API."""
        try:
            async with async_timeout.timeout(10):
                async with aiohttp.ClientSession() as session:
                    async with session.get(self.api_url) as response:
                        if response.status != 200:
                            _LOGGER.error(
                                "Failed to fetch data from %s, status: %s",
                                self.api_url,
                                response.status,
                            )
                            return None
                        data = await response.json()
                        return data
        except Exception as err:
            _LOGGER.error("Error fetching Nosana node data: %s", err)
            return None