# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version number follows the `ennie_laadkosten` component (`custom_components/ennie_laadkosten/manifest.json`).

## [Unreleased]

### Changed
- Dashboard: the *Effectieve laadprijs* tile now turns orange and shows "binnen marge" when the effective price is just above the maximum while `binary_sensor.ennie_zon_maakt_laden_gunstig` is still on (the 3% hysteresis band), instead of showing red while Ennie keeps charging on solar. The tile now also refreshes when that sensor changes.

### Fixed
- Dashboard: the *Laadadvies* tile said "Wachten op lagere prijs" while Ennie was charging on solar surplus. It now shows "Laden met zon gunstig" when `binary_sensor.ennie_zon_maakt_laden_gunstig` is on, and only falls back to comparing the grid all-in price with the maximum price otherwise.

## [2.1.0] - 2026-11-12

### Added
- First public release: Ennie dashboard, smart-charging and manual-charging packages, Nord Pool chart prices, ERE certificates and the `ennie_laadkosten` custom component with PDF expense claims.

[Unreleased]: https://github.com/EefDelies/skodaevha/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/EefDelies/skodaevha/releases/tag/v2.1.0
