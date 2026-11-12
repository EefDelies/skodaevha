"""Rekenkern voor Ennie laadkosten (zonder Home Assistant-afhankelijkheden).

Invoer zijn uurstatistieken uit de recorder:
- meter: oplopende Zaptec-meterstand. Een rij met start H bevat de stand die
  de Zaptec om ~H:00:10 meldt, d.w.z. de energie t/m H. Het verschil tussen
  rij H en rij H+1 is dus de energie in het uur [H, H+1).
- prijs: gemiddelde kale beursprijs per uur (rij met start H = uur [H, H+1)).
- tarieven: rates_for(uur) geeft energiebelasting en inkoopvergoeding (excl.
  btw) die in dat uur golden.
- extern: oplopende extern geladen energie (zelfde opbouw als zon); alleen
  getoond, nooit in kosten of vergoeding.
- zon: oplopende zonne-laadenergie (integratiesensor). Een rij met start H
  bevat de stand aan het einde van dat uur, dus zon in [H, H+1) is
  rij H - rij H-1.

Ontbrekende meteruren worden gelijkmatig over de tussenliggende uren
verdeeld; dat deel is een schatting.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Callable
from zoneinfo import ZoneInfo

HOUR = 3600


@dataclass(frozen=True)
class Rates:
    energiebelasting: float
    inkoopvergoeding: float
    vergoeding: float  # werkgeversvergoeding per kWh
    bron: str  # "historie" of "helpers"


def _money(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def _hour(ts: float) -> int:
    return int(ts // HOUR) * HOUR


def calculate(
    meter_rows: list[tuple[float, float]],
    price_rows: list[tuple[float, float]],
    solar_rows: list[tuple[float, float]],
    extern_rows: list[tuple[float, float]],
    from_date: date,
    to_date: date,
    tz_name: str,
    rates_for: Callable[[int], Rates],
    vat: float,
    max_kw: float,
) -> dict:
    zone = ZoneInfo(tz_name)
    start_ts = datetime.combine(from_date, datetime.min.time(), zone).timestamp()
    stop_ts = datetime.combine(to_date, datetime.max.time(), zone).timestamp() + 1e-6

    def local_day(ts: float) -> date:
        return datetime.fromtimestamp(ts, timezone.utc).astimezone(zone).date()

    # 1. Energie per uur uit de meterstanden.
    energy: dict[int, float] = defaultdict(float)
    estimated: dict[int, float] = defaultdict(float)
    gaps = intervals = 0
    ignored_kwh = 0.0
    rows = sorted(meter_rows)
    for (prev_ts, prev_val), (ts, val) in zip(rows, rows[1:]):
        duration = ts - prev_ts
        delta = val - prev_val
        if duration <= 0 or delta <= 0:
            continue
        if delta / (duration / HOUR) > max_kw:
            ignored_kwh += delta
            continue
        overlap_start, overlap_stop = max(prev_ts, start_ts), min(ts, stop_ts)
        if overlap_stop <= overlap_start:
            continue
        is_gap = duration > HOUR + 2
        gaps += is_gap
        rate = delta / duration
        cursor = overlap_start
        while cursor < overlap_stop - 1e-4:
            h = _hour(cursor)
            nxt = min(overlap_stop, h + HOUR)
            part = rate * (nxt - cursor)
            energy[h] += part
            if is_gap:
                estimated[h] += part
            cursor = nxt
        intervals += 1

    # 2. Zon en extern per uur (verschil van opeenvolgende uurrijen).
    def per_hour(rows_in: list[tuple[float, float]]) -> dict[int, float]:
        out: dict[int, float] = {}
        ordered = sorted(rows_in)
        for (prev_ts, prev_val), (ts, val) in zip(ordered, ordered[1:]):
            if ts - prev_ts == HOUR and val >= prev_val:
                out[_hour(ts)] = val - prev_val
        return out

    solar = per_hour(solar_rows)
    extern_by_day: dict[date, float] = defaultdict(float)
    for h, kwh in per_hour(extern_rows).items():
        if start_ts <= h < stop_ts and kwh > 0:
            extern_by_day[local_day(h)] += kwh

    prices = {_hour(ts): p for ts, p in price_rows}

    # 3. Kosten per uur, opgeteld per dag.
    days = defaultdict(lambda: {"kwh": 0.0, "cost": 0.0, "solar": 0.0, "missing": 0.0, "employer": 0.0})
    used_sources: set[str] = set()
    employer_rates: set[float] = set()
    for h in sorted(energy):
        kwh = energy[h]
        if kwh <= 0:
            continue
        day = local_day(h)
        d = days[day]
        sun = min(solar.get(h, 0.0), kwh)
        r = rates_for(h)
        used_sources.add(r.bron)
        employer_rates.add(round(r.vergoeding, 4))
        d["kwh"] += kwh
        d["solar"] += sun
        d["employer"] += kwh * r.vergoeding
        if h in prices:
            all_in = (prices[h] + r.inkoopvergoeding + r.energiebelasting) * (1 + vat)
            d["cost"] += (kwh - sun) * all_in
        else:
            d["missing"] += kwh

    daily = []
    for day in sorted(set(days) | set(extern_by_day), reverse=True):
        v = days[day]
        daily.append(
            {
                "datum": day.isoformat(),
                "kwh": round(v["kwh"], 3),
                "extern_kwh": round(extern_by_day.get(day, 0.0), 3),
                "zonne_kwh": round(v["solar"], 3),
                "kosten": _money(v["cost"]),
                "vergoeding": _money(v["employer"]),
                "zonder_prijs_kwh": round(v["missing"], 3),
            }
        )

    total_kwh = sum(v["kwh"] for v in days.values())
    total_cost = sum(v["cost"] for v in days.values())
    missing = sum(v["missing"] for v in days.values())
    priced = total_kwh - missing
    # Totaal = som van de afgeronde dagregels, zodat de declaratie optelt.
    employer = _money(sum(d["vergoeding"] for d in daily))
    cost = _money(total_cost)

    return {
        "kwh": round(total_kwh, 3),
        "cost": cost,
        "employer": employer,
        "difference": _money(employer - cost),
        "average": round(total_cost / priced, 4) if priced > 0 else 0,
        "solar_kwh": round(sum(v["solar"] for v in days.values()), 3),
        # Alleen ter informatie; telt niet mee in kosten of vergoeding.
        "extern_kwh": round(sum(extern_by_day.values()), 3),
        "priced_kwh": round(priced, 3),
        "missing_kwh": round(missing, 3),
        "estimated_kwh": round(sum(estimated.values()), 3),
        "gaps": gaps,
        "ignored_kwh": round(ignored_kwh, 3),
        "intervals": intervals,
        "daily": daily[:120],
        "daily_truncated": len(daily) > 120,
        "tariefbron": sorted(used_sources),
        "vergoeding_tarieven": sorted(employer_rates),
        "period": f"{from_date.isoformat()} t/m {to_date.isoformat()}",
        "note": (
            "Meterstandverschillen per uur; zonne-energie telt als gratis. "
            "Verdeling over ontbrekende uren en dynamische kosten zijn schattingen; "
            "geen exacte sessie- of factuurdata."
        ),
    }
