# Ennie – smart EV charging for Home Assistant

A complete Home Assistant setup for a **Škoda Enyaq** charged by a **Zaptec Go 2** home charger on a **dynamic (hourly) electricity contract** in the Netherlands. It includes:

- **Smart charging** – charges automatically when the all-in electricity price is at or below your maximum, or when there is enough solar surplus to make charging worthwhile.
- **Charge limit** – stops at your chosen state of charge (home charging only).
- **Manual charging** – a one-tap override that ends by itself when the session is finished.
- **Charging cost administration** – a custom integration (`ennie_laadkosten`) that calculates the cost of every home-charged kWh for any period, with historical tariffs, free solar energy, and a PDF expense claim for your employer.
- **External charging** – detects charging away from home (office, public charger). External kWh are shown but never counted in costs, reimbursement or ERE.
- **Dashboard** – a dark-green dashboard with separate desktop and mobile layouts.

The dashboard and the entity names are in **Dutch**. The logic is specific to the Dutch market (energy tax, supplier surcharge, ERE certificates), but it can be adapted to other markets.

> Ennie is the name of the car. You will see it throughout the entity IDs (`ennie_*`).

## Requirements

| Component | Used for |
|---|---|
| Home Assistant (tested on 2026.11) | |
| [MySkoda](https://github.com/skodaconnect/homeassistant-myskoda) integration | battery, charging state, cable, location, doors and windows |
| [Zaptec](https://www.home-assistant.io/integrations/zaptec/) integration | charger mode, meter reading, start/stop |
| Nord Pool integration | hourly day-ahead prices |
| A P1 / smart meter integration | grid import/export, for the solar surplus |
| Frontend: [button-card](https://github.com/custom-cards/button-card), [card-mod](https://github.com/thomasloven/lovelace-card-mod), [expander-card](https://github.com/MelleD/lovelace-expander-card), [apexcharts-card](https://github.com/RomRider/apexcharts-card), datetime-picker-card | dashboard |

## Repository layout

```
custom_components/ennie_laadkosten/   charging cost integration (+ PDF claim)
packages/ennie_slim_laden.yaml        helpers, price/solar sensors, smart charging automations
packages/ennie_laadkosten.yaml        period helpers for the cost administration
dashboard/ennie-dashboard.yaml        the dashboard (raw configuration)
www/ennie/                            dashboard images
tests/test_calc.py                    tests for the cost calculation and the PDF
```

## Installation

1. **Packages** – enable packages in `configuration.yaml` if you have not already:

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

   Copy the files from `packages/` to `/config/packages/`.

2. **Integration** – copy `custom_components/ennie_laadkosten` to `/config/custom_components/` and add it to `configuration.yaml`:

   ```yaml
   ennie_laadkosten:
     # Optional: override the default entities (see const.py)
     meter: sensor.my_charger_meter_reading
     prijs: sensor.nord_pool_nl_current_price
     declaratie:
       naam: !secret ennie_declaratie_naam
       bron: !secret ennie_declaratie_bron           # e.g. "Zaptec Go 2 - serial ... - address"
       iban: !secret ennie_declaratie_iban
       rekeninghouder: !secret ennie_declaratie_rekeninghouder
   ```

   Every `declaratie` field is optional. Fields you leave empty are left out of the PDF. Keep personal data in `secrets.yaml`, never in the repository.

3. **Images** – copy `www/ennie/` to `/config/www/ennie/`.

4. **Dashboard** – create a new dashboard, open the raw configuration editor and paste the contents of `dashboard/ennie-dashboard.yaml`.

5. Check the configuration and restart Home Assistant.

## Adapting to your own installation

The entity IDs come from the author's installation. Replace them with your own (search and replace across `packages/` and the dashboard):

| In this repo | What it is |
|---|---|
| `sensor.oprit_zaptec_go2_*`, `switch.oprit_zaptec_go2_*`, `binary_sensor.oprit_zaptec_go2_*` | Zaptec charger entities ("oprit" is the charger name) |
| `sensor.skoda_enyaq_*`, `binary_sensor.skoda_enyaq_*`, `lock.…`, `climate.…`, `device_tracker.skoda_enyaq_skoda_enyaq` | MySkoda entities |
| `sensor.electricity_meter_energieverbruik` / `…_energieproductie` | P1 meter import/export power |
| `sensor.nord_pool_nl_huidige_prijs` | Nord Pool current price |

Zaptec actions target the charger with `device_id: "{{ device_id('sensor.oprit_zaptec_go2_opladermodus') }}"`, so renaming that sensor is enough.

## Settings

All tariffs are set on the dashboard (section *Instellingen*) and kept as history, so a change only affects the hours after it:

- **Energiebelasting** – energy tax per kWh (excl. VAT)
- **Inkoopvergoeding** – supplier surcharge per kWh (excl. VAT)
- **Vergoeding werkgever** – reimbursement per kWh from your employer
- **Maximale all-in prijs** – charge when the all-in price is at or below this
- **Maximaal laadpercentage** – charge limit for home charging

## Privacy and security

- Files in `/config/www/` are served under `/local/` **without authentication**. The PDF claims are stored in `/config/www/declaraties/` with a random suffix in the file name, so the URL cannot be guessed. Remove old claims you no longer need.
- Personal data for the claim (name, address, IBAN) belongs in `secrets.yaml`.

## Tests

```bash
python3 tests/test_calc.py
```

The tests cover the cost calculation (compared with the previous implementation over 200 random periods), solar energy, tariff history, employer reimbursement, external charging and the PDF output. They do not need Home Assistant.

## License

MIT – see [LICENSE](LICENSE).
