"""Taux de victoire en parties complètes (premier à 501 points), comme une vraie
partie de belote, en parties dupliquées : chaque partie est jouée deux fois avec
la même suite de donnes, mains échangées. La main A mène une manche sur deux.

    python -m scripts.evaluate_full_games --opponent trumpcount
    python -m scripts.evaluate_full_games --agent heuristic --opponent random
"""
import argparse
import math
import random
import sys

from belote.rl.agents import HeuristicAgent, RandomAgent, TrumpCountAgent, VoidExploitAgent
from belote.rl.env import BeloteEnv
from belote.rl.evaluation import play_episode
from scripts.compare_checkpoints import load_agent
from scripts.oracle import TARGET, outcome, random_deal

AGENTS = {"random": RandomAgent, "heuristic": HeuristicAgent, "voidexploit": VoidExploitAgent, "trumpcount": TrumpCountAgent}


def make_agent(name):
    """Nom d'un agent de référence, ou chemin d'un modèle PPO (.pt)."""
    return AGENTS[name]() if name in AGENTS else load_agent(name)


def play_game(env, agent, opponent, deals, agent_has_a):
    """Une partie complète. Retourne (score agent, score adversaire, nombre de manches)."""
    agent_total = opp_total = 0
    for k, (a, b, trump) in enumerate(deals):
        a_leads = k % 2 == 0
        hand0, hand1 = (a, b) if a_leads else (b, a)  # siège 0 = meneur
        agent_seat0 = agent_has_a == a_leads
        seat0, seat1 = (agent, opponent) if agent_seat0 else (opponent, agent)
        p0, p1 = play_episode(env, seat0, seat1, deal=(hand0, hand1, trump))
        agent_total += p0 if agent_seat0 else p1
        opp_total += p1 if agent_seat0 else p0
        if max(agent_total, opp_total) >= TARGET:
            return agent_total, opp_total, k + 1
    raise RuntimeError("partie trop longue : augmenter le nombre de donnes préparées")


def evaluate(agent, opponent, n_pairs, seed=0):
    env = BeloteEnv(belief=getattr(agent, "uses_belief", False) or getattr(opponent, "uses_belief", False))
    rng = random.Random(seed)
    pair_scores, rounds = [], 0
    for _ in range(n_pairs):
        random.seed(rng.random())
        deals = [random_deal() for _ in range(40)]
        pair = 0.0
        for agent_has_a in (True, False):
            mine, theirs, n = play_game(env, agent, opponent, deals, agent_has_a)
            pair += outcome(mine, theirs) / 2
            rounds += n
        pair_scores.append(pair)
    mean = sum(pair_scores) / n_pairs
    sd = math.sqrt(sum((x - mean) ** 2 for x in pair_scores) / (n_pairs - 1))
    return {"win_rate": mean, "win_rate_ci95": 1.96 * sd / math.sqrt(n_pairs),
            "n_games": 2 * n_pairs, "rounds_per_game": rounds / (2 * n_pairs)}


def main():
    parser = argparse.ArgumentParser(description="Taux de victoire en parties complètes (premier à 501 points).")
    parser.add_argument("--agent", default="models/ppo_CA_3M.pt", help="modèle .pt ou random|heuristic|voidexploit|trumpcount")
    parser.add_argument("--opponent", default="random", choices=sorted(AGENTS))
    parser.add_argument("--pairs", type=int, default=500, help="parties dupliquées (2 parties chacune)")
    parser.add_argument("--seed", type=int, default=123)
    args = parser.parse_args()
    r = evaluate(make_agent(args.agent), make_agent(args.opponent), args.pairs, args.seed)
    print(f"{args.agent} vs {args.opponent} : {100 * r['win_rate']:.1f}% (±{100 * r['win_rate_ci95']:.1f}pp) "
          f"de parties gagnées sur {r['n_games']} parties, {r['rounds_per_game']:.1f} manches par partie")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
