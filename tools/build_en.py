#!/usr/bin/env python3
"""Erzeugt die englischen Seiten unter en/ aus den deutschen Seiten im Hauptordner.

Quelle der englischen Texte ist das Objekt T.en im <script> jeder Seite.
Titel und Beschreibungen für Suchmaschinen stehen unten in EN_META.

Aufruf:  python3 tools/build_en.py          -> en/ neu schreiben
         python3 tools/build_en.py --check  -> nur prüfen, ob en/ aktuell ist (für die GitHub Action)

Braucht Python 3 und Node.js (zum Auslesen der Übersetzungsobjekte). Keine weiteren Pakete.
Die Dateien in en/ nie direkt bearbeiten – sie werden bei jedem Lauf überschrieben.
"""
import html
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "en"
BASE = "https://tinkervision.de/"

# Seiten ohne englische Fassung (404 wird vom Server unter beliebigen URLs ausgeliefert).
SKIP = {"404.html"}

EN_META = {
    "index.html": ("TinkerVision – CAD design, 3D scanning & 3D printing",
                   "TinkerVision from northern Germany: 3D scanning, CAD design and FEA – from prototype to custom build. Digital models on Cults3D and Printables.",
                   "TinkerVision – Idea becomes geometry"),
    "leistungen.html": ("Services: CAD, 3D scanning, FEA & 3D printing – TinkerVision",
                        "Technical drawings, 3D scans, parametric 3D files, FEA and prototypes – plus an overview of filaments and materials.",
                        "Services – TinkerVision"),
    "kontakt.html": ("Contact – TinkerVision",
                     "Idea, order or question? Write to TinkerVision via the contact form or by email.",
                     "Contact – TinkerVision"),
    "spezial.html": ("Custom products – TinkerVision",
                     "Configurable one-offs and small runs from the 3D printer, such as the table tennis net gauge in club colours.",
                     "Custom products – TinkerVision"),
    "netzlehre.html": ("Table tennis net gauge in club colours – TinkerVision",
                       "Table tennis net gauge (15.25 cm net height, rubber thickness) in up to 3 club colours with your own text. As a 3MF file from €7 or printed.",
                       "Table tennis net gauge club edition – TinkerVision"),
    "non-ittf.html": ("Note: not ITTF approved – TinkerVision", "Note on products without ITTF approval.",
                      "Note: not ITTF approved – TinkerVision"),
    "projekte.html": ("Projects and references – TinkerVision",
                      "Selected TinkerVision projects: brief, solution and result from CAD design, 3D scanning and 3D printing.",
                      "Projects and references – TinkerVision"),
    "impressum.html": ("Imprint – TinkerVision", "Legal notice (Impressum) of TinkerVision.", "Imprint – TinkerVision"),
    "datenschutz.html": ("Privacy – TinkerVision", "Privacy policy of TinkerVision.", "Privacy – TinkerVision"),
    "agb.html": ("Terms and conditions – TinkerVision", "General terms and conditions of TinkerVision.", "Terms – TinkerVision"),
    "widerruf.html": ("Right of withdrawal – TinkerVision", "Right of withdrawal and model withdrawal form of TinkerVision.",
                      "Withdrawal – TinkerVision"),
    "changelog.html": ("Changelog – TinkerVision", "Changes to the TinkerVision website.", "Changelog – TinkerVision"),
}

# Deutsche Texte in Attributen (alt, aria-label, placeholder …), die nicht über T laufen.
ATTR_TEXT = {
    "Dunkles Design umschalten": "Toggle dark mode",
    "Kategorien": "Categories",
    "Schrift": "Font",
    "Vereinsname 2026": "Club name 2026",
    "Netzlehre": "Net gauge",
    "Platzhalter – Foto folgt": "Placeholder – photo coming soon",
    "TinkerVision – Idee wird Geometrie. 3D-Scan, CAD-Konstruktion, FEM-Analyse":
        "TinkerVision – Idea becomes geometry. 3D scanning, CAD design, FEA",
}


def page_url(name, lang):
    path = "" if name == "index.html" else name
    return BASE + ("en/" if lang == "en" else "") + path


