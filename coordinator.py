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

# Module-level so the cooldown survives config-entry setup retries/reloads.
# Parcel API allows 20 requests/hour; hammering after a 429 extends the ban.
_RATE_LIMITED_UNTIL = None

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
    Robust delivered calculation. status_code == 0 is the primary signal per the
    Parcel API docs (https://parcelapp.net/help/api-view-deliveries.html). Event
    phrase matching is a fallback for carriers whose status codes aren't normalised.
    Guards against false positives like:
    'Your package will be delivered one business day later than expected.'
    """

    # Primary signal: API-authoritative — status_code 0 means completed delivery
    status_code = _coerce_int(delivery.get("status_code"))
    if status_code == 0:
        return True

    # Guard 1: if expected delivery is in the future, it cannot be delivered
    dt_expected = _parse_date_expected(delivery.get("date_expected"))
    if dt_expected and dt_expected > now:
        return False

    # Guard 2: if days_to_delivery is today/future (>= 0), it cannot be delivered
    days = _coerce_int(delivery.get("days_to_delivery"))
    if days is not None and days >= 0:
        return False

    # Fallback: event phrase match (exact only, no substring "delivered" checks)
    latest = _latest_event_text(delivery).lower().strip()

    if any(bad in latest for bad in NOT_DELIVERED_CONTAINS):
        return False

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
        global _RATE_LIMITED_UNTIL
        if _RATE_LIMITED_UNTIL and datetime.now() < _RATE_LIMITED_UNTIL:
            _LOGGER.debug(
                "Parcel API in rate-limit cooldown until %s; serving cached data",
                _RATE_LIMITED_UNTIL,
            )
            if self.data is not None:
                return self.data
            raise UpdateFailed("Parcel API rate limited; waiting out cooldown")

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
        except requests.exceptions.Timeout:
            _LOGGER.error("Parcel API request timed out after 10 s")
            raise UpdateFailed("Parcel API request timed out")
        except requests.exceptions.ConnectionError as err:
            _LOGGER.error("Parcel API connection error: %s", err)
            raise UpdateFailed(f"Parcel API connection error: {err}")
        except Exception as err:
            _LOGGER.error("Unexpected error during Parcel API request: %s", err, exc_info=True)
            raise UpdateFailed(f"Unexpected request error: {err}")

        if response.status_code == 429:
            _RATE_LIMITED_UNTIL = datetime.now() + timedelta(minutes=45)
            _LOGGER.warning(
                "Parcel API rate limited (429); pausing polls until %s",
                _RATE_LIMITED_UNTIL,
            )
            if self.data is not None:
                return self.data
            raise UpdateFailed("Parcel API rate limited (429)")

        if not response.ok:
            _LOGGER.error(
                "Parcel API returned HTTP %s — body: %s",
                response.status_code,
                response.text[:500],
            )
            response.raise_for_status()

        try:
            payload = response.json()
        except Exception as err:
            _LOGGER.error(
                "Parcel API response is not valid JSON (status %s) — body: %s",
                response.status_code,
                response.text[:500],
            )
            raise UpdateFailed(f"Invalid JSON from Parcel API: {err}")

        deliveries = payload.get("deliveries", [])
        if not isinstance(deliveries, list):
            _LOGGER.error(
                "Parcel API 'deliveries' field is not a list, got %s — full payload: %s",
                type(deliveries).__name__,
                str(payload)[:500],
            )
            raise UpdateFailed("Unexpected payload shape from Parcel API")

        _LOGGER.debug("Parcel API returned %d deliveries", len(deliveries))

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