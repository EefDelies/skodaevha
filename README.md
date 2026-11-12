# Smart EV charging for Home Assistant

A complete Home Assistant setup for a **Škoda Enyaq** charged by a **Zaptec Go 2** home charger on a **dynamic (hourly) electricity contract** in the Netherlands. It includes:

- **Smart charging** – charges automatically when the all-in electricity price is at or below your maximum, or when there is enough solar surplus to make charging worthwhile.
- **Charge limit** – stops at your chosen state of charge (home charging only).
- **Manual charging** – a one-tap override that ends by itself when the session is finished.
- **Charging cost administration** – a custom integration (`ennie_laadkosten`) that calculates the cost of every home-charged kWh for any period, with historical tariffs, free solar energy, and a PDF expense claim for your employer.
- **ERE certificates** – tracks the kWh charged at home, the number of ERE certificates and the expected net revenue (groen-laden.nl price, scraped daily).
- **External charging** – detects charging away from home (office, public charger). External kWh are shown but never counted in costs, reimbursement or ERE.
- **Dashboard** – a dark-green dashboard with separate desktop and mobile layouts.

The dashboard and the entity names are in **Dutch**. The logic is specific to the Dutch market (energy tax, supplier surcharge, ERE certificates), but it can be adapted to other markets.

> Ennie is the name of the car. You will see it throughout the entity IDs (`ennie_*`).

