"""Tests for the QL Label Printer entities and print actions.

Date: 2026-11-10 00:25 GMT (updated; first written 2026-11-09 23:40 GMT)
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Covers: the sensors' states, the app being unreachable at start-up, each
print action sending the right fields, a refused print (cover open)
raising a readable error, choosing between two label printers, and
unloading.
"""
from __future__ import annotations

from datetime import date

import pytest

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.ql_label_printer.const import DOMAIN

from .conftest import COVER_OPEN, URL


async def setup(hass: HomeAssistant, entry) -> None:
    """Add the label printer and wait for it to load."""
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


def state_of(hass: HomeAssistant, suffix: str):
    """The state of this integration's entity whose ID ends with suffix."""
    matches = [s for s in hass.states.async_all() if s.entity_id.endswith(suffix)]
    assert matches, f"no entity ending {suffix}"
    return matches[0]


async def test_sensors_ready(hass: HomeAssistant, app, config_entry) -> None:
    """With the printer ready: status ready, roll shown, ready to print."""
    await setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.LOADED
    status = state_of(hass, "_printer_status")
    assert status.state == "ready"
    assert status.attributes["message"] == "Printer ready"
    assert state_of(hass, "_loaded_roll").state == "62mm continuous"
    assert state_of(hass, "_ready_to_print").state == "on"


async def test_sensors_offline(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    """The app's "unavailable" (printer off) shows as offline, and not ready to print."""
    aioclient_mock.get(f"{URL}/api/options", json={"models": [], "version": "1.2.0"})
    aioclient_mock.get(f"{URL}/api/printer/status",
                       json={"ok": False, "state": "unavailable", "message": "Printer unavailable", "media": None})
    await setup(hass, config_entry)
    assert state_of(hass, "_printer_status").state == "offline"
    assert state_of(hass, "_ready_to_print").state == "off"


async def test_app_unreachable(hass: HomeAssistant, aioclient_mock, config_entry) -> None:
    """If the app can't be reached, setup is retried later rather than failing."""
    aioclient_mock.get(f"{URL}/api/options", exc=TimeoutError())
    await setup(hass, config_entry)
    assert config_entry.state is ConfigEntryState.SETUP_RETRY


@pytest.mark.parametrize(
    ("action", "data", "kind", "sent"),
    [
        ("print_address", {"name": "Alex Example", "address": "1 High Street\nAnytown", "icon": "gift"},
         "address", {"name": "Alex Example", "address": "1 High Street\nAnytown", "icon": "gift"}),
        ("print_address", {"name": "Alex Example", "address": "1 High Street", "note": "Please leave with a neighbour",
                           "note_align": "center"},
         "address", {"name": "Alex Example", "address": "1 High Street", "note": "Please leave with a neighbour",
                     "note_align": "center"}),
        ("print_battery", {"device": "Hallway sensor", "battery": "CR2032", "changed": "2026-11-09"},
         "battery", {"device": "Hallway sensor", "battery": "CR2032", "changed": "2026-11-09"}),
        ("print_food", {"title": "Beef chilli", "shelf": 3, "shelf_unit": "months", "method": "from_frozen"},
         "food", {"title": "Beef chilli", "storage": "frozen", "shelf": 3, "shelf_unit": "months", "method": "from_frozen"}),
        ("print_food", {"title": "Soup", "storage": "fridge", "method": "cook", "appliance": "microwave", "minutes": 3,
                        "watts": 900, "notes": "Stir, then 2 more min"},
         "food", {"title": "Soup", "storage": "fridge", "method": "cook", "appliance": "microwave", "minutes": 3,
                  "watts": 900, "notes": "Stir, then 2 more min"}),
        ("print_network", {"name": "Label printer", "ip": "192.168.1.20", "vlan": "20"},
         "network", {"name": "Label printer", "ip": "192.168.1.20", "vlan": "20"}),
        ("print_label", {"kind": "luggage", "fields": {"name": "Alex Example", "flights": "1 Mar XX 95 AAA-BBB"}},
         "luggage", {"name": "Alex Example", "flights": "1 Mar XX 95 AAA-BBB"}),
        ("print_label", {"kind": "battery", "fields": {"device": "Smoke alarm", "battery": "9V"}},
         "battery", {"device": "Smoke alarm", "battery": "9V"}),
    ],
)
async def test_print_actions(hass: HomeAssistant, app, config_entry, action, data, kind, sent) -> None:
    """Each action posts the right fields to /api/print/<kind> and returns the app's message."""
    app.post(f"{URL}/api/print/{kind}", json={"ok": True, "message": "Label sent to printer"})
    await setup(hass, config_entry)
    response = await hass.services.async_call(DOMAIN, action, {**data, "copies": 2}, blocking=True, return_response=True)
    assert response == {"ok": True, "message": "Label sent to printer"}
    method, url, body, _ = [c for c in app.mock_calls if str(c[1]).endswith(f"/api/print/{kind}")][-1]
    assert method == "POST"
    assert body == {**sent, "copies": 2}


async def test_print_refused(hass: HomeAssistant, app, config_entry) -> None:
    """If the app refuses (cover open), the action fails with the app's message."""
    app.post(f"{URL}/api/print/battery", status=409,
             json={"ok": False, "message": "Not printed: Printer cover open", "printer": COVER_OPEN})
    await setup(hass, config_entry)
    with pytest.raises(HomeAssistantError, match="Printer cover open"):
        await hass.services.async_call(DOMAIN, "print_battery", {"device": "Sensor"}, blocking=True)


async def test_date_object_sent_as_text(hass: HomeAssistant, app, config_entry) -> None:
    """A date chosen in the action editor reaches the app as YYYY-MM-DD."""
    app.post(f"{URL}/api/print/battery", json={"ok": True, "message": "Label sent to printer"})
    await setup(hass, config_entry)
    await hass.services.async_call(DOMAIN, "print_battery", {"device": "Sensor", "changed": date(2026, 1, 2)},
                                   blocking=True)
    body = [c for c in app.mock_calls if str(c[1]).endswith("/api/print/battery")][-1][2]
    assert body["changed"] == "2026-01-02"


async def test_two_printers_need_choosing(hass: HomeAssistant, app, config_entry) -> None:
    """With two label printers set up, an action must say which one."""
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.ql_label_printer.const import CONF_PASSWORD, CONF_URL
    other_url = "http://other.test:8013"
    app.get(f"{other_url}/api/options", json={"models": [], "version": "1.2.0"})
    app.get(f"{other_url}/api/printer/status", json={"ok": True, "state": "ready", "message": "Printer ready"})
    app.post(f"{other_url}/api/print/battery", json={"ok": True, "message": "Label sent to printer"})
    other = MockConfigEntry(domain=DOMAIN, unique_id=other_url, data={CONF_URL: other_url, CONF_PASSWORD: ""})
    await setup(hass, config_entry)
    await setup(hass, other)
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "print_battery", {"device": "Sensor"}, blocking=True)
    await hass.services.async_call(DOMAIN, "print_battery", {"device": "Sensor", "config_entry_id": other.entry_id},
                                   blocking=True)
    assert any(str(c[1]).startswith(other_url) and str(c[1]).endswith("/api/print/battery") for c in app.mock_calls)


