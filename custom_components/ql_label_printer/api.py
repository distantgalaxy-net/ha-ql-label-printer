"""Client for the QL Label Printer app's JSON API.

Date: 2026-11-10 01:00 GMT (updated; first written 2026-11-09 23:25 GMT)
Developer: Ash @ Distant Galaxy (distantgalaxy-net)

The label printer app (github.com/distantgalaxy-net/ql-label-printer) does
the real work: it lays out the label and sends it to the Brother printer.
This client only calls its API:
    GET  /api/options          app version (also proves the URL and password work)
    GET  /api/printer/status   is the printer ready, and which roll is loaded
    POST /api/print/<kind>     print a label (the app checks the printer first)
If the app has a password, it's sent as HTTP Basic auth.
"""
from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import AUTH_USERNAME, PRINT_TIMEOUT, STATE_OFFLINE, STATUS_TIMEOUT


class LabelPrinterError(Exception):
    """Base class for problems talking to the app."""


class CannotConnect(LabelPrinterError):
    """The app couldn't be reached (wrong address, app stopped, network)."""


class InvalidAuth(LabelPrinterError):
    """The app has a password and ours is missing or wrong."""


class PrintFailed(LabelPrinterError):
    """The app refused or couldn't print. str(error) is the app's own message,
    e.g. "Not printed: Printer cover open"."""

    def __init__(self, message: str, status: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status = status          # the printer's state, when that was the reason


class LabelPrinterClient:
    """Talks to one label printer app."""

    def __init__(self, session: aiohttp.ClientSession, url: str, password: str | None = None) -> None:
        """Remember the app's address (without a trailing slash) and password."""
        self._session = session
        self.url = url.rstrip("/")
        self._headers: dict[str, str] = {}
        if password:
            # Basic auth header made by hand, so every request carries it
            self._headers["Authorization"] = aiohttp.BasicAuth(AUTH_USERNAME, password).encode()

    async def _request(self, method: str, path: str, timeout: int, json: dict | None = None) -> tuple[int, dict]:
        """Make one request. Returns (HTTP status, JSON body).

        Raises CannotConnect if the app can't be reached or doesn't answer
        with JSON, and InvalidAuth if it asks for a password.
        """
        try:
            async with self._session.request(
                method, f"{self.url}{path}", json=json, headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status == 401:
                    raise InvalidAuth("The password is wrong, or the label printer app needs a password.")
                try:
                    body = await resp.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError) as exc:
                    raise CannotConnect(f"The address {self.url} doesn't seem to be the label printer app.") from exc
                return resp.status, body if isinstance(body, dict) else {}
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise CannotConnect(f"Home Assistant can't reach the label printer app at {self.url}. Check the app is running.") from exc

    async def get_version(self) -> str:
        """The app's version (e.g. "1.2.0"). Used to check the URL and password."""
        status, body = await self._request("GET", "/api/options", STATUS_TIMEOUT)
        if status != 200 or "models" not in body:
            raise CannotConnect(f"The address {self.url} doesn't seem to be the label printer app.")
        return str(body.get("version") or "unknown")

    async def get_status(self) -> dict[str, Any]:
        """The printer's state: {ok, state, message, media, source}.

        The app's "unavailable" (printer switched off or unreachable) is
        renamed "offline", because Home Assistant reserves "unavailable".
        """
        _, body = await self._request("GET", "/api/printer/status", STATUS_TIMEOUT)
        return normalise_status(body)

    async def print_label(self, kind: str, fields: dict[str, Any], copies: int = 1) -> str:
        """Print a label. Returns the app's message ("Label sent to printer").

        Raises PrintFailed with the app's message if it refused (e.g. the
        printer's cover is open) or the print didn't go through.
        """
        status, body = await self._request("POST", f"/api/print/{kind}", PRINT_TIMEOUT,
                                           json={**fields, "copies": copies})
        message = str(body.get("message") or "")
        if status == 200 and body.get("ok"):
            return message or "Label sent to printer"
        printer = normalise_status(body["printer"]) if isinstance(body.get("printer"), dict) else None
        raise PrintFailed(message or f"The label printer app couldn't print the label (error {status}).", printer)


def normalise_status(body: dict[str, Any]) -> dict[str, Any]:
    """Tidy a status reply from the app into the fields the entities use."""
    state = str(body.get("state") or "error")
    if state == "unavailable":
        state = STATE_OFFLINE
    return {
        "ok": bool(body.get("ok")),
        "state": state,
        "message": body.get("message") or "",
        "media": body.get("media"),
        "source": body.get("source"),
    }
