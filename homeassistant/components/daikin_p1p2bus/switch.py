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
from .entity import DaikinEntity, DaikinP1P2EntityDescription

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, kw_only=True)
class DaikinP1P2SwitchEntityDescription(
    DaikinP1P2EntityDescription, SwitchEntityDescription
):
    """Describes Daikin P1P2 switch entity."""

    parameter: int
    offset: int


SWITCH_TYPES: tuple[DaikinP1P2SwitchEntityDescription, ...] = (
    # DHW pump manual control
    # Works on EJHAxxxxxx
    DaikinP1P2SwitchEntityDescription(
        key="parameter0x35_123",
        parameter=0x35,
        offset=123,
        translation_key="parameter0x35_123",
        name="parameter0x35_123",
        device_class=SwitchDeviceClass.SWITCH,
        is_dhw=True,
        is_ejha=True,
    ),
    DaikinP1P2SwitchEntityDescription(
        key="parameter0x35_124",
        parameter=0x35,
        offset=124,
        translation_key="parameter0x35_124",
        name="parameter0x35_124",
        device_class=SwitchDeviceClass.SWITCH,
        is_dhw=True,
        is_ejha=True,
    ),
    # FOR testing
    # DHW comfort mode? enables gas boiler
    DaikinP1P2SwitchEntityDescription(
        key="parameter0x35_67",
        parameter=0x35,
        offset=67,
        translation_key="parameter0x35_67",
        name="parameter0x35_67",
        device_class=SwitchDeviceClass.SWITCH,
        is_dhw=True,
        is_ejha=True,
    ),
    DaikinP1P2SwitchEntityDescription(
        key="parameter0x35_68",
        parameter=0x35,
        offset=68,
        translation_key="parameter0x35_68",
        name="parameter0x35_68",
        device_class=SwitchDeviceClass.SWITCH,
        is_dhw=True,
        is_ejha=True,
    ),
    # DHW eco mode?
    DaikinP1P2SwitchEntityDescription(
        key="parameter0x35_69",
        parameter=0x35,
        offset=69,
        translation_key="parameter0x35_69",
        name="parameter0x35_69",
        device_class=SwitchDeviceClass.SWITCH,
        is_dhw=True,
        is_ejha=True,
    ),
    DaikinP1P2SwitchEntityDescription(
        key="parameter0x35_70",
        parameter=0x35,
        offset=70,
        translation_key="parameter0x35_70",
        name="parameter0x35_70",
        device_class=SwitchDeviceClass.SWITCH,
        is_dhw=True,
        is_ejha=True,
    ),
    # DHW ?
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_71",
    #    parameter=0x35,
    #    offset=71,
    #    translation_key="parameter0x35_71",
    #    name="parameter0x35_71",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_72",
    #    parameter=0x35,
    #    offset=72,
    #    translation_key="parameter0x35_72",
    #    name="parameter0x35_72",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # gas boiler on/circ pump on? not writable
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_18",
    #    parameter=0x35,
    #    offset=18,
    #    translation_key="parameter0x35_18",
    #    name="parameter0x35_18",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # DHW heat on? not writeable
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_80",
    #    parameter=0x35,
    #    offset=80,
    #    translation_key="parameter0x35_80",
    #    name="parameter0x35_80",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # compressor on ? not writable
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_10",
    #    parameter=0x35,
    #    offset=10,
    #    translation_key="parameter0x35_10",
    #    name="parameter0x35_10",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # TODO
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_19",
    #    parameter=0x35,
    #    offset=19,
    #    translation_key="parameter0x35_19",
    #    name="parameter0x35_19",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_33",
    #    parameter=0x35,
    #    offset=33,
    #    translation_key="parameter0x35_33",
    #    name="parameter0x35_33",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_34",
    #    parameter=0x35,
    #    offset=34,
    #    translation_key="parameter0x35_34",
    #    name="parameter0x35_34",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_39",
    #    parameter=0x35,
    #    offset=39,
    #    translation_key="parameter0x35_39",
    #    name="parameter0x35_39",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_57",
    #    parameter=0x35,
    #    offset=57,
    #    translation_key="parameter0x35_57",
    #    name="parameter0x35_57",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
    # DaikinP1P2SwitchEntityDescription(
    #    key="parameter0x35_58",
    #    parameter=0x35,
    #    offset=58,
    #    translation_key="parameter0x35_58",
    #    name="parameter0x35_58",
    #    device_class=SwitchDeviceClass.SWITCH,
    #    is_dhw=True,
    #    is_ejha=True,
    # ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up switches."""

    coordinator = config_entry.runtime_data
    if coordinator.allow_writes():
        async_add_entities(
            DaikinP1P2Switch(entity_description, coordinator, config_entry)
            for entity_description in SWITCH_TYPES
        )


class DaikinP1P2Switch(DaikinEntity, SwitchEntity):
    """Representation of an Daikin P1P2 switch device."""

    entity_description: DaikinP1P2SwitchEntityDescription

    _attr_should_rate_limit = False

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

        if self._attr_is_on is None:
            self._attr_is_on = None if new_value is None else bool(new_value)
            return True

        if self._attr_is_on == bool(new_value):
            return False

        self._attr_is_on = None if new_value is None else bool(new_value)
        return True

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        p_o = self.entity_description.key.replace("parameter", "").split("_")
        self._proto.set_parameter(int(p_o[0], base=0), int(p_o[1], base=0), 1)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        p_o = self.entity_description.key.replace("parameter", "").split("_")
        self._proto.set_parameter(int(p_o[0], base=0), int(p_o[1], base=0), 0)
