"""Base class for Acmeda Roller Blinds."""

from __future__ import annotations

from abc import abstractmethod

from homeassistant.const import EntityCategory
from homeassistant.core import callback
from homeassistant.helpers import device_registry as dr, entity
from homeassistant.util.dt import utcnow

from .const import DOMAIN, MANUFACTURER, MIN_TIME_BETWEEN_UPDATES
from .coordinator import DaikinP1P2UpdateCoordinator


class DaikinEntity(entity.Entity):
    """Base representation of a Daikin system."""

    _attr_should_poll = False
    _attr_has_entity_name = True
    _attr_available = False
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(
        self, entity_description, coordinator: DaikinP1P2UpdateCoordinator
    ) -> None:
        """Initialize the entity."""
        self.entity_description = entity_description
        self._proto = coordinator.proto()
        self._attr_device_info = coordinator.device_info
        self._min_time = MIN_TIME_BETWEEN_UPDATES
        self._last_update = utcnow()
        self._model = ""
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{entity_description.key}"
        )

    @property
    def device_id(self) -> str:
        """Return device_id."""
        return self.entity_description.key

    @property
    def device_info(self) -> dr.DeviceInfo:
        """Return the device info."""
        return dr.DeviceInfo(
            identifiers={(DOMAIN, self.entity_description.key)},
            manufacturer=MANUFACTURER,
            model=self._model,
        )

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

    @callback
    def _on_model(self, name: str) -> None:
        """Set model name."""
        self._model = name

    async def async_added_to_hass(self) -> None:
        """Run when entity about to be added to hass."""
        self._proto.add_settings_change_listener(
            self.entity_description.key, self._on_event
        )
        self._proto.add_connection_listener(self._on_connection)
        self._proto.add_model_listener(self._on_model)

    async def async_will_remove_from_hass(self) -> None:
        """Run when entity will be removed from hass."""
        self._proto.remove_settings_change_listener(
            self.entity_description.key, self._on_event
        )
        self._proto.remove_connection_listener(self._on_connection)
        self._proto.remove_model_listener(self._on_model)

    @property
    def available(self) -> bool:
        """Returns whether entity is available."""
        return self._proto.connected()
