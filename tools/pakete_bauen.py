#!/usr/bin/env python3
"""Baut die beiden Lieferpakete einer Website-Runde.

  tinkervision-upload-<version>.zip
      Inhalt direkt fürs Repo (Branch `website`): alles außer .git und stats.json.
      stats.json fehlt absichtlich – die pflegt die GitHub Action täglich selbst.

  tinkervision-lokaltest-<version>.zip
      Ordner mit der kompletten Seite unter website/ und anklickbaren Startskripten
      für Linux, Mac und Windows. Die Skripte starten einen lokalen Webserver und
      öffnen die Seite im Browser. Diese ZIP nie ins Repo hochladen.

Aufruf: python3 tools/pakete_bauen.py [Zielordner]
"""
import re
import stat
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKIP_DIRS = {".git", "__pycache__"}
SKIP_UPLOAD = {"stats.json"}

LINUX_MAC = r'''#!/usr/bin/env bash
# TinkerVision – Website lokal testen.
# Doppelklick (ggf. "Im Terminal ausführen" wählen) oder im Terminal: ./"Lokal testen (Linux).sh"
# Beenden: Terminalfenster schließen oder Strg+C.

DIR="$(cd "$(dirname "$0")" && pwd)"

# Ohne Terminal gestartet? Dann in einem Terminalfenster neu öffnen, damit man den Server sieht und stoppen kann.
if [ ! -t 1 ] && [ -z "$TV_IN_TERMINAL" ]; then
  export TV_IN_TERMINAL=1
  for t in x-terminal-emulator gnome-terminal konsole xfce4-terminal mate-terminal tilix kitty alacritty xterm; do
    if command -v "$t" >/dev/null 2>&1; then
      case "$t" in
        gnome-terminal|tilix) exec "$t" -- bash "$0" ;;
        *) exec "$t" -e bash "$0" ;;
      esac
    fi
  done
fi

cd "$DIR/website" || { echo "Ordner 'website' nicht gefunden."; read -r -p "Enter zum Schließen"; exit 1; }

PY=""
for p in python3 python; do command -v "$p" >/dev/null 2>&1 && { PY="$p"; break; }; done
if [ -z "$PY" ]; then
  echo "Python 3 wird benötigt (Linux: sudo apt install python3)."
  read -r -p "Enter zum Schließen"; exit 1
fi

PORT=$("$PY" -c 'import socket
for p in range(8000, 8100):
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", p)); print(p); break
    except OSError:
        pass
    finally:
        s.close()')
URL="http://localhost:$PORT/"

echo "TinkerVision läuft lokal: $URL"
echo "Englisch: ${URL}en/   ·   Beenden: Strg+C oder Fenster schließen"
echo
( sleep 1; if command -v xdg-open >/dev/null 2>&1; then xdg-open "$URL"; elif command -v open >/dev/null 2>&1; then open "$URL"; fi ) >/dev/null 2>&1 &
exec "$PY" -m http.server "$PORT" --bind 127.0.0.1
'''

WINDOWS = r'''@echo off
rem TinkerVision - Website lokal testen. Doppelklick genuegt. Beenden: Fenster schliessen.
chcp 65001 >nul
cd /d "%~dp0website" || (echo Ordner "website" nicht gefunden. & pause & exit /b 1)
set PY=
where py >nul 2>nul && set PY=py -3
if not defined PY where python >nul 2>nul && set PY=python
if not defined PY (echo Python 3 wird benoetigt: https://www.python.org/downloads/ & pause & exit /b 1)
set PORT=8000
echo TinkerVision laeuft lokal: http://localhost:%PORT%/
echo Englisch: http://localhost:%PORT%/en/   -   Beenden: Fenster schliessen
start "" "http://localhost:%PORT%/"
%PY% -m http.server %PORT% --bind 127.0.0.1
pause
'''

README = """TinkerVision – lokaler Test ({version})
=====================================

Starten
  Linux:   „Lokal testen (Linux).sh“ doppelklicken (ggf. „Im Terminal ausführen“ wählen)
           oder im Terminal:  ./"Lokal testen (Linux).sh"
  Mac:     „Lokal testen (Mac).command“ doppelklicken
           (beim ersten Mal: Rechtsklick → Öffnen)
  Windows: „Lokal testen (Windows).bat“ doppelklicken

Das Skript startet einen kleinen Webserver (Python 3) und öffnet die Seite im Browser,
meist unter http://localhost:8000/ – Englisch unter /en/.
Beenden: Terminalfenster schließen oder Strg+C.

Falls das Doppelklicken unter Linux nicht startet: Rechtsklick → Eigenschaften →
„Als Programm ausführen“ erlauben, oder im Terminal:  chmod +x *.sh

Was testen?
  - Hell/Dunkel-Schalter auf mehreren Seiten
  - DE/EN-Schalter (wechselt zwischen /seite.html und /en/seite.html)
  - Startseite: Zahlen, alle Kacheln
  - Leistungen: beide Reiter, Materialien aufklappen
  - Netzlehre: Farben und Text ändern
  - Kontaktformular NICHT abschicken – das ginge an den echten Dienst.

Diese ZIP ist nur zum Testen. Hochgeladen wird die „upload“-ZIP.
"""


def files(base):
    for p in sorted(base.rglob("*")):
        rel = p.relative_to(base)
        if any(part in SKIP_DIRS for part in rel.parts) or p.is_dir():
            continue
        yield p, rel


def add(zf, arcname, data=None, path=None, executable=False):
    info = zipfile.ZipInfo(arcname, date_time=time.localtime()[:6])
    info.compress_type = zipfile.ZIP_DEFLATED
    mode = 0o755 if executable else 0o644
    info.external_attr = (stat.S_IFREG | mode) << 16
    zf.writestr(info, data if data is not None else path.read_bytes())


def version():
    m = re.search(r'<p class="ver">([^<]+)</p>', (ROOT / "changelog.html").read_text(encoding="utf-8"))
    return m.group(1).strip() if m else time.strftime("%Y-%m-%d")


def main():
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent
    out.mkdir(parents=True, exist_ok=True)
    ver = version()
    upload = out / f"tinkervision-upload-{ver}.zip"
    test = out / f"tinkervision-lokaltest-{ver}.zip"

    with zipfile.ZipFile(upload, "w") as zf:
        for p, rel in files(ROOT):
            if str(rel) in SKIP_UPLOAD:
                continue
            add(zf, rel.as_posix(), path=p, executable=bool(p.stat().st_mode & 0o111))

    top = f"tinkervision-lokaltest-{ver}"
    with zipfile.ZipFile(test, "w") as zf:
        for p, rel in files(ROOT):
            if rel.parts[0] in (".github", "tools"):
                continue
            add(zf, f"{top}/website/{rel.as_posix()}", path=p)
        add(zf, f"{top}/Lokal testen (Linux).sh", data=LINUX_MAC, executable=True)
        add(zf, f"{top}/Lokal testen (Mac).command", data=LINUX_MAC, executable=True)
        add(zf, f"{top}/Lokal testen (Windows).bat", data=WINDOWS.replace("\n", "\r\n"))
        add(zf, f"{top}/LIES MICH.txt", data=README.format(version=ver))

    print(upload)
    print(test)


if __name__ == "__main__":
    main()
