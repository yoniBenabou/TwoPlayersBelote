"""Comment un agent annonce : à quelle fréquence il prend (tour 1, tour 2), et
combien de fois il chute ("dedans") quand il prend. Manches contre un
adversaire, l'agent parlant en premier une manche sur deux.

    python -m scripts.bidding_stats --agent experiments/bidding_CA_seed1/checkpoints/ppo_2000000.pt
    python -m scripts.bidding_stats --agent heurbid:models/ppo_CA_3M.pt --opponent trumpcount
"""
import argparse
import random
import sys

import numpy as np

from belote.rl.env import BeloteEnv, PASS
from scripts.evaluate_full_games import make_agent


def bidding_stats(agent, opponent, n_rounds, seed=0):
    random.seed(seed)
    np.random.seed(seed)
    ppo = agent if hasattr(agent, "env_kwargs") else opponent if hasattr(opponent, "env_kwargs") else None
    env = BeloteEnv(**ppo.env_kwargs()) if ppo else BeloteEnv(bidding=True)
    s = {"rounds": 0, "redeal": 0, "take1": 0, "take2": 0, "opp_take": 0,
         "dedans": 0, "opp_dedans": 0, "taker_points": 0, "opp_taker_points": 0}
    for k in range(n_rounds):
        agent_seat = k % 2
        obs, info = env.reset(options={"starting_player": k // 2 % 2})
        players = {agent_seat: agent, 1 - agent_seat: opponent}
        bids = []
        done = False
        while not done:
            seat = env.current_idx
            phase = info["phase"]
            action = players[seat].act(obs, info["legal_actions"], info)
            if phase in ("bid1", "bid2"):
                bids.append((seat, phase, action))
            obs, _, done, info = env.step(action)
        s["rounds"] += 1
        if info["redeal"]:
            s["redeal"] += 1
            continue
        taker = env.taker
        points = info["final_points"]
        if taker == agent_seat:
            phase = next(p for seat, p, a in bids if seat == taker and a != PASS)
            s["take1" if phase == "bid1" else "take2"] += 1
            s["dedans"] += info["dedans"]
            s["taker_points"] += points[taker] - points[1 - taker]
        else:
            s["opp_take"] += 1
            s["opp_dedans"] += info["dedans"]
            s["opp_taker_points"] += points[taker] - points[1 - taker]
    return s


def report(s):
    takes = s["take1"] + s["take2"]
    n = s["rounds"]
    lines = [
        f"manches : {n}, redistribuées (4 passes) : {100 * s['redeal'] / n:.1f}%",
        f"l'agent prend : {100 * takes / n:.1f}% des manches "
        f"(tour 1 : {100 * s['take1'] / n:.1f}%, tour 2 : {100 * s['take2'] / n:.1f}%)",
        f"  dedans quand il prend : {100 * s['dedans'] / max(takes, 1):.1f}%, "
        f"écart moyen preneur - défenseur : {s['taker_points'] / max(takes, 1):+.1f} points",
        f"l'adversaire prend : {100 * s['opp_take'] / n:.1f}%, dedans : "
        f"{100 * s['opp_dedans'] / max(s['opp_take'], 1):.1f}%, écart moyen : "
        f"{s['opp_taker_points'] / max(s['opp_take'], 1):+.1f} points",
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Statistiques d'annonces d'un agent.")
    parser.add_argument("--agent", required=True, help="modèle .pt (avec annonces) ou heurbid:<modèle .pt>")
    parser.add_argument("--opponent", default="trumpcount")
    parser.add_argument("--rounds", type=int, default=10000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    s = bidding_stats(make_agent(args.agent), make_agent(args.opponent), args.rounds, args.seed)
    print(f"{args.agent} vs {args.opponent}")
    print(report(s))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
