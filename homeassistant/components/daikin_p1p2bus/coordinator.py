"""Data update coordinator for Daikin P1/P2 gateway."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_SERIAL_PORT,
    CONF_SERIAL_PORT_BAUD,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
)
from .p1p2 import P1P2Protocol

_LOGGER = logging.getLogger(__name__)


class DaikinP1P2UpdateCoordinator(DataUpdateCoordinator[None]):
    """Data update coordinator for pushed data from Daikin P1/P2 gateway."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        port = config_entry.data[CONF_SERIAL_PORT]
        baud = config_entry.data[CONF_SERIAL_PORT_BAUD]

        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=f"{port}:{baud}",
            update_interval=None,  # Disable update interval as server pushes
        )
        self._proto = P1P2Protocol(port, baud)
        self.device_info = DeviceInfo(
            name=DEFAULT_DEVICE_NAME,
            manufacturer=MANUFACTURER,
            identifiers={(DOMAIN, config_entry.unique_id)},
        )

        self.last_update_success = False
        _LOGGER.debug(
            "Initialized Daikin P1/P2 coordinator on %s@%d baud", port, baud)

    def proto(self) -> P1P2Protocol:
        """Return the protocol."""
        return self._proto

    @callback
    def _on_model(self, name: str) -> None:
        """Set model name."""
        self.device_info["model"] = name

    async def _async_setup(self) -> None:
        """Perform async setup for the coordinator."""
        # Start the server
        try:
            await self._proto.connect(self.hass.loop)
        except OSError as ex:
            raise UpdateFailed from ex
        self._proto.add_model_listener(self._on_model)

    async def _async_update_data(self) -> None:
        """Empty update method since data is pushed."""
