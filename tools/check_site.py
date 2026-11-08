#!/usr/bin/env python3
"""Prüft die Website auf typische Fehler, bevor sie live geht.

Aufruf: python3 tools/check_site.py
Läuft auch automatisch als GitHub Action bei jedem Push (.github/workflows/site.yml).
Braucht Python 3 und Node.js, keine weiteren Pakete.

Geprüft wird:
- interne Links und Bilder zeigen auf vorhandene Dateien
- jedes Bild hat einen alt-Text
- jede Seite hat Titel; indexierbare Seiten auch Beschreibung und canonical
- strukturierte Daten (JSON-LD) sind gültiges JSON
- jeder data-i18n-Schlüssel hat eine deutsche und eine englische Übersetzung
- kein fest weißer Hintergrund im Seiten-CSS (bricht den Dark Mode)
- keine Platzhalter wie "[Projekt 1: Titel]" auf indexierbaren Seiten
- Sitemap zeigt nur auf vorhandene Seiten
- en/ ist auf dem Stand der deutschen Seiten
"""
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_en import translations  # noqa: E402

errors = []


def err(page, msg):
    errors.append(f"{page.relative_to(ROOT)}: {msg}")


def strip_comments(src):
    return re.sub(r"<!--.*?-->", "", src, flags=re.S)


def target_exists(page, ref):
    path = urlparse(ref).path
    if not path:
        return True
    if path.startswith("/"):
        target = ROOT / path.lstrip("/")
    else:
        target = (page.parent / path).resolve()
    if path.endswith("/"):
        target = target / "index.html"
    return target.exists()


def check_page(page):
    raw = page.read_text(encoding="utf-8")
    src = strip_comments(raw)
    noindex = re.search(r'name="robots" content="[^"]*noindex', src) is not None

    # Links und Bilder
    for attr, ref in re.findall(r'\b(href|src)="([^"]*)"', src):
        if not ref or ref.startswith(("#", "http:", "https:", "mailto:", "tel:", "data:", "javascript:")) or "${" in ref:
            continue
        if not target_exists(page, ref):
            err(page, f'{attr}="{ref}" zeigt ins Leere')
    for ref in re.findall(r'url\(["\']?([^)"\'#]+)["\']?\)', src):
        if not ref.startswith(("http:", "https:", "data:")) and not target_exists(page, ref):
            err(page, f"CSS url({ref}) zeigt ins Leere")
    for ref in re.findall(r'fetch\("([^"]+)"', src):
        if not target_exists(page, ref):
            err(page, f'fetch("{ref}") zeigt ins Leere')

    # Bilder ohne alt
    for tag in re.findall(r"<img\b[^>]*>", src):
        if not re.search(r'\balt="', tag):
            err(page, f"Bild ohne alt-Text: {tag[:80]}")

    # Meta
    if not re.search(r"<title>[^<]+</title>", src):
        err(page, "kein <title>")
    if not noindex and page.name != "404.html":
        if 'name="description"' not in src:
            err(page, "keine meta description")
        if 'rel="canonical"' not in src:
            err(page, "kein canonical")

    # JSON-LD
    for block in re.findall(r'<script type="application/ld\+json">(.*?)</script>', src, re.S):
        try:
            json.loads(block)
        except json.JSONDecodeError as e:
            err(page, f"JSON-LD ungültig: {e}")

    # Übersetzungen
    if "const T = " in src:
        de, en = translations(src, page.name)
        for key in sorted(set(re.findall(r'data-i18n="([^"]+)"', src))):
            if key not in de and key != "enNote":
                err(page, f"Schlüssel '{key}' fehlt in T.de")
            if key not in en:
                err(page, f"Schlüssel '{key}' fehlt in T.en")

    # Dark Mode: kein fest weißer Hintergrund im Seiten-CSS
    for style in re.findall(r"<style>(.*?)</style>", src, re.S):
        for m in re.finditer(r"background(-color)?\s*:\s*#fff(fff)?\b", style, re.I):
            line = style[:m.start()].count("\n")
            err(page, f"fest weißer Hintergrund im CSS (Zeile ~{line} im <style>) – var(--card-solid) verwenden")

    # Platzhalter
    if not noindex and re.search(r"\[(Projekt|Project) \d", src):
        err(page, "enthält noch Platzhalter, ist aber indexierbar")

    return noindex


def main():
    pages = sorted(list(ROOT.glob("*.html")) + list((ROOT / "en").glob("*.html")))
    for page in pages:
        check_page(page)

    sitemap = (ROOT / "sitemap.xml").read_text(encoding="utf-8")
    for loc in re.findall(r"<loc>([^<]+)</loc>", sitemap):
        path = urlparse(loc).path.lstrip("/")
        target = ROOT / (path + "index.html" if path.endswith("/") or not path else path)
        if not target.exists():
            errors.append(f"sitemap.xml: {loc} gibt es nicht")

    res = subprocess.run([sys.executable, str(ROOT / "tools" / "build_en.py"), "--check"], capture_output=True, text=True)
    if res.returncode != 0:
        errors.append("en/ ist nicht aktuell – 'python3 tools/build_en.py' ausführen\n" + res.stdout.strip())

    if errors:
        print(f"{len(errors)} Problem(e) gefunden:\n")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print(f"Alles in Ordnung ({len(pages)} Seiten geprüft).")


if __name__ == "__main__":
    main()
