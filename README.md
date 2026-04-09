# 📦 Parcel App — Home Assistant Integration

> Track your deliveries inside Home Assistant using the [Parcel App](https://parcelapp.net) API.

---

## Overview

This custom integration pulls your delivery data from the Parcel App API and exposes it as a sensor in Home Assistant. You can see how many packages you have in-flight, check statuses, expected delivery dates, and the latest tracking events — all without leaving your dashboard.

---

## Features

- **Delivery count sensor** — state = number of active/recent deliveries
- **Rich attributes** — per-delivery tracking number, carrier, description, status, expected date, days until delivery, latest event, and full event history
- **Smart delivered detection** — avoids false positives (e.g. "will be delivered one business day later") by using exact phrase matching and date guards
- **Manual refresh button** — reload the integration on demand from the UI
- **Service call** — `parcelapp.refresh` to force a data refresh from automations
- **Configurable filter mode** — choose between `active` (in-transit only) or `recent` (includes recently delivered)

---

## Requirements

- Home Assistant **2024.6.0** or newer
- A [Parcel App](https://parcelapp.net) account with an **API key**
  - Get your API key at: https://parcelapp.net/help/api-view-deliveries.html
- The `requests` Python library (listed in `manifest.json` — installed automatically by HA)

---

## Installation

### HACS (Recommended)

1. Open HACS → **Integrations**
2. Click the three-dot menu → **Custom repositories**
3. Add this repo URL and select category **Integration**
4. Search for **Parcel App Delivery Tracker** and install
5. Restart Home Assistant

### Manual

1. Copy the `parcelapp/` folder into your `config/custom_components/` directory
2. Restart Home Assistant

---

## Setup

1. Go to **Settings → Devices & Services → Add Integration**
2. Search for **Parcel App**
3. Enter your **API key**
4. Choose a **filter mode**:
   - `recent` *(default)* — shows active and recently delivered packages
   - `active` — shows only packages currently in transit
5. Click **Submit**

---

## Sensor

### `sensor.parcel_deliveries`

| Property | Description |
|---|---|
| **State** | Number of deliveries returned by the API |
| **Icon** | `mdi:package-variant-closed` |
| **Unique ID** | `parcelapp_deliveries` |

### Attributes

Each delivery in the `deliveries` list contains:

| Attribute | Type | Description |
|---|---|---|
| `tracking_number` | string | The package tracking number |
| `carrier_code` | string | Carrier identifier (e.g. `ups`, `fedex`) |
| `description` | string | Custom label you set in Parcel App |
| `status_code` | string/int | Raw status code from the API |
| `date_expected` | string | Expected delivery date/time (ISO format) |
| `days_to_delivery` | int | Days until expected delivery (negative = past) |
| `latest_event` | string | Most recent tracking event text |
| `events` | list | Full event history array |
| `delivered` | bool | Whether the package is considered delivered |

---

## Delivered Detection Logic

The integration uses a multi-layered approach to determine if a package is delivered — avoiding common false positives from carrier event text like *"Your package will be delivered one business day later than expected."*

Rules applied in order:

1. If `date_expected` is in the future → **not delivered**
2. If `days_to_delivery >= 0` → **not delivered**
3. If the latest event contains phrases like `"out for delivery"`, `"will be delivered"`, `"delayed"` → **not delivered**
4. If the latest event **exactly matches** a known delivered phrase → **delivered**

Known delivered phrases include:
- `delivered`
- `package delivered`
- `delivered at front door`
- `delivered to mailbox`
- `left at front door`
- `left at porch`
- `left at residence`
- `delivered to agent`

---

## Services

### `parcelapp.refresh`

Force an immediate data refresh for all configured Parcel App entries.

```yaml
service: parcelapp.refresh
```

Useful in automations — for example, refreshing on-demand when you receive a carrier notification.

---

## Entities Created

| Entity | Type | Description |
|---|---|---|
| `sensor.parcel_deliveries` | Sensor | Delivery count + full attributes |
| `button.reload_parcel_app_integration` | Button | Reloads the integration on press |

---

## Update Interval

Data refreshes every **5 minutes** (300 seconds) by default. Use the `parcelapp.refresh` service or the reload button to trigger an immediate update.

---

## Example: Automation

Notify when a package is delivered:

```yaml
alias: Notify on delivery
trigger:
  - platform: template
    value_template: >
      {% set deliveries = state_attr('sensor.parcel_deliveries', 'deliveries') %}
      {{ deliveries | selectattr('delivered', 'equalto', true) | list | count > 0 }}
action:
  - service: notify.mobile_app
    data:
      message: "A package has been delivered!"
```

---

## File Structure

```
custom_components/parcelapp/
├── __init__.py          # Integration setup and service registration
├── coordinator.py       # Data fetching and delivered logic
├── sensor.py            # Sensor entity
├── button.py            # Reload button entity
├── config_flow.py       # UI-based configuration flow
├── const.py             # Constants (domain, API URL, defaults)
├── services.yaml        # Service definitions
├── manifest.json        # Integration metadata
└── icon.png             # Integration icon
```

---

## Troubleshooting

**No deliveries showing up**
- Confirm your API key is valid at https://parcelapp.net/help/api-view-deliveries.html
- Try switching filter mode to `recent` instead of `active`

**Packages incorrectly marked as delivered**
- Check the `latest_event` attribute value
- If the phrase isn't in the known delivered list in `coordinator.py`, it won't be marked delivered — this is by design to avoid false positives
- You can add custom phrases to `DELIVERED_EXACT_PHRASES` in `coordinator.py`

**Data is stale**
- Press the **Reload Parcel App Integration** button entity, or call `parcelapp.refresh`

---

## License

MIT — see [LICENSE](LICENSE) for details.
