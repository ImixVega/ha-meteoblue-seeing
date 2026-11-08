"""Parse meteoblue's publicly rendered astronomy seeing HTML table.

No browser, JavaScript engine, built-in HA Scrape integration, or external parser
package is needed. This parser intentionally reads only the main seeing table.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser
import re
from zoneinfo import ZoneInfo


class SeeingParseError(ValueError):
    """The downloaded page does not contain a usable seeing forecast."""


@dataclass(frozen=True)
class SeeingHour:
    """A single hour from the meteoblue forecast."""

    time: datetime
    is_night: bool
    cloud_low: int | None
    cloud_mid: int | None
    cloud_high: int | None
    seeing_arcsec: float | None
    seeing_1: int | None
    seeing_2: int | None
    jetstream: float | None
    badlayer_bottom: float | None
    badlayer_top: float | None
    badlayer_gradient: float | None
    temperature: float | None
    humidity: int | None

    def as_dict(self) -> dict:
        """Expose only small JSON-compatible values in sensor attributes."""
        return {
            "time": self.time.isoformat(),
            "night": self.is_night,
            "cloud_low": self.cloud_low,
            "cloud_mid": self.cloud_mid,
            "cloud_high": self.cloud_high,
            "seeing_arcsec": self.seeing_arcsec,
            "seeing_1": self.seeing_1,
            "seeing_2": self.seeing_2,
            "jetstream": self.jetstream,
            "badlayer_bottom": self.badlayer_bottom,
            "badlayer_top": self.badlayer_top,
            "badlayer_gradient": self.badlayer_gradient,
            "temperature": self.temperature,
            "humidity": self.humidity,
        }


@dataclass
class SeeingForecast:
    """Normalized downloaded forecast."""

    hours: list[SeeingHour]
    days: dict[date, dict[str, str | int]] = field(default_factory=dict)


def _numeric(value: str, *, integer: bool = False) -> float | int | None:
    """Extract one value, accepting spaces, narrow spaces and unit suffixes."""
    match = re.search(r"[-+]?\d+(?:[.,]\d+)?", value)
    if match is None:
        return None
    number = float(match.group(0).replace(",", "."))
    if integer:
        return int(number)
    return number


class _SeeingTableParser(HTMLParser):
    """Extract direct cells of main table, ignoring embedded planet tables."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.current_row: dict | None = None
        self.current_cell: list[str] | None = None
        self.current_cell_is_date = False
        self.rows: list[dict] = []
        self.dates: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if tag == "table":
            if self.depth:
                self.depth += 1
            elif "table-seeing" in classes:
                self.depth = 1
            return
        if self.depth != 1:
            return
        if tag == "tr":
            self.current_row = None
            if "hour-row" in classes and a.get("data-day") is not None and a.get("data-hour") is not None:
                try:
                    self.current_row = {
                        "day": int(a["data-day"]),
                        "hour": int(a["data-hour"]),
                        "night": "night" in classes,
                        "cells": [],
                    }
                except (TypeError, ValueError):
                    pass
        if tag in ("td", "th"):
            self.current_cell_is_date = "new-day" in classes
            if self.current_row is not None or self.current_cell_is_date:
                self.current_cell = []
            else:
                self.current_cell = None

    def handle_data(self, data: str) -> None:
        if self.depth == 1 and self.current_cell is not None:
            self.current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "table":
            if self.depth:
                self.depth -= 1
            return
        if self.depth != 1:
            return
        if tag in ("td", "th") and self.current_cell is not None:
            text = " ".join("".join(self.current_cell).split())
            if self.current_cell_is_date:
                self.dates.append(text)
            elif self.current_row is not None:
                self.current_row["cells"].append(text)
            self.current_cell = None
            self.current_cell_is_date = False
        if tag == "tr":
            if self.current_row is not None:
                if len(self.current_row["cells"]) >= 13:
                    self.rows.append(self.current_row)
                self.current_row = None


def parse_seeing_html(html: str, timezone: str) -> SeeingForecast:
    """Read the hourly table and associate data-day indices with local dates.

    The input must be an actual server-rendered astronomy-seeing page; a login
    page, blocked request, or an HTML redesign raises SeeingParseError.
    """
    parser = _SeeingTableParser()
    parser.feed(html)

    if not parser.dates or not parser.rows:
        raise SeeingParseError("Brak tabeli Astronomy Seeing w odpowiedzi serwera")

    try:
        tz = ZoneInfo(timezone)
    except (KeyError, ValueError) as err:
        raise SeeingParseError(f"Nieprawidłowa strefa czasowa: {timezone}") from err

    dates: list[date] = []
    metadata: dict[date, dict[str, str | int]] = {}
    for header in parser.dates:
        match = re.search(r"\d{4}-\d{2}-\d{2}", header)
        if match is None:
            continue
        try:
            current_date = date.fromisoformat(match.group(0))
        except ValueError:
            continue
        dates.append(current_date)
        info: dict[str, str | int] = {}
        for key in ("sunrise", "sunset", "moonrise", "moonset"):
            m = re.search(rf"\b{key}:\s*(\d{{2}}:\d{{2}})", header)
            if m:
                info[key] = m.group(1)
        m = re.search(r"\bmoonphase:\s*(\d+)%", header)
        if m:
            info["moonphase"] = int(m.group(1))
        metadata[current_date] = info

    if not dates:
        raise SeeingParseError("Nie udało się rozpoznać dat prognozy")

    entries: list[SeeingHour] = []
    for row in parser.rows:
        day_index = row["day"]
        hour = row["hour"]
        if day_index < 0 or day_index >= len(dates) or not 0 <= hour <= 23:
            continue
        c = row["cells"]
        # Column order from site: hour, 3x cloud, arcsec, 2x index,
        # jetstream, bad-layer bottom/top/gradient, ground temp/humidity.
        # The optional last column contains nested planet data; ignore it.
        seeing = _numeric(c[4])
        if seeing is None:
            continue
        entries.append(
            SeeingHour(
                time=datetime.combine(dates[day_index], datetime.min.time(), tzinfo=tz).replace(hour=hour),
                is_night=row["night"],
                cloud_low=_numeric(c[1], integer=True),
                cloud_mid=_numeric(c[2], integer=True),
                cloud_high=_numeric(c[3], integer=True),
                seeing_arcsec=seeing,
                seeing_1=_numeric(c[5], integer=True),
                seeing_2=_numeric(c[6], integer=True),
                jetstream=_numeric(c[7]),
                badlayer_bottom=_numeric(c[8]),
                badlayer_top=_numeric(c[9]),
                badlayer_gradient=_numeric(c[10]),
                temperature=_numeric(c[11]),
                humidity=_numeric(c[12], integer=True),
            )
        )

    entries.sort(key=lambda item: item.time)
    if len(entries) < 12:
        raise SeeingParseError(f"Zbyt mało odczytanych godzin prognozy: {len(entries)}")
    if len({r.time for r in entries}) != len(entries):
        raise SeeingParseError("Wykryto powielone daty i godziny w prognozie")
    return SeeingForecast(hours=entries, days=metadata)
