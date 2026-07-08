import math

from .agents import HeuristicAgent, RandomAgent, TrumpCountAgent, VoidExploitAgent
from .env import BeloteEnv, MAX_SCORE


def play_episode(env, agent_seat0, agent_seat1):
    """agent_seat0 mène toujours le premier pli (avantage structurel du siège 0)."""
    obs, info = env.reset()
    agents = {0: agent_seat0, 1: agent_seat1}
    cumulative = {"0": 0.0, "1": 0.0}

    while True:
        player_idx = env.current_idx
        action = agents[player_idx].act(obs, info["legal_actions"], info)
        obs, rewards, done, info = env.step(action)
        cumulative["0"] += rewards["0"]
        cumulative["1"] += rewards["1"]
        if done:
            return cumulative["0"] * MAX_SCORE, cumulative["1"] * MAX_SCORE


def evaluate_against(agent, opponent, n_episodes):
    """Joue n_episodes contre opponent, sièges alternés toutes les parties
    (agent au siège 0 une partie sur deux, comme benchmark.run_match, pour
    ne pas biaiser par l'avantage structurel du meneur). Retourne un dict
    structuré (win rate + IC95%, scores moyens) plutôt que d'imprimer."""
    env = BeloteEnv()
    wins, losses, ties = 0, 0, 0
    total_agent_score, total_opponent_score = 0.0, 0.0

    for i in range(n_episodes):
        if i % 2 == 0:
            score_agent, score_opponent = play_episode(env, agent, opponent)
        else:
            score_opponent, score_agent = play_episode(env, opponent, agent)

        total_agent_score += score_agent
        total_opponent_score += score_opponent
        if score_agent > score_opponent:
            wins += 1
        elif score_opponent > score_agent:
            losses += 1
        else:
            ties += 1

    win_rate = wins / n_episodes
    win_rate_ci95 = 1.96 * math.sqrt(win_rate * (1 - win_rate) / n_episodes)

    return {
        "n_episodes": n_episodes,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": win_rate,
        "win_rate_ci95": win_rate_ci95,
        "avg_score_agent": total_agent_score / n_episodes,
        "avg_score_opponent": total_opponent_score / n_episodes,
    }


# Protocole d'évaluation défini en amont : adversaires de référence et volume
# de parties par adversaire (plus de parties là où l'écart attendu est plus
# faible, pour un intervalle de confiance exploitable).
EVAL_OPPONENTS = [
    ("RandomAgent", RandomAgent, 200),
    ("HeuristicAgent", HeuristicAgent, 500),
    ("VoidExploitAgent", VoidExploitAgent, 500),
    ("TrumpCountAgent", TrumpCountAgent, 1000),
]


def run_evaluation_suite(agent):
    """Évalue agent contre chaque adversaire de EVAL_OPPONENTS séparément.
    Retourne {nom_adversaire: résultat} (voir evaluate_against)."""
    results = {}
    for name, opponent_cls, n_episodes in EVAL_OPPONENTS:
        result = evaluate_against(agent, opponent_cls(), n_episodes)
        results[name] = result
        print(
            f"  {name:<16} win_rate={result['win_rate'] * 100:5.1f}% "
            f"(±{result['win_rate_ci95'] * 100:.1f}pp, n={result['n_episodes']}) | "
            f"score {result['avg_score_agent']:.1f} vs {result['avg_score_opponent']:.1f}"
        )
    return results
