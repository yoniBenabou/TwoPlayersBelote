"""Coinche à 4 : résultats des joueurs humains contre l'IA (et les robots), à
partir du fichier écrit par l'appli (demo4/logs/games.jsonl par défaut).

L'humain joue Sud avec un robot en Nord (sa convention) ; Est et Ouest sont
l'adversaire choisi (« ai_search » = IA + PIMC, « ai » = réseau seul, ou une
convention de robots). Les parties à deux humains (Sud et Nord) sont comptées à
part (« ai_search_duo », etc.). Ne compte que les parties terminées où les autres
mains n'ont jamais été montrées ; les parties abandonnées ("New game" en
cours de partie) et interrompues (serveur arrêté, page fermée) sont seulement
signalées. Taux de victoire de l'adversaire avec intervalle de Wilson à 95 %
(adapté aux petits échantillons), écart moyen de points par donne, détail
par joueur, prises et contrats réussis de chaque côté.

    python -m scripts.coinche_human_results
    python -m scripts.coinche_human_results --exclude Noa --opponents ai_search
"""
import argparse
import json
import math
import sys
from collections import defaultdict

DEFAULT_LOG = "demo4/logs/games.jsonl"
LABELS = {"ai_search": "IA + PIMC", "ai": "IA (réseau seul)", "asr": "AsR", "papirobert": "Papi Robert",
          "petitjeu": "Petit jeu", "simple": "Robots simples"}
LABELS.update({f"{k}_duo": f"2 joueurs vs {v}" for k, v in list(LABELS.items())})
ORDER = ["ai_search", "ai", "asr", "papirobert", "petitjeu", "simple"]
ORDER = ORDER + [f"{k}_duo" for k in ORDER]


def wilson(k, n, z=1.96):
    """Intervalle de confiance de Wilson pour une proportion k/n."""
    if n == 0:
        return float("nan"), float("nan")
    p = k / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def mean_ci(values):
    n = len(values)
    if n == 0:
        return float("nan"), float("nan")
    m = sum(values) / n
    if n < 2:
        return m, float("nan")
    sd = math.sqrt(sum((v - m) ** 2 for v in values) / (n - 1))
    return m, 1.96 * sd / math.sqrt(n)


