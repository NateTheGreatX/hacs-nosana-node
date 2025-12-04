# custom_components/nosana_node/coordinator.py
"""Data coordinator for Nosana Node integration."""
import logging
from datetime import timedelta

import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

_LOGGER = logging.getLogger(__name__)


class NosanaNodeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Nosana node data."""

    def __init__(self, hass, node_address):
        """Initialize the coordinator."""
        self.node_address = node_address
        self.info_url = f"https://{node_address}.node.k8s.prd.nos.ci/node/info"
        self.specs_url = f"https://dashboard.k8s.prd.nos.ci/api/nodes/{node_address}/specs"
        self.markets_url = "https://dashboard.k8s.prd.nos.ci/api/markets"
        # Reuse Home Assistant's shared aiohttp session
        self._session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name="Nosana Node",
            update_interval=timedelta(seconds=60),
        )

    async def _async_update_data(self):
        """Fetch data from Nosana API and related endpoints.

        Returns a dict that preserves the original `/node/info` top-level keys
        for backward compatibility, and adds `specs` and `market` dict.
        """
        try:
            async with async_timeout.timeout(10):
                # Fetch the node info
                resp_info = await self._session.get(self.info_url)
                if resp_info.status != 200:
                    _LOGGER.error("Failed to fetch node info from %s, status: %s", self.info_url, resp_info.status)
                    raise UpdateFailed(f"Failed to fetch node info: {resp_info.status}")
                info = await resp_info.json()

                # Fetch specs
                resp_specs = await self._session.get(self.specs_url)
                if resp_specs.status != 200:
                    _LOGGER.warning("Failed to fetch specs from %s, status: %s", self.specs_url, resp_specs.status)
                    specs = {}
                else:
                    specs = await resp_specs.json()

                # Fetch markets list
                resp_markets = await self._session.get(self.markets_url)
                markets = []
                if resp_markets.status == 200:
                    try:
                        markets = await resp_markets.json()
                    except Exception:
                        _LOGGER.warning("Failed to decode markets JSON from %s", self.markets_url)
                        markets = []
                else:
                    _LOGGER.debug("Markets endpoint returned status %s", getattr(resp_markets, "status", None))

                # Determine market address from specs (fallback to info)
                market_address = None
                if isinstance(specs, dict):
                    market_address = specs.get("marketAddress") or specs.get("market_address")
                if not market_address and isinstance(info, dict):
                    market_address = info.get("marketAddress") or info.get("market_address")

                market = {
                    "address": market_address,
                    "name": None,
                    "type": None,
                    "nos_reward_per_second": None,
                    "usd_reward_per_hour": None,
                }

                if market_address and isinstance(markets, list):
                    for m in markets:
                        if not isinstance(m, dict):
                            continue
                        # try a few common key names to match the market address
                        for key in ("address", "marketAddress", "market_address", "id"):
                            if m.get(key) == market_address:
                                # extract a name from common keys
                                market["name"] = m.get("name") or m.get("marketName") or m.get("title")
                                # market type
                                market["type"] = m.get("type") or m.get("marketType") or m.get("category")
                                # slug
                                market["slug"] = m.get("slug") or m.get("marketSlug")
                                # try to extract reward fields using several possible keys, prefer snake_case keys present in your example
                                market["nos_reward_per_second"] = (
                                    m.get("nos_reward_per_second")
                                    or m.get("nosRewardPerSecond")
                                    or m.get("rewardPerSecond")
                                    or m.get("reward_per_second")
                                )
                                market["usd_reward_per_hour"] = (
                                    m.get("usd_reward_per_hour")
                                    or m.get("usdRewardPerHour")
                                    or m.get("rewardPerHourUsd")
                                    or m.get("rewardPerHour")
                                    or m.get("reward_per_hour_usd")
                                )
                                break
                        if market.get("name"):
                            break

                # Merge info with extra fields so existing sensors keep working
                merged = {**(info or {}), "specs": specs or {}, "market": market}
                return merged
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception("Error fetching Nosana node data: %s", err)
            raise UpdateFailed(err)
