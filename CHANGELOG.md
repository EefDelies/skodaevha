# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).
The version number follows the `ennie_laadkosten` component (`custom_components/ennie_laadkosten/manifest.json`).

## [Unreleased]

## [2.3.0] - 2026-11-22

### Added

- Backup stop through the car: when the Zaptec is offline it charges on its own fallback current, outside Home Assistant's control. If Ennie then charges at home while it should not (maximum charge level reached, or no favourable price/sun and manual charging off), charging is stopped with the MySkoda `switch.skoda_enyaq_opladen` and a notification is sent. The switch is turned back on once the Zaptec is online again, the cable is unplugged or the car leaves home (`input_boolean.ennie_reserve_stop_actief` tracks whether Home Assistant set the stop).
- Business trip register (`todo.ennie_zakelijke_ritten`, a Local To-do list): each counted office day is added as "<km> km · Automatisch woon- werkverkeer". The "Zakelijke rit toevoegen" tile now opens one form for km, date and remark (`window.ennieRitPopup` in `www/ennie-dashboard.js`), handled by the new `script.ennie_zakelijke_rit_registreren`; trips dated in an earlier year are registered but not added to this year's total. New "Ritregister zakelijk" settings tile opens the list on a separate page (`ennie-ritten`). Editing the list does not change the km totals. A trip that is ticked off by accident is set back to open right away (`ennie_ritregister_vinkje_terugzetten`), so the register works as a log, not a to-do list.
- "Netto accucapaciteit" tile in the settings section (mobile and desktop), with an info popup, so the battery estimate works for other battery packs.
- Charger watchdog (`ennie_lader_bewaking`): when the car is home with the cable plugged in but the Zaptec reports "disconnected" for 5 minutes, send a notification and restart the Zaptec (at most once per 30 minutes; a second occurrence only notifies). Set `notify.mijn_telefoon` to your own phone.
- "Kantoor locatie" settings tile (`input_select.ennie_kantoor_zone`): pick the office zone from a list that is filled automatically with all zones; office days are counted when the car enters that zone. The choice survives restarts.
- `window.enniePopup(title, text)` in `www/ennie-dashboard.js`: a theme-aware info pop-up for short instructions behind an i-icon on dashboard tiles (on "Automatisch laden", "Handmatig laden", "Maximaal laadpercentage", "Maximale all-in prijs", "Effectieve laadprijs", "Zonne-overschot", "Benodigd overschot", "Laden met zon", the Kilometers card, the home/external split in Laadkosten and every tile in the settings section).
- Kilometers card (desktop and mobile): kilometres driven this lease year split into private and business, each against the limit prorated over the days since the lease start, with schedule marker, year-end forecast and remaining km per week.
- `packages/ennie_kilometers.yaml`: helpers for limits, office round-trip distance, extra business km and lease start date; office-day counter driven by entering the chosen office zone; automatic reset on 1 January.
- Settings tiles for the kilometer limits, office round trip, extra business km, office-day counter and lease start date.
- Excess-kilometre charge: private kilometres above the prorated private limit (business kilometres are not charged) multiplied by an adjustable rate per km (`input_number.ennie_km_tarief_meerkm`), shown on the Kilometers card for now and for the year-end forecast (`sensor.ennie_km_bijbetalen`), with a settings tile for the rate.
- "Zakelijke rit toevoegen" input: enter the kilometres of a single business trip and an automation adds them to the yearly extra business total and resets the field; the tile shows when a trip was last added; the total stays editable for corrections.

### Changed

