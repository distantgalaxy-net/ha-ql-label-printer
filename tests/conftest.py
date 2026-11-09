"""Shared test setup for the QL Label Printer integration.

Date: 2026-11-09 23:40 GMT
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Tests run inside Home Assistant's own test harness
(pytest-homeassistant-custom-component). The label printer app is faked
with `aioclient_mock`, which answers Home Assistant's web requests.
"""
from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.ql_label_printer.const import CONF_PASSWORD, CONF_URL, DOMAIN

URL = "http://labels.test:8013"

# What the app answers: options (version) and two printer states
OPTIONS = {"models": [{"id": "QL-810W", "min_length_mm": 12.7}], "timezones": ["Europe/London"], "version": "1.2.0"}
READY = {"ok": True, "state": "ready", "message": "Printer ready", "media": "62mm continuous", "source": "snmp"}
COVER_OPEN = {"ok": False, "state": "cover_open", "message": "Printer cover open", "media": "62mm continuous",
              "source": "snmp"}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant load integrations from custom_components/."""
    yield


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """A label printer set up at URL, without a password."""
    return MockConfigEntry(domain=DOMAIN, title="QL Label Printer", unique_id=URL,
                           data={CONF_URL: URL, CONF_PASSWORD: ""})


@pytest.fixture
def app(aioclient_mock):
    """A fake label printer app that's running with the printer ready."""
    aioclient_mock.get(f"{URL}/api/options", json=OPTIONS)
    aioclient_mock.get(f"{URL}/api/printer/status", json=READY)
    return aioclient_mock
