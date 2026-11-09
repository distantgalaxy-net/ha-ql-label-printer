"""Constants for the QL Label Printer integration.

Date: 2026-11-10 00:20 GMT (updated; first written 2026-11-09 23:25 GMT)
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

Shared names and settings: the integration's domain, config entry keys,
how often the printer is checked, the printer states the app reports and
the label types it can print.
"""
from datetime import timedelta

DOMAIN = "ql_label_printer"

# Config entry keys
CONF_URL = "url"                 # where the label printer app is, e.g. http://127.0.0.1:8013
CONF_PASSWORD = "password"       # the app's optional password (blank = none)
CONF_LINK_URL = "link_url"       # optional address for people to open the app in a browser

# The app runs on the same host as Home Assistant in the common setup
DEFAULT_URL = "http://127.0.0.1:8013"

# Username sent with the password (the app only checks the password)
AUTH_USERNAME = "homeassistant"

# How often to ask the app whether the printer is ready (same as the app's
# own page while all is well)
SCAN_INTERVAL = timedelta(seconds=60)

# Time limits for calls to the app, in seconds. A status check can take a
# few seconds (connection test, then SNMP); a print includes a status check
# and sending the label.
STATUS_TIMEOUT = 20
PRINT_TIMEOUT = 60

# Printer states, as reported by the app's GET /api/printer/status.
# The app calls a switched-off printer "unavailable"; Home Assistant uses
# that word for entities it can't read, so it's shown as "offline" here.
STATE_OFFLINE = "offline"
PRINTER_STATES = ["ready", "connected", "cover_open", "no_media", "wrong_media", "error", STATE_OFFLINE]

# Label types the app can print (POST /api/print/<kind>)
LABEL_KINDS = ["address", "food", "travel", "battery", "network"]

# Most copies the app will print in one go
MAX_COPIES = 20
