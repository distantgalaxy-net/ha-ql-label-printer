"""Setup screens for the QL Label Printer integration.

Date: 2026-11-10 00:20 GMT (updated; first written 2026-11-09 23:30 GMT)
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Settings → Devices & services → Add integration → QL Label Printer asks
for the label printer app's address and its password (if it has one), and
checks it can connect before saving. An optional second address is the
one the device page's "Visit" link opens in a browser: useful when Home
Assistant connects to the app at http://127.0.0.1:8013 (same host) but
people open it at an https:// name. Also:
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
from .const import CONF_LINK_URL, CONF_PASSWORD, CONF_URL, DEFAULT_URL, DOMAIN

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


def settings_schema() -> vol.Schema:
    """The setup / reconfigure form: app address, password, link address."""
    return vol.Schema({
        vol.Required(CONF_URL): URL_SELECTOR,
        vol.Optional(CONF_PASSWORD): PASSWORD_SELECTOR,
        vol.Optional(CONF_LINK_URL): URL_SELECTOR,
    })


def read_form(user_input: dict[str, Any]) -> tuple[dict[str, str], dict[str, str]]:
    """Tidy the form's values. Returns (data to save, errors for the form)."""
    errors: dict[str, str] = {}
    url = clean_url(user_input.get(CONF_URL, ""))
    if not url:
        errors[CONF_URL] = "invalid_url"
    link = (user_input.get(CONF_LINK_URL) or "").strip()
    if link:
        link = clean_url(link) or ""
        if not link:
            errors[CONF_LINK_URL] = "invalid_url"
    data = {CONF_URL: url or "", CONF_PASSWORD: user_input.get(CONF_PASSWORD) or "", CONF_LINK_URL: link}
    return data, errors


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
        """First setup: ask for the address, optional password and link address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = read_form(user_input)
            if not errors:
                await self.async_set_unique_id(data[CONF_URL].lower())
                self._abort_if_unique_id_configured()
                errors, _ = await self._check(data[CONF_URL], data[CONF_PASSWORD])
                if not errors:
                    return self.async_create_entry(title=TITLE, data=data)
        return self.async_show_form(
            step_id="user", errors=errors,
            data_schema=self.add_suggested_values_to_schema(settings_schema(), user_input or {CONF_URL: DEFAULT_URL}),
        )

    async def async_step_reconfigure(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Change the address or password of an existing label printer."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}
        if user_input is not None:
            data, errors = read_form(user_input)
            if not errors:
                url = data[CONF_URL]
                # A new address must not belong to another label printer already set up
                if url.lower() != entry.unique_id:
                    await self.async_set_unique_id(url.lower())
                    self._abort_if_unique_id_configured()
                errors, _ = await self._check(url, data[CONF_PASSWORD])
                if not errors:
                    return self.async_update_reload_and_abort(entry, unique_id=url.lower(), data_updates=data)
        return self.async_show_form(
            step_id="reconfigure", errors=errors,
            data_schema=self.add_suggested_values_to_schema(
                settings_schema(),
                user_input or {CONF_URL: entry.data[CONF_URL], CONF_LINK_URL: entry.data.get(CONF_LINK_URL, "")}),
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
