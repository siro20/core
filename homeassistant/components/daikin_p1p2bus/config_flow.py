"""Config flow for Daikin P1/P2 integration."""

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers import config_validation as cv

from .const import CONF_SERIAL_PORT, CONF_SERIAL_PORT_BAUD, DEFAULT_TITLE, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_PORT, default="/dev/ttyACM0"): str,
        vol.Required(CONF_SERIAL_PORT_BAUD, default=115200): cv.positive_int,
    }
)


class DaikinP1P2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Daikin P1/P2 config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the user setup step."""
        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_SERIAL_PORT: user_input[CONF_SERIAL_PORT],
                    CONF_SERIAL_PORT_BAUD: user_input[CONF_SERIAL_PORT_BAUD],
                }
            )

            return self.async_create_entry(
                title=DEFAULT_TITLE,
                data=user_input,
            )

        data_schema = self.add_suggested_values_to_schema(DATA_SCHEMA, user_input)
        return self.async_show_form(step_id="user", data_schema=data_schema)
