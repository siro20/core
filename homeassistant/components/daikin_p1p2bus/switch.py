"""Support for Daikin P1/P2 bus parameter control."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.switch import (
    SwitchDeviceClass,
    SwitchEntity,
    SwitchEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import DaikinP1P2UpdateCoordinator
from .entity import DaikinEntity

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DaikinP1P2SwitchEntityDescription(SwitchEntityDescription):
    """Describes Daikin P1P2 switch entity."""

    parameter: int
    offset: int


SWITCH_TYPES: tuple[DaikinP1P2SwitchEntityDescription, ...] = (
    # DHW pump manual control
    # Works on EJHAxxxxxx
    DaikinP1P2SwitchEntityDescription(
        key="parameter35_123",
        parameter=0x35,
        offset=123,
        translation_key="parameter35_123",
        name="parameter35_123",
        device_class=SwitchDeviceClass.SWITCH,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""

    coordinator = config_entry.runtime_data
    async_add_entities(
        DaikinP1P2Switch(entity_description, coordinator)
        for entity_description in SWITCH_TYPES
    )


class DaikinP1P2Switch(DaikinEntity, SwitchEntity):
    """Representation of an Daikin P1P2 switch device."""

    entity_description: DaikinP1P2SwitchEntityDescription

    def __init__(
        self, entity_description, coordinator: DaikinP1P2UpdateCoordinator
    ) -> None:
        """Initialize a Daikin P1P2 Entity."""
        DaikinEntity.__init__(self, entity_description, coordinator)

    @callback
    def _on_settings_change_event(self, key: str, new_value) -> bool:
        """Update attributes from last received message for this object."""

        if self._attr_is_on is None:
            self._attr_is_on = None if new_value is None else bool(new_value)
            return True

        if self._attr_is_on == bool(new_value):
            return False

        self._attr_is_on = None if new_value is None else bool(new_value)
        return True

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        self._proto.set_parameter(
            self.entity_description.parameter, self.entity_description.offset, 1
        )

        self._attr_is_on = True

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        self._proto.set_parameter(
            self.entity_description.parameter, self.entity_description.offset, 0
        )

        self._attr_is_on = False
