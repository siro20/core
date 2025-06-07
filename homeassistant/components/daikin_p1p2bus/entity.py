"""Base class for Acmeda Roller Blinds."""

from __future__ import annotations

from abc import abstractmethod

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.helpers import entity
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.util.dt import utcnow

from .const import (
    CONF_SYSTEM_HAS_ADDITIONAL_ZONE,
    CONF_SYSTEM_HAS_BACKUP_HEATER,
    CONF_SYSTEM_HAS_DHW,
    CONF_SYSTEM_HAS_GAS_BOILER,
    CONF_SYSTEM_SUPPORTS_COOLING,
    DEFAULT_DEVICE_NAME,
    DOMAIN,
    MANUFACTURER,
    MIN_TIME_BETWEEN_UPDATES,
)
from .coordinator import DaikinP1P2UpdateCoordinator


class DaikinP1P2EntityDescription:
    """Describes Daikin P1P2 entity."""

    requires_b8_packet_polling: bool = False
    requires_cooling_cap: bool = False
    requires_flow_meter_cap: bool = False
    is_additonal_zone: bool = False
    is_dhw: bool = False
    is_boiler: bool = False
    is_compressor: bool = False
    is_control_unit: bool = False
    is_backup_heater: bool = False


class DaikinEntity(entity.Entity):
    """Base representation of a Daikin system."""

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
        self.entity_description = entity_description
        self._proto = coordinator.proto()

        device_name = DEFAULT_DEVICE_NAME

        if entity_description.is_dhw:
            device_name = "DHW"
        elif entity_description.is_boiler:
            device_name = "Boiler"
        elif entity_description.is_compressor:
            device_name = "Compressor"
        elif entity_description.is_control_unit:
            device_name = "ControlUnit"
        elif entity_description.is_backup_heater:
            device_name = "BackupHeater"

        self._attr_device_info = DeviceInfo(
            name=device_name,
            manufacturer=MANUFACTURER,
            identifiers={(DOMAIN, device_name, config_entry.unique_id)},
        )

        self._min_time = MIN_TIME_BETWEEN_UPDATES
        self._last_update = utcnow()
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{device_name}_{entity_description.key}"
        self._hidden = False

        system_has_dhw = (
            bool(config_entry.data[CONF_SYSTEM_HAS_DHW])
            if CONF_SYSTEM_HAS_DHW in config_entry.data
            else False
        )
        system_has_gas_boiler = (
            bool(config_entry.data[CONF_SYSTEM_HAS_GAS_BOILER])
            if CONF_SYSTEM_HAS_GAS_BOILER in config_entry.data
            else False
        )
        system_has_additional_zone = (
            bool(config_entry.data[CONF_SYSTEM_HAS_ADDITIONAL_ZONE])
            if CONF_SYSTEM_HAS_ADDITIONAL_ZONE in config_entry.data
            else False
        )
        system_has_backup_heater = (
            bool(config_entry.data[CONF_SYSTEM_HAS_BACKUP_HEATER])
            if CONF_SYSTEM_HAS_BACKUP_HEATER in config_entry.data
            else False
        )
        system_supports_cooling = (
            bool(config_entry.data[CONF_SYSTEM_SUPPORTS_COOLING])
            if CONF_SYSTEM_SUPPORTS_COOLING in config_entry.data
            else False
        )

        if (
            entity_description.requires_b8_packet_polling
            and not coordinator.polls_energy_statistics()
        ):
            self._hidden = True
        if entity_description.requires_cooling_cap and not system_supports_cooling:
            self._hidden = True
        if entity_description.is_boiler and not system_has_gas_boiler:
            self._hidden = True
        if entity_description.is_additonal_zone and not system_has_additional_zone:
            self._hidden = True
        if entity_description.is_dhw and not system_has_dhw:
            self._hidden = True
        if entity_description.is_backup_heater and not system_has_backup_heater:
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
    def _on_event(self, key: str, new_value) -> None:
        """Filter events based on last update."""
        now = utcnow()
        if not self._attr_available or now > self._last_update + self._min_time:
            updated = self._on_settings_change_event(key, new_value)

            if updated:
                self._attr_available = True
                self._last_update = now
                self.async_write_ha_state()

    @callback
    def _on_connection(self, connected: bool) -> None:
        """Notify HA about new connection state."""
        self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._proto.add_settings_change_listener(
            self.entity_description.key, self._on_event
        )
        self._proto.add_connection_listener(self._on_connection)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self._proto.remove_settings_change_listener(
            self.entity_description.key, self._on_event
        )
        self._proto.remove_connection_listener(self._on_connection)

    @property
    def available(self) -> bool:
        """Returns whether entity is available."""
        return not self._hidden and self._proto.connected()
