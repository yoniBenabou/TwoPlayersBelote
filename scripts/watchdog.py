"""Surveille des entraînements lancés dans tmux et relance ceux qui sont morts
ou bloqués, avec --resume (reprise exacte depuis checkpoints/resume_state.pt).

    python -m scripts.watchdog /chemin/experiments/run1 /chemin/experiments/run2:session_tmux

Chaque argument est le dossier --out-dir d'un entraînement, suivi en option de
":nom_de_session_tmux" (par défaut : le nom du dossier). À lancer lui-même dans
tmux pour qu'il tourne la nuit :

    tmux new-session -d -s watchdog "python -m scripts.watchdog DIR1:bid1 DIR2:bid2"

Un run est "terminé" quand son train.log contient la ligne de fin ; "bloqué"
quand son train.log n'a pas bougé depuis --stall-minutes alors que sa session
tmux tourne encore. Au-delà de --max-restarts relances, il est abandonné (pour
ne pas boucler sur un vrai bug : voir alors nan_dump.pt ou la fin du log).
Tout est journalisé dans watchdog.log à côté de train.log.
"""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FINISHED_MARKER = "=== Entraînement terminé ==="
RESUME_FILE = os.path.join("checkpoints", "resume_state.pt")


def decide(finished, alive, log_age_minutes, restarts, has_resume_state, stall_minutes, max_restarts):
    """Que faire d'un run ? Retourne "done", "ok", "restart", "kill_restart" ou "give_up"."""
    if finished:
        return "done"
    stalled = alive and log_age_minutes is not None and log_age_minutes > stall_minutes
    if alive and not stalled:
        return "ok"
    if restarts >= max_restarts or not has_resume_state:
        return "give_up"
    return "kill_restart" if stalled else "restart"


def tmux_alive(session):
    return subprocess.run(["tmux", "has-session", "-t", session], capture_output=True).returncode == 0


def run_status(run_dir):
    log = os.path.join(run_dir, "train.log")
    finished, age = False, None
    if os.path.exists(log):
        with open(log, encoding="utf-8", errors="replace") as f:
            finished = FINISHED_MARKER in f.read()
        age = (time.time() - os.path.getmtime(log)) / 60
    return finished, age


def training_module(run_dir):
    """scripts.train (belote à 2) ou scripts.train_coinche (Coinche à 4, config avec total_deals)."""
    try:
        with open(os.path.join(run_dir, "config.json")) as f:
            return "scripts.train_coinche" if "total_deals" in json.load(f) else "scripts.train"
    except (OSError, ValueError):
        return "scripts.train"


def relaunch(run_dir, session, threads):
    command = (
        f"cd {REPO} && PYTHONPATH={REPO} OMP_NUM_THREADS={threads} MKL_NUM_THREADS={threads} "
        f"{sys.executable} -u -m {training_module(run_dir)} --resume --out-dir {run_dir} 2>&1 | tee -a {run_dir}/train.log"
    )
    subprocess.run(["tmux", "new-session", "-d", "-s", session, command], check=True)


def log(run_dir, message):
    line = f"[{datetime.now():%Y-%m-%d %H:%M}] {os.path.basename(run_dir)} : {message}"
    print(line, flush=True)
    with open(os.path.join(run_dir, "watchdog.log"), "a", encoding="utf-8") as f:
        f.write(line + "\n")


def check_once(runs, stall_minutes, max_restarts, threads):
    """Un passage sur tous les runs. Retourne True s'il reste des runs à surveiller."""
    pending = False
    for run_dir, session in runs:
        state_path = os.path.join(run_dir, "watchdog.json")
        state = json.load(open(state_path)) if os.path.exists(state_path) else {"restarts": 0, "given_up": False}
        if state["given_up"]:
            continue
        finished, age = run_status(run_dir)
        alive = tmux_alive(session)
        action = decide(finished, alive, age, state["restarts"], os.path.exists(os.path.join(run_dir, RESUME_FILE)),
                        stall_minutes, max_restarts)
        if action in ("restart", "kill_restart"):
            if action == "kill_restart":
                subprocess.run(["tmux", "kill-session", "-t", session], capture_output=True)
                log(run_dir, f"bloqué (log inchangé depuis {age:.0f} min) : session arrêtée")
            relaunch(run_dir, session, threads)
            state["restarts"] += 1
            log(run_dir, f"relancé avec --resume (relance {state['restarts']}/{max_restarts})")
        elif action == "give_up":
            state["given_up"] = True
            reason = "plus d'état de reprise" if not os.path.exists(os.path.join(run_dir, RESUME_FILE)) \
                else f"{max_restarts} relances déjà faites"
            log(run_dir, f"ABANDON ({reason}) : voir la fin de train.log et nan_dump.pt s'il existe")
        json.dump(state, open(state_path, "w"))
        pending = pending or action not in ("done", "give_up")
    return pending


def main():
    parser = argparse.ArgumentParser(description="Surveille et relance des entraînements tmux (--resume).")
    parser.add_argument("runs", nargs="+", help="dossier d'entraînement, optionnellement suivi de :session_tmux")
    parser.add_argument("--interval", type=int, default=30, help="minutes entre deux vérifications")
    parser.add_argument("--stall-minutes", type=int, default=60, help="log inchangé depuis ce délai = run bloqué")
    parser.add_argument("--max-restarts", type=int, default=3)
    parser.add_argument("--threads", type=int, default=3, help="OMP_NUM_THREADS des runs relancés")
    parser.add_argument("--once", action="store_true", help="une seule vérification puis sortie")
    args = parser.parse_args()

    runs = []
    for spec in args.runs:
        run_dir, _, session = spec.partition(":")
        run_dir = os.path.abspath(run_dir)
        runs.append((run_dir, session or os.path.basename(run_dir)))

    while check_once(runs, args.stall_minutes, args.max_restarts, args.threads) and not args.once:
        time.sleep(args.interval * 60)
    print("Plus rien à surveiller.", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
