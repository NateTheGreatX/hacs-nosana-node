# custom_components/nosana_node/config_flow.py
"""Config flow for Nosana Node integration."""
from homeassistant import config_entries
from homeassistant.const import CONF_NAME
import voluptuous as vol

from .const import DOMAIN, CONF_NODE_ADDRESS
from .coordinator import NosanaNodeCoordinator


class NosanaNodeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nosana Node."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            node_address = user_input[CONF_NODE_ADDRESS]

            # Validate the node address by attempting to fetch data
            coordinator = NosanaNodeCoordinator(self.hass, node_address)
            try:
                await coordinator.async_refresh()
                if coordinator.data is None:
                    errors["base"] = "cannot_connect"
                else:
                    # Ensure unique entry per node address
                    await self.async_set_unique_id(node_address[:8])
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=user_input.get(CONF_NAME, f"Nosana Node {node_address[:8]}"),
                        data={CONF_NODE_ADDRESS: node_address}
                    )
            except Exception:
                errors["base"] = "cannot_connect"

        data_schema = vol.Schema({
            vol.Required(CONF_NODE_ADDRESS): str,
            vol.Optional(CONF_NAME, default="Nosana Node"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )