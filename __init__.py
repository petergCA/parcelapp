import logging
import os

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.components.http import StaticPathConfig
from homeassistant.loader import async_get_integration

from .const import DOMAIN, SERVICE_REFRESH
from .coordinator import ParcelDataCoordinator

_LOGGER = logging.getLogger(__name__)

CARD_URL = "/parcelapp/parcelapp_card.js"


async def _async_register_card(hass: HomeAssistant) -> None:
    """Register the bundled Lovelace card as a dashboard resource."""
    lovelace = hass.data.get("lovelace")
    if lovelace is None or getattr(lovelace, "mode", None) != "storage":
        _LOGGER.warning(
            "Lovelace is in YAML mode; add %s as a dashboard resource manually",
            CARD_URL,
        )
        return

    resources = lovelace.resources
    if not resources.loaded:
        await resources.async_load()
        resources.loaded = True

    integration = await async_get_integration(hass, DOMAIN)
    versioned_url = f"{CARD_URL}?v={integration.version}"

    for item in resources.async_items():
        if item["url"].split("?")[0] == CARD_URL:
            if item["url"] != versioned_url:
                await resources.async_update_item(
                    item["id"], {"url": versioned_url}
                )
                _LOGGER.debug("Updated card resource to %s", versioned_url)
            return

    await resources.async_create_item(
        {"res_type": "module", "url": versioned_url}
    )
    _LOGGER.debug("Registered card resource %s", versioned_url)


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
    card_path = os.path.join(os.path.dirname(__file__), "parcelapp_card.js")
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig("/parcelapp/images", images_path, cache_headers=True),
            StaticPathConfig(CARD_URL, card_path, cache_headers=True),
        ]
    )
    _LOGGER.debug("Registered static path /parcelapp/images -> %s", images_path)

    await _async_register_card(hass)

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