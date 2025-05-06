import re
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from .const import DOMAIN, CONF_SOLANA_ADDRESS, CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL

class NosanaNodeConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Nosana Node."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        errors = {}
        if user_input is not None:
            # Validate Solana address (base58, 32-44 characters)
            address = user_input[CONF_SOLANA_ADDRESS]
            if not re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", address):
                errors["base"] = "invalid_solana_address"
            else:
                return self.async_create_entry(
                    title=address,
                    data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({
                vol.Required(CONF_SOLANA_ADDRESS): str,
                vol.Optional(CONF_UPDATE_INTERVAL, default=DEFAULT_UPDATE_INTERVAL): int,
            }),
            errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return OptionsFlowHandler(config_entry)

class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow."""

    async def async_step_init(self, user_input=None):
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Optional(
                    CONF_UPDATE_INTERVAL,
                    default=self.config_entry.data.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
                ): int
            })
        )