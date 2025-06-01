from collections.abc import Callable
import logging
from typing import Any

from abc import abstractmethod

from homeassistant.core import callback

from .p1p2_base import P1P2Packet
from .p1p2_parameter import P1P2ParameterProtocol

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class P1P2Protocol(P1P2ParameterProtocol):
    """P1P2 protocol"""

    def __init__(self, url, baud=112500, **kwargs) -> None:
        P1P2ParameterProtocol.__init__(self, url, baud, **kwargs)
        self._setting_listeners: dict[str,
                                      list[Callable[[str, Any], None]]] = {}

    @callback
    def on_setting_changed(self, key: str, value: Any) -> None:
        """Callback when a setting changed"""
        if key in self._setting_listeners:
            for listener in self._setting_listeners[key]:
                listener(key, value)

    @callback
    def on_regular_packet_received(self, pkt: P1P2Packet) -> None:
        """Callback when a regular packet was received"""

        for key in pkt.payload():
            value = pkt.payload()[key]
            self.on_setting_changed(key, value)

    def add_settings_change_listener(
        self, property: str, listener: Callable[[str, Any], None]
    ) -> None:
        """Register a callback handler that is invoked when a setting changes."""
        if property not in self._setting_listeners:
            self._setting_listeners[property] = list[Callable[[
                str, Any], None]]()
        self._setting_listeners[property].append(listener)

    def remove_settings_change_listener(
        self, property: str, listener: Callable[[str, Any], None]
    ) -> None:
        """Unregister a previously registered settings callback handler."""
        if property in self._setting_listeners:
            self._setting_listeners[property].remove(listener)
