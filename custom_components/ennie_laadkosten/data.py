"""Statistieken ophalen via de recorder-API en de berekening uitvoeren."""
from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from zoneinfo import ZoneInfo

from homeassistant.components.recorder import get_instance
from homeassistant.components.recorder.statistics import statistics_during_period
from homeassistant.core import HomeAssistant

from .calc import Rates, calculate
from .const import END_HELPER, MAX_PLAUSIBLE_KW, START_HELPER, Settings

_LOGGER = logging.getLogger(__name__)

# Hoe ver terug we zoeken naar de laatste meterstand vóór de periode.
LOOKBACK = timedelta(days=14)


def read_period(hass: HomeAssistant) -> tuple[date, date]:
    first = hass.states.get(START_HELPER)
    last = hass.states.get(END_HELPER)
    if first is None or last is None:
        raise ValueError("Maak eerst beide input_datetime helpers aan")
    from_date = date.fromisoformat(first.state[:10])
    to_date = date.fromisoformat(last.state[:10])
    if from_date > to_date:
        raise ValueError("Begindatum ligt na einddatum")
    if (to_date - from_date).days > 1095:
        raise ValueError("Kies maximaal drie jaar")
    return from_date, to_date


def _helper_value(hass: HomeAssistant, entity_id: str) -> float:
    state = hass.states.get(entity_id)
    try:
        return float(state.state)  # type: ignore[union-attr]
    except (AttributeError, TypeError, ValueError) as exc:
        raise ValueError(f"{entity_id} heeft geen geldige waarde") from exc


def _rows(stats: dict, statistic_id: str, key: str, fallback: str | None = None) -> list[tuple[float, float]]:
    out = []
    for row in stats.get(statistic_id, []):
        value = row.get(key)
        if value is None and fallback:
            value = row.get(fallback)
        if value is None:
            continue
        start = row["start"]
        if isinstance(start, datetime):
            start = start.timestamp()
        out.append((float(start), float(value)))
    return out


async def async_calculate(hass: HomeAssistant, settings: Settings, from_date: date, to_date: date) -> dict:
    zone = ZoneInfo(hass.config.time_zone)
    start = datetime.combine(from_date, datetime.min.time(), zone)
    stop = datetime.combine(to_date + timedelta(days=1), datetime.min.time(), zone)

    # Meter: één uur extra aan het eind (rij met start = stop bevat de stand t/m stop)
    # en een stuk terug voor de laatste stand vóór de periode.
    stats = await get_instance(hass).async_add_executor_job(
        statistics_during_period,
        hass,
        start - LOOKBACK,
        stop + timedelta(hours=1),
        {
            settings.meter,
            settings.price,
            settings.solar,
            settings.extern,
            settings.tax_sensor,
            settings.surcharge_sensor,
            settings.employer_sensor,
        },
        "hour",
        None,
        {"state", "sum", "mean"},
    )

    start_ts, stop_ts = start.timestamp(), stop.timestamp()

    def in_period(rows):
        return [r for r in rows if start_ts - 3600 <= r[0] < stop_ts]

    meter = _rows(stats, settings.meter, "sum", fallback="state")
    before = [r for r in meter if r[0] < start_ts]
    meter = before[-1:] + [r for r in meter if start_ts <= r[0] <= stop_ts]
    prices = in_period(_rows(stats, settings.price, "mean"))
    solar = in_period(_rows(stats, settings.solar, "sum", fallback="state"))
    extern = in_period(_rows(stats, settings.extern, "sum", fallback="state"))

    # Tarief per uur uit de historie van de tarief-sensoren; voor uren zonder
    # historie (vóór de installatie) de huidige helperwaarde.
    tax_hist = {int(ts // 3600) * 3600: v for ts, v in in_period(_rows(stats, settings.tax_sensor, "mean"))}
    sur_hist = {int(ts // 3600) * 3600: v for ts, v in in_period(_rows(stats, settings.surcharge_sensor, "mean"))}
    emp_hist = {int(ts // 3600) * 3600: v for ts, v in in_period(_rows(stats, settings.employer_sensor, "mean"))}
    tax_now = _helper_value(hass, settings.tax_helper)
    sur_now = _helper_value(hass, settings.surcharge_helper)
    try:
        emp_now = _helper_value(hass, settings.employer_helper)
    except ValueError:
        emp_now = settings.employer_rate

    def rates_for(hour_ts: int) -> Rates:
        tax, sur, emp = tax_hist.get(hour_ts), sur_hist.get(hour_ts), emp_hist.get(hour_ts)
        source = "historie" if None not in (tax, sur, emp) else "helpers"
        return Rates(
            tax_now if tax is None else tax,
            sur_now if sur is None else sur,
            emp_now if emp is None else emp,
            source,
        )

    return await hass.async_add_executor_job(
        calculate,
        meter,
        prices,
        solar,
        extern,
        from_date,
        to_date,
        hass.config.time_zone,
        rates_for,
        settings.vat,
        MAX_PLAUSIBLE_KW,
    )
