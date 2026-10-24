import math

from .agents import HeuristicAgent, RandomAgent, TrumpCountAgent, VoidExploitAgent
from .env import BeloteEnv


def play_episode(env, agent_seat0, agent_seat1, deal=None):
    """Joue une manche, siège 0 meneur du premier pli. deal impose la donne
    (main0, main1, atout) au lieu d'en tirer une au hasard. Retourne les
    points réels (cartes + dix de der + belote-rebelote) de chaque siège."""
    obs, info = env.reset(options={"starting_player": 0, "deal": deal})
    agents = {0: agent_seat0, 1: agent_seat1}

    while True:
        player_idx = env.current_idx
        action = agents[player_idx].act(obs, info["legal_actions"], info)
        obs, _rewards, done, info = env.step(action)
        if done:
            return info["final_points"]


def _mean_and_ci95(values):
    n = len(values)
    mean = sum(values) / n
    if n < 2:
        return mean, 0.0
    variance = sum((v - mean) ** 2 for v in values) / (n - 1)
    return mean, 1.96 * math.sqrt(variance / n)


def _outcome(points_agent, points_opponent):
    """1 victoire, 0.5 égalité, 0 défaite."""
    if points_agent > points_opponent:
        return 1.0
    if points_agent < points_opponent:
        return 0.0
    return 0.5


def evaluate_against(agent, opponent, n_deals):
    """Évaluation par donnes dupliquées (comme au bridge) : chaque donne est
    jouée deux fois en échangeant les mains. Partie 1 : agent au siège 0
    (main A, meneur), adversaire au siège 1 (main B). Partie 2 : même donne,
    adversaire au siège 0 (main A, meneur), agent au siège 1 (main B).

    Chacun ayant joué les deux mains et les deux positions, la chance de la
    donne s'annule et il ne reste que la différence de qualité de jeu. Les
    intervalles de confiance sont calculés sur les n_deals paires (les deux
    parties d'une paire ne sont pas indépendantes).

    Retourne (sur les 2 * n_deals parties) : win rate (égalité = 0.5) + IC95,
    écart moyen de points réels par partie (agent - adversaire) + IC95,
    points moyens de chacun."""
    env = BeloteEnv(**agent.env_kwargs()) if hasattr(agent, "env_kwargs") else BeloteEnv()
    wins, losses, ties = 0, 0, 0
    deal_win_scores, deal_point_diffs = [], []
    total_agent_points, total_opponent_points = 0, 0

    for _ in range(n_deals):
        agent_a, opponent_b = play_episode(env, agent, opponent)
        deal = env.deal
        opponent_a, agent_b = play_episode(env, opponent, agent, deal=deal)

        pair_outcomes = []
        for points_agent, points_opponent in ((agent_a, opponent_b), (agent_b, opponent_a)):
            outcome = _outcome(points_agent, points_opponent)
            pair_outcomes.append(outcome)
            wins += outcome == 1.0
            losses += outcome == 0.0
            ties += outcome == 0.5
            total_agent_points += points_agent
            total_opponent_points += points_opponent

        deal_win_scores.append(sum(pair_outcomes) / 2)
        deal_point_diffs.append(((agent_a - opponent_b) + (agent_b - opponent_a)) / 2)

    n_games = 2 * n_deals
    win_rate, win_rate_ci95 = _mean_and_ci95(deal_win_scores)
    avg_point_diff, avg_point_diff_ci95 = _mean_and_ci95(deal_point_diffs)

    return {
        "n_deals": n_deals,
        "n_games": n_games,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "win_rate": win_rate,
        "win_rate_ci95": win_rate_ci95,
        "avg_point_diff": avg_point_diff,
        "avg_point_diff_ci95": avg_point_diff_ci95,
        "avg_points_agent": total_agent_points / n_games,
        "avg_points_opponent": total_opponent_points / n_games,
    }


# Protocole d'évaluation : adversaires de référence et nombre de donnes par
# adversaire (chaque donne = 2 parties). Plus de donnes là où l'écart
# attendu est plus faible, pour un intervalle de confiance exploitable.
EVAL_OPPONENTS = [
    ("RandomAgent", RandomAgent, 100),
    ("HeuristicAgent", HeuristicAgent, 250),
    ("VoidExploitAgent", VoidExploitAgent, 250),
    ("TrumpCountAgent", TrumpCountAgent, 500),
]


def run_evaluation_suite(agent):
    """Évalue agent contre chaque adversaire de EVAL_OPPONENTS séparément.
    Retourne {nom_adversaire: résultat} (voir evaluate_against)."""
    results = {}
    for name, opponent_cls, n_deals in EVAL_OPPONENTS:
        result = evaluate_against(agent, opponent_cls(), n_deals)
        results[name] = result
        print(
            f"  {name:<16} win_rate={result['win_rate'] * 100:5.1f}% "
            f"(±{result['win_rate_ci95'] * 100:.1f}pp) | "
            f"écart points {result['avg_point_diff']:+6.1f} (±{result['avg_point_diff_ci95']:.1f}) "
            f"| n={result['n_games']} parties"
        )
    return results
