# custom_components/nosana_node/coordinator.py
"""Data coordinator for Nosana Node integration."""
import logging
from datetime import timedelta, datetime
from typing import Optional, Tuple, List

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


# --- minimal base58 encoding (pure python) ---
_B58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"


def _b58encode(data: bytes) -> str:
    """Encode bytes to base58 (pure Python)."""
    num = int.from_bytes(data, "big")
    if num == 0:
        # preserve leading zeros count
        n_pad = len(data) - len(data.lstrip(b"\0"))
        return _B58_ALPHABET[0] * n_pad
    enc = []
    while num > 0:
        num, rem = divmod(num, 58)
        enc.append(_B58_ALPHABET[rem])
    # leading zero bytes -> '1'
    n_pad = len(data) - len(data.lstrip(b"\0"))
    return _B58_ALPHABET[0] * n_pad + "".join(reversed(enc))


def _decode_account_data(raw) -> Optional[bytes]:
    """Decode account data shapes returned by Solana RPC into raw bytes."""
    if raw is None:
        return None
    # common RPC shape: [base64_string, "base64"]
    if isinstance(raw, (list, tuple)) and len(raw) >= 1 and isinstance(raw[0], str):
        import base64

        return base64.b64decode(raw[0])
    if isinstance(raw, (bytes, bytearray)):
        return bytes(raw)
    return None


def _extract_pubkey_vec_candidates(raw: bytes) -> List[List[bytes]]:
    """Heuristic: find possible borsh Vec(pubkey) occurrences in raw bytes.

    Borsh vec encodes a u32 little-endian length followed by N items. For pubkeys
    items are 32 bytes each. This scans for any plausible (length, items) slice
    and returns candidate lists of pubkey byte sequences.
    """
    candidates: List[List[bytes]] = []
    if not raw:
        return candidates
    Lmax = (len(raw) // 32) + 1
    # scan through the blob looking for a 4-byte little-endian length that yields
    # a plausible number of 32-byte pubkey entries remaining
    for i in range(0, max(1, len(raw) - 4)):
        # read u32 LE at position i
        length = int.from_bytes(raw[i : i + 4], "little")
        if length <= 0 or length > Lmax:
            continue
        start = i + 4
        needed = length * 32
        if start + needed <= len(raw):
            pubkeys = [
                raw[start + j * 32 : start + (j + 1) * 32] for j in range(length)
            ]
            if all(len(pk) == 32 for pk in pubkeys):
                candidates.append(pubkeys)
    return candidates


def _get_queue_position_from_market_raw(market_raw: bytes, node_addr_b58: str) -> Optional[Tuple[int, int]]:
    """Return (position, total) if node found in any plausible queue vec, else None.

    If multiple candidate vecs are found prefer the longest one.
    """
    candidates = _extract_pubkey_vec_candidates(market_raw)
    if not candidates:
        return None
    candidates.sort(key=lambda c: len(c), reverse=True)
    for pubkeys in candidates:
        pubkey_strs = [_b58encode(pk) for pk in pubkeys]
        try:
            idx = pubkey_strs.index(node_addr_b58)
            return idx + 1, len(pubkey_strs)
        except ValueError:
            continue
    return None


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
                # Fetch the node info (graceful fallback to Offline)
                info: dict = {}
                try:
                    resp_info = await self._session.get(self.info_url)
                    if resp_info.status == 200:
                        info = await resp_info.json()
                    else:
                        _LOGGER.warning(
                            "Failed to fetch node info from %s, status: %s",
                            self.info_url,
                            resp_info.status,
                        )
                        info = {}
                except Exception as e:
                    _LOGGER.warning(
                        "Error fetching node info from %s: %s",
                        self.info_url,
                        e,
                    )
                    info = {}

                # Ensure a status field exists; default to Offline when unknown/invalid
                status = None
                if isinstance(info, dict):
                    status = info.get("status") or info.get("nodeStatus") or info.get("state")
                if not isinstance(status, str) or not status:
                    # set multiple commonly used keys to ensure sensors see Offline
                    info["status"] = "Offline"
                    info["nodeStatus"] = "Offline"
                    info["state"] = "Offline"

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
