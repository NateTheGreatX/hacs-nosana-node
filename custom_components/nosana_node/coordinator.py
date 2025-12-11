# custom_components/nosana_node/coordinator.py
"""Data coordinator for Nosana Node integration."""
import logging
from datetime import timedelta, datetime
from typing import Optional, Tuple

import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession

# Import UpdateFailed in a way that works across Home Assistant versions
try:
    # Preferred location in many versions
    from homeassistant.exceptions import UpdateFailed  # type: ignore
except Exception:  # pragma: no cover - defensive fallback
    try:
        from homeassistant.helpers.update_coordinator import UpdateFailed  # type: ignore
    except Exception:
        class UpdateFailed(Exception):
            """Fallback UpdateFailed exception."""

_LOGGER = logging.getLogger(__name__)


class NosanaNodeCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Nosana node data."""

    def __init__(self, hass, node_address: str):
        """Initialize the coordinator."""
        self.node_address = node_address
        self.info_url = f"https://{node_address}.node.k8s.prd.nos.ci/node/info"
        self.specs_url = f"https://dashboard.k8s.prd.nos.ci/api/nodes/{node_address}/specs"
        self.markets_url = "https://dashboard.k8s.prd.nos.ci/api/markets"
        # Reuse Home Assistant's shared aiohttp session
        self._session = async_get_clientsession(hass)

        # markets cache (avoid fetching the markets list every update)
        self._markets_cache: Optional[list] = None
        self._markets_last_fetch: Optional[datetime] = None
        # configure how often to refetch markets (seconds)
        self._markets_ttl_seconds = 300

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

                # Fetch markets list (cached)
                markets = []
                now = datetime.utcnow()
                should_refetch_markets = True
                if self._markets_cache is not None and self._markets_last_fetch is not None:
                    elapsed = (now - self._markets_last_fetch).total_seconds()
                    if elapsed < self._markets_ttl_seconds:
                        should_refetch_markets = False

                if should_refetch_markets:
                    try:
                        resp_markets = await self._session.get(self.markets_url)
                        if resp_markets.status == 200:
                            markets = await resp_markets.json()
                        else:
                            _LOGGER.debug("Markets endpoint returned status %s", getattr(resp_markets, "status", None))
                            markets = []
                        # update cache
                        self._markets_cache = markets
                        self._markets_last_fetch = now
                    except Exception:
                        _LOGGER.warning("Failed to fetch markets from %s", self.markets_url)
                        markets = self._markets_cache or []
                else:
                    markets = self._markets_cache or []

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
                                # try to extract reward fields using several possible keys
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

    # ---------- Solana queue position helper (optional dependencies) ----------
    async def async_get_node_queue_position(self, node_id_str: str, market_id_str: Optional[str] = None, rpc_url: str = "https://api.mainnet-beta.solana.com") -> Tuple[Optional[int], Optional[int], Optional[int]]:
        """Return (position, total_in_queue, status_code).

        This uses optional Solana dependencies. If the required packages are not
        installed the method will log a debug message and return (None, None, None).
        """
        try:
            # Lazy import so integration still loads without these packages
            from solana.rpc.async_api import AsyncClient  # type: ignore
            from solana.publickey import PublicKey  # type: ignore
            import base64
            import borsh_construct as borsh  # type: ignore
        except Exception:
            _LOGGER.debug("Solana libraries not available; cannot fetch queue position")
            return None, None, None

        # Minimal borsh schemas (discriminator=8 bytes, pubkeys 32 bytes)
        market_schema = borsh.CStruct(
            "discriminator" / borsh.Bytes(8),
            "authority" / borsh.Bytes(32),
            "queue_type" / borsh.U8,
            "job_price" / borsh.U64,
            "job_timeout" / borsh.I64,
            "job_expiration" / borsh.I64,
            "node_stake_minimum" / borsh.U128,
            "queue" / borsh.Vec(borsh.Bytes(32)),
        )

        node_schema = borsh.CStruct(
            "discriminator" / borsh.Bytes(8),
            "authority" / borsh.Bytes(32),
            "market" / borsh.Bytes(32),
            "status" / borsh.U8,
        )

        def _decode_account_data(raw) -> Optional[bytes]:
            if raw is None:
                return None
            if isinstance(raw, (list, tuple)) and len(raw) >= 1 and isinstance(raw[0], str):
                return base64.b64decode(raw[0])
            if isinstance(raw, (bytes, bytearray)):
                return bytes(raw)
            return None

        try:
            async with AsyncClient(rpc_url) as client:
                node_pubkey = PublicKey(node_id_str)

                node_resp = await client.get_account_info(node_pubkey)
                node_raw = _decode_account_data(node_resp.value.data if node_resp.value else None)
                if not node_raw:
                    _LOGGER.debug("Node account not found on Solana: %s", node_id_str)
                    return None, None, None

                parsed_node = node_schema.parse(node_raw)
                market_pubkey = PublicKey(bytes(parsed_node.market))

                if market_id_str and str(market_pubkey) != market_id_str:
                    _LOGGER.debug("Node not in specified market (on-chain) %s != %s", market_id_str, market_pubkey)
                    return None, None, int(parsed_node.status)

                status = int(parsed_node.status)

                market_resp = await client.get_account_info(market_pubkey)
                market_raw = _decode_account_data(market_resp.value.data if market_resp.value else None)
                if not market_raw:
                    _LOGGER.debug("Market account not found on Solana: %s", market_pubkey)
                    return None, None, status

                parsed_market = market_schema.parse(market_raw)
                queue_bytes_list = parsed_market.queue or []
                queue = [PublicKey(bytes(pk)) for pk in queue_bytes_list]
                total = len(queue)

                for i, pk in enumerate(queue):
                    if str(pk) == str(node_pubkey):
                        return i + 1, total, status

                return None, total, status
        except Exception as e:
            _LOGGER.debug("Error fetching queue position from Solana RPC: %s", e)
            return None, None, None

