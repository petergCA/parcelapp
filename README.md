# Parcel App Delivery Tracker

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A Home Assistant integration that pulls your active deliveries from [Parcel App](https://parcelapp.net) and exposes them as a sensor with full delivery detail attributes.

## Features

- Single `sensor.parcel_deliveries` entity — state is the count of active deliveries
- Full delivery attributes: tracking number, carrier, description, expected date, days to delivery, events timeline
- Robust delivered detection (avoids false positives from phrases like "will be delivered one business day later")
- Manual refresh via `parcelapp.refresh` service
- Configurable filter mode: `active` (in-transit only) or `recent` (includes delivered)

## Requirements

- [Parcel App](https://parcelapp.net) account with an API key  
  *(Settings → Integrations → API in the Parcel App)*

## Installation via HACS

1. Add this repository as a **Custom Repository** in HACS (Category: Integration)
2. Install **Parcel App Delivery Tracker**
3. Restart Home Assistant
4. Go to **Settings → Devices & Services → Add Integration** and search for **Parcel App**
5. Enter your API key and choose a filter mode

## Configuration

| Option | Description | Default |
|---|---|---|
| `api_key` | Your Parcel App API key | required |
| `filter_mode` | `active` or `recent` | `recent` |

## Usage with the ParcelApp Card

Install the companion [ParcelApp Card](https://github.com/peterlgray/ha-parcelapp-card) for a rich Lovelace UI.

```yaml
type: custom:parcelapp-card
entity: sensor.parcel_deliveries
```