- `www/ennie-pdf-button.js` renamed to `www/ennie-dashboard.js`, because it now holds more than the PDF button (info pop-ups, business trip form). Point your dashboard resource at `/local/ennie-dashboard.js?v=1`. The old file is kept as a small loader for the new one, so an existing `/local/ennie-pdf-button.js` resource keeps working.
- Kilometers card: "Op schema" renamed to "Budget tot vandaag" and "prognose" to "prognose 31 dec"; the info popup now explains the bar, the white marker, the forecast and the km-per-week figure.
- Settings section split into framed groups, like the Laadkosten period cards: "Kosten en vergoeding energie" (energy tax, purchase fee, employer kWh fee, private excess km rate), "Algemeen" (battery capacity, lease start) and "Kilometer registratie" (km limits, office location and return distance, add trip, extra business km, trip register, office days). On mobile the groups are stacked inside the Instellingen expander.
- Laadkosten home/external split: the note "extern geladen telt niet mee in kosten, vergoeding en ERE" moved from the tile into its info popup; the tile only shows the percentage split.
- Smart charging uses the Zaptec stop/resume button entities instead of the deprecated `zaptec.stop_charging` / `zaptec.resume_charging` actions.
- Hero card: at home, a plugged-in cable that the Zaptec does not see now shows "Lader ziet Ennie niet" instead of "Extern aangesloten".
- Settings: tiles renamed to "Inkoopvergoeding stroom" , "kWh-vergoeding werkgever" and "Tarief overschrijding privékilometers".
- Dashboard follows the Home Assistant light/dark mode: all colours on the main view are CSS variables (`--ec-*`) that keep the original dark palette in dark mode and switch to a light palette when the theme background is light (CSS relative colour syntax; older browsers keep the dark palette). The hero image card is unchanged; white text and the PDF button (`www/ennie-dashboard.js`) follow the palette too.
- Settings: the employer compensation ("Vergoeding werkgever") tile now matches the other settings tiles instead of using a tile card with +/- buttons.

### Fixed

- "Maximaal laadpercentage" and "Maximale all-in prijs" tiles: the title ran under the info icon, also on laptop-width screens; the title now keeps space free for the icon and wraps to a second line when needed.
- Settings tiles: on laptop-width screens long titles ran through the tile icon; titles now wrap within the space next to the icon.
- "Extra zakelijke km (totaal)" and "Ritregister zakelijk" tiles did not refresh after adding a trip until the page was reloaded; they now also update on `script.ennie_zakelijke_rit_registreren`.
- Charging overshot the maximum charge level when MySkoda sent no battery update for a long time (e.g. 96% instead of 90%). While charging at home, `sensor.ennie_accupercentage` is now estimated from the Zaptec session energy since the last MySkoda report; each new report resets the estimate. Set the net battery capacity with the new helper `input_number.ennie_accucapaciteit`; at 0 (the default after install) no estimate is made.
- "Resterende laadtijd" tile now shows the time to the dashboard maximum charge level (e.g. "1 u 22 min tot 90%"), scaled from the car's own estimate, which runs to the car's charge limit (usually 100%).
- "Benodigd overschot" tile shows the actual assumed charging power (`sensor.ennie_laadvermogen_aanname`: measured power while charging, otherwise 3 × 230 V × the Zaptec max current) instead of a fixed "11 kW".

## [2.2.0] - 2026-11-15

### Changed
- Dashboard: the *Effectieve laadprijs* tile now turns orange and shows "binnen marge" when the effective price is just above the maximum while `binary_sensor.ennie_zon_maakt_laden_gunstig` is still on (the 3% hysteresis band), instead of showing red while Ennie keeps charging on solar. The tile now also refreshes when that sensor changes.

### Fixed
- Dashboard: the *Laadadvies* tile said "Wachten op lagere prijs" while Ennie was charging on solar surplus. It now shows "Laden met zon gunstig" when `binary_sensor.ennie_zon_maakt_laden_gunstig` is on, and only falls back to comparing the grid all-in price with the maximum price otherwise.

## [2.1.0] - 2026-11-12

### Added
- First public release: Ennie dashboard, smart-charging and manual-charging packages, Nord Pool chart prices, ERE certificates and the `ennie_laadkosten` custom component with PDF expense claims.

[Unreleased]: https://github.com/EefDelies/skodaevha/compare/v2.3.0...HEAD
[2.3.0]: https://github.com/EefDelies/skodaevha/compare/v2.2.0...v2.3.0
[2.2.0]: https://github.com/EefDelies/skodaevha/compare/v2.1.0...v2.2.0
[2.1.0]: https://github.com/EefDelies/skodaevha/releases/tag/v2.1.0
