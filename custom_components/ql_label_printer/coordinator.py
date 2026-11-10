"""Regular printer status checks for the QL Label Printer integration.

Date: 2026-11-10 01:00 GMT (updated; first written 2026-11-09 23:25 GMT)
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Asks the label printer app once a minute whether the printer is ready.
All the entities read from this one check, so the app (and printer) is
only asked once per minute however many entities there are.
"""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, InvalidAuth, LabelPrinterClient
from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)


@dataclass
class LabelPrinterData:
    """What the integration keeps for each label printer app (config entry)."""

    client: LabelPrinterClient
    coordinator: "LabelPrinterCoordinator"
    version: str                      # the app's version, shown on the device page


type LabelPrinterConfigEntry = ConfigEntry[LabelPrinterData]


class LabelPrinterCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetches the printer's status from the app every SCAN_INTERVAL."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: LabelPrinterClient) -> None:
        """Set up the regular check for one app."""
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL)
        self.client = client

    async def _async_update_data(self) -> dict[str, Any]:
        """Ask the app for the printer's status.

        If the app itself can't be reached the entities show as unavailable
        (a printer that's off but whose app answers shows as "offline").
        """
        try:
            return await self.client.get_status()
        except InvalidAuth as exc:
            raise UpdateFailed("The label printer app's password has changed. Enter the new one in the integration's settings.") from exc
        except CannotConnect as exc:
            raise UpdateFailed(str(exc)) from exc
