from collections import OrderedDict
from collections.abc import Callable
import logging
from typing import Any

from construct import (
    BitsInteger,
    Bitwise,
    Const,
    Container,
    Int8ub,
    Int16ub,
    Int16ul,
    Padding,
    Struct,
    Subconstruct,
)

from .serial import P1P2SerialProtocol

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class Adapter(Subconstruct):
    """Helper class for custom Adapters."""

    def _parse(self, stream, context, path):
        return self._decode(self.subcon._parse(stream, context, path), context, path)

    def _build(self, obj, stream, context, path):
        return self.subcon._build(
            self._encode(obj, context, path), stream, context, path
        )


class F8P8(Adapter):
    """Decodes the f8.p8 format used on the P1/P2 bus."""

    def __init__(self) -> None:
        """Call parent constructor."""
        super().__init__(Int16ub)

    def _decode(self, obj, context, path):
        return float(obj) / 256.0

    def _encode(self, obj, context, path):
        return Int16ub(obj * 256.0)


class SABS4(Adapter):
    """Decodes the signed 4bit format used on the P1/P2 bus."""

    def __init__(self) -> None:
        """Call parent constructor."""
        super().__init__(Int8ub)

    def _decode(self, obj, context, path):
        return int(obj & 0xF) - int(obj & 0x10)

    def _encode(self, obj, context, path):
        if obj < 0:
            return Int8ub(obj & 0xF) | 0x10
        return Int8ub(obj & 0xF)


class P1P2Paket:
    """Represents received and decoded P1/P2 messages."""

    def __init__(self, h: dict, p: dict) -> None:
        """Create a P1/P2 packet."""
        self._h = h
        self._p = p

    def header(self) -> dict:
        """Return the header of the P1/P2 packet."""
        return self._h

    def payload(self) -> dict:
        """Return the payload of the P1/P2 packet."""
        return self._p

    def type(self) -> int:
        """Return the type of the P1/P2 packet."""
        return self._h["type"]

    def request(self) -> bool:
        """True for P1/P2 request packets."""
        return self._h["request_response"] & 0x40 > 0

    def __str__(self):
        """Pretty print the P1/P2 packet."""
        return "P1P2Paket: " + str(self._h) + " " + str(self._p)