def load(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def label(key):
    return LABELS.get(key, key)


def opp_wins(games):
    """Victoires de l'adversaire, égalités comptées pour moitié."""
    return sum(g["winner"] == "opponents" for g in games) + sum(g["winner"] is None for g in games) / 2


def deal_stats(deals):
    """Écarts par donne (adversaire - joueurs), prises et réussites de chaque côté."""
    played = [d for d in deals if not d["redeal"]]
    diffs = [d["scores"]["opponents"] - d["scores"]["you"] for d in played]
    side = {}
    for team in ("opponents", "you"):
        taken = [d for d in played if d["contract"]["team"] == team]
        side[team] = {"taken": len(taken), "made": sum(d["made"] for d in taken),
                      "coinched": sum(d["contract"]["mult"] > 1 for d in taken),
                      "capots": sum(d.get("capot_team") == team for d in taken)}
    return played, diffs, side


def main():
    parser = argparse.ArgumentParser(description="Résultats des joueurs humains contre l'IA à la Coinche à 4.")
    parser.add_argument("--log", default=DEFAULT_LOG)
    parser.add_argument("--exclude", nargs="*", default=[], help="joueurs à exclure (ex. les auteurs du projet)")
    parser.add_argument("--opponents", default="ai_search",
                        help="adversaire étudié en détail : ai_search, ai, asr, papirobert, petitjeu, simple (+ _duo à deux)")
    parser.add_argument("--model", help="ne garder que les parties contre ce modèle (chemin du .pt, ou un bout du chemin)")
    args = parser.parse_args()
    records = load(args.log)
    excluded = {name.lower() for name in args.exclude}
    keep = lambda r: ((r.get("player") or "").lower() not in excluded
                      and (not args.model or args.model in (r.get("model") or "") or not r["opponents"].startswith("ai")))
    records = [r for r in records if keep(r)]
    for r in records:  # parties à deux humains : un adversaire à part
        if r.get("humans") == 2:
            r["opponents"] += "_duo"
            r["player"] = " + ".join(r["players"].values())

    games = [r for r in records if r["type"] == "game"]
    finished = [g for g in games if g["status"] == "finished" and not g["revealed"]]
    print(f"Parties enregistrées : {len(games)} (terminées : {sum(g['status'] == 'finished' for g in games)}, "
          f"abandonnées : {sum(g['status'] == 'abandoned' for g in games)}, "
          f"autres mains regardées : {sum(g['revealed'] for g in games)})")
    closed = {g["game_id"] for g in games}
    interrupted = {r["game_id"] for r in records if r["type"] == "deal" and r["game_id"] not in closed}
    if interrupted:
        print(f"Parties interrompues (serveur arrêté ou page fermée, non comptées) : {len(interrupted)}")
    models = sorted({g["model"] for g in finished if g.get("model")})
    if len(models) > 1:
        print("Attention, plusieurs modèles d'IA mélangés (--model pour en garder un) : " + ", ".join(models))
    if not finished:
        print("Aucune partie terminée sans regarder les autres mains.")
        return

    by_opp = defaultdict(list)
    for g in finished:
        by_opp[g["opponents"]].append(g)
    ids = {g["game_id"] for g in finished}
    deals_by_opp = defaultdict(list)
    for r in records:
        if r["type"] == "deal" and r["game_id"] in ids:
            deals_by_opp[r["opponents"]].append(r)

    print("\nPar adversaire (en solo, l'humain joue avec un robot partenaire) :")
    for k in [k for k in ORDER if k in by_opp] + [k for k in by_opp if k not in ORDER]:
        gs = by_opp[k]
        w = opp_wins(gs)
        lo, hi = wilson(w, len(gs))
        _played, diffs, _side = deal_stats(deals_by_opp[k])
        m, ci = mean_ci(diffs)
        print(f"  {label(k):<18} {len(gs):>4} parties, l'adversaire gagne {100 * w / len(gs):5.1f}% "
              f"(IC 95 % [{100 * lo:.1f}% ; {100 * hi:.1f}%]) ; "
              f"écart {m:+.1f} pts/donne (±{ci:.1f}) sur {len(diffs)} donnes")

    focus = args.opponents
    focus_games = by_opp.get(focus, [])
    focus_deals = deals_by_opp.get(focus, [])
    print(f"\nDétail contre {label(focus)} :")
    if not focus_games:
        print("  aucune partie terminée.")
    else:
        print(f"  {'Joueur':<20} {'parties':>7} {'adversaire gagne':>17} {'score moyen (joueur - adversaire)':>36}")
        by_player = defaultdict(list)
        for g in focus_games:
            by_player[g["player"] or "?"].append(g)
        for player, gs in sorted(by_player.items(), key=lambda kv: -len(kv[1])):
            print(f"  {player:<20} {len(gs):>7} {opp_wins(gs):>17g} "
                  f"{sum(g['totals']['you'] for g in gs) / len(gs):>20.0f} - "
                  f"{sum(g['totals']['opponents'] for g in gs) / len(gs):.0f}")
        played, _diffs, side = deal_stats(focus_deals)
        for team, name in (("opponents", label(focus)), ("you", "Joueurs")):
            s = side[team]
            print(f"  {name:<18} prise {100 * s['taken'] / max(1, len(played)):.0f}% des donnes, contrats réussis "
                  f"{100 * s['made'] / max(1, s['taken']):.0f}%, coinchés {100 * s['coinched'] / max(1, s['taken']):.0f}%, "
                  f"capots réussis {s['capots']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
