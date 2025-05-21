"""Constants for the Daikin P1/P2 component."""

from datetime import timedelta
import logging

LOGGER = logging.getLogger(__package__)

DOMAIN = "daikin_p1p2bus"

MANUFACTURER = "Daikin"

CONF_SERIAL_PORT = "serial_port"
CONF_SERIAL_PORT_BAUD = "serial_port_baud"

SIGNAL_DAIKIN_P1P2_TELEGRAM = "daikin_p1p2_telegram"
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)

DEFAULT_TITLE = "Daikin P1/P2"

DEFAULT_DEVICE_NAME = "Daikin P1/P2 Gateway"