async def test_visit_link(hass: HomeAssistant, app) -> None:
    """The device page's Visit link uses the browser address if given, else the app address."""
    from homeassistant.helpers import device_registry as dr
    from pytest_homeassistant_custom_component.common import MockConfigEntry
    from custom_components.ql_label_printer.const import CONF_LINK_URL, CONF_PASSWORD, CONF_URL
    entry = MockConfigEntry(domain=DOMAIN, unique_id=URL,
                            data={CONF_URL: URL, CONF_PASSWORD: "", CONF_LINK_URL: "https://labels.home.example"})
    await setup(hass, entry)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, entry.entry_id)})
    assert device.configuration_url == "https://labels.home.example"


async def test_visit_link_defaults_to_app(hass: HomeAssistant, app, config_entry) -> None:
    """Without a browser address, the Visit link is the app address."""
    from homeassistant.helpers import device_registry as dr
    await setup(hass, config_entry)
    device = dr.async_get(hass).async_get_device(identifiers={(DOMAIN, config_entry.entry_id)})
    assert device.configuration_url == URL


async def test_unload(hass: HomeAssistant, app, config_entry) -> None:
    """Removing the label printer unloads cleanly."""
    await setup(hass, config_entry)
    assert await hass.config_entries.async_unload(config_entry.entry_id)
    assert config_entry.state is ConfigEntryState.NOT_LOADED
