"""Support for Daikin P1/P2 bus parameter control."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntity,
    NumberEntityDescription,
    NumberMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DaikinP1P2UpdateCoordinator
from .entity import DaikinEntity, DaikinP1P2EntityDescription

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DaikinP1P2SliderEntityDescription(
    DaikinP1P2EntityDescription, NumberEntityDescription
):
    """Describes Daikin P1P2 slider entity."""

    parameter: int
    offset: int


NUMBER_TYPES: tuple[DaikinP1P2SliderEntityDescription, ...] = (
    DaikinP1P2SliderEntityDescription(
        key="parameter0x36_03",
        translation_key="parameter0x36_03",
        native_step=0.1,
        native_min_value=40,
        native_max_value=60,
        parameter=0x36,
        offset=3,
        entity_category=EntityCategory.CONFIG,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        mode=NumberMode.SLIDER,
        is_dhw=True,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up sliders."""

    coordinator = config_entry.runtime_data
    if coordinator.allow_writes():
        async_add_entities(
            DaikinP1P2Slider(entity_description, coordinator, config_entry)
            for entity_description in NUMBER_TYPES
        )


class DaikinP1P2Slider(DaikinEntity, NumberEntity):
    """Representation of an Daikin P1P2 slider device."""

    entity_description: DaikinP1P2SliderEntityDescription
    _attr_has_entity_name = True
    _attr_icon = "mdi:thermometer"

    def __init__(
        self,
        entity_description,
        coordinator: DaikinP1P2UpdateCoordinator,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize a Daikin P1P2 Entity."""
        DaikinEntity.__init__(self, entity_description, coordinator, config_entry)

    @callback
    def _on_settings_change_event(self, key: str, new_value) -> bool:
        """Update attributes from last received message for this object."""

        if self._attr_native_value is None:
            self._attr_native_value = None if new_value is None else bool(new_value)
            return True

        if self._attr_native_value == bool(new_value):
            return False

        self._attr_native_value = None if new_value is None else bool(new_value)
        return True

    def set_native_value(self, value: float) -> None:
        """Set new parameter."""
        self._proto.set_parameter(
            self.entity_description.parameter,
            self.entity_description.offset,
            int(value),
        )
