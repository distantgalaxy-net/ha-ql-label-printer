"""The QL Label Printer integration.

Date: 2026-11-09 23:25 GMT
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Connects Home Assistant to the QL Label Printer app
(github.com/distantgalaxy-net/ql-label-printer), which prints labels on a
network Brother QL printer. This integration:
  - shows whether the printer is ready (sensor + problem binary sensor),
    checked once a minute;
  - adds actions to print labels: print_address, print_battery,
    print_food, print_network, and print_label for any label type.
The app does the layout and printing; nothing here talks to the printer.
"""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady, HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import CannotConnect, InvalidAuth, LabelPrinterClient, PrintFailed
from .const import CONF_PASSWORD, CONF_URL, DOMAIN, LABEL_KINDS, MAX_COPIES
from .coordinator import LabelPrinterConfigEntry, LabelPrinterCoordinator, LabelPrinterData

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.SENSOR, Platform.BINARY_SENSOR]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

# ---------------------------------------------------------------- actions
# Fields every print action accepts
ATTR_CONFIG_ENTRY = "config_entry_id"     # which label printer, if there's more than one
ATTR_COPIES = "copies"

BASE_SCHEMA = {
    vol.Optional(ATTR_CONFIG_ENTRY): cv.string,
    vol.Optional(ATTR_COPIES, default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=MAX_COPIES)),
}
text = cv.string
number = vol.All(vol.Coerce(int), vol.Range(min=0))

# Each action: label type it prints, and the fields it accepts (sent to the
# app as they are; the app's API documents them). Dates are YYYY-MM-DD.
ACTIONS: dict[str, tuple[str, dict]] = {
    "print_address": ("address", {
        vol.Required("name"): text,
        vol.Optional("address"): text,              # lines separated by new lines
        vol.Optional("icon"): text,                 # e.g. "gift", or one of your own icons
    }),
    "print_battery": ("battery", {
        vol.Required("device"): text,
        vol.Optional("battery"): text,              # e.g. "CR2032"
        vol.Optional("changed"): cv.date,           # default: today
    }),
    "print_food": ("food", {
        vol.Required("title"): text,
        vol.Optional("storage", default="frozen"): vol.In(["frozen", "fridge", "cupboard"]),
        vol.Optional("date"): cv.date,              # frozen/opened on; default: today
        vol.Optional("shelf"): number,              # use within...
        vol.Optional("shelf_unit"): vol.In(["days", "months"]),
        vol.Optional("method"): vol.In(["from_frozen", "defrost", "cook", "none"]),
        vol.Optional("minutes"): number,
        vol.Optional("temp"): number,               # in the app's temperature unit
        vol.Optional("fan"): number,
        vol.Optional("notes"): text,
    }),
    "print_network": ("network", {
        vol.Required("name"): text,
        vol.Optional("ip"): text,
        vol.Optional("vlan"): text,
        vol.Optional("mac"): text,
        vol.Optional("notes"): text,
    }),
}
# Any label type, with the fields as a dictionary (see the app's API)
PRINT_LABEL = "print_label"
PRINT_LABEL_SCHEMA = vol.Schema({
    **BASE_SCHEMA,
    vol.Required("kind"): vol.In(LABEL_KINDS),
    vol.Optional("fields", default=dict): dict,
})


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the print actions (once, for all label printers)."""

    def find_entry(call: ServiceCall) -> LabelPrinterConfigEntry:
        """The label printer to use: the one named, or the only one set up."""
        wanted = call.data.get(ATTR_CONFIG_ENTRY)
        loaded = [e for e in hass.config_entries.async_entries(DOMAIN) if e.state is ConfigEntryState.LOADED]
        if wanted:
            for entry in loaded:
                if entry.entry_id == wanted:
                    return entry
            raise ServiceValidationError("That label printer isn't set up, or isn't loaded")
        if not loaded:
            raise ServiceValidationError("No label printer is set up")
        if len(loaded) > 1:
            raise ServiceValidationError("More than one label printer is set up: choose one with config_entry_id")
        return loaded[0]

    async def send(call: ServiceCall, kind: str, fields: dict[str, Any]) -> ServiceResponse:
        """Print through the chosen app; raise a readable error if it can't."""
        entry = find_entry(call)
        data: LabelPrinterData = entry.runtime_data
        # Dates go to the app as YYYY-MM-DD text
        fields = {k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in fields.items()}
        try:
            message = await data.client.print_label(kind, fields, call.data.get(ATTR_COPIES, 1))
        except PrintFailed as exc:
            await data.coordinator.async_request_refresh()       # show the printer's state now
            raise HomeAssistantError(str(exc)) from exc
        except InvalidAuth as exc:
            raise HomeAssistantError("The label printer app's password has changed; reconfigure the integration") from exc
        except CannotConnect as exc:
            raise HomeAssistantError(str(exc)) from exc
        await data.coordinator.async_request_refresh()
        return {"ok": True, "message": message}

    def make_handler(kind: str):
        """An action handler that prints one label type from its own fields."""
        async def handler(call: ServiceCall) -> ServiceResponse:
            fields = {k: v for k, v in call.data.items() if k not in (ATTR_CONFIG_ENTRY, ATTR_COPIES)}
            return await send(call, kind, fields)
        return handler

    for action, (kind, fields) in ACTIONS.items():
        hass.services.async_register(DOMAIN, action, make_handler(kind),
                                     schema=vol.Schema({**BASE_SCHEMA, **fields}),
                                     supports_response=SupportsResponse.OPTIONAL)

    async def print_label(call: ServiceCall) -> ServiceResponse:
        """Print any label type from a dictionary of fields."""
        return await send(call, call.data["kind"], dict(call.data.get("fields") or {}))

    hass.services.async_register(DOMAIN, PRINT_LABEL, print_label, schema=PRINT_LABEL_SCHEMA,
                                 supports_response=SupportsResponse.OPTIONAL)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: LabelPrinterConfigEntry) -> bool:
    """Connect to one label printer app and start checking the printer."""
    client = LabelPrinterClient(async_get_clientsession(hass), entry.data[CONF_URL], entry.data.get(CONF_PASSWORD))
    try:
        version = await client.get_version()
    except InvalidAuth as exc:
        raise ConfigEntryAuthFailed(str(exc)) from exc
    except CannotConnect as exc:
        raise ConfigEntryNotReady(str(exc)) from exc     # Home Assistant will try again later
    coordinator = LabelPrinterCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = LabelPrinterData(client=client, coordinator=coordinator, version=version)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: LabelPrinterConfigEntry) -> bool:
    """Stop checking the printer and remove its entities."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
