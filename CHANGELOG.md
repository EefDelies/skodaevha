# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version number follows the `ennie_laadkosten` component (`custom_components/ennie_laadkosten/manifest.json`).

## [Unreleased]

### Added

- Kilometers card (desktop and mobile): kilometres driven this lease year split into private and business, each against the limit prorated over the days since the lease start, with schedule marker, year-end forecast and remaining km per week.
- `packages/ennie_kilometers.yaml`: helpers for limits, office round-trip distance, extra business km and lease start date; office-day counter driven by entering `zone.kantoor`; automatic reset on 1 January.
- Settings tiles for the kilometer limits, office round trip, extra business km, office-day counter and lease start date.
- Excess-kilometre charge: private kilometres above the prorated private limit (business kilometres are not charged) multiplied by an adjustable rate per km (`input_number.ennie_km_tarief_meerkm`), shown on the Kilometers card for now and for the year-end forecast (`sensor.ennie_km_bijbetalen`), with a settings tile for the rate.
- "Zakelijke rit toevoegen" input: enter the kilometres of a single business trip and an automation adds them to the yearly extra business total and resets the field; the total stays editable for corrections.

### Changed

- Settings: the employer compensation ("Vergoeding werkgever") tile now matches the other settings tiles instead of using a tile card with +/- buttons.

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
