"""Daikin energy estimator"""

from __future__ import annotations

from abc import abstractmethod
import datetime
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import CALLBACK_TYPE, callback
from homeassistant.helpers import entity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.util.dt import utcnow

from .const import DOMAIN, MANUFACTURER
from .coordinator import DaikinP1P2UpdateCoordinator

_LOGGER = logging.getLogger(__name__)


class DaikinDHWAndCompressorOntimeEntity:
    """Counts compressor on-time in seconds when DHW is (not) running."""

    def __init__(
        self,
        invert: bool,
        coordinator: DaikinP1P2UpdateCoordinator,
    ) -> None:
        """Initialize the entity."""
        self._proto = coordinator.proto()
        self._invert = invert

        # How long is compressor running without energy counter incrementing
        self._compressor_on_time: int = 0  # seconds

        # True when compressor is on
        self._compressor_status: bool = None

        # True when DHW is on
        self._dhw_status: bool = None

        # When did the combined status turn on/off?
        self._last_combined_status_change: datetime = None  # Datetime

        self._combined_status: bool = None

    @callback
    @abstractmethod
    def _on_status_change_event(self, compressor_is_on: bool) -> None:
        """Implement in derived class."""

    def get_compressor_ontime(self) -> int:
        """Return the time in seconds the compressor was on."""
        if self._combined_status is None:
            return 0
        isOn = False
        if not self._invert:
            isOn = self._dhw_status and self._compressor_status
        else:
            isOn = not self._dhw_status and self._compressor_status
        if isOn:
            self._compressor_on_time += (
                utcnow() - self._last_combined_status_change
            ).total_seconds()
            self._last_combined_status_change = utcnow()
        return self._compressor_on_time

    def get_compressor_ontime_and_reset(self) -> int:
        """Return the time in seconds the compressor was on and reset the counter."""
        ontime = self.get_compressor_ontime()
        self._compressor_on_time = 0
        return ontime

    @callback
    def _on_change_event(self) -> bool:
        if self._compressor_status is None or self._dhw_status is None:
            return
        isOn = False
        if not self._invert:
            isOn = self._dhw_status and self._compressor_status
        else:
            isOn = not self._dhw_status and self._compressor_status
        if self._combined_status is None:
            self._last_combined_status_change = utcnow()
            self._combined_status = isOn
            self._on_status_change_event(isOn)
            return

        if self._combined_status != isOn:
            if not isOn:
                self._compressor_on_time += (
                    utcnow() - self._last_combined_status_change
                ).total_seconds()
            self._last_combined_status_change = utcnow()
            self._combined_status = isOn
            self._on_status_change_event(isOn)

    @callback
    def _on_dhw_zone_enabled_change_event(self, key: str, dhw_zone_is_on: bool) -> bool:
        if self._dhw_status is None or (dhw_zone_is_on != self._dhw_status):
            self._dhw_status = dhw_zone_is_on
            _LOGGER.warning(f"DHW status is {self._dhw_status}")
            self._on_change_event()

    @callback
    def _on_operation_change_event(self, key: str, compressor_is_on: bool) -> bool:
        if self._compressor_status is None or (
            compressor_is_on != self._compressor_status
        ):
            self._compressor_status = compressor_is_on
            _LOGGER.warning(f"Compressor status is {self._compressor_status}")
            self._on_change_event()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._proto.add_settings_change_listener(
            "compressor_running", self._on_operation_change_event
        )
        self._proto.add_settings_change_listener(
            "dhw_zone_enabled", self._on_dhw_zone_enabled_change_event
        )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self._proto.remove_settings_change_listener(
            "compressor_running", self._on_operation_change_event
        )
        self._proto.remove_settings_change_listener(
            "dhw_zone_enabled", self._on_dhw_zone_enabled_change_event
        )


