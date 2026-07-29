"""Config flow for the Ecovacs T90 Pro CN patch."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class EcovacsT90PatchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Create the single compatibility-patch entry."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Install the patch without requesting additional credentials."""
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="T90 Pro CN", data={})
