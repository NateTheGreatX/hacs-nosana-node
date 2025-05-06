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
        """Initialize."""
        self.config_entry = config_entry
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=config_entry.data[CONF_UPDATE_INTERVAL]),
        )

    async def _async_update_data(self):
        """Fetch data from API."""
        try:
            address = self.config_entry.data[CONF_SOLANA_ADDRESS]
            url = f"https://{address}.node.k8s.prd.nos.ci/node/info"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
        except aiohttp.ClientError as err:
            _LOGGER.error(f"Error fetching data: {err}")
            raise UpdateFailed(f"Error fetching data: {err}")