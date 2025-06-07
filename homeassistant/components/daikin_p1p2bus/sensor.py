"""Support for Daikin P1/P2 bus temperature sensors."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfEnergy,
    UnitOfTemperature,
    UnitOfTime,
    UnitOfVolume,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DaikinP1P2UpdateCoordinator
from .entity import DaikinEntity, DaikinP1P2EntityDescription

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DaikinP1P2SensorEntityDescription(
    DaikinP1P2EntityDescription, SensorEntityDescription
):
    """Describes Daikin P1P2 sensor entity."""


SENSOR_TYPES: tuple[DaikinP1P2SensorEntityDescription, ...] = (
    DaikinP1P2SensorEntityDescription(
        key="lwt_temperature",
        translation_key="lwt_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_compressor=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="dhw_temperature",
        translation_key="dhw_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_dhw=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="outside_temperature",
        translation_key="outside_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_control_unit=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="return_water_temperature",
        translation_key="return_water_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_compressor=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="gas_boiler_temperature",
        translation_key="gas_boiler_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_boiler=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="refrigerant_temperature",
        translation_key="refrigerant_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_compressor=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="actual_room_temperature",
        translation_key="actual_room_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_control_unit=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="external_sensor_temperature",
        translation_key="external_sensor_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_control_unit=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="dhw_tank_target_temperature",
        translation_key="dhw_tank_target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_dhw=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="dhw_setpoint_temperature",
        translation_key="dhw_setpoint_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_dhw=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="main_zone_target_temperature",
        translation_key="main_zone_target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_control_unit=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="add_zone_target_temperature",
        translation_key="add_zone_target_temperature",
        device_class=SensorDeviceClass.TEMPERATURE,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        suggested_display_precision=1,
        is_additonal_zone=True,
        is_control_unit=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="compressor_for_heating",
        translation_key="compressor_for_heating",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        requires_b8_packet_polling=True,
        is_compressor=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="compressor_for_cooling",
        translation_key="compressor_for_cooling",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        requires_cooling_cap=True,
        requires_b8_packet_polling=True,
        is_compressor=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="compressor_for_dhw",
        translation_key="compressor_for_dhw",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        requires_b8_packet_polling=True,
        is_compressor=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="total_energy_used",
        translation_key="total_energy_used",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        requires_b8_packet_polling=True,
        is_control_unit=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="gas_boiler_operation_hours_heating",
        translation_key="gas_boiler_operation_hours_heating",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfTime.HOURS,
        requires_b8_packet_polling=True,
        is_boiler=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="gas_boiler_operation_hours_dhw",
        translation_key="gas_boiler_operation_hours_dhw",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.HOURS,
        requires_b8_packet_polling=True,
        is_boiler=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="gas_usage_heating",
        translation_key="gas_usage_heating",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.VOLUME,
        requires_b8_packet_polling=True,
        is_boiler=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="number_of_boiler_start",
        translation_key="number_of_boiler_start",
        state_class=SensorStateClass.TOTAL_INCREASING,
        requires_b8_packet_polling=True,
        is_boiler=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="gas_usage_total",
        translation_key="gas_usage_total",
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfVolume.CUBIC_METERS,
        device_class=SensorDeviceClass.VOLUME,
        requires_b8_packet_polling=True,
        is_boiler=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="backup_heater_for_heating",
        translation_key="backup_heater_for_heating",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfTime.HOURS,
        requires_b8_packet_polling=True,
        is_backup_heater=True,
    ),
    DaikinP1P2SensorEntityDescription(
        key="backup_heater_for_dhw",
        translation_key="backup_heater_for_dhw",
        state_class=SensorStateClass.TOTAL_INCREASING,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfTime.HOURS,
        requires_b8_packet_polling=True,
        is_backup_heater=True,
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
        DaikinP1P2Sensor(entity_description, coordinator, config_entry)
        for entity_description in SENSOR_TYPES
    )


class DaikinP1P2Sensor(DaikinEntity, SensorEntity):
    """Representation of a Daikin P1/P2 sensor."""

    _attr_should_poll = False
    _attr_has_entity_name = True

    entity_description: DaikinP1P2SensorEntityDescription

    def __init__(
        self,
        entity_description,
        coordinator: DaikinP1P2UpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize a Daikin P1P2 sensor."""
        DaikinEntity.__init__(self, entity_description,
                              coordinator, config_entry)

    @callback
    def _on_settings_change_event(self, key: str, new_value) -> bool:
        """Update attributes from last received message for this object."""

        if self._attr_native_value is None:
            self._attr_native_value = new_value
            return True

        if isinstance(new_value, float) and isinstance(self._attr_native_value, float):
            if (
                self._attr_native_value < new_value + 0.5
                and self._attr_native_value > new_value - 0.5
            ):
                return False
        elif self._attr_native_value == new_value:
            return False

        self._attr_native_value = new_value
        return True

    @property
    def available(self) -> bool:
        """Returns whether entity is available."""
        return super().available and self._attr_native_value is not None
