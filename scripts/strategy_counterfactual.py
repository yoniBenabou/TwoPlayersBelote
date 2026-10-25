"""Contrefactuels : un choix de l'agent rapporte-t-il des points ?

Tous les joueurs étant déterministes (PPO en mode argmax, heuristiques), une
manche se rejoue à l'identique. On rejoue donc la manche jusqu'à une décision
de l'agent, on force une autre carte à cet endroit, puis on laisse l'agent
finir la manche normalement. Gain = points (agent - adversaire) avec le choix
de l'agent - avec la carte de remplacement, sur la même donne.

Familles étudiées (sur les données de scripts.strategy_collect --shadow old) :
  - "shadow" : là où l'ancien agent (sans annonces) aurait joué autre chose ;
  - "big_ruff" : coupe avec un atout qui n'est pas le plus petit -> plus petit atout ;
  - "rich_discard" : défausse d'un As ou d'un 10 alors qu'il a une carte à 0 -> la moins chère
    ("rich_discard_on_trump" : même chose quand l'adversaire a entamé atout).

    python -m scripts.strategy_counterfactual --samples 3000
"""
import argparse
import math
import os
import pickle
import random
import sys

from belote.rl.agents import TrumpCountAgent
from belote.rl.env import CARD_INDEX, BeloteEnv
from belote.core.cards import Rank
from scripts.strategy_collect import DEFAULT_OUT, make_subject


def replay(agent, log, force_at=None, force_card=None):
    """Rejoue la manche log ; à la force_at-ième carte jouée par l'agent, joue force_card.
    Retourne points agent - points adversaire."""
    env = BeloteEnv(bidding=True, win_bonus=False)
    opponent = TrumpCountAgent()
    me = log["me"]
    obs, info = env.reset(options={"starting_player": log["first"], "deal": (*log["hands"], log["turned"])})
    agents = {me: agent, 1 - me: opponent}
    my_cards = 0
    done = False
    while not done:
        seat = env.current_idx
        action = agents[seat].act(obs, info["legal_actions"], info)
        if seat == me and env.phase == "play":
            if my_cards == force_at:
                assert info["legal_actions"][CARD_INDEX[force_card]], "carte forcée illégale"
                action = CARD_INDEX[force_card]
            my_cards += 1
        obs, _, done, info = env.step(action)
    pts = info["final_points"]
    return pts[me] - pts[1 - me]


def cheapest(cards, trump):
    return min(cards, key=lambda c: (c.points(trump), c.strength(trump)))


def candidates(data):
    """(famille, index de la manche, rang de la carte chez l'agent, carte de remplacement)."""
    out = {"shadow": [], "big_ruff": [], "rich_discard": [], "rich_discard_on_trump": []}
    counter = {}
    for p in data["plays"]:
        i = counter.get(p["r"], 0)
        counter[p["r"]] = i + 1
        hand, trump, led = p["hand"], p["trump"], p["led"]
        if p["shadow"] is not None and p["shadow"] != p["card"]:
            out["shadow"].append((p["r"], i, p["shadow"], p))
        if led is None or any(c.suit == led.suit for c in hand):
            continue
        trumps = [c for c in hand if c.suit == trump]
        if led.suit != trump and len(trumps) >= 2:
            low = min(trumps, key=lambda c: c.strength(trump))
            if p["card"] != low:
                out["big_ruff"].append((p["r"], i, low, p))
        # défausse (ni fournir ni couper, y compris sur une entame atout)
        if not trumps and p["card"].rank in (Rank.ACE, Rank.TEN) and any(c.points(trump) == 0 for c in hand):
            out["rich_discard" if led.suit != trump else "rich_discard_on_trump"].append((p["r"], i, cheapest(hand, trump), p))
    return out


def mean_ci(xs):
    n = len(xs)
    m = sum(xs) / n
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1)) if n > 1 else 0.0
    return m, 1.96 * sd / math.sqrt(n)


def main():
    parser = argparse.ArgumentParser(description="Gain en points des choix de l'agent (contrefactuels).")
    parser.add_argument("--data-dir", default=DEFAULT_OUT)
    parser.add_argument("--samples", type=int, default=3000, help="décisions tirées au hasard par famille")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    with open(os.path.join(args.data_dir, "new.pkl"), "rb") as f:
        data = pickle.load(f)
    agent = make_subject("new")[0]
    rounds = {r["k"]: r for r in data["rounds"]}
    rng = random.Random(args.seed)
    results = {}
    for family, cands in candidates(data).items():
        sample = rng.sample(cands, min(args.samples, len(cands)))
        gains, by_role = [], {}
        for r, i, alt, p in sample:
            base = replay(agent, rounds[r])
            assert base == rounds[r]["my_points"] - rounds[r]["opp_points"], "la manche ne se rejoue pas à l'identique"
            gain = base - replay(agent, rounds[r], i, alt)
            gains.append(gain)
            by_role.setdefault((p["role"], "lead" if p["lead"] else "follow"), []).append(gain)
        m, ci = mean_ci(gains)
        better = 100 * sum(g > 0 for g in gains) / len(gains)
        worse = 100 * sum(g < 0 for g in gains) / len(gains)
        results[family] = (m, ci, better, worse, len(gains), len(cands))
        print(f"{family:<13} gain moyen du choix de l'agent : {m:+.2f} points (±{ci:.2f}) | meilleur {better:.0f}% / "
              f"pire {worse:.0f}% / égal {100 - better - worse:.0f}% | n={len(gains)} sur {len(cands)} cas")
        for key, gs in sorted(by_role.items(), key=lambda kv: str(kv[0])):
            if len(gs) >= 50:
                mm, cc = mean_ci(gs)
                print(f"    {str(key[0]):<9} {key[1]:<6} {mm:+.2f} (±{cc:.2f}) n={len(gs)}")
    with open(os.path.join(args.data_dir, "counterfactual.pkl"), "wb") as f:
        pickle.dump(results, f)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
