"""Dependency-free, single-page/multi-page PDF export for Ennie charging."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import os
import secrets



def _money(value):
    return f"EUR {value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP):,.2f}".replace(',', '_').replace('.', ',').replace('_', '.')


def _pdf_text(value):
    # Standard PDF Helvetica uses WinAnsi; all generated labels are ASCII.
    value = str(value).encode('ascii', 'replace').decode('ascii')
    return value.replace('\\', '\\\\').replace('(', '\\(').replace(')', '\\)')


def _pdf_bytes(pages):
    """Build a simple standards-compliant PDF 1.4 with built-in Helvetica."""
    objects = []
    def add(payload):
        objects.append(payload)
        return len(objects)
    catalog_id = add(b'')
    pages_id = add(b'')
    font_id = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>')
    page_ids = []
    for lines in pages:
        commands = []
        for item in lines:
            if item[0] == 'rect':
                _, x, y, w, h, gray = item
                commands.append(f'{gray} G 0.6 w {x} {y} {w} {h} re S')
            elif item[0] == 'rule':
                _, x1, y1, x2, y2 = item
                commands.append(f'0.55 G 0.6 w {x1} {y1} m {x2} {y2} l S')
            else:
                y, size, text, *rest = item
                x = rest[0] if rest else 48
                commands.append(f"0 G BT /F1 {size} Tf {x} {y} Td ({_pdf_text(text)}) Tj ET")
        stream = ('\n'.join(commands) + '\n').encode('ascii')
        content_id = add(f'<< /Length {len(stream)} >>\nstream\n'.encode() + stream + b'endstream')
        page_id = add(f'<< /Type /Page /Parent {pages_id} 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 {font_id} 0 R >> >> /Contents {content_id} 0 R >>'.encode())
        page_ids.append(page_id)
    kids = ' '.join(f'{i} 0 R' for i in page_ids)
    objects[catalog_id - 1] = f'<< /Type /Catalog /Pages {pages_id} 0 R >>'.encode()
    objects[pages_id - 1] = f'<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>'.encode()
    result = bytearray(b'%PDF-1.4\n%\xe2\xe3\xcf\xd3\n')
    offsets = [0]
    for i, obj in enumerate(objects, 1):
        offsets.append(len(result))
        result.extend(f'{i} 0 obj\n'.encode() + obj + b'\nendobj\n')
    xref = len(result)
    result.extend(f'xref\n0 {len(objects) + 1}\n0000000000 65535 f \n'.encode())
    for off in offsets[1:]:
        result.extend(f'{off:010d} 00000 n \n'.encode())
    result.extend(f'trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref}\n%%EOF\n'.encode())
    return bytes(result)


def make_pdf(data, from_date, to_date, output_dir, declarant=None):
    """Return (path, url_path) for a PDF based on a fresh calculation.

    Bedragen komen uit de berekening: per uur geldt de werkgeversvergoeding
    die toen in Home Assistant was ingesteld. Naam, bron en rekening komen
    uit de configuratie (declarant); lege velden worden weggelaten.
    """
    naam = getattr(declarant, 'naam', '') or ''
    bron = getattr(declarant, 'bron', '') or ''
    iban = getattr(declarant, 'iban', '') or ''
    houder = getattr(declarant, 'rekeninghouder', '') or ''
    rates = [Decimal(str(r)) for r in data.get('vergoeding_tarieven', [])]
    if data.get('error'):
        raise ValueError(data['error'])
    kwh = Decimal(str(data['kwh']))
    # Alleen dagen met thuisladen; extern laden wordt nooit gedeclareerd.
    rows = sorted((d for d in data.get('daily', []) if d['kwh'] > 0), key=lambda d: d['datum'])
    # Totaal = som van de afgeronde dagbedragen, zodat de tabel exact optelt.
    compensation = sum((Decimal(str(r['vergoeding'])) for r in rows), Decimal('0'))
    if data.get('daily_truncated'):
        raise ValueError('Dagtotalen zijn afgekapt; kies een kortere periode')
    if kwh <= 0:
        raise ValueError('Geen geladen energie gevonden in deze periode')

    pages = []
    lines = []
    def new_page():
        nonlocal lines
        if lines:
            pages.append(lines)
        lines = []
        return 787
    y = new_page()
    def line(text, size=10, space=20):
        nonlocal y
        if y < 68:
            y = new_page()
        lines.append((y, size, text))
        y -= space

    titel = 'DECLARATIE ZAKELIJK THUISLADEN'
    line(f'{titel} - {naam.upper()}' if naam else titel, 14, 37)
    line(f'Periode: {from_date:%d-%m-%Y} t/m {to_date:%d-%m-%Y}', 11, 23)
    if bron:
        line(f'Bron: {bron}', 9, 33)
    line(f'Geladen energie in declaratieperiode: {kwh:.3f} kWh', 12, 25)
    if len(rates) == 1:
        line(f"Vergoeding per kWh: {_money(rates[0])}", 12, 25)
    else:
        line('Vergoeding per kWh: volgens dagoverzicht (tarief gewijzigd in periode)', 12, 25)
    line(f'TOTAAL TE DECLAREREN: {_money(compensation)}', 14, 27)
    if iban:
        line(f'Rekening begunstigde: {iban}' + (',' if houder else ''), 12, 19)
        if houder:
            line(f't.n.v. {houder}', 12, 36)
        else:
            y -= 17
    else:
        y -= 10
    line('Dagoverzicht declaratieperiode', 11, 29)

    # Tabel met echte getekende randen, inclusief verticale kolomscheidingen.
    left, right = 48, 547
    x1, x2 = 220, 365
    row_height = 25
    def table_row(values, header=False):
        nonlocal y
        if y - row_height < 65:
            y = new_page()
            if not header:
                table_row(('Datum', 'kWh', 'Vergoeding'), header=True)
        top = y + 7
        bottom = top - row_height
        lines.append(('rect', left, bottom, right - left, row_height, 0.55))
        lines.append(('rule', x1, bottom, x1, top))
        lines.append(('rule', x2, bottom, x2, top))
        size = 10 if header else 9
        for x, value in zip((left + 9, x1 + 9, x2 + 9), values):
            lines.append((y - 10, size, str(value), x))
        y -= row_height

    table_row(('Datum', 'kWh', 'Vergoeding'), header=True)
    for row in rows:
        amount = Decimal(str(row['vergoeding']))
        table_row((row['datum'], f"{Decimal(str(row['kwh'])):.3f}", _money(amount)))
    pages.append(lines)

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    # /local/ is zonder inloggen bereikbaar: een willekeurig achtervoegsel
    # maakt de bestandsnaam onvoorspelbaar.
    filename = (f'ennie_declaratie_{from_date:%Y-%m-%d}_tm_{to_date:%Y-%m-%d}_'
                f'{secrets.token_hex(8)}.pdf')
    path = out / filename
    tmp = path.with_suffix('.pdf.tmp')
    tmp.write_bytes(_pdf_bytes(pages))
    os.replace(tmp, path)
    return str(path), f'/local/declaraties/{filename}'
