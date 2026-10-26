"""Démo web : jouer à la belote à deux contre l'agent PPO dans le navigateur.

    python -m demo.server            # puis ouvrir http://localhost:8000
    python -m demo.server --port 8080 --target 301
    python -m demo.server --study    # parties contre des volontaires (point C)

Chaque navigateur a sa propre partie (cookie belote_sid) : plusieurs personnes
peuvent jouer en même temps. Chaque manche et chaque partie sont enregistrées
dans --log (JSONL, demo/logs/games.jsonl par défaut) ; scripts.human_results
en tire le taux de victoire de l'agent. --study cache la main de l'agent
(le bouton pour la voir disparaît, et elle n'est jamais envoyée).

Sur la machine du Technion, VS Code (onglet Ports) redirige le port vers
ton navigateur. Uniquement la bibliothèque standard : pas de dépendance en plus.
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

from demo.game import DEFAULT_CHECKPOINT, DEFAULT_TARGET_SCORE, GameLog, GameSession, IllegalMove
from scripts.compare_checkpoints import load_agent

INDEX_HTML = Path(__file__).with_name("index.html")
DEFAULT_LOG = str(Path(__file__).with_name("logs") / "games.jsonl")
COOKIE = "belote_sid"
MAX_SESSIONS = 500  # au-delà, on oublie les parties restées inactives le plus longtemps


class Sessions:
    """Une GameSession par navigateur, toutes avec le même agent (chargé une fois)."""

    def __init__(self, checkpoint, target, log, study):
        self.agent = load_agent(checkpoint)
        self.kwargs = {"checkpoint": checkpoint, "target": target, "log": log, "study": study, "agent": self.agent}
        self.sessions = {}  # sid -> [GameSession, verrou, dernier accès]
        self.lock = threading.Lock()

    def get(self, sid):
        """(sid, session, verrou) ; nouvelle session si sid est inconnu."""
        with self.lock:
            if sid not in self.sessions:
                if len(self.sessions) >= MAX_SESSIONS:
                    oldest = min(self.sessions, key=lambda k: self.sessions[k][2])
                    del self.sessions[oldest]
                sid = secrets.token_urlsafe(16)
                self.sessions[sid] = [GameSession(**self.kwargs), threading.Lock(), time.time()]
            entry = self.sessions[sid]
            entry[2] = time.time()
            return sid, entry[0], entry[1]


def make_handler(sessions):
    class Handler(BaseHTTPRequestHandler):
        def _session(self):
            cookie = SimpleCookie(self.headers.get("Cookie") or "")
            sid = cookie[COOKIE].value if COOKIE in cookie else None
            return sessions.get(sid)

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
                sid, session, lock = self._session()
                with lock:
                    self._send(200, session.state([]), sid=sid)
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"error": "invalid JSON"})
            sid, session, lock = self._session()
            actions = {
                "/api/new": lambda: session.new_game(),
                "/api/play": lambda: session.play_human(payload.get("card")),
                "/api/bid": lambda: session.bid_human(payload.get("bid")),
                "/api/next": lambda: session.next_round(),
                "/api/name": lambda: session.set_player(payload.get("name")),
                "/api/reveal": lambda: session.reveal(payload.get("on")),
            }
            if self.path not in actions:
                return self._send(404, {"error": "not found"})
            with lock:
                try:
                    self._send(200, actions[self.path](), sid=sid)
                except (IllegalMove, TypeError, ValueError) as exc:
                    self._send(400, {"error": str(exc)}, sid=sid)

        def log_message(self, fmt, *args):
            pass  # pas de log à chaque requête

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Démo web : belote à deux contre l'agent PPO.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT,
                        help="modèle avec annonces (par défaut) ou sans (atout tiré au hasard)")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET_SCORE)
    parser.add_argument("--log", default=DEFAULT_LOG, help="fichier JSONL des manches et parties ('' : rien)")
    parser.add_argument("--study", action="store_true", help="parties contre des volontaires : main de l'agent cachée")
    args = parser.parse_args()

    log = None
    if args.log:
        os.makedirs(os.path.dirname(os.path.abspath(args.log)), exist_ok=True)
        log = GameLog(args.log)
    sessions = Sessions(args.checkpoint, args.target, log, args.study)
    # La machine du Technion est partagée : si le port est pris (par un autre
    # utilisateur), on essaie les suivants plutôt que d'échouer.
    for port in range(args.port, args.port + 50):
        try:
            server = ThreadingHTTPServer((args.host, port), make_handler(sessions))
            break
        except OSError:
            continue
    else:
        sys.exit(f"No free port between {args.port} and {args.port + 49}.")
    mode = "study mode, agent's hand hidden" if args.study else "demo mode"
    print(f"Belote demo running: http://localhost:{port}  ({mode}; games logged to {args.log or 'nowhere'})"
          "  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
