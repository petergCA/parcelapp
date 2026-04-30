# Parcel App Delivery Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant integration that pulls your active deliveries from [Parcel App](https://parcelapp.net) and exposes them as a sensor with full delivery detail attributes.

## Features

- Single `sensor.parcel_deliveries` entity — state is the count of active deliveries
- Full delivery attributes per package: tracking number, carrier, description, expected date, days to delivery, event timeline
- Robust delivered detection that avoids false positives (e.g. "will be delivered one business day later" is not treated as delivered)
- Configurable filter mode: `active` (in-transit only) or `recent` (includes recently delivered)
- Manual refresh via the `parcelapp.refresh` service call
- Polls automatically every 5 minutes

## Requirements

- [Parcel App](https://parcelapp.net) account with an API key
  *(In the Parcel App: Settings → Integrations → API)*

## Installation via HACS

1. In HACS, go to the three-dot menu → **Custom repositories**
2. Add `https://github.com/petergCA/parcelapp` with category **Integration**
3. Click **Install** on the Parcel App Delivery Tracker entry
4. Restart Home Assistant
5. Go to **Settings → Devices & Services → Add Integration** and search for **Parcel App**
6. Enter your API key and choose a filter mode

## Manual Installation

1. Download the [latest release](https://github.com/petergCA/parcelapp/releases/latest) and unzip
2. Copy the `parcelapp/` folder into `/config/custom_components/`
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration** and search for **Parcel App**
5. Enter your API key and choose a filter mode

## Configuration

| Option | Description | Default |
|---|---|---|
| `api_key` | Your Parcel App API key | required |
| `filter_mode` | `active` (in-transit only) or `recent` (includes delivered) | `recent` |

## Sensor Attributes

The `sensor.parcel_deliveries` state is the count of packages. The full data is in the `deliveries` attribute — a list of objects, one per package:

| Attribute | Type | Description |
|---|---|---|
| `tracking_number` | string | Carrier tracking number |
| `carrier_code` | string | Carrier identifier (e.g. `ups`, `usps`, `fedex`, `amzlus`) |
| `description` | string | Package description from Parcel App |
| `status_code` | string/int | Raw status code from the API |
| `date_expected` | string | Expected delivery date/time |
| `days_to_delivery` | int | Days until delivery (negative = past due, 0 = today) |
| `latest_event` | string | Most recent tracking event text |
| `events` | list | Full event timeline — each item has `event` and `description` |
| `delivered` | boolean | Whether the package is considered delivered |

### Example automation

```yaml
automation:
  - alias: "Notify when package delivered"
    trigger:
      - platform: template
        value_template: >
          {{ state_attr('sensor.parcel_deliveries', 'deliveries')
             | selectattr('delivered', 'eq', true) | list | count > 0 }}
    action:
      - service: notify.mobile_app
        data:
          message: "A package has been delivered!"
```

### Manual refresh

```yaml
service: parcelapp.refresh
```

## Usage with the ParcelApp Card

Install the companion [ParcelApp Card](https://github.com/petergCA/parcelapp_card) for a rich Lovelace dashboard UI with carrier icons, timeline, and tap-to-expand details.

```yaml
type: custom:parcelapp-card
entity: sensor.parcel_deliveries
```
