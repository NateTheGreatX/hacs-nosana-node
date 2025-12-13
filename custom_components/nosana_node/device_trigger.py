"""Device triggers for Nosana Node integration.

Provides device automation triggers for status changes so the HA UI shows
"No triggers available" → fixed. We map device triggers to a standard state
trigger on the status sensor entity belonging to the device.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.components.device_automation import DEVICE_TRIGGER_SCHEMA
from homeassistant.components.automation import state as state_trigger

from .const import DOMAIN

# Supported trigger types
TRIGGER_TYPES = {"running", "queued", "offline"}


async def async_get_triggers(hass: HomeAssistant, device_id: str) -> List[Dict]:
    """Return a list of triggers for a device.

    We expose triggers for the device's status sensor becoming Running/Queued/Offline.
    """
    triggers: List[Dict] = []

    ent_reg = er.async_get(hass)
    dev_reg = dr.async_get(hass)

    device = dev_reg.async_get(device_id)
    if device is None:
        return triggers

    # Collect all entity_ids for this device in our domain
    entries = [e for e in ent_reg.entities.get_entries_for_device_id(device_id) if e.domain == "sensor"]

    # Find the status sensor entity (suffix contains "_status")
    status_entity_id: Optional[str] = None
    for entry in entries:
        if entry.platform == DOMAIN and entry.entity_id.endswith("_status"):
            status_entity_id = entry.entity_id
            break

    if not status_entity_id:
        return triggers

    # For each trigger type, add a device trigger that maps to a state transition
    for trig_type in TRIGGER_TYPES:
        triggers.append(
            {
                "platform": "device",
                "domain": DOMAIN,
                "device_id": device_id,
                "entity_id": status_entity_id,
                "type": trig_type,
            }
        )

    return triggers


async def async_attach_trigger(
    hass: HomeAssistant,
    config: Dict,
    action,
    trigger_info,
):
    """Attach a trigger for the given device automation config.

    Map our device trigger types to a standard state trigger on the status sensor.
    """
    DEVICE_TRIGGER_SCHEMA(config)  # basic validation

    entity_id = config.get("entity_id")
    trig_type = config.get("type")

    # Map type -> expected state value
    to_map = {
        "running": "Running",
        "queued": "Queued",
        "offline": "Offline",
    }
    to_state = to_map.get(trig_type)
    if not entity_id or not to_state:
        return None

    # Build a state trigger config
    state_config = {
        "platform": "state",
        "entity_id": entity_id,
        "to": to_state,
    }

    # Attach the underlying state trigger
    return await state_trigger.async_attach_trigger(hass, state_config, action, trigger_info,)


async def async_get_trigger_capabilities(hass: HomeAssistant, config: Dict) -> Dict:
    """Return trigger capabilities (none for these simple triggers)."""
    return {"extra_fields": []}

