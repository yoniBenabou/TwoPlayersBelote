import sys

from belote.cli import run

if __name__ == "__main__":
    # La console Windows utilise parfois un encodage (cp1252) qui ne
    # supporte pas les symboles de cartes (♠ ♥ ♦ ♣) : on force l'UTF-8.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    run()