def translations(src, name):
    m = re.search(r"const T = ", src)
    if not m:
        return {}, {}
    start, depth, k, q = m.end(), 0, m.end(), None
    while k < len(src):
        c = src[k]
        if q:
            if c == "\\":
                k += 2
                continue
            if c == q:
                q = None
        elif c in "\"'`":
            q = c
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                break
        k += 1
    js = "const T = " + src[start:k + 1] + ";\nconsole.log(JSON.stringify({de: T.de || {}, en: T.en || {}}));"
    try:
        res = subprocess.run(["node", "-e", js], capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(f"{name}: Übersetzungsobjekt T lässt sich nicht lesen:\n{e.stderr}")
    data = json.loads(res.stdout)
    return data["de"], data["en"]


def hreflang_block(name, here):
    """here = 'de' oder 'en': bestimmt die relativen data-path-Werte für lokale Vorschau."""
    file = name
    de_path = file if here == "de" else "../" + file
    en_path = "en/" + file if here == "de" else file
    return (f'  <link rel="alternate" hreflang="de" href="{page_url(name, "de")}" data-path="{de_path}">\n'
            f'  <link rel="alternate" hreflang="en" href="{page_url(name, "en")}" data-path="{en_path}">\n'
            f'  <link rel="alternate" hreflang="x-default" href="{page_url(name, "de")}" data-path="{de_path}">\n')


def ensure_hreflang(src, name):
    """Deutsche Seite: hreflang-Block hinter canonical setzen bzw. erneuern."""
    src = re.sub(r'  <link rel="alternate" hreflang="[^"]+"[^>]*>\n', "", src)
    return re.sub(r'(  <link rel="canonical"[^>]*>\n)', lambda m: m.group(1) + hreflang_block(name, "de"), src, count=1)


def relink(value, en_pages):
    """Relativen Pfad aus Sicht von en/ umschreiben."""
    if not value or value.startswith(("#", "/", "http:", "https:", "mailto:", "tel:", "data:", "javascript:")):
        return value
    path = re.split(r"[?#]", value, maxsplit=1)[0]
    if path in en_pages:
        return value
    return "../" + value


def build_page(name, src, en_pages):
    de, en = translations(src, name)
    title, desc, og = EN_META[name]
    raw_html = name == "non-ittf.html"
    problems = []

    # Texte mit data-i18n: deutschen Inhalt durch englischen ersetzen
    body_at = src.find("<body")
    head, body = src[:body_at], src[body_at:]

    def swap(m):
        tag, attrs, key, inner = m.group(1), m.group(2), m.group(3), m.group(4)
        value = en.get(key)
        if not isinstance(value, str):
            problems.append(f"{name}: Schlüssel '{key}' fehlt in T.en")
            return m.group(0)
        if key == "enNote":
            attrs = attrs.replace(" hidden", "")
        text = value if (raw_html or "data-i18n-html" in attrs) else html.escape(value, quote=False)
        return f"<{tag}{attrs}>{text}</{tag}>"

    body = re.sub(r'<(\w+)(\s[^>]*?\bdata-i18n="([^"]+)"[^>]*)>(.*?)</\1>', swap, body, flags=re.S)
    body = body.replace('data-set-lang="de" aria-pressed="true"', 'data-set-lang="de" aria-pressed="false"')
    body = body.replace('data-set-lang="en" aria-pressed="false"', 'data-set-lang="en" aria-pressed="true"')
    src = head + body

    # Kopf: Sprache, Meta, canonical, hreflang
    src = src.replace('<html lang="de">', '<html lang="en">', 1)
    src = re.sub(r"<title>.*?</title>", f"<title>{html.escape(title, quote=False)}</title>", src, count=1, flags=re.S)
    src = re.sub(r'<meta name="description" content="[^"]*">', f'<meta name="description" content="{html.escape(desc)}">', src, count=1)
    src = re.sub(r'<meta property="og:title" content="[^"]*">', f'<meta property="og:title" content="{html.escape(og)}">', src, count=1)
    src = re.sub(r'<meta property="og:description" content="[^"]*">', f'<meta property="og:description" content="{html.escape(desc)}">', src, count=1)
    src = src.replace('<meta property="og:locale" content="de_DE">', '<meta property="og:locale" content="en_GB">')
    src = src.replace('<meta property="og:locale:alternate" content="en_GB">', '<meta property="og:locale:alternate" content="de_DE">')
    src = re.sub(r'<meta property="og:url" content="[^"]*">', f'<meta property="og:url" content="{page_url(name, "en")}">', src, count=1)
    src = src.replace(f'content="{BASE}og-image.jpg"', f'content="{BASE}og-image-en.jpg"')
    src = re.sub(r'<link rel="canonical" href="[^"]*">', f'<link rel="canonical" href="{page_url(name, "en")}">', src, count=1)
    src = re.sub(r'  <link rel="alternate" hreflang="[^"]+"[^>]*>\n', "", src)
    src = re.sub(r'(  <link rel="canonical"[^>]*>\n)', lambda m: m.group(1) + hreflang_block(name, "en"), src, count=1)

    # Attributtexte
    for de_text, en_text in ATTR_TEXT.items():
        src = src.replace(f'="{de_text}"', f'="{html.escape(en_text)}"')

    # Pfade: Attribute, CSS url(), fetch() im Skript
    src = re.sub(r'\b(src|href)="([^"]*)"',
                 lambda m: f'{m.group(1)}="{relink(m.group(2), en_pages)}"', src)
    src = re.sub(r'url\((["\']?)([^)"\']+)\1\)', lambda m: f"url({m.group(1)}{relink(m.group(2), en_pages)}{m.group(1)})", src)
    src = re.sub(r'fetch\("([^"]+)"', lambda m: f'fetch("{relink(m.group(1), en_pages)}"', src)

    # Kontaktformular: nach dem Absenden auf die englische Seite zurück
    src = src.replace(f'value="{BASE}kontakt.html?sent=1"', f'value="{BASE}en/kontakt.html?sent=1"')

    note = f"<!-- Automatisch erzeugt aus ../{name} durch tools/build_en.py – nicht direkt bearbeiten. -->\n"
    src = src.replace("<!DOCTYPE html>\n", "<!DOCTYPE html>\n" + note, 1)
    return src, problems


def sitemap(pages):
    """Sitemap mit deutschen und englischen URLs; Seiten mit noindex bleiben draußen."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for name in pages:
        for lang in ("de", "en"):
            lines.append("  <url>")
            lines.append(f"    <loc>{page_url(name, lang)}</loc>")
            for alt in ("de", "en"):
                lines.append(f'    <xhtml:link rel="alternate" hreflang="{alt}" href="{page_url(name, alt)}"/>')
            lines.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{page_url(name, "de")}"/>')
            lines.append("  </url>")
    lines.append("</urlset>")
    return "\n".join(lines) + "\n"


def main():
    check = "--check" in sys.argv
    names = sorted(p.name for p in ROOT.glob("*.html") if p.name not in SKIP)
    missing = [n for n in names if n not in EN_META]
    if missing:
        sys.exit("Für diese Seiten fehlen englische Titel/Beschreibungen in EN_META: " + ", ".join(missing))

    wanted, problems = {}, []
    indexable = []
    for name in names:
        path = ROOT / name
        src = path.read_text(encoding="utf-8")
        de_src = ensure_hreflang(src, name)
        wanted[path] = de_src
        en_src, probs = build_page(name, de_src, set(names))
        problems += probs
        wanted[OUT / name] = en_src
        if not re.search(r'name="robots" content="[^"]*noindex', src):
            indexable.append(name)
    order = ["index.html", "leistungen.html", "spezial.html", "netzlehre.html", "projekte.html", "kontakt.html"]
    indexable.sort(key=lambda n: (order.index(n) if n in order else len(order), n))
    wanted[ROOT / "sitemap.xml"] = sitemap(indexable)

    stale = [p for p, text in wanted.items() if not p.exists() or p.read_text(encoding="utf-8") != text]
    orphans = [p for p in OUT.glob("*.html") if p not in wanted] if OUT.exists() else []

    for msg in problems:
        print("WARNUNG:", msg)
    if check:
        if stale or orphans:
            for p in stale + orphans:
                print("nicht aktuell:", p.relative_to(ROOT))
            sys.exit("en/ ist nicht aktuell – bitte 'python3 tools/build_en.py' ausführen.")
        print("en/ ist aktuell.")
        return
    OUT.mkdir(exist_ok=True)
    for p in stale:
        p.write_text(wanted[p], encoding="utf-8")
        print("geschrieben:", p.relative_to(ROOT))
    for p in orphans:
        p.unlink()
        print("entfernt:", p.relative_to(ROOT))
    if not stale and not orphans:
        print("Nichts zu tun, alles aktuell.")


if __name__ == "__main__":
    main()
