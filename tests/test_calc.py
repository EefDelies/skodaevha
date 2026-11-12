import sys, random, importlib.util, pathlib
COMP = pathlib.Path(__file__).resolve().parents[1] / "custom_components" / "ennie_laadkosten"
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
spec = importlib.util.spec_from_file_location("calc", COMP / "calc.py")
calc = importlib.util.module_from_spec(spec); sys.modules["calc"]=calc; spec.loader.exec_module(calc)

SUR, TAX, VAT, EMP = 0.0181, 0.0916, 1.21, 0.35
def old(rows, price_rows, from_date, to_date, tz='Europe/Amsterdam'):
    # Letterlijke kern van de oude _calculate (zonder SQLite)
    zone = ZoneInfo(tz)
    start = datetime.combine(from_date, datetime.min.time(), zone)
    stop = datetime.combine(to_date + timedelta(days=1), datetime.min.time(), zone)
    start_ts, stop_ts = start.timestamp(), stop.timestamp()
    preceding = [r for r in rows if r[0] < start_ts][-1:]
    meter_rows = [r for r in rows if start_ts <= r[0] <= stop_ts]
    rows = preceding + meter_rows
    prices = {int(ts // 3600) * 3600: float(m) for ts, m in price_rows if start_ts-3600 <= ts < stop_ts+3600}
    days = defaultdict(lambda: {"kwh": 0.0, "cost": 0.0})
    tk=tc=0.0
    for (pt, pv), (ts, v) in zip(rows, rows[1:]):
        d = ts-pt
        if d <= 0: continue
        delta = v-pv
        if delta <= 0: continue
        if delta/(d/3600) > 22: continue
        os_, oe = max(pt, start_ts), min(ts, stop_ts)
        if oe <= os_: continue
        rate = delta/d; c = os_
        while c < oe-0.0001:
            h = int(c//3600)*3600; n = min(oe, h+3600); e = rate*(n-c)
            day = datetime.fromtimestamp(c, timezone.utc).astimezone(zone).date()
            days[day]["kwh"] += e; tk += e
            if h in prices:
                cost = e*(prices[h]+SUR+TAX)*VAT; tc += cost; days[day]["cost"] += cost
            c = n
    return round(tk,3), round(tc,2)

def rates_for(h): return calc.Rates(TAX, SUR, EMP, "helpers")
random.seed(1)
zone = ZoneInfo('Europe/Amsterdam')
t0 = datetime(2026,10,9,1,tzinfo=zone).timestamp()
worst = 0
for trial in range(200):
    rows=[]; v=32.0; ts=t0
    for i in range(24*40):
        ts += 3600
        if random.random() < 0.05: continue           # ontbrekende uren
        if random.random() < 0.15: v += random.uniform(0, 11)
        rows.append((ts, v))
    prices=[(t0+3600*i, random.uniform(0.05,0.6)) for i in range(24*40) if random.random()>0.03]
    f = date(2026,10,1)+timedelta(days=random.randint(0,20)); t = f+timedelta(days=random.randint(0,15))
    ok, oc = old(rows, prices, f, t)
    zst = datetime.combine(f, datetime.min.time(), zone).timestamp()
    zsp = datetime.combine(t+timedelta(days=1), datetime.min.time(), zone).timestamp()
    m = [r for r in rows if r[0] < zst][-1:] + [r for r in rows if zst <= r[0] <= zsp]
    p = [r for r in prices if zst-3600 <= r[0] < zsp]
    new = calc.calculate(m, p, [], [], f, t, 'Europe/Amsterdam', rates_for, 0.21, 22.0)
    assert abs(new["kwh"]-ok) < 0.002, (trial, new["kwh"], ok)
    worst = max(worst, abs(new["cost"]-oc))
    assert abs(new["cost"]-oc) <= 0.02, (trial, new["cost"], oc)
    assert abs(new["employer"] - round(sum(d["vergoeding"] for d in new["daily"]),2)) < 1e-9
print("200 willekeurige periodes: kWh identiek, max kostenverschil €%.2f (afronding)" % worst)

# Zon: 1 uur laden 10 kWh, waarvan 3 kWh zon -> 7 kWh betaald
h = datetime(2026,11,10,12,tzinfo=zone).timestamp()
meter = [(h-3600, 100.0), (h, 100.0), (h+3600, 110.0)]       # energie in [h, h+1)
solar = [(h-3600, 5.0), (h, 8.0)]                            # zon in [h, h+1) = 3
price = [(h, 0.20)]
r = calc.calculate(meter, price, solar, [], date(2026,11,10), date(2026,11,10), 'Europe/Amsterdam', rates_for, 0.21, 22.0)
exp = round(7*(0.20+SUR+TAX)*1.21, 2)
assert r["kwh"]==10 and r["solar_kwh"]==3 and r["cost"]==exp and r["employer"]==3.5, r
print("Zon-test: 10 kWh, 3 kWh zon gratis, kosten €%.2f (verwacht €%.2f), vergoeding €%.2f" % (r["cost"], exp, r["employer"]))

# Tarief uit historie: tot 1-1-2027 0,0916, daarna 0,0500 (duidelijk verschil)
cut = datetime(2027,1,1,0,tzinfo=zone).timestamp()
def hist(h):
    return calc.Rates(0.0916 if h < cut else 0.0500, 0.0181, 0.35 if h < cut else 0.40, "historie")
h1 = datetime(2026,12,31,23,tzinfo=zone).timestamp()
meter=[(h1-3600,0.0),(h1,0.0),(h1+3600,1.0),(h1+7200,2.0)]
price=[(h1,0.20),(h1+3600,0.20)]
r = calc.calculate(meter, price, [], [], date(2026,12,31), date(2027,1,1), 'Europe/Amsterdam', hist, 0.21, 22.0)
d = {x["datum"]: x["kosten"] for x in r["daily"]}
exp = {"2026-12-31": round((0.2+0.0181+0.0916)*1.21,2), "2027-01-01": round((0.2+0.0181+0.05)*1.21,2)}
assert d == exp, (d, exp)
assert r["tariefbron"] == ["historie"]
print("Tarief-historie-test: 31-12 en 01-01 elk met eigen tarief:", d)

# Werkgeversvergoeding wisselt per 1-1: 1 kWh x 0,35 + 1 kWh x 0,40
v = {x["datum"]: x["vergoeding"] for x in r["daily"]}
assert v == {"2026-12-31": 0.35, "2027-01-01": 0.40} and r["employer"] == 0.75 and r["vergoeding_tarieven"] == [0.35, 0.4], (v, r["employer"])
print("Vergoeding-test: dagbedragen", v, "totaal", r["employer"])

# PDF genereren met beide tarieven
import importlib.util as u
sp = u.spec_from_file_location("declaratie", COMP / "declaratie.py")
dec = u.module_from_spec(sp); sys.modules["declaratie"] = dec; sp.loader.exec_module(dec)
path, url = dec.make_pdf(r, date(2026,12,31), date(2027,1,1), "/tmp/pdftest")
pdf = open(path, "rb").read()
assert b"TOTAAL TE DECLAREREN: EUR 0,75" in pdf and b"volgens dagoverzicht" in pdf, pdf[:2000]
print("PDF-test:", path, len(pdf), "bytes, totaal EUR 0,75 en 'volgens dagoverzicht'")

# Extern laden: 11-11 thuis 0 kWh, extern 5 kWh -> telt nergens mee
h = datetime(2026,11,11,9,tzinfo=zone).timestamp()
meter = [(h-7200, 50.0), (h-3600, 50.0), (h, 50.0), (h+3600, 52.0)]   # 2 kWh thuis in uur h
ext = [(h-3600, 10.0), (h, 15.0)]                                     # 5 kWh extern in uur h
r = calc.calculate(meter, [(h, 0.2)], [], ext, date(2026,11,11), date(2026,11,11), 'Europe/Amsterdam', rates_for, 0.21, 22.0)
assert r["kwh"] == 2 and r["extern_kwh"] == 5 and r["employer"] == 0.7, r
# Alleen-extern dag
r2 = calc.calculate([(h-3600,50.0),(h,50.0),(h+3600,50.0)], [(h,0.2)], [], ext, date(2026,11,11), date(2026,11,11), 'Europe/Amsterdam', rates_for, 0.21, 22.0)
assert r2["kwh"] == 0 and r2["cost"] == 0 and r2["employer"] == 0 and r2["extern_kwh"] == 5 and r2["daily"][0]["extern_kwh"] == 5, r2
print("Extern-test: thuis 2 kWh (vergoeding 0,70), extern 5 kWh telt niet mee; alleen-extern dag: kosten 0, vergoeding 0")
# Declaratie bevat geen extern-only dagen
r3 = calc.calculate(meter, [(h,0.2)], [], ext + [(h+3600*24, 15.0), (h+3600*25, 20.0)], date(2026,11,11), date(2026,11,12), 'Europe/Amsterdam', rates_for, 0.21, 22.0)
path, _ = dec.make_pdf(r3, date(2026,11,11), date(2026,11,12), "/tmp/pdftest2")
pdf = open(path,"rb").read()
assert b"2026-11-12" not in pdf and b"2026-11-11" in pdf
print("Declaratie-test: dag met alleen extern laden staat niet in de PDF")
import shutil; shutil.rmtree("/tmp/pdftest2")


# Declarant uit configuratie: gegevens verschijnen alleen als ze zijn ingesteld
from types import SimpleNamespace
d = SimpleNamespace(naam="Jan Jansen", bron="Zaptec Go 2 - Voorbeeldstraat 1", iban="NL00TEST0123456789", rekeninghouder="J. Jansen")
p1, u1 = dec.make_pdf(r3, date(2026,11,11), date(2026,11,12), "/tmp/pdftest3", d)
b = open(p1, "rb").read()
assert b"JAN JANSEN" in b and b"NL00TEST0123456789" in b and b"t.n.v. J. Jansen" in b
p2, _ = dec.make_pdf(r3, date(2026,11,11), date(2026,11,12), "/tmp/pdftest3")
b2 = open(p2, "rb").read()
assert b"Rekening begunstigde" not in b2 and b"Bron:" not in b2
assert p1 != p2 and u1.startswith("/local/declaraties/ennie_declaratie_2026-11-11_tm_2026-11-12_")
print("declarant OK")
