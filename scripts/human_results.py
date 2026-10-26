"""Résultats de l'agent contre des humains (point C), à partir du fichier
écrit par la démo web (demo/logs/games.jsonl par défaut).

Les réglages de l'agent (réseau seul, recherche PIMC à K mains) sont séparés ;
--search K n'en garde qu'un. Ne compte que les parties terminées où le joueur n'a pas regardé la main de
l'agent ; les parties abandonnées ("New game" en cours de partie) et
interrompues (serveur arrêté ou page fermée) sont seulement signalées. Taux de victoire de l'agent avec intervalle de Wilson à 95 %
(adapté aux petits échantillons), détail par joueur, et statistiques par
manche (écart de points, prises et dedans de chaque côté).

    python -m scripts.human_results
    python -m scripts.human_results --log demo/logs/games.jsonl --exclude Noa
"""
import argparse
import json
import math
import sys
from collections import defaultdict

DEFAULT_LOG = "demo/logs/games.jsonl"


def wilson(k, n, z=1.96):
    """Intervalle de confiance de Wilson pour une proportion k/n."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    parser = argparse.ArgumentParser(description="Taux de victoire de l'agent contre des humains.")
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--exclude", nargs="*", default=[], help="joueurs à exclure (ex. les auteurs du projet)")
    parser.add_argument("--search", type=int, help="ne garder qu'un réglage de l'agent : 0 = réseau seul, K = recherche PIMC")
    args = parser.parse_args()
    records = load(args.log)
    excluded = {name.lower() for name in args.exclude}
    keep = lambda r: (r.get("player") or "").lower() not in excluded

    games = [r for r in records if r["type"] == "game" and keep(r)]
    finished = [g for g in games if g["status"] == "finished" and not g["revealed"]]
    print(f"Parties enregistrées : {len(games)} (terminées : {sum(g['status'] == 'finished' for g in games)}, "
          f"abandonnées : {sum(g['status'] == 'abandoned' for g in games)}, "
          f"main de l'agent regardée : {sum(g['revealed'] for g in games)})")
    # Manches d'une partie jamais close : serveur arrêté ou onglet fermé en cours de partie.
    closed = {g["game_id"] for g in records if g["type"] == "game"}
    interrupted = {r["game_id"] for r in records if r["type"] == "round" and r["game_id"] not in closed and keep(r)}
    if interrupted:
        print(f"Parties interrompues (serveur arrêté ou page fermée en cours de partie, non comptées) : {len(interrupted)}")
    setting = lambda g: g.get("search", 0)  # parties enregistrées avant l'option : réseau seul
    by_setting = defaultdict(list)
    for g in finished:
        by_setting[setting(g)].append(g)
    if len(by_setting) > 1 or args.search is not None:
        print("\nPar réglage de l'agent :")
        for k, gs in sorted(by_setting.items()):
            w = sum(g["winner"] == "agent" for g in gs) + sum(g["winner"] is None for g in gs) / 2
            lo, hi = wilson(w, len(gs))
            label = "réseau seul" if k == 0 else f"recherche PIMC, {k} mains"
            print(f"  {label:<26} {len(gs):>4} parties, l'agent gagne {100 * w / len(gs):.1f}% "
                  f"(IC 95 % [{100 * lo:.1f}% ; {100 * hi:.1f}%])")
    if args.search is not None:
        finished = by_setting.get(args.search, [])
        print(f"\nDétail pour le réglage --search {args.search} :")
    elif len(by_setting) > 1:
        print("\nDétail, tous réglages confondus (--search K pour un seul) :")
    n = len(finished)
    if n == 0:
        print("Aucune partie terminée sans regarder la main de l'agent.")
        return
    wins = sum(g["winner"] == "agent" for g in finished)
    draws = sum(g["winner"] is None for g in finished)
    lo, hi = wilson(wins + draws / 2, n)
    print(f"\nL'agent gagne {wins} parties sur {n} ({100 * (wins + draws / 2) / n:.1f}%, "
          f"IC 95 % [{100 * lo:.1f}% ; {100 * hi:.1f}%]), {draws} égalité(s) comptée(s) pour moitié.")

    print(f"\n{'Joueur':<20} {'parties':>7} {'agent gagne':>12} {'score moyen (joueur - agent)':>30}")
    by_player = defaultdict(list)
    for g in finished:
        by_player[g["player"] or "?"].append(g)
    for player, gs in sorted(by_player.items(), key=lambda kv: -len(kv[1])):
        w = sum(g["winner"] == "agent" for g in gs)
        print(f"{player:<20} {len(gs):>7} {w:>12} {sum(g['you'] for g in gs) / len(gs):>14.0f} - "
              f"{sum(g['agent'] for g in gs) / len(gs):.0f}")

    ids = {g["game_id"] for g in finished}
    rounds = [r for r in records if r["type"] == "round" and r["game_id"] in ids and not r["redeal"]]
    if rounds:
        diffs = [r["points"]["agent"] - r["points"]["you"] for r in rounds]
        m = sum(diffs) / len(diffs)
        sd = math.sqrt(sum((d - m) ** 2 for d in diffs) / max(len(diffs) - 1, 1))
        print(f"\nPar manche ({len(rounds)} manches) : écart moyen agent - joueur {m:+.1f} points "
              f"(±{1.96 * sd / math.sqrt(len(diffs)):.1f})")
        for side, name in (("agent", "l'agent prend"), ("you", "les joueurs prennent")):
            takes = [r for r in rounds if r["taker"] == side]
            if takes:
                print(f"  {name} dans {100 * len(takes) / len(rounds):.0f}% des manches, dedans "
                      f"{100 * sum(r['dedans'] for r in takes) / len(takes):.0f}% du temps")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
