from abc import abstractmethod
import asyncio
from collections.abc import Callable
import logging
import time
from typing import Any
from urllib.parse import urlparse

from serial import SerialException
from serial_asyncio_fast import create_serial_connection

from homeassistant.core import callback

_LOGGER = logging.getLogger(__name__)
_LOGGER.addHandler(logging.NullHandler())


class P1P2SerialProtocol(asyncio.Protocol):
    """Wrapper to asynchronously receive ASCII hex lines over the serial."""

    def __init__(self, url, baud, wait_time=120) -> None:
        asyncio.Protocol.__init__(self)
        self._url = urlparse(url)
        self._transport = None
        self._loop = None
        self._running = False
        self._buf = b""
        self._lock: asyncio.Lock = asyncio.Lock()
        self._last_update = 0.0
        self._timeout_delay = wait_time
        self._watchdog: asyncio.Task[Any] = None
        self._baud = baud
        self._connection_listeners: list[Callable[[bool], None]] = []

    async def _resume_reading(self, delay):
        await asyncio.sleep(delay)
        self._transport.resume_reading()

    def _delay_reading(self, delay):
        self._transport.pause_reading()
        asyncio.ensure_future(self._resume_reading(delay), loop=self._loop)

    @callback
    @abstractmethod
    def on_serial_line_received(self, line: str) -> None:
        """Callback for each line received over serial."""

    def add_connection_listener(self, listener: Callable[[bool], None]) -> None:
        """Register a callback handler that is invoked when connection changes."""
        self._connection_listeners.append(listener)
        listener(self.connected())

    def remove_connection_listener(self, listener: Callable[[bool], None]) -> None:
        """Unregister a previously registered connection callback handler."""
        self._connection_listeners.remove(listener)

    def data_received(self, data: bytes):
        """Call when data has been received over the serial port."""
        self._buf += data
        # P1/P2 runs at 9600 baud. About 1 byte per msec.
        delay = 0.005
        self._last_update = time.time()
        lines = str(self._buf, "utf-8")

        # Received not a full line yet..
        if "\n" not in lines:
            self._delay_reading(delay)
            return

        # Each line represents a packet
        for line in lines.splitlines(True):
            if "\n" not in line:
                # When a line hasn't fully been received opt out
                continue
            # Pop from bytes buffer
            self._buf = self._buf[len(line) :]

            # Get rid of newlines
            line = line.replace("\r", "").replace("\n", "")

            # Nothing to do for empty lines
            if line == "":
                continue

            self.on_serial_line_received(line)

        # Average delay between two packets is 30msec
        delay = 0.030
        self._delay_reading(delay)

    @callback
    @abstractmethod
    def on_connection_lost(self, exc: Exception | None) -> None:
        """Callback on connection lost."""

    @callback
    @abstractmethod
    def on_connection_established(self) -> None:
        """Callback on connection reestablished."""

    def write(self, data: bytes) -> None:
        """Write to the P1/P2 serial gateway."""
        if not self._running or self._transport is None:
            return
        if self._lock.locked():
            return
        _LOGGER.info(f"sending {data} to serial P1P2 gateway")
        self._transport.write(data)
        self._transport.flush()

    def _connection_lost(self, exc: Exception | None):
        _LOGGER.debug("port closed")
        self.on_connection_lost(exc)
        for con_listener in self._connection_listeners:
            con_listener(False)

        self._transport = None
        if self._running and not self._lock.locked():
            asyncio.ensure_future(self._reconnect(), loop=self._loop)

    async def _create_connection(self):
        kwargs = {
            "url": self._url.geturl(),
            "baudrate": self._baud,
        }
        coro = create_serial_connection(self._loop, lambda: self, **kwargs)
        return await coro

    async def _reconnect(self, delay: int = 60):
        async with self._lock:
            await self._disconnect()
            await asyncio.sleep(delay)
            try:
                async with asyncio.timeout(5):
                    self._transport, _ = await self._create_connection()
            except (
                TimeoutError,
                BrokenPipeError,
                ConnectionRefusedError,
                SerialException,
            ) as exc:
                _LOGGER.warning(exc)
                asyncio.ensure_future(self._reconnect(), loop=self._loop)
            else:
                _LOGGER.info("Connected to %s", self._url.geturl())
                if self._timeout_delay:
                    self._last_update = time.time()
                    self._watchdog = asyncio.create_task(self._timeout())
                self.on_connection_established()
                for con_listener in self._connection_listeners:
                    con_listener(True)

    async def connect(self, loop=None):
        """Connect to the serial device and start decoding received lines."""
        if self._running:
            return

        if not loop:
            loop = asyncio.get_event_loop()

        self._loop = loop
        self._running = True
        await self._reconnect(delay=0)

    def connected(self):
        """Return state if currently connected."""
        return self._running and self._transport is not None

    async def _disconnect(self):
        if self._watchdog and not self._watchdog.done():
            self._watchdog.cancel()
        if self._transport:
            self._transport.abort()
            self._transport = None
        self.on_connection_lost(None)
        for con_listener in self._connection_listeners:
            con_listener(False)

    async def _timeout(self):
        while True:
            last_update = self._last_update
            sleep_time = last_update + self._timeout_delay - time.time()
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                if last_update != self._last_update:
                    continue
            _LOGGER.warning(
                "Timeout while waiting for P1/P2 data. Please check gateway device"
            )
            self._connection_lost(TimeoutError())

            return
