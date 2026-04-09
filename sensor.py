import logging
from datetime import datetime

from homeassistant.components.sensor import SensorEntity

_LOGGER = logging.getLogger(__name__)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
):
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [ParcelSummarySensor(coordinator)],
        update_before_add=True,
    )


class ParcelSummarySensor(CoordinatorEntity, SensorEntity):
    """Single entity representing all Parcel deliveries."""

    _attr_name = "Parcel Deliveries"
    _attr_unique_id = "parcelapp_deliveries"
    _attr_icon = "mdi:package-variant-closed"

    @property
    def state(self):
        deliveries = self.coordinator.data or []
        return len(deliveries)

    @property
    def extra_state_attributes(self):
        deliveries = self.coordinator.data or []
        parsed = []

        for delivery in deliveries:
            expected = delivery.get("date_expected")
            days_to_delivery = None

            if expected:
                try:
                    expected_date = datetime.fromisoformat(expected).date()
                    days_to_delivery = (
                        expected_date - datetime.now().date()
                    ).days
                except Exception as err:
                    _LOGGER.warning(
                        "Could not parse date_expected %r for tracking %r: %s",
                        expected,
                        delivery.get("tracking_number"),
                        err,
                    )

            events = delivery.get("events") or []

            latest_event_text = None

            events = delivery.get("events") or []

            if events:
                latest_event = events[0]
                latest_event_text = (
                    latest_event.get("event")
                    or latest_event.get("description")
                    or ""
                )
            else:
                latest_event_text = "No tracking data available"

            # Trust coordinator logic
            delivered = delivery.get("delivered", False)

            parsed.append(
                {
                    "tracking_number": delivery.get("tracking_number"),
                    "carrier_code": delivery.get("carrier_code"),
                    "description": delivery.get("description"),
                    "status_code": delivery.get("status_code"),
                    "date_expected": expected,
                    "days_to_delivery": days_to_delivery,
                    "events": events,
                    "latest_event": latest_event_text,
                    "delivered": delivered,
                }
            )

        return {
            "deliveries": parsed
        }