"""Sensors for the QL Label Printer integration.

Date: 2026-11-09 23:30 GMT
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

  Printer status  ready / connected / cover_open / no_media / wrong_media /
                  error / offline, with the app's message as an attribute.
  Loaded roll     e.g. "62mm continuous" (unknown if the printer doesn't say).
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PRINTER_STATES
from .coordinator import LabelPrinterConfigEntry
from .entity import LabelPrinterEntity


async def async_setup_entry(hass: HomeAssistant, entry: LabelPrinterConfigEntry,
                            async_add_entities: AddConfigEntryEntitiesCallback) -> None:
    """Add the two sensors for a label printer."""
    async_add_entities([PrinterStatusSensor(entry), LoadedRollSensor(entry)])


class PrinterStatusSensor(LabelPrinterEntity, SensorEntity):
    """The printer's state, as one of a fixed list (so automations can match it)."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = PRINTER_STATES
    _attr_translation_key = "status"

    def __init__(self, entry: LabelPrinterConfigEntry) -> None:
        """Create the status sensor."""
        super().__init__(entry, "status")

    @property
    def native_value(self) -> str | None:
        """Current state, e.g. "cover_open"."""
        return self.coordinator.data.get("state")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """The app's own message and where the answer came from."""
        data = self.coordinator.data
        return {"message": data.get("message"), "source": data.get("source")}


class LoadedRollSensor(LabelPrinterEntity, SensorEntity):
    """Which roll is loaded, e.g. "62mm continuous" (if the printer reports it)."""

    _attr_translation_key = "media"

    def __init__(self, entry: LabelPrinterConfigEntry) -> None:
        """Create the loaded-roll sensor."""
        super().__init__(entry, "media")

    @property
    def native_value(self) -> str | None:
        """The roll's description, or None (unknown) when not reported."""
        return self.coordinator.data.get("media")