class P1P2Base:
    """Decodes known P1/P2 packets and checks integrity."""

    def __init__(self) -> None:
        self._PACKETS: OrderedDict[int, Struct] = OrderedDict(
            [
                # Periodically and unconditionally exchanged on the bus
                # 'target_address' is always 0.
                # Can only be monitored.
                # NOTE: Bitwise start from MSB
                (
                    0x1000,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x10, Int8ub),
                        ),
                        "heating" / Int8ub,
                        "operation_mode"
                        / Bitwise(
                            Struct(
                                # FIXME: gas boiler is 0 even when being used
                                "gas_boiler_enabled" / BitsInteger(1),
                                Padding(7),
                            )
                        ),
                        "dhw_tank"
                        / Bitwise(
                            Struct(
                                Padding(7),
                                # Monitor DHW tank and heat if permitted/scheduled
                                "dhw_tank_enabled" / BitsInteger(1),
                            )
                        ),
                        "reserved" / Padding(4),
                        "target_room_temperature" / Int8ub,
                        "reserved1" / Padding(1),
                        "operation_flags" / Int8ub,
                        "quiet_mode_request" / Int8ub,
                        "dhw_circulation"
                        / Bitwise(
                            Struct(
                                Padding(2),
                                # FIXME: Not working. UI says enabled, but pump isn't running...
                                "dhw_circulation_running" / BitsInteger(1),
                                Padding(5),
                            )
                        ),
                        "reserved2" / Padding(5),
                        "dhw_tank_mode"
                        / Bitwise(
                            Struct(
                                Padding(6),
                                "dhw_booster_enabled" / BitsInteger(1),
                                Padding(1),
                            )
                        ),
                        "dhw_tank_target_temperature_request" / F8P8(),
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                (
                    0x1040,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0x40, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x10, Int8ub),
                        ),
                        "heating_status"
                        / Bitwise(
                            Struct(
                                Padding(6),
                                # System is permitted to cool based on temperature/schedule
                                "cooling_enabled" / BitsInteger(1),
                                # System is permitted to heat based on temperature/schedule
                                "heating_enabled" / BitsInteger(1),
                            )
                        ),
                        "reserved" / Int8ub,
                        "zone_config"
                        / Bitwise(
                            Struct(
                                # Monitor DHW zone and heat if permitted/scheduled
                                "dhw_zone_enabled" / BitsInteger(1),
                                "additional_zone_enabled" / BitsInteger(1),
                                "main_zone_enabled" / BitsInteger(1),
                                Padding(3),
                                "cooling_zone_enabled" / BitsInteger(1),
                                "heating_zone_enabled" / BitsInteger(1),
                            )
                        ),
                        "three_way_valve" / Int8ub,
                        "dhw_tank_target_temperature" / F8P8(),
                        "reserved1" / Padding(5),
                        "quiet_mode"
                        / Bitwise(
                            Struct(
                                Padding(6),
                                "quiet_mode_enabled" / BitsInteger(1),
                                Padding(1),
                            )
                        ),
                        "reserved2" / Padding(6),
                        "pump_and_compressor_status"
                        / Bitwise(
                            Struct(
                                Padding(4),
                                "main_pump_running" / BitsInteger(1),
                                Padding(2),
                                "compressor_running" / BitsInteger(1),
                            )
                        ),
                        "dhw_active"
                        / Bitwise(
                            Struct(
                                Padding(1),
                                # 1 when DHW is heated by gas boiler
                                "dhw_boiler_running" / BitsInteger(1),
                                Padding(6),
                            )
                        ),
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                (
                    0x1100,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x11, Int8ub),
                        ),
                        "actual_room_temperature_request" / F8P8(),
                        "reserved" / Padding(6),
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                (
                    0x1140,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0x40, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x11, Int8ub),
                        ),
                        "lwt_temperature" / F8P8(),
                        "dhw_temperature" / F8P8(),
                        "outside_temperature" / F8P8(),
                        "return_water_temperature" / F8P8(),
                        "gas_boiler_temperature" / F8P8(),
                        "refrigerant_temperature" / F8P8(),
                        "actual_room_temperature" / F8P8(),
                        "external_sensor_temperature" / F8P8(),
                        "reserved" / Padding(4),
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                (
                    0x1200,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x12, Int8ub),
                        ),
                        "new_hour_indicator" / Int8ub,
                        "day_of_week" / Int8ub,
                        "time_hours" / Int8ub,
                        "time_minutes" / Int8ub,
                        "date_year" / Int8ub,
                        "date_month" / Int8ub,
                        "date_day_of_month" / Int8ub,
                        "reserved" / Padding(5),
                        "date_flags" / Int8ub,
                        "date_flags2" / Int8ub,
                        "reserved2" / Padding(1),
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                (
                    0x1340,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0x40, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x13, Int8ub),
                        ),
                        "dhw_setpoint_temperature" / F8P8(),
                        "pump_flags" / Int16ub,
                        "reserved" / Padding(2),
                        "pump_flags2" / Int8ub,
                        "reserved2" / Padding(1),
                        "flow_deci_liter_per_min" / Int16ub,
                        "control_software_version" / Int16ub,
                        "heat_pump_software_version" / Int16ub,
                        "reserved3" / Padding(2),
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                (
                    0x1400,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x14, Int8ub),
                        ),
                        "reserved" / Padding(8),
                        "delta_t" / SABS4(),
                        "eco_mode" / Int8ub,
                        "reserved2" / Padding(5),
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                (
                    0x1440,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0x40, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x14, Int8ub),
                        ),
                        "reserved" / Padding(15),  # Echo of 0x1400
                        "main_zone_target_temperature" / F8P8(),
                        "add_zone_target_temperature" / F8P8(),
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                (
                    0x1600,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0x00, Int8ub),
                            "target_address" / Const(0, Int8ub),
                            "type" / Const(0x16, Int8ub),
                        ),
                        "uptime_minutes" / Int16ub,
                        "reserved" / Padding(14),  # Read as 0 on EJHA
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
                # The following are only send when a 'gateway' is on the bus.
                # The 'gateway' must answer type 0x30 packets on address 0xf0, 0xf1, ...
                # with a bitmask set for additional type 0x3x packets to be send.
                #
                # Capture parameter type 35h packets as they allow external control
                # of the system and it stores the ASCII model name.
                # Unused slot: offset == 0xffff
                #
                # When the P1/P2 serial adapter is *the* gateway, it can answer
                # type 3xh packets and home assistant can change system settings.
                #
                # WARNING: type 3xh parameters are system specific! Changing parameters
                #          might permanently brick your system! Use with care!
                (
                    0x3500,
                    Struct(
                        "header"
                        / Struct(
                            "request_response" / Const(0x00, Int8ub),
                            "target_address" / Int8ub,
                            "type" / Const(0x35, Int8ub),
                        ),
                        "offset0" / Int16ul,
                        "value0" / Int8ub,
                        "offset1" / Int16ul,
                        "value1" / Int8ub,
                        "offset2" / Int16ul,
                        "value2" / Int8ub,
                        "offset3" / Int16ul,
                        "value3" / Int8ub,
                        "offset4" / Int16ul,
                        "value4" / Int8ub,
                        "offset5" / Int16ul,
                        "value5" / Int8ub,
                        "trailer" / Struct("crc" / Int8ub),
                    ),
                ),
            ]
        )

    @staticmethod
    def _calculate_crc(byte_array: bytes) -> int:
        crc = 0

        for b in byte_array:
            current_byte = b
            for _ in range(8):
                if (crc ^ current_byte) & 0x01 > 0:
                    crc = (crc >> 1) ^ 0xD9
                else:
                    crc = crc >> 1
                current_byte >>= 1
        return crc & 0xFF

    @staticmethod
    def parse(s: Struct, data: bytes):
        """Parse the bytes by using construct.Struct."""
        if len(data) <= 3:
            raise ValueError("Packet too small")

        container = s.parse(data)
        if container is None:
            return None

        expected = P1P2Base._calculate_crc(data[:-1])
        if container.trailer.crc != expected:
            raise ValueError(
                f"CRC mismatch {container.trailer.crc}, expected {expected}"
            )
        payload = {}
        header = {}
        for i in container:
            if i in ("header", "trailer"):
                continue
            if isinstance(container[i], (int, float)) and not isinstance(
                container[i], bool
            ):
                payload[i] = container[i]
            if isinstance(container[i], Container):
                for j in container[i]:
                    if isinstance(container[i][j], (int, float)) and not isinstance(
                        container[i][j], bool
                    ):
                        payload[j] = container[i][j]
        for i in container.header:
            if isinstance(container.header[i], (int, float)) and not isinstance(
                container.header[i], bool
            ):
                header[i] = container.header[i]

        return P1P2Paket(header, payload)

    def decode(self, buf: bytes):
        """Decode the bytes object into a P1P2Paket when it's supported."""
        if len(buf) <= 3:
            return None
        addr = int(buf[0]) | (int(buf[2]) << 8)
        if addr in self._PACKETS:
            try:
                return P1P2Base.parse(self._PACKETS[addr], buf)
            except Exception as ex:
                _LOGGER.warning(f"Exception {ex} when processing {buf.hex()}")
                return None
        else:
            _LOGGER.debug("Ignoring packet %x", addr)
        return None

    def encode(self, answer: bool, address: int, type: int, payload: bytes) -> bytes:
        """Encode a paket and calculate the CRC."""
        buf = b""
        buf += b"\x40" if answer else b"\x00"
        buf += address.to_bytes(1)
        buf += type.to_bytes(1)
        buf += payload

        crc = P1P2Base._calculate_crc(buf)
        buf += crc