class DaikinCompressorOntimeEntity:
    """Counts compressor on-time in seconds."""

    def __init__(
        self,
        coordinator: DaikinP1P2UpdateCoordinator,
    ) -> None:
        """Initialize the entity."""
        self._proto = coordinator.proto()

        # How long is compressor running without energy counter incrementing
        self._compressor_on_time: int = 0  # seconds

        # When did the compressor power on? None if off.
        self._last_compressor_status_change: datetime = None  # Datetime

        # True when compressor is on
        self._compressor_status: bool = None

    @callback
    @abstractmethod
    def _on_compressor_change_event(self, compressor_is_on: bool) -> None:
        """Implement in derived class."""

    def get_compressor_ontime(self) -> int:
        """Return the time in seconds the compressor was on."""
        if self._compressor_status is None:
            return 0
        if self._compressor_status:
            self._compressor_on_time += (
                utcnow() - self._last_compressor_status_change
            ).total_seconds()
            self._last_compressor_status_change = utcnow()
        return self._compressor_on_time

    def get_compressor_ontime_and_reset(self) -> int:
        """Return the time in seconds the compressor was on and reset the counter."""
        ontime = self.get_compressor_ontime()
        self._compressor_on_time = 0
        return ontime

    def _on_operation_change_event(self, key: str, compressor_is_on: bool) -> bool:
        """Called every time a status paket is received."""
        if self._compressor_status is None:
            self._compressor_status = compressor_is_on
            self._last_compressor_status_change = utcnow()

        if not compressor_is_on and self._compressor_status:
            self._compressor_on_time += (
                utcnow() - self._last_compressor_status_change
            ).total_seconds()

        if compressor_is_on != self._compressor_status:
            self._compressor_status = compressor_is_on
            self._last_compressor_status_change = utcnow()

            _LOGGER.warning(f"Compressor status is {self._compressor_status}")
            self._on_compressor_change_event(compressor_is_on)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._proto.add_settings_change_listener(
            "compressor_running", self._on_operation_change_event
        )

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self._proto.remove_settings_change_listener(
            "compressor_running", self._on_operation_change_event
        )


class DaikinWaitForFirstUpdateEntity:
    """Wait's for monotonic setting to increment."""

    def __init__(
        self,
        key,
        coordinator: DaikinP1P2UpdateCoordinator,
    ) -> None:
        """Initialize the entity."""
        self._proto = coordinator.proto()
        self._key = key

        self._energy_counter: int = None

    @callback
    @abstractmethod
    def _on_setting_flip_event(self, key: str, new_value) -> None:
        """Implement in derived class."""

    @callback
    def _on_key_change_event(self, key: str, new_value) -> bool:
        if new_value is None:
            return
        if self._energy_counter is None:
            # Updated on POR
            self._energy_counter = new_value
            return
        if new_value == self._energy_counter:
            return
        self._energy_counter = new_value
        _LOGGER.warning(f"_on_setting_flip_event {self._key}={new_value} kWh")
        self._on_setting_flip_event(key, new_value)

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._proto.add_settings_change_listener(
            self._key, self._on_key_change_event)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self._proto.remove_settings_change_listener(
            self._key, self._on_key_change_event
        )


