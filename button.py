from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities,
) -> None:
    async_add_entities(
        [ParcelAppReloadButton(hass, entry)],
        update_before_add=False,
    )


class ParcelAppReloadButton(ButtonEntity):
    _attr_has_entity_name = True
    _attr_icon = "mdi:reload"

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._hass = hass
        self._entry_id = entry.entry_id

        self._attr_name = "Reload Parcel App Integration"
        self._attr_unique_id = f"{entry.entry_id}_reload"

    async def async_press(self) -> None:
        await self._hass.config_entries.async_reload(self._entry_id)
