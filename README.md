# TinkerVision

Quelltext der Website [tinkervision.de](https://tinkervision.de), gehostet über GitHub Pages.

## Aufbau

- `site.css` – gemeinsame Basis: Farben (Hell/Dunkel), Schriften, Schalter, Sprachwahl, Footer.
  Farben auf den Seiten immer über Variablen setzen (`var(--card-solid)`, `var(--on-ink)` …), nie fest `#fff`.
- `site.js` – Dark Mode (folgt dem System, bis man selbst umschaltet), Sprachumschaltung, sicherer localStorage-Zugriff.
  Jede Seite bindet es vor ihrem eigenen `<script>` ein und ruft `TV.setLang(T, lang)` auf.
- `fonts/` – selbst gehostete Schriften (keine externen Anfragen).
- Deutsche Texte stehen direkt im HTML, Englisch kommt per JS aus dem Objekt `T` der Seite.
  Bei Textänderungen beides anpassen.
- `stats.json` – Download-Zahlen, täglich per GitHub Action (`update-downloads.py`) aktualisiert.
  Die Zahl der Konstruktionen (`cad`) wird von Hand gepflegt.
- `404.html` nutzt absolute Pfade (`/site.css`), weil sie unter beliebigen URLs ausgeliefert wird.

## Englische Seiten (`en/`)

- `en/` wird automatisch aus den deutschen Seiten erzeugt: `python3 tools/build_en.py`
  (läuft auch bei jedem Push als GitHub Action `site check`). Dateien in `en/` nie direkt bearbeiten.
- Englische Texte kommen aus `T.en` der jeweiligen Seite, englische Titel und Beschreibungen aus `EN_META` in `tools/build_en.py`.
  Neue Seite? Dort einen Eintrag ergänzen.
- Das Skript pflegt auch die hreflang-Links in den deutschen Seiten und die `sitemap.xml` (Seiten mit `noindex` bleiben draußen).

## Prüfung

`python3 tools/check_site.py` prüft Links, Bilder, alt-Texte, Übersetzungen, JSON-LD, Sitemap, Dark-Mode-Farben und Platzhalter.
Läuft automatisch nach jedem Push; bei Fehlern wird der Lauf rot und GitHub schickt eine Mail.

## Projekte-Seite

`projekte.html` ist vorbereitet, aber noch ausgeblendet (`noindex`, nicht verlinkt). Zum Freischalten:
Projekte eintragen (Anleitung als Kommentar in der Datei), `noindex`-Zeile löschen, Link auf der Startseite einkommentieren.
