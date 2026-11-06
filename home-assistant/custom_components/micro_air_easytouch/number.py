"""Support for MicroAirEasyTouch temperature alert thresholds."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.bluetooth import async_ble_device_from_address
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo, EntityCategory
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .micro_air_easytouch.parser import MicroAirEasyTouchBluetoothDeviceData

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up MicroAirEasyTouch alert threshold numbers."""
    data = hass.data[DOMAIN][config_entry.entry_id]["data"]
    mac_address = config_entry.unique_id
    assert mac_address is not None
    async_add_entities(
        [
            MicroAirEasyTouchAlertNumber(
                data, mac_address, "alertLL", "Low Temperature Alert"
            ),
            MicroAirEasyTouchAlertNumber(
                data, mac_address, "alertUL", "High Temperature Alert"
            ),
        ]
    )


class MicroAirEasyTouchAlertNumber(NumberEntity):
    """A device-wide temperature alert threshold (freeze/overheat warning).

    Field name and meaning inferred from the raw status payload (alertLL/alertUL
    alongside a 40/85 reading matching typical freeze/overheat alert defaults);
    not documented by Micro-Air.
    """

    _attr_has_entity_name = True
    _attr_native_unit_of_measurement = UnitOfTemperature.FAHRENHEIT
    _attr_native_min_value = 0
    _attr_native_max_value = 120
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_should_poll = False
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(
        self,
        data: MicroAirEasyTouchBluetoothDeviceData,
        mac_address: str,
        field: str,
        name: str,
    ) -> None:
        """Initialize the alert threshold number."""
        self._data = data
        self._mac_address = mac_address
        self._field = field
        self._attr_unique_id = f"microaireasytouch_{mac_address}_{field}"
        self._attr_name = name
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"MicroAirEasyTouch_{mac_address}")},
            name=f"EasyTouch {mac_address}",
            manufacturer="Micro-Air",
            model="Thermostat",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current threshold from shared device state."""
        return self._data.current_state.get(self._field)

    async def async_set_native_value(self, value: float) -> None:
        """Set a new alert threshold."""
        ble_device = async_ble_device_from_address(self.hass, self._mac_address)
        if not ble_device:
            _LOGGER.error("Could not find BLE device")
            return
        message = {
            "Type": "Change",
            "Changes": {"zone": 0, self._field: int(value)},
        }
        await self._data.send_command(self.hass, ble_device, message)

    def _handle_data_update(self) -> None:
        """Push updated state to Home Assistant when shared data changes."""
        self.schedule_update_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register callback to update when climate platform fetches data."""
        self._data.register_callback(self._handle_data_update)

    async def async_will_remove_from_hass(self) -> None:
        """Unregister callback when entity is removed."""
        self._data.unregister_callback(self._handle_data_update)