class DaikinPowerEstimatorEntity(
    DaikinCompressorOntimeEntity, DaikinWaitForFirstUpdateEntity, entity.Entity
):
    """Base representation of a Daikin power estimator."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_available = False

    def __init__(
        self,
        entity_description,
        coordinator: DaikinP1P2UpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""
        DaikinWaitForFirstUpdateEntity.__init__(
            self, "total_energy_used", coordinator)
        DaikinCompressorOntimeEntity.__init__(self, coordinator)

        self.entity_description = entity_description
        self._proto = coordinator.proto()
        self._hysteresis = entity_description.hysteresis

        self._last_total_energy_used: int = None  # KWh

        self._estimate_power: float = None  # W

        device_name = "ControlUnit"

        self._attr_device_info = DeviceInfo(
            name=device_name,
            manufacturer=MANUFACTURER,
            identifiers={(DOMAIN, device_name, config_entry.unique_id)},
        )

        self._last_update = utcnow()
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_name}_{entity_description.key}"
        self._hidden = False

        if not coordinator.polls_energy_statistics():
            self._hidden = True

        if self._hidden:
            self._attr_entity_registry_enabled_default = False
            self._attr_entity_registry_visible_default = False

    @property
    def device_id(self) -> str:
        """Return device_id."""
        return self.entity_description.key

    def estimated_power(self) -> (float | None):
        return self._estimate_power

    def _on_setting_flip_event(self, key: str, new_value) -> None:
        if key != "total_energy_used":
            return

        # After POR need to wait for _last_total_energy_used to flip the first time
        if self._last_total_energy_used is None:
            self._last_total_energy_used = new_value
            self.get_compressor_ontime_and_reset()
            return
        # Sanity check
        if new_value <= self._last_total_energy_used:
            return

        compressor_on_time = self.get_compressor_ontime_and_reset()

        # Calculate how long (in seconds) it was on for 1kWh
        last_total_ontime = compressor_on_time / (
            new_value - self._last_total_energy_used
        )
        self._last_total_energy_used = new_value

        # Needed _last_total_ontime seconds for 1KWh = 1000 Wh = 1000 * 60 * 60 Ws
        estimate = (1000.0 * 3600.0) / float(last_total_ontime)
        if self._estimate_power is None:
            self._estimate_power = estimate
        else:
            self._estimate_power = self._estimate_power * 0.75 + estimate * 0.25

        _LOGGER.warning(
            "Last ontime %d seconds for 1KWh, %d W",
            last_total_ontime,
            self._estimate_power,
        )

        self._on_event()

    @callback
    @abstractmethod
    def _on_settings_change_event(self, key: str, new_value) -> bool:
        """Implement in derived class."""

    @callback
    def _on_event(self) -> None:
        """Filter events based on last update."""
        updated = False

        if self._estimate_power is None:
            self._attr_available = False
            self.async_write_ha_state()
            return

        updated = self._on_settings_change_event(
            self.entity_description.key, self._estimate_power
        )

        if updated:
            self._attr_available = True
            self._last_update = utcnow()
            self.async_write_ha_state()

    @callback
    def _on_compressor_change_event(self, compressor_is_on: bool) -> None:
        return

    @callback
    def _on_connection(self, connected: bool) -> None:
        """Notify HA about new connection state."""
        if not connected:
            self._estimate_power = None
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await DaikinWaitForFirstUpdateEntity.async_added_to_hass(self)
        await DaikinCompressorOntimeEntity.async_added_to_hass(self)
        self._proto.add_connection_listener(self._on_connection)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await DaikinWaitForFirstUpdateEntity.async_will_remove_from_hass(self)
        await DaikinCompressorOntimeEntity.async_will_remove_from_hass(self)
        self._proto.remove_connection_listener(self._on_connection)

    @property
    def available(self) -> bool:
        """Returns whether entity is available."""
        return (
            not self._hidden
            and self._proto.connected()
            and self._estimate_power is not None
        )


class DaikinEnergyEstimatorDHWEntity(
    DaikinWaitForFirstUpdateEntity, DaikinDHWAndCompressorOntimeEntity, entity.Entity
):
    """Base representation of a Daikin energy estimator."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_available = False

    def __init__(
        self,
        power_estimator: DaikinPowerEstimatorEntity,
        entity_description,
        coordinator: DaikinP1P2UpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""

        if entity_description.key == "compressor_energy_dhw_energy_estimate":
            DaikinDHWAndCompressorOntimeEntity.__init__(
                self, False, coordinator)
            DaikinWaitForFirstUpdateEntity.__init__(
                self, "compressor_for_dhw", coordinator
            )
        elif entity_description.key == "compressor_energy_heating_estimate":
            DaikinDHWAndCompressorOntimeEntity.__init__(
                self, True, coordinator)
            DaikinWaitForFirstUpdateEntity.__init__(
                self, "compressor_for_heating", coordinator
            )
        else:
            raise Exception("Unsupported")

        self.entity_description = entity_description
        self._proto = coordinator.proto()
        self._hysteresis = entity_description.hysteresis
        self._power_estimator = power_estimator

        # KWh
        self._energy_counter_estimate: float = None
        self._energy_counter: int = None

        self._periodic_counter: CALLBACK_TYPE | None = None

        device_name = "ControlUnit"

        self._attr_device_info = DeviceInfo(
            name=device_name,
            manufacturer=MANUFACTURER,
            identifiers={(DOMAIN, device_name, config_entry.unique_id)},
        )

        self._last_update = utcnow()
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_name}_{entity_description.key}"
        self._hidden = False

        if not coordinator.polls_energy_statistics():
            self._hidden = True

        if self._hidden:
            self._attr_entity_registry_enabled_default = False
            self._attr_entity_registry_visible_default = False

    @property
    def device_id(self) -> str:
        """Return device_id."""
        return self.entity_description.key

    @callback
    @abstractmethod
    def _on_settings_change_event(self, key: str, new_value) -> bool:
        """Implement in derived class."""

    @callback
    def _on_status_change_event(self, compressor_is_on: bool) -> None:
        """Called when operation status changes."""
        if compressor_is_on and self._periodic_counter is None:
            self._periodic_counter = async_track_time_interval(
                self.hass, self._async_five_minute_task, timedelta(minutes=5)
            )
        if not compressor_is_on and self._periodic_counter is not None:
            self._periodic_counter()
            self._periodic_counter = None

    @callback
    def _on_event(self) -> None:
        """Filter events based on last update."""

        updated = self._on_settings_change_event(
            self.entity_description.key, self._energy_counter_estimate
        )

        if updated:
            self._attr_available = True
            self._last_update = utcnow()
            self.async_write_ha_state()

    @callback
    def _on_setting_flip_event(self, key: str, new_value) -> None:
        """Called when entity_description.key flips over"""
        self._energy_counter = int(new_value)
        if self._energy_counter_estimate is None:
            self._energy_counter_estimate = float(new_value)
        # Reset ontime counter
        self.get_compressor_ontime_and_reset()

        # Reset estimate when it lacks behind
        self._energy_counter_estimate = max(
            float(self._energy_counter), self._energy_counter_estimate
        )

        self._on_event()

    @callback
    def _on_connection(self, connected: bool) -> None:
        """Notify HA about new connection state."""
        self.async_write_ha_state()

    @callback
    def _async_five_minute_task(self, now: datetime) -> None:
        """Run tasks every 5 minutes."""
        if (
            self._power_estimator is None
            or self._power_estimator.estimated_power() is None
            or self._power_estimator.estimated_power() == 0
        ):
            return
        # Real value must exist
        if self._energy_counter is None:
            return
        # Estimate must exist
        if self._energy_counter_estimate is None:
            return

        ontime = self.get_compressor_ontime()
        if ontime == 0:
            return
        estimated_kwh = (
            float(ontime) * self._power_estimator.estimated_power() /
            float(1000 * 3600)
        )

        # When accumulated to fast wait a bit, even though it's "on"
        if estimated_kwh > 2.1:
            return

        _LOGGER.warning(
            f"New estimate for {self.entity_description.key} estimate after {ontime} seconds ontime is {estimated_kwh} KWh"
        )
        new_estimate = float(self._energy_counter) + estimated_kwh

        # No backwards running counter
        self._energy_counter_estimate = max(
            self._energy_counter_estimate, new_estimate)
        self._on_event()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await DaikinWaitForFirstUpdateEntity.async_added_to_hass(self)
        await DaikinDHWAndCompressorOntimeEntity.async_added_to_hass(self)
        self._proto.add_connection_listener(self._on_connection)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await DaikinWaitForFirstUpdateEntity.async_will_remove_from_hass(self)
        await DaikinDHWAndCompressorOntimeEntity.async_will_remove_from_hass(self)

        self._proto.remove_connection_listener(self._on_connection)
        if self._periodic_counter is not None:
            self._periodic_counter()
            self._periodic_counter = None

    @property
    def available(self) -> bool:
        """Returns whether entity is available."""
        return (
            not self._hidden
            and self._proto.connected()
            and self._energy_counter_estimate is not None
        )


