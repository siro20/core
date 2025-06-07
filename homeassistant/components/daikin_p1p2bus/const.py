"""Constants for the Daikin P1/P2 component."""

from datetime import timedelta
import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = "daikin_p1p2bus"

MANUFACTURER = "Daikin"

CONF_SERIAL_PORT = "serial_port"
CONF_SERIAL_PORT_BAUD = "serial_port_baud"
CONF_P1P2_DEBUG = "p1p2_debug"
CONF_GW_SUPPORTS_TX = "gateway_supports_tx"
CONF_POLL_ENERGY_STATS = "poll_energy_stats"
CONF_SYSTEM_HAS_DHW = "system_has_dhw"
CONF_SYSTEM_HAS_GAS_BOILER = "system_has_gas_boiler"
CONF_SYSTEM_HAS_ADDITIONAL_ZONE = "system_has_additional_zone"
CONF_SYSTEM_HAS_BACKUP_HEATER = "system_has_backup_heater"
CONF_SYSTEM_SUPPORTS_COOLING = "system_supports_cooling"

SIGNAL_DAIKIN_P1P2_TELEGRAM = "daikin_p1p2_telegram"
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

DEFAULT_TITLE = "Daikin P1/P2"

DEFAULT_DEVICE_NAME = "Daikin P1/P2 Gateway"
