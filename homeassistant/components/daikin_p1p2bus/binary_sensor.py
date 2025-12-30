"""Support for Daikin P1/P2 bus temperature sensors."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DaikinP1P2UpdateCoordinator
from .entity import DaikinEntity, DaikinP1P2EntityDescription


@dataclass(frozen=True, kw_only=True)
class DaikinP1P2BinarySensorEntityDescription(
    DaikinP1P2EntityDescription, BinarySensorEntityDescription
):
    """Describes Daikin P1P2 binary sensor entity."""


BINARY_SENSOR_TYPES: tuple[DaikinP1P2BinarySensorEntityDescription, ...] = (
    DaikinP1P2BinarySensorEntityDescription(
        key="compressor_running",
        name="compressor_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="compressor_running",
        is_compressor=True,
    ),
    DaikinP1P2BinarySensorEntityDescription(
        key="main_pump_running",
        name="main_pump_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="main_pump_running",
        is_control_unit=True,
    ),
    DaikinP1P2BinarySensorEntityDescription(
        key="dhw_boiler_running",
        name="dhw_boiler_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="dhw_boiler_running",
        is_dhw=True,
    ),
    DaikinP1P2BinarySensorEntityDescription(
        key="dhw_circulation_running",
        name="dhw_circulation_running",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="dhw_circulation_running",
        is_dhw=True,
    ),
    # If enabled system may use gas boiler
    DaikinP1P2BinarySensorEntityDescription(
        key="gas_boiler_enabled",
        name="gas_boiler_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="gas_boiler_enabled",
        is_boiler=True,
    ),
    # If enabled system may heat DHW tank
    # Can be disabled on user schedule or manually
    DaikinP1P2BinarySensorEntityDescription(
        key="dhw_tank_enabled",
        name="dhw_tank_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="dhw_tank_enabled",
        is_dhw=True,
    ),
    # If enabled system may heat MainZone or AdditionalZone
    # Can be disabled on user schedule or manually
    DaikinP1P2BinarySensorEntityDescription(
        key="heating_enabled",
        name="heating_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="heating_enabled",
        is_control_unit=True,
    ),
    # If enabled system may cool MainZone or AdditionalZone
    # Can be disabled on user schedule, manually or system
    # might not have cooling capabilities.
    DaikinP1P2BinarySensorEntityDescription(
        key="cooling_enabled",
        name="cooling_enabled",
        device_class=BinarySensorDeviceClass.POWER,
        translation_key="cooling_enabled",
        requires_cooling_cap=True,
        is_control_unit=True,
    ),
    DaikinP1P2BinarySensorEntityDescription(
        key="heating_zone_enabled",
        name="heating_zone_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="heating_zone_enabled",
        is_control_unit=True,
    ),
    DaikinP1P2BinarySensorEntityDescription(
        key="cooling_zone_enabled",
        name="cooling_zone_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="cooling_zone_enabled",
        requires_cooling_cap=True,
        is_control_unit=True,
    ),
    # True when main zone needs heating
    DaikinP1P2BinarySensorEntityDescription(
        key="main_zone_enabled",
        name="main_zone_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="main_zone_enabled",
        is_control_unit=True,
    ),
    DaikinP1P2BinarySensorEntityDescription(
        key="additional_zone_enabled",
        name="additional_zone_enabled",
        device_class=BinarySensorDeviceClass.RUNNING,
        translation_key="additional_zone_enabled",
        is_additonal_zone=True,
        is_control_unit=True,
    ),
    # True when DHW needs heating
    DaikinP1P2BinarySensorEntityDescription(
        key="dhw_zone_enabled",
        name="dhw_zone_enabled",
        translation_key="dhw_zone_enabled",
        is_control_unit=True,
    ),
    DaikinP1P2BinarySensorEntityDescription(
        key="parameter0x35_9",
        name="operation_mode_stay_warm",
        translation_key="operation_mode_stay_warm",
        is_control_unit=True,
        is_ejha=True,
    ),
)

# Parameter 0x35
# Silence level 1:
# 900 W
# parameter0x35_0 = 1
# parameter0x35_1 = 1
# parameter0x35_3 = 1
# parameter0x35_4 = 1

# Silence level 2:
# parameter0x35_0 = 2
# parameter0x35_1 = 2
# parameter0x35_3 = 1
# parameter0x35_4 = 1

# No silence level:
# 1600 W
# parameter0x35_0 = 0
# parameter0x35_1 = 0
# parameter0x35_3 = 0
# parameter0x35_4 = 0


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sensors."""

    coordinator = config_entry.runtime_data

    async_add_entities(
        DaikinP1P2BinarySensor(entity_description, coordinator, config_entry)
        for entity_description in BINARY_SENSOR_TYPES
    )


class DaikinP1P2BinarySensor(DaikinEntity, BinarySensorEntity):
    """Representation of a Daikin P1/P2 binary sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    entity_description: DaikinP1P2BinarySensorEntityDescription

    def __init__(
        self,
        entity_description,
        coordinator: DaikinP1P2UpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize a Daikin P1P2 Entity."""
        DaikinEntity.__init__(self, entity_description,
                              coordinator, config_entry)

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