class P1P2Protocol(P1P2SerialProtocol, P1P2Base):
    """High level functions of the P1P2 decoder."""

    def __init__(self, url, baud=112500, **kwargs) -> None:
        P1P2SerialProtocol.__init__(self, url, baud, **kwargs)
        P1P2Base.__init__(self)
        self._packet_listeners: list[Callable[[P1P2Paket], None]] = []
        self._setting_listeners: dict[str,
                                      list[Callable[[str, Any], None]]] = {}
        self._connection_listeners: list[Callable[[bool], None]] = []
        self._model_listeners: list[Callable[[str], None]] = []
        self._parameter35: dict[int, int] = {}
        self._model = ""

    def on_serial_line_received(self, line: str) -> None:
        """Callback when a line was received over serial"""
        # _LOGGER.warning(line)
        # Parse ASCII hex data
        data = b""
        try:
            data = bytes.fromhex(line)
        except Exception:
            return

        # if data[2] == 0x35:
        #    d = datetime.datetime.now()
        #    if self._last_update != d.minute:
        #        self._last_update = d.minute
        #        offset = 0xffff
        #        value = 0xff
        #        self.write(b"\x40\xf0\x35" + offset.to_bytes(2,
        #                                                     byteorder='little') + value.to_bytes(1) + b"\xff\xff\xff" + b"\xff\xff\xff" + b"\xff\xff\xff" + b"\xff\xff\xff" + b"\xff\xff\xff" + b"x\00")

        # Decode the packet
        res = self.decode(data)
        if res:
            self._dispatch(res)

    def on_connection_lost(self, exc: Exception | None) -> None:
        """Callback when connection was lost"""
        for con_listener in self._connection_listeners:
            con_listener(False)

    def on_connection_established(self) -> None:
        """Callback when connection was established"""
        for con_listener in self._connection_listeners:
            con_listener(True)

    def _handle_parameter35(self, pkt: P1P2Paket) -> None:
        """Cache parameters as only 6 at maximum are exchanged per packet."""
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

            if off not in self._parameter35:
                self._parameter35[off] = val

            if self._parameter35[off] != val:
                _LOGGER.info(f"parameter35 {off} = {val}")

        # Model name is stored somewhere in parameter35
        if self._model == "" and self.model() != "":
            self._model = self.model()
            for model_listener in self._model_listeners:
                model_listener(self._model)

    def _model_162(self) -> str:
        """Returns the name at offset 0x162 (if any)"""
        name = ""
        for i in range(0x162, 0x16C):
            if i not in self._parameter35:
                return ""
            name += chr(self._parameter35[i])
        if name.startswith("EJHA"):
            return name
        return ""

    def _model_13a(self) -> str:
        """Returns the name at offset 0x13a (if any)"""
        name = ""
        for i in range(0x13A, 0x145):
            if i not in self._parameter35:
                return ""
            name += chr(self._parameter35[i])
        # FIXME: EHVX as well?
        if name.startswith("EHYB"):
            return name
        return ""

    def model(self) -> str:
        """Return the name when enough parameter 35h packets have been received."""
        if self._model_162() != "":
            return self._model_162()
        return self._model_13a()

    def _dispatch(self, pkt: P1P2Paket) -> None:
        if pkt.type() == 0x35:
            self._handle_parameter35(pkt)
        # _LOGGER.warning(pkt)
        for key in pkt.payload():
            value = pkt.payload()[key]
            if key not in self._setting_listeners:
                continue

            for listener in self._setting_listeners[key]:
                listener(key, value)
        for pkt_listener in self._packet_listeners:
            pkt_listener(pkt)

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

    def add_packet_listener(self, listener: Callable[[P1P2Paket], None]) -> None:
        """Register a callback handler that is invoked when a packet is received."""
        self._packet_listeners.append(listener)

    def remove_packet_listener(self, listener: Callable[[P1P2Paket], None]) -> None:
        """Unregister a previously registered packet callback handler."""
        self._packet_listeners.remove(listener)

    def add_connection_listener(self, listener: Callable[[bool], None]) -> None:
        """Register a callback handler that is invoked when connection changes."""
        self._connection_listeners.append(listener)
        listener(self.connected())

    def remove_connection_listener(self, listener: Callable[[bool], None]) -> None:
        """Unregister a previously registered connection callback handler."""
        self._connection_listeners.remove(listener)

    def add_model_listener(self, listener: Callable[[str], None]) -> None:
        """Register a callback handler providing the model name."""
        self._model_listeners.append(listener)
        if self._model != "":
            listener(self._model)

    def remove_model_listener(self, listener: Callable[[str], None]) -> None:
        """Unregister a previously registered model callback handler."""
        self._model_listeners.remove(listener)
