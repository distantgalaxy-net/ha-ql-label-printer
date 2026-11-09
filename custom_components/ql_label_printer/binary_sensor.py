"""Binary sensor for the QL Label Printer integration.

Date: 2026-11-09 23:30 GMT
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

  Printer problem  on when the printer can't print (off, cover open, roll
                   finished, wrong roll, error) – handy for notifications.
"""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import LabelPrinterConfigEntry
from .entity import LabelPrinterEntity


async def async_setup_entry(hass: HomeAssistant, entry: LabelPrinterConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Add the problem sensor for a label printer."""
    async_add_entities([PrinterProblemSensor(entry)])


class PrinterProblemSensor(LabelPrinterEntity, BinarySensorEntity):
    """On ("Problem") while the printer can't print."""

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_translation_key = "problem"

    def __init__(self, entry: LabelPrinterConfigEntry) -> None:
        """Create the problem sensor."""
        super().__init__(entry, "problem")

    @property
    def is_on(self) -> bool:
        """True when the app says the printer isn't ready."""
        return not self.coordinator.data.get("ok", False)
