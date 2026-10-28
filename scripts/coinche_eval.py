"""Coinche à 4 : match entre deux équipes, avec statistiques d'annonces.

Chaque équipe est un modèle .pt (scripts/train_coinche.py), "bots"
(CoincheBot) ou "random" (cartes au hasard parmi les cartes jouables ; ses
annonces sont faites par CoincheBot, des annonces au hasard n'ayant pas de sens). Un modèle entraîné avec --bidding annonce pour ses places ; un
modèle "cartes seulement" laisse les annonces de ses places à CoincheBot.

Donnes dupliquées : chaque donne (mains, donneur) est jouée deux fois, l'équipe
A en Sud-Nord puis en Est-Ouest. Puis des parties complètes en 1 500 points.

    python -m scripts.coinche_eval --a experiments/coinche_bid_mix25_seed1/checkpoints/ppo_04000000.pt --b bots
"""
import argparse
import random
import sys
from collections import Counter, defaultdict

import torch

from belote.coinche.engine import CAPOT, DEFAULT_TARGET, SEAT_NAMES, team_of
from belote.coinche.rl_env import NUM_ACTIONS_BIDDING, NUM_ACTIONS_PLAY, CoincheEnv
from belote.rl.networks import ActorCriticNetwork
from belote.rl.ppo_agent import PPOAgent
from scripts.train_coinche import mean_ci


class Side:
    """Une équipe : réseau (coup le plus probable) ou robots."""

    def __init__(self, spec):
        self.name = spec
        self.agent = None
        self.bids = False
        self.rng = random.Random(1)
        if spec not in ("bots", "random"):
            network = ActorCriticNetwork.from_checkpoint(spec)
            network.eval()
            self.agent = PPOAgent(network, deterministic=True)
            self.bids = network.num_actions == NUM_ACTIONS_BIDDING

    def act(self, env, obs):
        if self.name == "random" and env.phase == "play":
            return self.rng.choice([i for i, ok in enumerate(env.legal_mask()) if ok])
        if self.agent is None or (env.phase == "bidding" and not self.bids):
            return env.play_bot()
        mask = env.legal_mask()
        if not self.bids:
            mask = mask[:NUM_ACTIONS_PLAY]
        return self.agent.act(obs, mask)


def play_deal(env, sides, deal=None):
    """sides[t] joue l'équipe t. Retourne env.game.result (None si redistribution)."""
    bid_seats = {s for s in range(4) if sides[team_of(s)].bids}
    obs = env.reset(deal=deal, bid_seats=bid_seats)
    done = env.done
    while not done:
        obs, _rewards, done = env.step(sides[team_of(env.current)].act(env, obs))
    return None if env.game.phase == "redeal" else env.game.result


def main():
    parser = argparse.ArgumentParser(description="Match Coinche à 4 entre deux équipes (modèle .pt ou bots).")
    parser.add_argument("--a", required=True)
    parser.add_argument("--b", default="bots")
    parser.add_argument("--deals", type=int, default=2000, help="donnes dupliquées (jouées 2 fois chacune)")
    parser.add_argument("--games", type=int, default=200, help="parties en 1 500 points")
    parser.add_argument("--seed", type=int, default=777)
    parser.add_argument("--show", type=int, default=0, help="affiche le déroulé des N premières donnes")
    args = parser.parse_args()
    torch.set_num_threads(1)
    a, b = Side(args.a), Side(args.b)
    env = CoincheEnv(bidding=a.bids or b.bids, seed=args.seed)
    # stats par équipe ("A" / "B")
    takes, made, coinched, capots = Counter(), Counter(), Counter(), Counter()
    by_value = defaultdict(lambda: [0, 0])  # (équipe, valeur) -> [pris, réussis]
    redeals = 0
    diffs = []
    for i in range(args.deals):
        deal = env.random_deal()
        pair = []
        for a_team in (0, 1):
            sides = [a, b] if a_team == 0 else [b, a]
            try:
                result = play_deal(env, sides, deal)
            except ValueError:  # donne imposée sans contrat (tous des robots qui passent)
                result = None
            if result is None:
                redeals += 1
                pair.append(0.0)
                continue
            s = result["scores"]
            pair.append(s[a_team] - s[1 - a_team])
            c = result["contract"]
            who = "A" if team_of(c["seat"]) == a_team else "B"
            takes[who] += 1
            made[who] += result["made"]
            coinched[who] += c["mult"] > 1
            capots[who] += result["capot_team"] is not None and (result["capot_team"] == team_of(c["seat"]))
            v = by_value[(who, c["value"])]
            v[0] += 1
            v[1] += result["made"]
            if i < args.show:
                print(f"Donne {i + 1}, A en {'Sud-Nord' if a_team == 0 else 'Est-Ouest'} : annonces "
                      + ", ".join(f"{SEAT_NAMES[st]} {act}" for st, act in env.game.bids)
                      + f" -> {'réussi' if result['made'] else 'chuté'}, points {result['points']}, scores {s}")
        diffs.append(sum(pair) / 2)
    m, ci = mean_ci(diffs)
    n = 2 * args.deals
    print(f"\n{args.a}\n  contre {args.b}")
    print(f"Donnes dupliquées ({args.deals} x 2) : écart A - B = {m:+.1f} points par donne (±{ci:.1f}) ; "
          f"redistributions {redeals}")
    for who in ("A", "B"):
        t = takes[who]
        print(f"  {who} prend {100 * t / n:4.1f}% des donnes, réussit {100 * made[who] / max(1, t):4.1f}%, "
              f"coinché {100 * coinched[who] / max(1, t):4.1f}%, capots réussis {capots[who]}")
        line = "    par contrat (pris / réussis) : " + ", ".join(
            f"{'capot' if v == CAPOT else v} {by_value[(who, v)][0]}/{100 * by_value[(who, v)][1] / by_value[(who, v)][0]:.0f}%"
            for v in sorted(k[1] for k in by_value if k[0] == who))
        print(line)

    wins = []
    game_env = CoincheEnv(bidding=a.bids or b.bids, seed=args.seed + 1)
    for g in range(args.games):
        a_team = g % 2
        sides = [a, b] if a_team == 0 else [b, a]
        totals = [0, 0]
        while max(totals) < DEFAULT_TARGET or totals[0] == totals[1]:
            result = play_deal(game_env, sides)
            if result is not None:
                totals = [totals[t] + result["scores"][t] for t in (0, 1)]
        wins.append(1.0 if totals[a_team] > totals[1 - a_team] else 0.0)
    w, wci = mean_ci(wins)
    print(f"Parties en {DEFAULT_TARGET} points : A gagne {100 * w:.1f}% (±{100 * wci:.1f}) sur {args.games}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    random.seed(0)
    main()