class DaikinEnergyEstimatorEntity(
    DaikinWaitForFirstUpdateEntity, DaikinCompressorOntimeEntity, entity.Entity
):
    """Base representation of a Daikin energy estimator."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_available = False

    def __init__(
        self,
        power_estimator: DaikinPowerEstimatorEntity,
        entity_description,
        coordinator: DaikinP1P2UpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the entity."""

        if entity_description.key != "compressor_energy_total_energy_estimate":
            raise Exception("Unsupported")
        DaikinCompressorOntimeEntity.__init__(self, coordinator)
        DaikinWaitForFirstUpdateEntity.__init__(
            self, "total_energy_used", coordinator)

        self.entity_description = entity_description
        self._proto = coordinator.proto()
        self._hysteresis = entity_description.hysteresis
        self._power_estimator = power_estimator

        # KWh
        self._energy_counter_estimate: float = None
        self._energy_counter: int = None

        self._periodic_counter: CALLBACK_TYPE | None = None

        device_name = "ControlUnit"

        self._attr_device_info = DeviceInfo(
            name=device_name,
            manufacturer=MANUFACTURER,
            identifiers={(DOMAIN, device_name, config_entry.unique_id)},
        )

        self._last_update = utcnow()
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_name}_{entity_description.key}"
        self._hidden = False

        if not coordinator.polls_energy_statistics():
            self._hidden = True

        if self._hidden:
            self._attr_entity_registry_enabled_default = False
            self._attr_entity_registry_visible_default = False

    @property
    def device_id(self) -> str:
        """Return device_id."""
        return self.entity_description.key

    @callback
    @abstractmethod
    def _on_settings_change_event(self, key: str, new_value) -> bool:
        """Implement in derived class."""

    @callback
    def _on_compressor_change_event(self, compressor_is_on: bool) -> None:
        """Called when operation status changes."""
        if compressor_is_on and self._periodic_counter is None:
            self._periodic_counter = async_track_time_interval(
                self.hass, self._async_five_minute_task, timedelta(minutes=5)
            )
        if not compressor_is_on and self._periodic_counter is not None:
            self._periodic_counter()
            self._periodic_counter = None

    @callback
    def _on_event(self) -> None:
        """Filter events based on last update."""

        updated = self._on_settings_change_event(
            self.entity_description.key, self._energy_counter_estimate
        )

        if updated:
            self._attr_available = True
            self._last_update = utcnow()
            self.async_write_ha_state()

    @callback
    def _on_setting_flip_event(self, key: str, new_value) -> None:
        """Called when entity_description.key flips over"""

        self._energy_counter = int(new_value)
        if self._energy_counter_estimate is None:
            self._energy_counter_estimate = float(new_value)
        # Reset ontime counter
        self.get_compressor_ontime_and_reset()

        # Reset estimate when it lacks behind
        self._energy_counter_estimate = max(
            float(self._energy_counter), self._energy_counter_estimate
        )
        self._on_event()

    @callback
    def _on_connection(self, connected: bool) -> None:
        """Notify HA about new connection state."""
        self.async_write_ha_state()

    @callback
    def _async_five_minute_task(self, now: datetime) -> None:
        """Run tasks every 5 minutes."""
        if (
            self._power_estimator is None
            or self._power_estimator.estimated_power() == 0
        ):
            return
        # Real value must exist
        if self._energy_counter is None:
            return
        # Estimate value must exist
        if self._energy_counter_estimate is None:
            return

        ontime = self.get_compressor_ontime()
        if ontime == 0:
            return
        estimated_kwh = (
            float(ontime) * self._power_estimator.estimated_power() /
            float(1000 * 3600)
        )

        # When accumulated to fast wait a bit, even though it's "on"
        if estimated_kwh > 2.1:
            return

        _LOGGER.warning(
            f"New estimate for total after {ontime} seconds ontime is {estimated_kwh} KWh"
        )
        new_estimate = float(self._energy_counter) + estimated_kwh
        # No backwards running counter
        self._energy_counter_estimate = max(
            self._energy_counter_estimate, new_estimate)
        self._on_event()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        await DaikinWaitForFirstUpdateEntity.async_added_to_hass(self)
        await DaikinCompressorOntimeEntity.async_added_to_hass(self)
        self._proto.add_connection_listener(self._on_connection)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        await DaikinWaitForFirstUpdateEntity.async_will_remove_from_hass(self)
        await DaikinCompressorOntimeEntity.async_will_remove_from_hass(self)

        self._proto.remove_connection_listener(self._on_connection)
        if self._periodic_counter is not None:
            self._periodic_counter()
            self._periodic_counter = None

    @property
    def available(self) -> bool:
        """Returns whether entity is available."""
        return (
            not self._hidden
            and self._proto.connected()
            and self._energy_counter_estimate is not None
        )
