"""Setup screens for the QL Label Printer integration.

Date: 2026-11-09 23:30 GMT
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Settings → Devices & services → Add integration → QL Label Printer asks
for the label printer app's address and its password (if it has one), and
checks it can connect before saving. Also:
  - reconfigure: change the address or password later;
  - reauth: asked for automatically if the app's password changes.
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig, TextSelectorType

from .api import CannotConnect, InvalidAuth, LabelPrinterClient
from .const import CONF_PASSWORD, CONF_URL, DEFAULT_URL, DOMAIN

TITLE = "QL Label Printer"
PASSWORD_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))
URL_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.URL))


def clean_url(url: str) -> str | None:
    """Tidy an address the user typed; None if it isn't an http(s) address."""
    url = (url or "").strip().rstrip("/")
    parts = urlparse(url)
    if parts.scheme not in ("http", "https") or not parts.netloc:
        return None
    return url


class LabelPrinterConfigFlow(ConfigFlow, domain=DOMAIN):
    """Add, reconfigure or re-authenticate a label printer app."""

    VERSION = 1

    async def _check(self, url: str, password: str | None) -> tuple[dict[str, str], str | None]:
        """Try the address and password. Returns (errors for the form, app version)."""
        client = LabelPrinterClient(async_get_clientsession(self.hass), url, password)
        try:
            return {}, await client.get_version()
        except InvalidAuth:
            return {"base": "invalid_auth"}, None
        except CannotConnect:
            return {"base": "cannot_connect"}, None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """First setup: ask for the address and optional password."""
        errors: dict[str, str] = {}
        if user_input is not None:
            url = clean_url(user_input[CONF_URL])
            password = user_input.get(CONF_PASSWORD) or ""
            if not url:
                errors[CONF_URL] = "invalid_url"
            else:
                await self.async_set_unique_id(url.lower())
                self._abort_if_unique_id_configured()
                errors, _ = await self._check(url, password)
                if not errors:
                    return self.async_create_entry(title=TITLE, data={CONF_URL: url, CONF_PASSWORD: password})
        return self.async_show_form(
            step_id="user", errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_URL): URL_SELECTOR, vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR}),
                user_input or {CONF_URL: DEFAULT_URL}),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the address or password of an existing label printer."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            url = clean_url(user_input[CONF_URL])
            password = user_input.get(CONF_PASSWORD) or ""
            if not url:
                errors[CONF_URL] = "invalid_url"
            else:
                # A new address must not belong to another label printer already set up
                if url.lower() != entry.unique_id:
                    await self.async_set_unique_id(url.lower())
                    self._abort_if_unique_id_configured()
                errors, _ = await self._check(url, password)
                if not errors:
                    return self.async_update_reload_and_abort(
                        entry, unique_id=url.lower(), data_updates={CONF_URL: url, CONF_PASSWORD: password})
        return self.async_show_form(
            step_id="reconfigure", errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_URL): URL_SELECTOR, vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR}),
                user_input or {CONF_URL: entry.data[CONF_URL]}),
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        """The app's password was refused: ask for the new one."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ask for the app's current password and check it."""
        entry = self._get_reauth_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            password = user_input.get(CONF_PASSWORD) or ""
            errors, _ = await self._check(entry.data[CONF_URL], password)
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_PASSWORD: password})
        return self.async_show_form(
            step_id="reauth_confirm", errors=errors,
            data_schema=vol.Schema({vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR}),
            description_placeholders={"url": entry.data[CONF_URL]},
        )
