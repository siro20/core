from abc import abstractmethod
from collections.abc import Callable
import logging
from typing import Any

from homeassistant.core import callback

from .p1p2_base import P1P2Base, P1P2Packet

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class P1P2ParameterProtocol(P1P2Base):
    """Low level functions of the P1P2 decoder."""

    def __init__(self, url, baud=112500, **kwargs) -> None:
        P1P2Base.__init__(self, url, baud, **kwargs)
        self._parameter: dict[int, dict[int, int]] = {}
        self._model_listeners: list[Callable[[str], None]] = []
        self._model: str = ""

    @callback
    @abstractmethod
    def on_setting_changed(self, key: str, value: Any) -> None:
        """Callback when a setting changed"""

    @callback
    @abstractmethod
    def on_regular_packet_received(self, pkt: P1P2Packet) -> None:
        """Callback when a regular packet was received"""

    @callback
    def on_packet_received(self, pkt: P1P2Packet) -> None:
        """Callback for each known packet received over serial."""

        if pkt.type() >= 0x32 and pkt.type() < 0x40:
            # Let upper layer handle parameter packets
            self.on_parameter_packet_received(pkt)
        else:
            self.on_regular_packet_received(pkt)

    def on_parameter_packet_received(self, pkt: P1P2Packet) -> None:
        """Cache parameters as only 6 at maximum are exchanged per packet."""
        assert pkt.type() >= 0x32 and pkt.type() < 0x40
        if pkt.type() not in self._parameter:
            self._parameter[pkt.type()] = {}

        for i in ("0", "1", "2", "3", "4", "5"):
            value = f"value{i}"
            offset = f"offset{i}"
            if value not in pkt.payload():
                continue
            if offset not in pkt.payload():
                continue

            off = int(pkt.payload()[offset])
            if off == 0xFFFF:
                continue

            val = int(pkt.payload()[value])
            key = f"parameter{hex(pkt.type())}_{off}"

            if off not in self._parameter[pkt.type()]:
                self._parameter[pkt.type()][off] = val
                self.on_setting_changed(key, val)

                _LOGGER.info(f"{key} = {val}")

            if (
                self._parameter[pkt.type()][off] != val
                and off != 375
                and off != 376
                and off != 377
            ):
                self._parameter[pkt.type()][off] = val
                self.on_setting_changed(key, val)

                _LOGGER.info(f"{key} = {val}")

        # Model name is stored somewhere in parameter35
        if pkt.type() == 0x35 and self._model == "" and self.model() != "":
            self._model = self.model()
            for model_listener in self._model_listeners:
                model_listener(self._model)

    def _model_162(self) -> str:
        """Returns the name at offset 0x162 (if any)"""
        name = ""
        for i in range(0x162, 0x16C):
            if i not in self._parameter[0x35]:
                return ""
            name += chr(self._parameter[0x35][i])
        if name.startswith("EJHA"):
            return name
        return ""

    def _model_13a(self) -> str:
        """Returns the name at offset 0x13a (if any)"""
        name = ""
        for i in range(0x13A, 0x145):
            if i not in self._parameter[0x35]:
                return ""
            name += chr(self._parameter[0x35][i])
        # FIXME: EHVX as well?
        if name.startswith("EHYB"):
            return name
        return ""

    def model(self) -> str:
        """Return the name when enough parameter 35h packets have been received."""
        if self._model_162() != "":
            return self._model_162()
        return self._model_13a()

    def set_parameter(self, parameter: int, offset: int, value: int) -> None:
        """Send a parameter to the serial gateway."""
        packet = b""
        if parameter <= 0x30 or parameter >= 0x3F:
            raise AttributeError(f"parameter {parameter} out of range")
        if offset < 0 or offset > 0xFFFF:
            raise AttributeError(f"offset {offset} out of range")
        if value < 0:
            raise AttributeError(f"value {value} out of range")

        packet += parameter.to_bytes(1)
        packet += offset.to_bytes(2, byteorder="little")

        if parameter in (0x35, 0x3A):
            if value > 0xFF:
                raise AttributeError(f"value {value} out of range")
            packet += value.to_bytes(1)
            packet += b"\xff" * 15
        elif parameter in (0x36, 0x3B):
            if value > 0xFFFF:
                raise AttributeError(f"value {value} out of range")
            packet += value.to_bytes(2, byteorder="little")
            packet += b"\xff" * 16
        elif parameter in (0x37, 0x3C):
            if value > 0xFFFFFF:
                raise AttributeError(f"value {value} out of range")
            packet += value.to_bytes(3, byteorder="little")
            packet += b"\xff" * 15
        elif parameter in (0x38, 0x39, 0x3D):
            if value > 0xFFFFFFFF:
                raise AttributeError(f"value {value} out of range")
            packet += value.to_bytes(4, byteorder="little")
            packet += b"\xff" * 12
        else:
            raise AttributeError(f"parameter {parameter} not supported")

        packet = P1P2Base.encode(True, 0xF0, parameter, packet)
        line = f"{packet.hex()}\r\n"
        self.write(line.encode())

        if parameter not in self._parameter:
            self._parameter[parameter] = {}

        self._parameter[parameter][offset] = value

    def add_model_listener(self, listener: Callable[[str], None]) -> None:
        """Register a callback handler providing the model name."""
        self._model_listeners.append(listener)
        if self._model != "":
            listener(self._model)

    def remove_model_listener(self, listener: Callable[[str], None]) -> None:
        """Unregister a previously registered model callback handler."""
        self._model_listeners.remove(listener)
