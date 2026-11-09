# Development guide – QL Label Printer for Home Assistant

Read this before changing the code. It explains what this integration is,
the decisions already made and the constraints that aren't obvious from
the code.

_Last updated: 2026-11-09 23:55 GMT · Owner: Ash @ Distant Galaxy (distantgalaxy-net)_

---

## What this is

A Home Assistant custom integration (installed through the **Marketplace**,
formerly HACS) for the
[QL Label Printer app](https://github.com/distantgalaxy-net/ql-label-printer).
The app lays out labels and prints them on a network Brother QL printer;
this integration only calls the app's JSON API. It never talks to the
printer itself.

**This repo is public. Never commit personal data** – no real names,
addresses, phone numbers, IP addresses, host names, network names or
domain names, including in examples, tests, docs and commit messages. Use
generic examples ("Alex Example", `192.168.1.20`, `labels.home.example`,
`labels.test`).

## Current state

- **Config flow:** app URL + optional password, checked against
  `GET /api/options`; reconfigure; reauth when the password changes.
  Unique ID = the URL in lower case.
- **Coordinator:** `GET /api/printer/status` every 60 s.
- **Entities** (one device per app):
  - Printer status: enum sensor, with the app's message as an attribute.
  - Loaded roll: sensor.
  - Printer problem: binary sensor, device class problem.
- **Actions** (registered in `async_setup`, with an optional
  `config_entry_id`):
  - `print_address`, `print_battery`, `print_food`, `print_network`:
    typed fields.
  - `print_label`: any kind, fields given as a dictionary.

  Each one posts to `/api/print/<kind>` and returns `{ok, message}`. A
  refused print raises `HomeAssistantError` with the app's message.
- **Brand images** in `custom_components/ql_label_printer/brand/` (HA
  2026.3+ serves them; older versions show a placeholder).

## Constraints

- **Native look only.** No custom panels, cards or frontend code: setup,
  device page, entities and actions all use Home Assistant's own UI, so it
  looks built in and follows the user's theme. Text reads like Home
  Assistant's own (sentence case, plain English).
- **The app does the work.** Label layout, printer checks and printing stay
  in the app; this integration just passes fields through. New label
  fields need no change here except, for the typed actions, adding the
  field to `ACTIONS` in `__init__.py`, `services.yaml` and
  `translations/en.json`.
- **"unavailable" is reserved** by Home Assistant, so the app's
  `unavailable` printer state is shown as `offline`.
- **Minimum Home Assistant:** 2025.2 (`AddConfigEntryEntitiesCallback`).
  Keep `hacs.json` in step.
- **No requirements:** only Home Assistant's own libraries (aiohttp,
  voluptuous).
- **Brand images:** original artwork only. Never Home Assistant's branding
  or a printer maker's logo. Square PNG, transparent, trimmed, 256 and 512
  px, with `dark_` versions.

## Code layout

```
custom_components/ql_label_printer/
  __init__.py       setup, unload, the print actions
  api.py            client for the app's API (Basic auth if a password is set)
  config_flow.py    setup / reconfigure / reauth screens
  coordinator.py    once-a-minute status check, runtime data type
  entity.py         shared device info for the entities
  sensor.py         printer status + loaded roll
  binary_sensor.py  printer problem
  const.py          names, timings, states
  services.yaml     action fields and selectors
  translations/en.json  all user-facing text
  icons.json        entity and action icons
  manifest.json     integration metadata (version!)
  brand/            icon.png, icon@2x.png, dark_ versions
hacs.json           Marketplace metadata
tests/              pytest-homeassistant-custom-component tests
.github/workflows/validate.yml   tests, hassfest, Marketplace validation
```

## Coding conventions

- **Comments:** every function gets a docstring, and there are enough
  comments to follow the options and logic.
- **Header block** at the top of every code file: date and time written,
  `Developer: Ash @ Distant Galaxy (distantgalaxy-net)`. Update the date
  whenever you change a file. JSON files can't hold comments, so they have
  no header.
- **UK English**, plain wording.
- **Work on a branch** and open a pull request; don't commit straight to
  `main`.
- **Licence:** MIT (`LICENSE`).

## Versions

- The version is in `custom_components/ql_label_printer/manifest.json`
  (`"version"`).
- **Test builds:** add one to the last number for each set of changes
  pushed for testing (0.1.0 → 0.1.1 …).
- **Releases:** the owner decides minor or major. Set the manifest version
  (e.g. `1.0.0`), merge, then publish a GitHub release tagged `v1.0.0`. The
  Marketplace offers releases to users.

## Testing

```bash
python -m venv .venv && .venv/bin/pip install -r requirements_test.txt
```

```bash
.venv/bin/pytest
```

Tests fake the app with `aioclient_mock`. GitHub runs them on every pull
request, together with Home Assistant's `hassfest` and the Marketplace
(HACS) validation.

## Decisions log

- 2026-11-09 – Separate repo from the app, so the integration has its own
  releases and the Marketplace sees one integration per repo. MIT licence
  (it doesn't include the app's GPL printing library).
- 2026-11-09 – Integration rather than YAML blueprints: setup in the UI,
  status entities, typed print actions with readable errors.
- 2026-11-09 – Domain `ql_label_printer` (specific enough not to clash
  with any future core integration).
- 2026-11-09 – Own brand icon in `brand/` (HA 2026.3+), so it doesn't
  show a placeholder like a "budget add-on".
