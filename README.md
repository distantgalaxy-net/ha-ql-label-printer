# QL Label Printer for Home Assistant

Print labels on a Brother QL label printer from Home Assistant, and see
whether the printer is ready.

_Updated: 2026-11-09 23:55 GMT · Developer: Ash @ Distant Galaxy (distantgalaxy-net)_

This integration connects Home Assistant to the
[QL Label Printer app](https://github.com/distantgalaxy-net/ql-label-printer),
a small self-hosted service that lays out and prints labels on a
network-connected Brother QL printer. The app does the printing; this
integration lets Home Assistant use it.

> Working on the code? Read the [development guide](docs/DEVELOPMENT.md) first.

## What you get

- **Printer status sensor:** *Ready*, *Cover open*, *Label spool finished*,
  *Wrong roll fitted*, *Offline*, *Error*, or *Connected (status not
  reported)* for printers that don't report their state. Checked every
  minute.
- **Loaded roll sensor:** e.g. *62mm continuous*.
- **Printer problem binary sensor:** on while the printer can't print, for
  notifications and automations.
- **Print actions** with proper fields in Home Assistant's action editor:
  - **Print address label:** name, address, icon.
  - **Print battery label:** device, battery type, date changed.
  - **Print food label:** freezer/fridge/cupboard, use-by, cooking instructions.
  - **Print network label:** name, IP address, VLAN, MAC address.
  - **Print any label:** any label type, with its fields as a dictionary.

  If the printer can't print (for example the cover is open), the action
  fails with that reason instead of failing silently.

Everything appears in Home Assistant's own screens (setup, device page,
action editor and dashboards), so it follows your theme.

## Requirements

- The [QL Label Printer app](https://github.com/distantgalaxy-net/ql-label-printer)
  **1.2.0 or later**, set up and printing.
- Home Assistant **2025.2** or later (**2026.3** or later to show this
  integration's own icon).
- Home Assistant must be able to reach the app. If Home Assistant runs on
  the same host as the app, `http://127.0.0.1:8013` usually works. Otherwise
  use the address you open the app at.

## Installation

### Marketplace (recommended)

1. In Home Assistant, open **Settings → Marketplace**.
2. Choose **Add from link** and paste
   `https://github.com/distantgalaxy-net/ha-ql-label-printer` (category:
   **Integration**).
3. Install **QL Label Printer**, then restart Home Assistant.

### Manual

Copy the `custom_components/ql_label_printer` folder into your Home
Assistant configuration's `custom_components` folder, then restart Home
Assistant.

## Setup

**Settings → Devices & services → Add integration → QL Label Printer.**
Enter:

- **App address:** e.g. `http://127.0.0.1:8013` or `https://labels.home.example`.
- **Password:** only if you set one in the app's Settings tab.

It checks it can connect before saving. To change the address or password
later, open the integration's **⋮** menu → **Reconfigure**. If the app's
password changes, Home Assistant asks for the new one.

## Using the print actions

In an automation, script or **Developer tools → Actions**:

```yaml
action: ql_label_printer.print_battery
data:
  device: Hallway motion sensor
  battery: CR2032
```

```yaml
action: ql_label_printer.print_address
data:
  name: Alex Example
  address: |
    1 High Street
    Anytown
    AB1 2CD
  icon: birthday
  copies: 2
```

```yaml
action: ql_label_printer.print_food
data:
  title: Beef chilli
  storage: frozen
  shelf: 3
  shelf_unit: months
  method: from_frozen
  minutes: 40
  temp: 180
```

```yaml
action: ql_label_printer.print_label
data:
  kind: travel
  fields:
    name: Alex Example
    legs:
      - { date: "2027-03-01", flight: "XX 0123", from: AAA, to: BBB, dep: "0900", arr: "1130" }
```

- **Dates** default to today, in the time zone set in the app.
- **Temperatures** use the unit chosen in the app's Settings (°C or °F).
- **Icons:** any built-in icon (gift, birthday, christmas, celebration,
  heart, star, balloon, wedding, new home, get well, good luck, horseshoe,
  flowers, snowman, snowflake, fireworks, sunshine, car) or one you
  uploaded in the app.
- **Response:** each action returns `{"ok": true, "message": "Label sent to
  printer"}` if you ask for a response (`response_variable` in a script).
- **More than one label printer:** add `config_entry_id` to choose which.

## Example automations

**Tell me when the printer needs attention**

```yaml
triggers:
  - trigger: state
    entity_id: binary_sensor.ql_label_printer_printer_problem
    to: "on"
    for: { minutes: 5 }
actions:
  - action: notify.notify
    data:
      message: "Label printer: {{ state_attr('sensor.ql_label_printer_printer_status', 'message') }}"
```

**Print a battery label when you record a battery change**

If you use the [Battery Notes](https://github.com/andrew-codechimp/HA-Battery-Notes)
integration, it fires an event when a battery is marked as replaced. Check
Battery Notes' documentation for the event's exact fields.

```yaml
triggers:
  - trigger: event
    event_type: battery_notes_battery_replaced
actions:
  - action: ql_label_printer.print_battery
    data:
      device: "{{ trigger.event.data.device_name }}"
      battery: "{{ trigger.event.data.battery_type }}"
```

Entity IDs depend on the device's name in your Home Assistant. Check
yours on the device page.

## Troubleshooting

| Problem | What to check |
|---|---|
| Setup says it can't reach the app | The address, and that Home Assistant can reach that host and port. An app published only on `127.0.0.1` is reachable only from the same host. |
| Setup says the password is wrong | The password set in the app's **Settings → Password**. |
| Status always *Connected (status not reported)* | The printer isn't answering status checks. See the app's README: it needs SNMP, and UDP 161 open to the printer. |
| An action fails with *Not printed: …* | The app checked the printer first and found a problem (the reason is in the message). Fix it, then try again. |

## Licence

[MIT](LICENSE). The QL Label Printer app itself is licensed separately
(GPL v3).
