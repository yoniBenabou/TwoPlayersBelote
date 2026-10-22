"""Démo web : jouer à la belote à deux contre l'agent PPO dans le navigateur.

    python -m demo.server            # puis ouvrir http://localhost:8000
    python -m demo.server --port 8080 --target 301

Sur la machine du Technion, VS Code (onglet Ports) redirige le port vers
ton navigateur. Uniquement la bibliothèque standard : pas de dépendance en plus.
"""
import argparse
import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from demo.game import DEFAULT_TARGET_SCORE, GameSession, IllegalMove

INDEX_HTML = Path(__file__).with_name("index.html")


def make_handler(session):
    lock = threading.Lock()  # une seule partie partagée : on sérialise les actions

    class Handler(BaseHTTPRequestHandler):
        def _send(self, status, body, content_type="application/json; charset=utf-8"):
            data = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                self._send(200, INDEX_HTML.read_bytes(), "text/html; charset=utf-8")
            elif self.path == "/api/state":
                with lock:
                    self._send(200, session.state([]))
            else:
                self._send(404, {"error": "not found"})

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except json.JSONDecodeError:
                return self._send(400, {"error": "invalid JSON"})
            actions = {
                "/api/new": lambda: session.new_game(),
                "/api/play": lambda: session.play_human(payload.get("card")),
                "/api/next": lambda: session.next_round(),
            }
            if self.path not in actions:
                return self._send(404, {"error": "not found"})
            with lock:
                try:
                    self._send(200, actions[self.path]())
                except (IllegalMove, TypeError, ValueError) as exc:
                    self._send(400, {"error": str(exc)})

        def log_message(self, fmt, *args):
            pass  # pas de log à chaque requête

    return Handler


def main():
    parser = argparse.ArgumentParser(description="Démo web : belote à deux contre l'agent PPO.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--checkpoint", default="models/ppo_CA_3M.pt")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET_SCORE)
    args = parser.parse_args()

    session = GameSession(args.checkpoint, target=args.target)
    # La machine du Technion est partagée : si le port est pris (par un autre
    # utilisateur), on essaie les suivants plutôt que d'échouer.
    for port in range(args.port, args.port + 50):
        try:
            server = ThreadingHTTPServer((args.host, port), make_handler(session))
            break
        except OSError:
            continue
    else:
        sys.exit(f"No free port between {args.port} and {args.port + 49}.")
    print(f"Belote demo running: http://localhost:{port}  (Ctrl+C to stop)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
