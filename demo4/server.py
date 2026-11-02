"""Coinche à 4 dans le navigateur : tu joues Sud, avec Nord comme partenaire,
contre Est et Ouest. Écran d'accueil : ton nom, ta convention (jouée aussi par
ton partenaire) et tes adversaires (une convention, ou l'IA entraînée).

    python -m demo4.server                  # puis ouvrir http://localhost:8100
    python -m demo4.server --model chemin/ppo.pt   # modèle de l'IA (par défaut : DEFAULT_MODEL)
    python -m demo4.server --bots petitjeu  # robots qui annoncent au petit jeu
    python -m demo4.server --bots papirobert  # robots au jeu aux As de Papi Robert
    python -m demo4.server --bots asr  # robots aux conventions AsR
    python -m demo4.server --study --model chemin/ppo.pt  # parties contre des volontaires

Chaque donne et chaque partie est ajoutée à --log (JSONL, demo4/logs/games.jsonl
par défaut) ; scripts.coinche_human_results en tire les résultats et les
graphiques. --study cache le bouton "Show all hands" (mains des autres jamais
montrées) ; hors --study, une partie où les mains ont été montrées est marquée
et laissée de côté dans les résultats.

Chaque navigateur a sa propre table (cookie coinche_sid). Bouton "Show all
hands" pour vérifier les règles, bouton "Rules" pour les règles appliquées.
Uniquement la bibliothèque standard.
"""
import argparse
import json
import os
import secrets
import sys
import threading
import time
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from belote.coinche.engine import DEFAULT_TARGET
from demo.game import GameLog
from demo4.game import BOT_KINDS, IllegalMove, Table, load_network

INDEX_HTML = Path(__file__).with_name("index.html")
COOKIE = "coinche_sid"
MAX_TABLES = 200
# meilleur modèle à 4 avec la recherche (experiments/coinche_robots25_warm_asr2, 8 M de donnes dont un quart contre les robots)
DEFAULT_MODEL = str(Path(__file__).resolve().parent.parent / "models" / "coinche_4p.pt")
DEFAULT_LOG = str(Path(__file__).with_name("logs") / "games.jsonl")


class Tables:
    def __init__(self, target, bots="simple", network=None, log=None, study=False, model=None):
        self.target = target
        self.bots = bots
        self.network = network
        self.log = log
        self.study = study
        self.model = model
        self.tables = {}  # sid -> [Table, verrou, dernier accès]
        self.lock = threading.Lock()

    def get(self, sid):
        with self.lock:
            if sid not in self.tables:
                if len(self.tables) >= MAX_TABLES:
                    del self.tables[min(self.tables, key=lambda k: self.tables[k][2])]
                sid = secrets.token_urlsafe(16)
                self.tables[sid] = [Table(target=self.target, bots=self.bots, network=self.network, log=self.log,
                                          study=self.study, model=self.model),
                                    threading.Lock(), time.time()]
            entry = self.tables[sid]
            entry[2] = time.time()
            return sid, entry[0], entry[1]


def make_handler(tables):
    class Handler(BaseHTTPRequestHandler):
        def _table(self):
            cookie = SimpleCookie(self.headers.get("Cookie") or "")
            return tables.get(cookie[COOKIE].value if COOKIE in cookie else None)

        def _send(self, status, body, content_type="application/json; charset=utf-8", sid=None):
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            if sid:
                self.send_header("Set-Cookie", f"{COOKIE}={sid}; Path=/; Max-Age=2592000; HttpOnly; SameSite=Lax")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                sid, table, lock = self._table()
                with lock:
                    self._send(200, table.state([]), sid=sid)
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"error": "invalid JSON"})
            sid, table, lock = self._table()
            actions = {
                "/api/new": lambda: table.new_game(),
                "/api/setup": lambda: table.setup(payload),
                "/api/bid": lambda: table.bid_human(payload),
                "/api/play": lambda: table.play_human(payload.get("card")),
                "/api/next": lambda: table.next_deal(),
                "/api/reveal": lambda: table.set_reveal(payload.get("on")),
                "/api/coinche-now": lambda: table.coinche_now(),
                "/api/continue": lambda: table.continue_bidding(),
            }
            if self.path not in actions:
                return self._send(404, {"error": "not found"})
            with lock:
                try:
                    self._send(200, actions[self.path](), sid=sid)
                except (IllegalMove, TypeError, ValueError) as exc:
                    self._send(400, {"error": str(exc)}, sid=sid)

        def log_message(self, fmt, *args):
            pass

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Coinche à 4 dans le navigateur (Sud contre des robots).")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET)
    parser.add_argument("--bots", choices=sorted(BOT_KINDS), default="simple",
                        help="robots de la table avant l'écran d'accueil : simple, petitjeu, papirobert ou asr")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="modèle .pt de l'IA (Coinche à 4, avec annonces)")
    parser.add_argument("--log", default=DEFAULT_LOG, help="fichier JSONL des donnes et parties ('' : rien)")
    parser.add_argument("--study", action="store_true", help="parties contre des volontaires : mains des autres cachées")
    args = parser.parse_args()
    log = None
    if args.log:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        log = GameLog(args.log)
    network = load_network(args.model)
    print(f"AI model: {args.model}" if network is not None else f"AI model not found ({args.model}): AI disabled",
          flush=True)
    tables = Tables(args.target, args.bots, network, log, args.study, os.path.abspath(args.model))
    for port in range(args.port, args.port + 50):
        try:
            server = ThreadingHTTPServer((args.host, port), make_handler(tables))
            break
        except OSError:
            continue
    else:
        sys.exit(f"No free port between {args.port} and {args.port + 49}.")
    mode = "study mode, other hands hidden" if args.study else "demo mode"
    print(f"Coinche (4 players) running: http://localhost:{port}  ({mode}; games logged to {args.log or 'nowhere'})"
          "  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
