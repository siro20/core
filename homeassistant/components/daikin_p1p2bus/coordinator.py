"""Data update coordinator for Daikin P1/P2 gateway."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_GW_SUPPORTS_TX,
    CONF_P1P2_DEBUG,
    CONF_POLL_ENERGY_STATS,
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
        self._b8_packet_task: asyncio.Task[None] | None = None

        port = config_entry.data[CONF_SERIAL_PORT]
        baud = config_entry.data[CONF_SERIAL_PORT_BAUD]

        self._gateway_supports_tx = (
            bool(config_entry.data[CONF_GW_SUPPORTS_TX])
            if CONF_GW_SUPPORTS_TX in config_entry.data
            else True
        )
        self._poll_energy_stats = (
            self._gateway_supports_tx
            and bool(config_entry.options[CONF_POLL_ENERGY_STATS])
            if CONF_POLL_ENERGY_STATS in config_entry.options
            else self._gateway_supports_tx
        )
        self._p1p2_debug = (
            bool(config_entry.options[CONF_P1P2_DEBUG])
            if CONF_P1P2_DEBUG in config_entry.options
            else False
        )
        _LOGGER.debug("config:")
        _LOGGER.debug(f"port={port}")
        _LOGGER.debug(f"baud={baud}")
        _LOGGER.debug(f"p1p2_debug={self._p1p2_debug}")
        _LOGGER.info(f"gateway_supports_tx={self._gateway_supports_tx}")
        _LOGGER.info(f"poll_energy_stats={self._poll_energy_stats}")

        super().__init__(
            hass,
            logger=_LOGGER,
            config_entry=config_entry,
            name=f"{port}:{baud}",
            update_interval=None,  # Disable update interval as server pushes
        )
        self._proto = P1P2Protocol(port, baud, debug=self._p1p2_debug)
        self.device_info = DeviceInfo(
            name=DEFAULT_DEVICE_NAME,
            manufacturer=MANUFACTURER,
            identifiers={(DOMAIN, DEFAULT_DEVICE_NAME, config_entry.unique_id)},
        )
        self.last_update_success = False
        if self._gateway_supports_tx and self._poll_energy_stats:
            self._send_b8_packet_tti = None
            self._compressor_running = False

            # Get statistics once a day unconditionally...
            async_track_time_interval(
                hass,
                self._send_b8_packet,
                timedelta(days=1),
                cancel_on_shutdown=True,
            )

        _LOGGER.debug("Initialized Daikin P1/P2 coordinator on %s@%d baud", port, baud)

    def _send_b8_packet_cancel(self, now: datetime | None = None) -> None:
        """Send b8h packet when compressor is/was used."""
        # Stop interval when not running any more
        if not self._compressor_running and self._send_b8_packet_tti is not None:
            self._send_b8_packet_tti()
            self._send_b8_packet_tti = None

        self._send_b8_packet(now)

    @callback
    def _send_b8_packet(self, now: datetime | None = None) -> None:
        """Send b8h packet to pull energy statistics."""
        if not self._poll_energy_stats:
            return
        _LOGGER.info("Requesting energy statistics...\n")
        # Request update energy statistics by sending b8h packet.
        # When compressor is on, it draws minimum 700Watt.
        # Checking once an hour should be fine...
        self._proto.transmit(False, 0x00, 0xB8, b"\x00")
        self._proto.transmit(False, 0x00, 0xB8, b"\x05")

    def allow_writes(self) -> bool:
        return self._gateway_supports_tx

    def polls_energy_statistics(self) -> bool:
        return self._poll_energy_stats

    @callback
    def _on_compressor_running_event(self, key: str, new_value) -> None:
        """Update compressor state"""

        if new_value is None or self._compressor_running == bool(new_value):
            return
        self._compressor_running = bool(new_value)
        if self._compressor_running and self._send_b8_packet_tti is None:
            # Poll for enery statistics
            # Check every 5 minutes as long as compressor is running
            # to make sure energy estimation is exact.
            self._send_b8_packet_tti = async_track_time_interval(
                self.hass,
                self._send_b8_packet_cancel,
                timedelta(minutes=5),
                cancel_on_shutdown=True,
            )
        if not self._compressor_running and self._send_b8_packet_tti:
            self._send_b8_packet_cancel()

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

        if self._poll_energy_stats:
            self._proto.add_settings_change_listener(
                "compressor_running", self._on_compressor_running_event
            )

            # Get statistics now, but wait a bit until all sensors are created
            self.hass.loop.call_later(30, self._send_b8_packet, None)

    async def _async_update_data(self) -> None:
        """Empty update method since data is pushed."""
