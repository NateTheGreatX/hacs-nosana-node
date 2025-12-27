# custom_components/nosana_node/coordinator.py
"""Data coordinator for Nosana Node integration."""
import logging
from datetime import timedelta, datetime, timezone
from typing import Optional, Tuple, List, Dict, Any

import async_timeout
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store

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
        self.jobs_url_base = "https://dashboard.k8s.prd.nos.ci/api/jobs"
        # Reuse Home Assistant's shared aiohttp session
        self._session = async_get_clientsession(hass)
        # HA Store for per-node job accounting
        self._store = Store(hass, 1, f"nosana_node/node-{node_address}.jobs.json")

        # markets cache (avoid fetching the markets list every update)
        self._markets_cache: Optional[list] = None
        self._markets_last_fetch: Optional[datetime] = None
        # configure how often to refetch markets (seconds)
        self._markets_ttl_seconds = 300
        # jobs fetch TTL (seconds) and last status tracking
        self._jobs_last_fetch: Optional[datetime] = None
        self._jobs_ttl_seconds = 15 * 60  # 15 minutes
        self._last_status: Optional[str] = None

        super().__init__(
            hass,
            _LOGGER,
            name="Nosana Node",
            update_interval=timedelta(seconds=30),
        )

    async def _async_update_data(self):
        """Fetch data from Nosana API and related endpoints.

        Returns a dict that preserves the original `/node/info` top-level keys
        for backward compatibility, and adds `specs`, `market`, and `earnings` dicts.
        """
        try:
            async with async_timeout.timeout(15):
                # Fetch the node info (graceful fallback to Offline)
                info: dict = {}
                info_fetch_ok = False
                try:
                    resp_info = await self._session.get(self.info_url)
                    if resp_info.status == 200:
                        info = await resp_info.json()
                        info_fetch_ok = True
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

                # Normalize status/state for automations
                normalized_status = "Offline"
                raw_state = None
                if info_fetch_ok and isinstance(info, dict):
                    raw_state = info.get("state") or info.get("status") or info.get("nodeStatus")
                    if isinstance(raw_state, str):
                        s = raw_state.upper()
                        if s == "OTHER":
                            normalized_status = "Running"
                        elif s == "QUEUED":
                            normalized_status = "Queued"
                        elif s in ("RUNNING", "ONLINE"):
                            normalized_status = "Running"
                        elif s in ("OFFLINE", "STOPPED", "ERROR"):
                            normalized_status = "Offline"
                        else:
                            # unknown state but endpoint responded; assume Running
                            normalized_status = "Running"
                    else:
                        # info responded but no usable state string
                        normalized_status = "Running"
                else:
                    # info endpoint failed → Offline
                    normalized_status = "Offline"

                # Ensure consistent keys are present
                info = info if isinstance(info, dict) else {}
                info["status"] = normalized_status
                info["nodeStatus"] = normalized_status
                info["state"] = raw_state if isinstance(raw_state, str) else normalized_status

                # detect status change
                status_changed = self._last_status != normalized_status
                self._last_status = normalized_status

                # Fetch specs
                try:
                    resp_specs = await self._session.get(self.specs_url)
                    if resp_specs.status != 200:
                        _LOGGER.warning("Failed to fetch specs from %s, status: %s", self.specs_url, resp_specs.status)
                        specs = {}
                    else:
                        specs = await resp_specs.json()
                except Exception:
                    _LOGGER.warning("Error fetching specs from %s", self.specs_url)
                    specs = {}

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

                market: Dict[str, Any] = {
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

                # Jobs fetch: TTL (15 min) or immediate on status change
                should_fetch_jobs = False
                if status_changed:
                    should_fetch_jobs = True
                else:
                    if self._jobs_last_fetch is None:
                        should_fetch_jobs = True
                    else:
                        elapsed_jobs = (now - self._jobs_last_fetch).total_seconds()
                        should_fetch_jobs = elapsed_jobs >= self._jobs_ttl_seconds

                if should_fetch_jobs:
                    earnings = await self._async_update_jobs_and_earnings()
                    self._jobs_last_fetch = now
                else:
                    # Recompute totals from store without hitting jobs API
                    try:
                        store_data = await self._store.async_load() or {}
                        jobs_store: Dict[str, Any] = store_data.get("jobs") or {}
                    except Exception:
                        jobs_store = {}
                    total_seconds = 0
                    total_usd = 0.0
                    for rec in jobs_store.values():
                        if int(rec.get("timeEnd", 0) or 0) > 0:
                            total_seconds += int(rec.get("runtime_seconds", 0) or 0)
                            total_usd += float(rec.get("earned_usd", 0.0) or 0.0)
                    earnings = {
                        "usd_total": round(total_usd, 6),
                        "seconds_total": int(total_seconds),
                        "jobs_tracked": len(jobs_store),
                    }

                # Merge info with extra fields so existing sensors keep working
                merged = {**(info or {}), "specs": specs or {}, "market": market, "earnings": earnings}
                return merged
        except UpdateFailed:
            raise
        except Exception as err:
            _LOGGER.exception("Error fetching Nosana node data: %s", err)
            raise UpdateFailed(err)

    async def _async_update_jobs_and_earnings(self) -> Dict[str, Any]:
        """Fetch recent jobs, update HA Store for this node, and compute totals.

        Strategy:
        - Fetch up to 10 most recent jobs for this node.
        - Maintain a per-node store of jobs that we've seen/accounted.
        - Only count finalized jobs (timeEnd > 0) toward totals.
        - Save the store when new jobs are discovered, jobs finalize, or benchmark data is backfilled.
        - Parse llm-benchmark results and store under each job record as job['benchmark'].
        """
        try:
            # Load store (structure: {"jobs": {id: {record}}})
            store_data = await self._store.async_load() or {}
            jobs_store: Dict[str, Any] = store_data.get("jobs") or {}
        except Exception:
            jobs_store = {}
            store_data = {"jobs": jobs_store}

        # Fetch jobs list (limit=10)
        params = f"?limit=10&offset=0&node={self.node_address}"
        jobs_url = f"{self.jobs_url_base}{params}"
        jobs: List[Dict[str, Any]] = []
        try:
            resp = await self._session.get(jobs_url)
            if resp.status == 200:
                body = await resp.json()
                j = body.get("jobs") if isinstance(body, dict) else None
                if isinstance(j, list):
                    jobs = j
            else:
                _LOGGER.debug("Jobs endpoint returned status %s", resp.status)
        except Exception as e:
            _LOGGER.debug("Error fetching jobs from %s: %s", jobs_url, e)

        changed = False

        def _compute(job: Dict[str, Any]) -> Tuple[int, float]:
            start = int(job.get("timeStart", 0) or 0)
            end = int(job.get("timeEnd", 0) or 0)
            # Only count earnings/runtime if the job is finalized
            if start <= 0 or end <= 0 or end < start:
                return 0, 0.0
            runtime = max(0, end - start)
            usdph = float(job.get("usdRewardPerHour", 0.0) or 0.0)
            earned = (runtime / 3600.0) * usdph
            return runtime, earned

        def _extract_llm_benchmark(job: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            jr = job.get("jobResult")
            if not isinstance(jr, dict):
                return None
            op_states = jr.get("opStates")
            if not isinstance(op_states, list):
                return None
            for op in op_states:
                if not isinstance(op, dict):
                    continue
                if op.get("operationId") == "llm-benchmark" and op.get("status") == "success":
                    results = op.get("results", {})
                    arr = results.get("results_llm_benchmark")
                    if isinstance(arr, list) and arr:
                        raw = arr[0]
                        try:
                            import json as _json
                            parsed = _json.loads(raw)
                            model_id = parsed.get("model_id") or parsed.get("results", {}).get("users_1", {}).get("model_id")
                            tps = parsed.get("results", {}).get("users_1", {}).get("tokens_per_second", {})
                            mean = tps.get("mean")
                            if model_id and isinstance(mean, (int, float)):
                                return {"model_id": model_id, "tokens_per_second_mean": float(mean)}
                        except Exception:
                            return None
            return None

        latest_bench: Optional[Dict[str, Any]] = None
        latest_bench_time: int = 0

        for job in jobs:
            jid = str(job.get("id")) if job is not None else None
            if not jid or jid == "None":
                continue

            # Skip jobs with no start time
            if int(job.get("timeStart", 0) or 0) <= 0:
                continue

            runtime, earned = _compute(job)
            finalized = int(job.get("timeEnd", 0) or 0) > 0

            prev = jobs_store.get(jid)
            # Backfill benchmark if present and missing
            bench = _extract_llm_benchmark(job) if finalized else None
            if prev is None:
                new_record = {
                    "id": int(job.get("id", 0) or 0),
                    "timeStart": int(job.get("timeStart", 0) or 0),
                    "timeEnd": int(job.get("timeEnd", 0) or 0),
                    "usdRewardPerHour": float(job.get("usdRewardPerHour", 0.0) or 0.0),
                    "runtime_seconds": int(runtime),
                    "earned_usd": float(earned),
                    "state": job.get("state"),
                    "finalized": bool(finalized),
                    "last_seen": datetime.now(timezone.utc).isoformat(),
                }
                if bench:
                    new_record["benchmark"] = bench
                jobs_store[jid] = new_record
                changed = True
            else:
                prev_end = int(prev.get("timeEnd", 0) or 0)
                if finalized and (not prev.get("finalized") or prev_end != int(job.get("timeEnd", 0) or 0)):
                    # update finalized info
                    prev.update({
                        "timeEnd": int(job.get("timeEnd", 0) or 0),
                        "runtime_seconds": int(runtime),
                        "earned_usd": float(earned),
                        "finalized": True,
                        "usdRewardPerHour": float(job.get("usdRewardPerHour", 0.0) or 0.0),
                        "last_seen": datetime.now(timezone.utc).isoformat(),
                    })
                    if bench:
                        prev["benchmark"] = bench
                    changed = True
                else:
                    # If benchmark exists and not stored yet, backfill
                    if bench and not prev.get("benchmark"):
                        prev["benchmark"] = bench
                        prev["last_seen"] = datetime.now(timezone.utc).isoformat()
                        changed = True

            # Track latest benchmark by timeEnd
            if finalized and bench:
                time_end = int(job.get("timeEnd", 0) or 0)
                if time_end > latest_bench_time:
                    latest_bench_time = time_end
                    latest_bench = bench

        if changed:
            try:
                await self._store.async_save({"jobs": jobs_store})
            except Exception as e:
                _LOGGER.debug("Failed to save jobs store: %s", e)

        # Compute totals only from finalized jobs
        total_seconds = 0
        total_usd = 0.0
        for rec in jobs_store.values():
            if int(rec.get("timeEnd", 0) or 0) > 0:
                total_seconds += int(rec.get("runtime_seconds", 0) or 0)
                total_usd += float(rec.get("earned_usd", 0.0) or 0.0)

        # Expose latest benchmark (from latest 10 or store fallback)
        latest_bench_out: Dict[str, Any] = {}
        if latest_bench:
            latest_bench_out = latest_bench
        else:
            # fallback: scan store for any benchmark
            for rec in jobs_store.values():
                b = rec.get("benchmark")
                if isinstance(b, dict):
                    latest_bench_out = b
                    break

        return {
            "usd_total": round(total_usd, 6),
            "seconds_total": int(total_seconds),
            "jobs_tracked": len(jobs_store),
            "benchmark": latest_bench_out,
        }
