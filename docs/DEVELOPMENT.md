# Development guide – QL Label Printer for Home Assistant

Read this before changing the code. It explains what this integration is,
the decisions already made and the constraints that aren't obvious from
the code.

_Last updated: 2026-11-10 08:30 GMT · Owner: Ash @ Distant Galaxy (distantgalaxy-net)_

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
  `GET /api/options`, plus an optional "address to open in a browser"
  (`link_url`) for the device page's Visit link (falls back to the app URL);
  reconfigure; reauth when the password changes. Unique ID = the app URL in
  lower case.
- **Coordinator:** `GET /api/printer/status` every 60 s.
- **Entities** (one device per app):
  - Printer status: enum sensor, with the app's message as an attribute.
  - Loaded roll: sensor.
  - Ready to print: binary sensor, Yes/No (on = ready). It replaced a
    "Printer problem" sensor, whose standard "OK / Problem" wording read
    ambiguously.
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
  Assistant's own (sentence case, plain English). All user-facing text is in
  `translations/en.json`. Write it for people, not developers: short
  sentences that say what to do, with no "e.g." or jargon (follow the
  Distant Galaxy voice: plain UK English, speak to the reader as "you").
- **The app does the work.** Label layout, printer checks and printing stay
  in the app; this integration just passes fields through. New label
  fields need no change here except, for the typed actions, adding the
  field to `ACTIONS` in `__init__.py`, `services.yaml` and
  `translations/en.json`.
- **"unavailable" is reserved** by Home Assistant, so the app's
  `unavailable` printer state is shown as `offline`.
- **Minimum Home Assistant:** 2025.2 (`AddConfigEntryEntitiesCallback`).
  Keep `hacs.json` in step.
- **Category:** `computers_network.printers` in the manifest (Home
  Assistant's integration categories; shows it under Computers & network →
  Printers).
- **Help text and URLs:** hassfest rejects web addresses with a domain name
  (e.g. `https://…example`) in `translations/en.json`; pass them as
  description placeholders instead. IP addresses like `http://127.0.0.1:8013`
  are allowed.
- **No requirements:** only Home Assistant's own libraries (aiohttp,
  voluptuous).
- **Brand images:** original artwork only. Never Home Assistant's branding,
  a printer maker's logo, or the Distant Galaxy Pinwheel itself (the brand
  guide says the mark is never redrawn). The icon follows the Distant
  Galaxy brand guidelines (v1.0):
  - flat colours, no gradients, rounded corners;
  - Signal Blue `#1B7CB6` body, Nebula Teal `#12847C` band;
  - Ink `#0D2C54` / `#4A5468` text lines on a white label;
  - a Burnt Orange `#CD4C18` button on the printer as the only orange
    (the nod to the mark, whose core is the one orange element).

  Square PNG, transparent, trimmed, 256 and 512 px. The `dark_` versions
  drop the label's outline (#6B7A90), which is only needed on white.

## Code layout

```
custom_components/ql_label_printer/
  __init__.py       setup, unload, the print actions
  api.py            client for the app's API (Basic auth if a password is set)
  config_flow.py    setup / reconfigure / reauth screens
  coordinator.py    once-a-minute status check, runtime data type
  entity.py         shared device info for the entities
  sensor.py         printer status + loaded roll
  binary_sensor.py  ready to print (Yes/No)
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
- Released so far: v0.2.0, v0.2.1.

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
- 2026-11-10 – Separate browser link address: on the same host the app
  is best reached at http://127.0.0.1:8013, which is useless as a link.
- 2026-11-09 – Own brand icon in `brand/` (HA 2026.3+), so it doesn't
  show a placeholder like a "budget add-on". Drawn in the Distant Galaxy
  Signal palette with an orange printer button as the brand nod (an
  earlier loose "distant star" dot was dropped as looking random).
- 2026-11-11 – `print_food` gains `appliance` (oven, air fryer, microwave,
  hob) and `watts`, matching app 1.2.9. Both are optional, so automations
  written for 0.1.5 keep printing the same label (0.1.6).
  Also in 0.1.6: `print_address` gains `note` and `note_align`, and the
  travel label type is now `luggage`, matching app 1.2.10 (no `travel`
  alias: nothing was using it). No dedicated luggage action: a list of flights is awkward in
  an action form, and `print_label` covers it.
- 2026-11-11 – v0.2.0 (first release): everything up to 0.1.6. Needs app
  1.3.0 or later.
- 2026-11-11 – v0.2.1: the Marketplace checks now run in full (the
  "brands" check passes with the icon in `brand/`), as the Marketplace
  requires before adding a repository to its default list.