> **Note on the Škoda integration**
>
> Ennie is built on the custom [MySkoda](https://github.com/skodaconnect/homeassistant-myskoda) integration. That integration will be phased out soon. After that, this repository will be reworked to use the official Škoda integration in Home Assistant.
>
> For now that is not possible: the official integration is very limited and **read-only**. Ennie needs to control the car (lock, climate control, timers, flashing lights), and the official integration does not support that.

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
packages/ennie_handmatig_laden.yaml   manual charging toggle (script + auto-stop automation)
packages/ere_certificaten.yaml        ERE certificates and revenue estimate
packages/nord_pool_grafiekprijzen.yaml  today's and tomorrow's quarter-hour prices for the charts
dashboard/ennie-dashboard.yaml        the dashboard (raw configuration)
www/ennie/                            dashboard images
www/ennie-pdf-button.js               dashboard button that creates and opens the PDF claim
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

3. **Frontend files** – copy `www/ennie/` to `/config/www/ennie/` and `www/ennie-pdf-button.js` to `/config/www/`. Register the button as a dashboard resource (Settings → Dashboards → ⋮ → Resources): URL `/local/ennie-pdf-button.js?v=3`, type *JavaScript module*. Raise the `?v=` number whenever you update the file, otherwise browsers keep the old version.

4. **Dashboard** – create a new dashboard, open the raw configuration editor and paste the contents of `dashboard/ennie-dashboard.yaml`.

5. Check the configuration and restart Home Assistant.

## Adapting to your own installation

The entity IDs come from the author's installation. Replace them with your own (search and replace across `packages/` and the dashboard):

| In this repo | What it is |
|---|---|
| `sensor.oprit_zaptec_go2_*`, `switch.oprit_zaptec_go2_*`, `binary_sensor.oprit_zaptec_go2_*` | Zaptec charger entities ("oprit" is the charger name) |
| `sensor.skoda_enyaq_*`, `binary_sensor.skoda_enyaq_*`, `lock.…`, `climate.…`, `device_tracker.skoda_enyaq_skoda_enyaq` | MySkoda entities |
| `sensor.electricity_meter_energieverbruik` / `…_energieproductie` | P1 meter import/export power |
| `sensor.nord_pool_nl_huidige_prijs` | Nord Pool current price (also used to find the Nord Pool config entry) |

Zaptec actions target the charger with `device_id: "{{ device_id('sensor.oprit_zaptec_go2_opladermodus') }}"`, so renaming that sensor is enough.

## How smart charging works

Smart charging only acts when **Automatisch laden** is on, and only on the home charger. It never charges more than the charge limit.

### 1. The all-in price

Nord Pool publishes day-ahead prices per quarter hour. `sensor.ennie_beursprijs_uurgemiddelde` takes the average of the four quarters of the current hour (the price NextEnergy bills). If one of the four is missing, the sensor is unavailable and nothing happens.

The all-in price adds the supplier surcharge and energy tax, then VAT:

```
all-in = (market price + inkoopvergoeding + energiebelasting) × 1.21
```

`binary_sensor.ennie_prijs_gunstig` is on when the all-in price is at or below **Maximale all-in prijs**.

### 2. Solar surplus

When the price is too high, solar power can still make charging worthwhile: surplus that would otherwise be exported is treated as free.

- **Surplus** (`sensor.ennie_zonne_overschot`) = export − import from the P1 meter, plus the measured charging power while charging. That is the power that would be exported if the car were not charging.
- When charging starts, the Zaptec power arrives through the cloud and the P1 meter lags by about 30 seconds. For the first 2 minutes, or until the charger reports more than 1 kW, the sensor keeps its previous value. This prevents a "phantom surplus" at plug-in.
- The surplus is averaged over 10 minutes (time-weighted) to smooth out passing clouds.

The **effective charging price** is the all-in price for the part that does not come from the sun:

```
effective price = all-in × (charging power − surplus) / charging power
```

Charging power is the measured Zaptec power while charging, otherwise the nominal 3 × 230 V × max current (11 kW at 16 A). The dashboard also shows the **required surplus**: how much solar power is needed to bring the effective price down to your maximum.

`binary_sensor.ennie_zon_maakt_laden_gunstig` turns on when the effective price is at or below the maximum and both the current and the average surplus are at least 0.3 kW. It stays on until the effective price rises more than 3% above the maximum (hysteresis), so a single cloud does not stop the session.

### 3. The decision

`binary_sensor.ennie_laden_toegestaan` is on when the price is favourable **or** the sun makes charging favourable. The automation *Ennie - Dynamisch laden* runs every 5 minutes and whenever one of its inputs changes:

- **Stop** – charging is no longer allowed and the Zaptec is charging → stop the session. Stopping only needs the Zaptec status, because the car reports its cable state minutes late.
- **Start** – charging is allowed, the car is plugged into the home charger, the car data is less than 30 minutes old, the battery is below the charge limit and the Zaptec is waiting → resume charging. Up to 3 attempts; if the Zaptec still does not start, you get a notification.
- Without valid price data nothing happens: unknown prices never start or stop a session.

### 4. Charge limit

*Ennie - Laadlimiet bewaken* checks every minute and on every change. When the battery reaches **Maximaal laadpercentage** it stops the session, in automatic and manual mode alike. A limit of 0% means: do not charge at all.

### 5. Manual charging

**Handmatig laden** charges right away, regardless of price, but still up to the charge limit. It switches automatic charging off for the duration and restores the previous mode afterwards. The manual mode ends by itself when the cable is unplugged (after 1 minute) or the Zaptec reports *finished* for 5 minutes.

### 6. Charging away from home

`sensor.ennie_laadlocatie` is `thuis` when the Zaptec charges (or the car charges at home), `extern` when the car charges anywhere else. External charging is shown on the dashboard and counted in kWh, but price control, the charge limit, costs, reimbursement and ERE ignore it.

## ERE certificates

After the first start, set these helpers once (they keep their value):

- `input_number.ere_hernieuwbaar_aandeel` – renewable share published by the NEa (50.5 % for 2026; check every year)
- `input_number.ere_meterstand_begin_periode` – charger meter reading at the start of the period
- `input_datetime.ere_begin_periode` – start date of the period

`input_number.ere_prijs` is filled daily from groen-laden.nl. A new period starts automatically on 1 January.

## Settings

All tariffs are set on the dashboard (section *Instellingen*) and kept as history, so a change only affects the hours after it:

- **Energiebelasting** – energy tax per kWh (excl. VAT)
- **Inkoopvergoeding** – supplier surcharge per kWh (excl. VAT)
- **Vergoeding werkgever** – reimbursement per kWh from your employer
- **Maximale all-in prijs** – charge when the all-in price is at or below this
- **Maximaal laadpercentage** – charge limit for home charging

## Privacy and security

- Files in `/config/www/` are served under `/local/` **without authentication**. The PDF claims are stored in `/config/www/declaraties/` with a random suffix in the file name, so the URL cannot be guessed. Remove old claims you no longer need.
- The PDF button gets the file URL from the `ennie_laadkosten.maak_declaratie` service response, so it keeps working with the random file names.
- Personal data for the claim (name, address, IBAN) belongs in `secrets.yaml`.

## Tests

```bash
python3 tests/test_calc.py
```

The tests cover the cost calculation (compared with the previous implementation over 200 random periods), solar energy, tariff history, employer reimbursement, external charging and the PDF output. They do not need Home Assistant.

## License

MIT – see [LICENSE](LICENSE).
