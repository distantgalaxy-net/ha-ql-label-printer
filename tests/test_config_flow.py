"""Tests for the QL Label Printer setup screens.

Date: 2026-11-09 23:40 GMT
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Covers: a successful setup, an address that doesn't work, a wrong or
missing password, a bad address, setting up the same app twice,
reconfiguring, and re-entering a changed password.
"""
from __future__ import annotations

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.ql_label_printer.const import CONF_PASSWORD, CONF_URL, DOMAIN

from .conftest import OPTIONS, READY, URL


async def start(hass: HomeAssistant):
    """Open the setup form."""
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})


async def test_setup_ok(hass: HomeAssistant, app) -> None:
    """A working address (typed with a trailing slash) is saved tidied."""
    result = await start(hass)
    assert result["type"] is FlowResultType.FORM
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: f"{URL}/", CONF_PASSWORD: ""})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_URL: URL, CONF_PASSWORD: ""}


async def test_cannot_connect(hass: HomeAssistant, aioclient_mock) -> None:
    """Something that isn't the app gives cannot_connect."""
    aioclient_mock.get(f"{URL}/api/options", text="<html>not the app</html>")
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_wrong_password(hass: HomeAssistant, aioclient_mock) -> None:
    """A password the app refuses gives invalid_auth."""
    aioclient_mock.get(f"{URL}/api/options", status=401, json={"ok": False, "login": True})
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_PASSWORD: "nope"})
    assert result["errors"] == {"base": "invalid_auth"}


async def test_password_is_sent(hass: HomeAssistant, app) -> None:
    """The password goes to the app as HTTP Basic auth."""
    result = await start(hass)
    await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL, CONF_PASSWORD: "secret123"})
    _, _, _, headers = app.mock_calls[-1]
    assert headers["Authorization"].startswith("Basic ")


async def test_bad_url(hass: HomeAssistant) -> None:
    """An address without http:// or https:// is refused before trying it."""
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: "labels.test:8013"})
    assert result["errors"] == {CONF_URL: "invalid_url"}


async def test_already_configured(hass: HomeAssistant, app, config_entry) -> None:
    """The same app can't be added twice."""
    config_entry.add_to_hass(hass)
    result = await start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: URL})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reconfigure(hass: HomeAssistant, app, config_entry) -> None:
    """The address and password can be changed later."""
    new_url = "https://labels.example.test"
    app.get(f"{new_url}/api/options", json=OPTIONS)
    app.get(f"{new_url}/api/printer/status", json=READY)
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reconfigure_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: new_url, CONF_PASSWORD: "pw"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert config_entry.data == {CONF_URL: new_url, CONF_PASSWORD: "pw"}


async def test_reauth(hass: HomeAssistant, app, config_entry) -> None:
    """A changed password can be entered again."""
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["step_id"] == "reauth_confirm"
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_PASSWORD: "new-password"})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_PASSWORD] == "new-password"
