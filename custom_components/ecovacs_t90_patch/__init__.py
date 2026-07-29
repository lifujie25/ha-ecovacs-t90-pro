"""Ecovacs T90 Pro Chinese hardware-class patch."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components import frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.core import HomeAssistant

from .const import (
    CARD_MODULE_URL,
    CARD_STATIC_URL,
    DATA_CARD_REGISTERED,
    DATA_STATIC_PATH_REGISTERED,
    DOMAIN,
    ECOVACS_DOMAIN,
    TARGET_DEVICE_CLASS,
)
from .patch import install_hardware_alias

_LOGGER = logging.getLogger(__name__)
_FRONTEND_DIR = Path(__file__).parent / "frontend"


async def _async_register_map_card(hass: HomeAssistant) -> None:
    """Expose and load the map card bundled with the integration."""
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

    if not domain_data.get(DATA_CARD_REGISTERED):
        frontend.add_extra_js_url(hass, CARD_MODULE_URL)
        domain_data[DATA_CARD_REGISTERED] = True


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
        if entries.pop(DATA_CARD_REGISTERED, False):
            frontend.remove_extra_js_url(hass, CARD_MODULE_URL)
    return True
