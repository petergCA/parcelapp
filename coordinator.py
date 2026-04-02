import logging
from datetime import timedelta, datetime
import requests

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from .const import API_URL, DEFAULT_SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

# Only treat these as "delivered" when the latest event matches EXACTLY (case-insensitive)
DELIVERED_EXACT_PHRASES = {
    "delivered",
    "package delivered",
    "delivered at front door",
    "delivered to mailbox",
    "left at front door",
    "left at porch",
    "left at residence",
    "delivered to agent",
}

# Phrases that frequently contain the word "delivered" but are NOT delivered
NOT_DELIVERED_CONTAINS = (
    "will be delivered",
    "scheduled for delivery",
    "delivery date updated",
    "expected delivery",
    "out for delivery",
    "delayed",
    "one business day later",
)

# If your upstream has a reliable delivered code, put it here.
# If you're not sure, leave this set empty and delivery will rely on event phrases only.
DELIVERED_STATUS_CODES = set()  # e.g. {5, "delivered"}


def _coerce_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_date_expected(value):
    """Parse 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD HH:MM' into datetime, else None."""
    if not value:
        return None
    s = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _latest_event_text(delivery: dict) -> str:
    """Get the latest event text. Prefer events[0], fall back to latest_event field."""
    events = delivery.get("events") or []
    if isinstance(events, list) and events:
        txt = events[0].get("event") or events[0].get("description") or ""
        return str(txt).strip()
    return str(delivery.get("latest_event") or "").strip()


def _compute_delivered(delivery: dict, now: datetime) -> bool:
    """
    Robust delivered calculation to avoid false positives like:
    'Your package will be delivered one business day later than expected.'
    """

    # Guard 1: if expected delivery is in the future, it cannot be delivered
    dt_expected = _parse_date_expected(delivery.get("date_expected"))
    if dt_expected and dt_expected > now:
        return False

    # Guard 2: if days_to_delivery is today/future (>= 0), it cannot be delivered
    days = _coerce_int(delivery.get("days_to_delivery"))
    if days is not None and days >= 0:
        return False

    # Strong signal: known delivered status code (optional)
    status_code = delivery.get("status_code")
    if status_code in DELIVERED_STATUS_CODES:
        return True

    # Event-based signal: exact phrase match only (NO substring "delivered" checks)
    latest = _latest_event_text(delivery).lower().strip()

    # If latest contains common "not delivered" phrases, force false
    if any(bad in latest for bad in NOT_DELIVERED_CONTAINS):
        return False

    # Exact match only
    if latest in DELIVERED_EXACT_PHRASES:
        return True

    return False


class ParcelDataCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api_key: str, filter_mode: str):
        super().__init__(
            hass,
            _LOGGER,
            name="Parcel App Deliveries",
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL),
        )
        self.api_key = api_key
        self.filter_mode = filter_mode

    async def _async_update_data(self):
        headers = {"api-key": self.api_key}
        params = {"filter_mode": self.filter_mode}

        try:
            response = await self.hass.async_add_executor_job(
                lambda: requests.get(
                    API_URL,
                    headers=headers,
                    params=params,
                    timeout=10,
                )
            )

            response.raise_for_status()

            deliveries = response.json().get("deliveries", [])
            now = datetime.now()

            for d in deliveries:
                # Normalize latest_event consistently (helps the card)
                events = d.get("events") or []
                if isinstance(events, list) and events:
                    d["latest_event"] = events[0].get("event") or events[0].get("description")
                else:
                    d["latest_event"] = d.get("latest_event")

                # Force our computed delivered value (overrides API mistakes)
                d["delivered"] = _compute_delivered(d, now)

            return deliveries

        except Exception as err:
            raise UpdateFailed(f"Error fetching parcel data: {err}")