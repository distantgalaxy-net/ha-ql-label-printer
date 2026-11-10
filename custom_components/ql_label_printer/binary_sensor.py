"""Binary sensor for the QL Label Printer integration.

Date: 2026-11-10 00:50 GMT (updated; first written 2026-11-09 23:30 GMT)
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

  Ready to print  "Yes" when the printer can print, "No" when it can't
                  (off, cover open, labels finished, wrong roll, error).
                  Printer status says why. Handy for notifications.
It replaced a "Printer problem" sensor, whose standard "OK / Problem"
wording read ambiguously on the device page.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LabelPrinterConfigEntry
from .entity import LabelPrinterEntity


async def async_setup_entry(hass: HomeAssistant, entry: LabelPrinterConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Add the "Ready to print" sensor for a label printer."""
    async_add_entities([ReadyToPrintSensor(entry)])


class ReadyToPrintSensor(LabelPrinterEntity, BinarySensorEntity):
    """On ("Yes") while the printer is ready to print."""

    _attr_translation_key = "ready"     # name and Yes/No wording in translations/en.json

    def __init__(self, entry: LabelPrinterConfigEntry) -> None:
        """Create the Ready to print sensor."""
        super().__init__(entry, "ready")

    @property
    def is_on(self) -> bool:
        """True when the app says the printer can print."""
        return bool(self.coordinator.data.get("ok", False))
