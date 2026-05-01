import logging
import os

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.http import StaticPathConfig

from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import ParcelDataCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    async def handle_refresh(call: ServiceCall) -> None:
        _LOGGER.debug("Manual refresh triggered via service call")
        for coordinator in hass.data.get(DOMAIN, {}).values():
            await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_REFRESH,
        handle_refresh,
    )

    images_path = os.path.join(os.path.dirname(__file__), "parcel_app_images")
    await hass.http.async_register_static_paths(
        [StaticPathConfig("/parcelapp/images", images_path, cache_headers=True)]
    )
    _LOGGER.debug("Registered static path /parcelapp/images -> %s", images_path)

    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    api_key = entry.data.get("api_key")
    filter_mode = entry.data.get("filter_mode")

    _LOGGER.debug("Setting up Parcel App entry (filter_mode=%s)", filter_mode)

    coordinator = ParcelDataCoordinator(
        hass,
        api_key,
        filter_mode,
    )

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Parcel App initial fetch failed: %s", err, exc_info=True)
        raise ConfigEntryNotReady(f"Parcel App not ready, will retry: {err}") from err

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(
        entry,
        ["sensor"],
    )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        ["sensor"],
    )

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

    return unload_ok