# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version number follows the `ennie_laadkosten` component (`custom_components/ennie_laadkosten/manifest.json`).

## [Unreleased]

### Added

- Charger watchdog (`ennie_lader_bewaking`): when the car is home with the cable plugged in but the Zaptec reports "disconnected" for 5 minutes, send a notification and restart the Zaptec (at most once per 30 minutes; a second occurrence only notifies). Set `notify.mijn_telefoon` to your own phone.
- "Kantoor locatie" settings tile (`input_select.ennie_kantoor_zone`): pick the office zone from a list that is filled automatically with all zones; office days are counted when the car enters that zone. The choice survives restarts.
- `window.enniePopup(title, text)` in `www/ennie-pdf-button.js`: a theme-aware info pop-up for short instructions behind an i-icon on dashboard tiles (on "Automatisch laden", "Handmatig laden", "Maximaal laadpercentage", "Maximale all-in prijs", "Effectieve laadprijs", "Zonne-overschot", "Benodigd overschot", "Laden met zon" and the Kilometers card). Raise the resource to `?v=4`.
- Kilometers card (desktop and mobile): kilometres driven this lease year split into private and business, each against the limit prorated over the days since the lease start, with schedule marker, year-end forecast and remaining km per week.
- `packages/ennie_kilometers.yaml`: helpers for limits, office round-trip distance, extra business km and lease start date; office-day counter driven by entering the chosen office zone; automatic reset on 1 January.
- Settings tiles for the kilometer limits, office round trip, extra business km, office-day counter and lease start date.
- Excess-kilometre charge: private kilometres above the prorated private limit (business kilometres are not charged) multiplied by an adjustable rate per km (`input_number.ennie_km_tarief_meerkm`), shown on the Kilometers card for now and for the year-end forecast (`sensor.ennie_km_bijbetalen`), with a settings tile for the rate.
- "Zakelijke rit toevoegen" input: enter the kilometres of a single business trip and an automation adds them to the yearly extra business total and resets the field; the tile shows when a trip was last added; the total stays editable for corrections.

### Changed

- Smart charging uses the Zaptec stop/resume button entities instead of the deprecated `zaptec.stop_charging` / `zaptec.resume_charging` actions.
- Hero card: at home, a plugged-in cable that the Zaptec does not see now shows "Lader ziet Ennie niet" instead of "Extern aangesloten".
- Settings: tiles renamed to "Inkoopvergoeding stroom" , "kWh-vergoeding werkgever" and "Tarief overschrijding privékilometers".
- Dashboard follows the Home Assistant light/dark mode: all colours on the main view are CSS variables (`--ec-*`) that keep the original dark palette in dark mode and switch to a light palette when the theme background is light (CSS relative colour syntax; older browsers keep the dark palette). The hero image card is unchanged; white text and the PDF button (`www/ennie-pdf-button.js`) follow the palette too.
- Settings: the employer compensation ("Vergoeding werkgever") tile now matches the other settings tiles instead of using a tile card with +/- buttons.

### Fixed

- "Benodigd overschot" tile shows the actual assumed charging power (`sensor.ennie_laadvermogen_aanname`: measured power while charging, otherwise 3 × 230 V × the Zaptec max current) instead of a fixed "11 kW".

## [2.2.0] - 2026-11-15

### Changed
- Dashboard: the *Effectieve laadprijs* tile now turns orange and shows "binnen marge" when the effective price is just above the maximum while `binary_sensor.ennie_zon_maakt_laden_gunstig` is still on (the 3% hysteresis band), instead of showing red while Ennie keeps charging on solar. The tile now also refreshes when that sensor changes.

### Fixed
- Dashboard: the *Laadadvies* tile said "Wachten op lagere prijs" while Ennie was charging on solar surplus. It now shows "Laden met zon gunstig" when `binary_sensor.ennie_zon_maakt_laden_gunstig` is on, and only falls back to comparing the grid all-in price with the maximum price otherwise.

## [2.1.0] - 2026-11-12

### Added
- First public release: Ennie dashboard, smart-charging and manual-charging packages, Nord Pool chart prices, ERE certificates and the `ennie_laadkosten` custom component with PDF expense claims.

[Unreleased]: https://github.com/EefDelies/skodaevha/compare/v2.2.0...HEAD
[2.2.0]: https://github.com/EefDelies/skodaevha/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/EefDelies/skodaevha/releases/tag/v2.1.0
