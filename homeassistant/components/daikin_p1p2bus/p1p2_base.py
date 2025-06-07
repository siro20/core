from abc import abstractmethod
from collections.abc import Callable
import logging

from construct import (
    BitsInteger,
    Bitwise,
    Const,
    Container,
    Int8ub,
    Int16ub,
    Int16ul,
    Int24ub,
    Int32ul,
    Padding,
    Select,
    SelectError,
    Struct,
    Subconstruct,
)

from homeassistant.core import callback

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


class P1P2Packet:
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
        """Return true for P1/P2 request packets."""
        return self._h["request_response"] & 0x40 > 0

    def __str__(self):
        """Pretty print the P1/P2 packet."""
        return "P1P2Packet: " + str(self._h) + " " + str(self._p)


class P1P2Base(P1P2SerialProtocol):
    """Decodes known P1/P2 packets and checks integrity."""

    def __init__(
        self, url, allow_writes=False, baud=112500, debug=False, **kwargs
    ) -> None:
        P1P2SerialProtocol.__init__(self, url, baud, **kwargs)
        self._allow_writes = allow_writes
        self._debug = debug
        self._packet_listeners: list[Callable[[P1P2Packet], None]] = []
        # NOTE: construct Bitwise start from MSB
        self._PACKETS: Select = Select(
            # Periodically and unconditionally exchanged on the bus
            # 'target_address' is always 0.
            # Can only be monitored.
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
                        Padding(6),
                        # 1 when DHW is heated by gas boiler
                        "dhw_boiler_running" / BitsInteger(1),
                        Padding(1),
                    )
                ),
                "trailer" / Struct("crc" / Int8ub),
            ),
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
            # Temperatures
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
            # Time indicator. Used for schedules.
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
                "flow_deci_liter_per_min" / Int16ub,  # Read as 0 on EJHA
                "control_software_version" / Int16ub,
                "heat_pump_software_version" / Int16ub,
                "reserved3" / Padding(2),
                "trailer" / Struct("crc" / Int8ub),
            ),
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
            # Status/control parameters. Allows to enable/disable DHW circulation pump.
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
            # Temperature parameters
            Struct(
                "header"
                / Struct(
                    "request_response" / Const(0x00, Int8ub),
                    "target_address" / Int8ub,
                    "type" / Const(0x36, Int8ub),
                ),
                "offset0" / Int16ul,
                "value0" / Int16ul,
                "offset1" / Int16ul,
                "value1" / Int16ul,
                "offset2" / Int16ul,
                "value2" / Int16ul,
                "offset3" / Int16ul,
                "value3" / Int16ul,
                "offset4" / Int16ul,
                "value4" / Int16ul,
                "trailer" / Struct("crc" / Int8ub),
            ),
            # Energy, working hours and counters
            #
            # Packet type 38h is only updated when touching the control panel and
            # going to the energy usage menu. This will emit b8h type packets first.
            # Manually sending b8h packets will not force update of packet type 38h.
            # Rather useless, but parse it anyways....
            Struct(
                "header"
                / Struct(
                    "request_response" / Const(0x00, Int8ub),
                    "target_address" / Int8ub,
                    "type" / Const(0x38, Int8ub),
                ),
                "offset0" / Int16ul,
                "value0" / Int32ul,
                "offset1" / Int16ul,
                "value1" / Int32ul,
                "offset2" / Int16ul,
                "value2" / Int32ul,
                "trailer" / Struct("crc" / Int8ub),
            ),
            # Energy consumption
            # Must be actively requested by sending b8h packet.
            Struct(
                "header"
                / Struct(
                    "request_response" / Const(0x40, Int8ub),
                    "target_address" / Int8ub,
                    "type" / Const(0xB8, Int8ub),
                ),
                "data_type" / Const(0, Int8ub),
                "backup_heater_for_heating" / Int24ub,
                "backup_heater_for_dhw" / Int24ub,
                "compressor_for_heating" / Int24ub,
                "compressor_for_cooling" / Int24ub,
                "compressor_for_dhw" / Int24ub,
                "total_energy_used" / Int24ub,
                "trailer" / Struct("crc" / Int8ub),
            ),
            # Gas consumption
            # Must be actively requested by sending b8h packet.
            Struct(
                "header"
                / Struct(
                    "request_response" / Const(0x40, Int8ub),
                    "target_address" / Int8ub,
                    "type" / Const(0xB8, Int8ub),
                ),
                "data_type" / Const(5, Int8ub),
                "gas_boiler_operation_hours_heating" / Int24ub,
                "gas_boiler_operation_hours_dhw" / Int24ub,
                "gas_usage_heating" / Int24ub,
                "gas_usage_heating2" / Int24ub,
                "number_of_boiler_start" / Int24ub,
                "gas_usage_total" / Int24ub,
                "trailer" / Struct("crc" / Int8ub),
            ),
        ).compile()

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
    def parse(s: Struct, data: bytes) -> P1P2Packet | None:
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

        return P1P2Packet(header, payload)

    @staticmethod
    def encode(answer: bool, address: int, type: int, payload: bytes) -> bytes:
        """Encode a packet and calculate the CRC."""
        buf = b""
        buf += b"\x40" if answer else b"\x00"
        buf += address.to_bytes(1)
        buf += type.to_bytes(1)
        buf += payload

        crc = P1P2Base._calculate_crc(buf)
        buf += crc.to_bytes(1)
        return buf

    @callback
    @abstractmethod
    def on_packet_received(self, pkt: P1P2Packet) -> None:
        """Callback for each known packet received over serial."""

    def transmit(self, answer: bool, address: int, type: int, payload: bytes) -> None:
        """Transmit a packet to the bus"""
        if not self._allow_writes:
            raise Exception("Write operation not allowed")

        packet = P1P2Base.encode(answer, address, type, payload)
        line = f"{packet.hex()}\r\n"
        self.write(line.encode())
        if self._debug:
            _LOGGER.debug(f"sending {line}")

    def set_allow_writes(self, val: bool) -> None:
        """Allow to transmit to the gateway"""
        self._allow_writes = val

    def decode(self, buf: bytes) -> P1P2Packet | None:
        """Decode the bytes object into a P1P2Packet when it's supported."""
        # Every packet has at least 3 bytes
        if len(buf) <= 3:
            return None

        try:
            # Should only fail on CRC error.
            return P1P2Base.parse(self._PACKETS, buf)
        except SelectError:
            pass
        except Exception as ex:
            _LOGGER.warning(
                f"Exception {type(ex).__name__} when processing {buf.hex()}"
            )
        return None

    def add_packet_listener(self, listener: Callable[[P1P2Packet], None]) -> None:
        """Register a callback handler that is invoked when a packet is received."""
        self._packet_listeners.append(listener)

    def remove_packet_listener(self, listener: Callable[[P1P2Packet], None]) -> None:
        """Unregister a previously registered packet callback handler."""
        self._packet_listeners.remove(listener)

    @callback
    def on_serial_line_received(self, line: str) -> None:
        """Callback when a line was received over serial"""

        if self._debug:
            _LOGGER.debug(f"P1P2: {line}")

        # Drop comments
        if ";" in line:
            line = line.split(";")[0]
        if "#" in line:
            line = line.split("#")[0]

        # Parse ASCII hex data
        data = b""
        try:
            data = bytes.fromhex(line)
        except Exception:
            return

        # Decode the packet
        res = self.decode(data)
        if res:
            self.on_packet_received(res)
            # Invoke packet listeners
            for pkt_listener in self._packet_listeners:
                pkt_listener(res)
