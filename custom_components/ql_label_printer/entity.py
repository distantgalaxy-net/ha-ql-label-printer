"""Shared base for the QL Label Printer entities.

Date: 2026-11-10 00:20 GMT (updated; first written 2026-11-09 23:30 GMT)
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Every entity belongs to one device, "QL Label Printer", whose page shows
the app's version and a "Visit" link to the app's web page: the "address
to open in a browser" if one was given, otherwise the app address.
"""
from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_LINK_URL, DOMAIN
from .coordinator import LabelPrinterConfigEntry, LabelPrinterCoordinator


class LabelPrinterEntity(CoordinatorEntity[LabelPrinterCoordinator]):
    """An entity that reads the printer status from the shared coordinator."""

    _attr_has_entity_name = True

    def __init__(self, entry: LabelPrinterConfigEntry, key: str) -> None:
        """Attach the entity to the label printer's device; key makes its unique ID."""
        super().__init__(entry.runtime_data.coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="QL Label Printer",
            manufacturer="Distant Galaxy",
            model="QL Label Printer app",
            sw_version=entry.runtime_data.version,
            configuration_url=entry.data.get(CONF_LINK_URL) or entry.runtime_data.client.url,
        )
