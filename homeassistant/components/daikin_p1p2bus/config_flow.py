"""Config flow for Daikin P1/P2 integration."""

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.schema_config_entry_flow import (
    SchemaFlowFormStep,
    SchemaOptionsFlowHandler,
)

from .const import (
    CONF_GW_SUPPORTS_TX,
    CONF_P1P2_DEBUG,
    CONF_POLL_ENERGY_STATS,
    CONF_SERIAL_PORT,
    CONF_SERIAL_PORT_BAUD,
    CONF_SYSTEM_HAS_ADDITIONAL_ZONE,
    CONF_SYSTEM_HAS_BACKUP_HEATER,
    CONF_SYSTEM_HAS_DHW,
    CONF_SYSTEM_HAS_GAS_BOILER,
    CONF_SYSTEM_IS_EJHA_COMPATIBLE,
    CONF_SYSTEM_SUPPORTS_COOLING,
    DEFAULT_TITLE,
    DOMAIN,
)

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SERIAL_PORT, default="/dev/ttyACM0"): str,
        vol.Required(CONF_SERIAL_PORT_BAUD, default=115200): cv.positive_int,
        vol.Required(CONF_GW_SUPPORTS_TX, default=False): bool,
        vol.Required(CONF_SYSTEM_HAS_DHW, default=True): bool,
        vol.Required(CONF_SYSTEM_HAS_GAS_BOILER, default=True): bool,
        vol.Required(CONF_SYSTEM_HAS_ADDITIONAL_ZONE, default=True): bool,
        vol.Required(CONF_SYSTEM_HAS_BACKUP_HEATER, default=True): bool,
        vol.Required(CONF_SYSTEM_SUPPORTS_COOLING, default=True): bool,
        vol.Required(CONF_SYSTEM_IS_EJHA_COMPATIBLE, default=False): bool,
    }
)
CONFIG_FLOW = {
    "user": SchemaFlowFormStep(DATA_SCHEMA),
}


class DaikinP1P2ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Daikin P1/P2 config flow."""

    VERSION = 1
    config_flow = CONFIG_FLOW

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the user setup step."""
        if user_input is not None:
            self._async_abort_entries_match(
                {
                    CONF_SERIAL_PORT: user_input[CONF_SERIAL_PORT],
                    CONF_SERIAL_PORT_BAUD: user_input[CONF_SERIAL_PORT_BAUD],
                    CONF_GW_SUPPORTS_TX: user_input[CONF_GW_SUPPORTS_TX],
                    CONF_SYSTEM_HAS_DHW: user_input[CONF_SYSTEM_HAS_DHW],
                    CONF_SYSTEM_HAS_GAS_BOILER: user_input[CONF_SYSTEM_HAS_GAS_BOILER],
                    CONF_SYSTEM_HAS_ADDITIONAL_ZONE: user_input[
                        CONF_SYSTEM_HAS_ADDITIONAL_ZONE
                    ],
                    CONF_SYSTEM_HAS_BACKUP_HEATER: user_input[
                        CONF_SYSTEM_HAS_BACKUP_HEATER
                    ],
                    CONF_SYSTEM_SUPPORTS_COOLING: user_input[
                        CONF_SYSTEM_SUPPORTS_COOLING
                    ],
                    CONF_SYSTEM_IS_EJHA_COMPATIBLE: user_input[
                        CONF_SYSTEM_IS_EJHA_COMPATIBLE
                    ],
                }
            )

            return self.async_create_entry(
                title=DEFAULT_TITLE,
                data=user_input,
            )

        data_schema = self.add_suggested_values_to_schema(DATA_SCHEMA, user_input)
        return self.async_show_form(step_id="user", data_schema=data_schema)

    async def async_step_reconfigure(
        self, user_input: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle reconfiguration."""
        return await self.async_step_user()

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SchemaOptionsFlowHandler:
        """Get the options flow for this handler."""

        OPTIONS_FLOW = {
            "init": SchemaFlowFormStep(
                vol.Schema(
                    {
                        vol.Required(CONF_P1P2_DEBUG, default=False): bool,
                        vol.Required(
                            CONF_POLL_ENERGY_STATS,
                            default=config_entry.data[CONF_GW_SUPPORTS_TX],
                        ): bool,
                    }
                )
            ),
        }

        return SchemaOptionsFlowHandler(config_entry, OPTIONS_FLOW)
