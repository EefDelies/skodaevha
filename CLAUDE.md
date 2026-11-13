# Working on this repository

This repo is the public copy of the "Ennie" Home Assistant setup (dashboard, packages,
`ennie_laadkosten` component). The live version runs in the author's Home Assistant;
this repo must be kept in sync with it.

## After every change in Home Assistant

Whenever the Ennie dashboard (`dashboard-ennie2-2`), an Ennie package, the
`ennie_laadkosten` component or the frontend files are changed in Home Assistant:

1. Apply the same change to the matching file here:
   - dashboard → `dashboard/ennie-dashboard.yaml` (the exported raw dashboard config)
   - packages → `packages/*.yaml`
   - component → `custom_components/ennie_laadkosten/`
2. Keep personal data out: no IBAN, address, names, tokens or IP addresses.
   Personal claim data belongs in `secrets.yaml` (see README).
3. Add an entry under `## [Unreleased]` in `CHANGELOG.md`
   (sections: Added / Changed / Fixed / Removed), written in English.
4. Validate YAML (`python3 -c "import yaml; yaml.safe_load(open('<file>'))"`)
   and run `python3 tests/test_calc.py` when the component changed.
5. Commit with a short English message and push to `main`.

## Releases

Releases are automatic: `.github/workflows/weekly-release.yml` runs every Sunday
at 19:00 (Amsterdam) and, only when `[Unreleased]` has entries, runs the tests,
moves the entries to a new version heading, bumps the version in
`custom_components/ennie_laadkosten/manifest.json`, tags `vX.Y.Z` and publishes a
GitHub release with the changelog section as notes. It can also be started by
hand from the Actions tab ("Run workflow").

- Only "Fixed" entries -> patch (x.y.Z); anything else -> minor (x.Y.0)
- Major (X.0.0) is never automatic: for changes that need users to adapt their
  config, make that release by hand.

So: never edit version numbers or release headings yourself — just add entries
under `[Unreleased]`.

README is in English; dashboard texts stay in Dutch.
