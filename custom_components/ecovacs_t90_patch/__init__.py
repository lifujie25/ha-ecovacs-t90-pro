"""Ecovacs T90 Pro Chinese hardware-class patch."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.lovelace.const import (
    CONF_RESOURCE_TYPE_WS,
    LOVELACE_DATA,
)
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant

from .const import (
    CARD_MODULE_URL,
    CARD_STATIC_URL,
    DATA_EXTRA_CARD_REGISTERED,
    DATA_STATIC_PATH_REGISTERED,
    DOMAIN,
    ECOVACS_DOMAIN,
    TARGET_DEVICE_CLASS,
)
from .patch import install_hardware_alias

_LOGGER = logging.getLogger(__name__)
_FRONTEND_DIR = Path(__file__).parent / "frontend"


async def _async_register_map_card(hass: HomeAssistant) -> None:
    """Expose the bundled map card and persist its Lovelace resource."""
    domain_data = hass.data.setdefault(DOMAIN, {})

    if not domain_data.get(DATA_STATIC_PATH_REGISTERED):
        await hass.http.async_register_static_paths(
            [
                StaticPathConfig(
                    CARD_STATIC_URL,
                    str(_FRONTEND_DIR),
                    False,
                )
            ]
        )
        domain_data[DATA_STATIC_PATH_REGISTERED] = True

    lovelace_data = hass.data.get(LOVELACE_DATA)
    resources = lovelace_data.resources if lovelace_data else None
    if resources is not None and hasattr(resources, "async_create_item"):
        await resources.async_get_info()
        bundled_resources = [
            resource
            for resource in resources.async_items()
            if resource.get(CONF_URL, "").startswith(
                f"{CARD_STATIC_URL}/ecovacs-t90-map-card.js"
            )
        ]
        if bundled_resources:
            resource = bundled_resources[0]
            if resource.get(CONF_URL) != CARD_MODULE_URL:
                await resources.async_update_item(
                    resource["id"],
                    {
                        CONF_URL: CARD_MODULE_URL,
                        CONF_RESOURCE_TYPE_WS: "module",
                    },
                )
        else:
            await resources.async_create_item(
                {
                    CONF_URL: CARD_MODULE_URL,
                    CONF_RESOURCE_TYPE_WS: "module",
                }
            )
        return

    _LOGGER.warning(
        "Lovelace resources are not in storage mode; loading the T90 map card "
        "for the current frontend session only"
    )
    if not domain_data.get(DATA_EXTRA_CARD_REGISTERED):
        frontend.add_extra_js_url(hass, CARD_MODULE_URL)
        domain_data[DATA_EXTRA_CARD_REGISTERED] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Install the profile, load the card, and reload Ecovacs cloud entries."""
    await hass.async_add_executor_job(install_hardware_alias)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = TARGET_DEVICE_CLASS
    await _async_register_map_card(hass)

    for ecovacs_entry in hass.config_entries.async_entries(ECOVACS_DOMAIN):
        if ecovacs_entry.state in (
            ConfigEntryState.LOADED,
            ConfigEntryState.SETUP_ERROR,
            ConfigEntryState.SETUP_RETRY,
        ):
            _LOGGER.info(
                "Reloading Ecovacs entry after installing support for class %s",
                TARGET_DEVICE_CLASS,
            )
            await hass.config_entries.async_reload(ecovacs_entry.entry_id)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the helper entry without disrupting an active Ecovacs device."""
    entries = hass.data.get(DOMAIN)
    if isinstance(entries, dict):
        entries.pop(entry.entry_id, None)
        if entries.pop(DATA_EXTRA_CARD_REGISTERED, False):
            frontend.remove_extra_js_url(hass, CARD_MODULE_URL)
    return True


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove the automatically managed Lovelace resource."""
    lovelace_data = hass.data.get(LOVELACE_DATA)
    resources = lovelace_data.resources if lovelace_data else None
    if resources is None or not hasattr(resources, "async_delete_item"):
        return

    await resources.async_get_info()
    for resource in list(resources.async_items()):
        if resource.get(CONF_URL, "").startswith(
            f"{CARD_STATIC_URL}/ecovacs-t90-map-card.js"
        ):
            await resources.async_delete_item(resource["id"])
