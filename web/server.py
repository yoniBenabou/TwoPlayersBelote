"""Site web de Coinche à 4 : tu joues Sud avec un partenaire en Nord (l'IA, un robot à
convention ou un ami invité par lien) contre l'IA entraînée en Est et Ouest.

    python -m web.server                         # puis ouvrir http://localhost:8200
    python -m web.server --model chemin/ppo.pt   # autre modèle de l'IA
    python -m web.server --study                 # mains des autres jamais montrées

Même API que coinche4 (/api/state, /api/setup, /api/step, /api/duo/create, ...), servie
par le gestionnaire de coinche4 ; seule la page (web/index.html) et la table (WebTable, qui
accepte l'IA comme partenaire) changent. Donnes et parties sont ajoutées à --log
(web/logs/games.jsonl par défaut), et envoyées à Supabase si SUPABASE_URL et
SUPABASE_SECRET_KEY sont définies. Uniquement la bibliothèque standard (plus torch pour l'IA).
"""
import argparse
import os
import sys
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

import torch

from belote.coinche.engine import DEFAULT_TARGET
from coinche4.game import load_network
from coinche4.server import DEFAULT_MODEL, Tables, make_handler
from coinche4.supabase_log import SupabaseGameLog
from demo.game import GameLog
from web.game import WebTable

HERE = Path(__file__).resolve().parent
INDEX_HTML = HERE / "index.html"
DEFAULT_LOG = str(HERE / "logs" / "games.jsonl")


class WebTables(Tables):
    def _new_table(self):
        return WebTable(target=self.target, bots=self.bots, network=self.network, log=self.log,
                        study=self.study, model=self.model)


def make_web_handler(tables):
    base = make_handler(tables)

    class Handler(base):
        def do_GET(self):
            if urlparse(self.path).path in ("/", "/index.html"):
                return self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
            return super().do_GET()

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Site de Coinche à 4 (toi et ton partenaire contre l'IA).")
    parser.add_argument("--port", type=int, default=8200)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="modèle .pt de l'IA (Coinche à 4, avec annonces)")
    parser.add_argument("--log", default=DEFAULT_LOG, help="fichier JSONL des donnes et parties ('' : rien)")
    parser.add_argument("--study", action="store_true", help="mains des autres toujours cachées")
    args = parser.parse_args()
    log = None
    if args.log:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        if os.environ.get("SUPABASE_URL") and os.environ.get("SUPABASE_SECRET_KEY"):
            log = SupabaseGameLog(args.log)
            print("Supabase logging enabled", flush=True)
        else:
            log = GameLog(args.log)
    torch.set_num_threads(1)  # un cœur par coup de l'IA : plusieurs tables en même temps ne se gênent pas
    network = load_network(args.model)
    print(f"AI model: {args.model}" if network is not None else f"AI model not found ({args.model}): AI disabled",
          flush=True)
    tables = WebTables(args.target, "simple", network, log, args.study, os.path.abspath(args.model))
    for port in range(args.port, args.port + 50):
        try:
            server = ThreadingHTTPServer((args.host, port), make_web_handler(tables))
            break
        except OSError:
            continue
    else:
        sys.exit(f"No free port between {args.port} and {args.port + 49}.")
    print(f"Coinche site running: http://localhost:{port}  (games logged to {args.log or 'nowhere'})  (Ctrl+C to stop)",
          flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
