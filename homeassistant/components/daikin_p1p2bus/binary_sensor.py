"""Support for Daikin P1/P2 bus temperature sensors."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DaikinP1P2UpdateCoordinator
from .entity import DaikinEntity

BINARY_SENSOR_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="compressor_running",
        name="compressor_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="compressor_running",
    ),
    BinarySensorEntityDescription(
        key="main_pump_running",
        name="main_pump_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="main_pump_running",
    ),
    BinarySensorEntityDescription(
        key="dhw_boiler_running",
        name="dhw_boiler_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="dhw_boiler_running",
    ),
    BinarySensorEntityDescription(
        key="dhw_circulation_running",
        name="dhw_circulation_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="dhw_circulation_running",
    ),
    # If enabled system may use gas boiler
    BinarySensorEntityDescription(
        key="gas_boiler_enabled",
        name="gas_boiler_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="gas_boiler_enabled",
    ),
    # If enabled system may heat DHW tank
    # Can be disabled on user schedule or manually
    BinarySensorEntityDescription(
        key="dhw_tank_enabled",
        name="dhw_tank_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="dhw_tank_enabled",
    ),
    # If enabled system may heat MainZone or AdditionalZone
    # Can be disabled on user schedule or manually
    BinarySensorEntityDescription(
        key="heating_enabled",
        name="heating_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="heating_enabled",
    ),
    # If enabled system may cool MainZone or AdditionalZone
    # Can be disabled on user schedule, manually or system
    # might not have cooling capabilities.
    BinarySensorEntityDescription(
        key="cooling_enabled",
        name="cooling_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="cooling_enabled",
    ),
    BinarySensorEntityDescription(
        key="heating_zone_enabled",
        name="heating_zone_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="heating_zone_enabled",
    ),
    BinarySensorEntityDescription(
        key="cooling_zone_enabled",
        name="cooling_zone_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="cooling_zone_enabled",
    ),
    BinarySensorEntityDescription(
        key="main_zone_enabled",
        name="main_zone_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="main_zone_enabled",
    ),
    BinarySensorEntityDescription(
        key="additional_zone_enabled",
        name="additional_zone_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="additional_zone_enabled",
    ),
    BinarySensorEntityDescription(
        key="dhw_zone_enabled",
        name="dhw_zone_enabled",
        translation_key="dhw_zone_enabled",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""

    coordinator = config_entry.runtime_data
    async_add_entities(
        DaikinP1P2BinarySensor(entity_description, coordinator)
        for entity_description in BINARY_SENSOR_TYPES
    )


class DaikinP1P2BinarySensor(DaikinEntity, BinarySensorEntity):
    """Representation of a Daikin P1/P2 binary sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, entity_description, coordinator: DaikinP1P2UpdateCoordinator
    ) -> None:
        """Initialize a Daikin P1P2 Entity."""
        DaikinEntity.__init__(self, entity_description, coordinator)

    def _on_settings_change_event(self, key: str, new_value) -> bool:
        """Update attributes from last received message for this object."""

        if self._attr_is_on is None:
            self._attr_is_on = None if new_value is None else bool(new_value)
            return True

        if self._attr_is_on == bool(new_value):
            return False

        self._attr_is_on = None if new_value is None else bool(new_value)
        return True

    @property
    def available(self) -> bool:
        """Returns whether entity is available."""
        return super().available and self._attr_is_on is not None
