import sys
import time

from belote.agents import HeuristicAgent, RandomAgent, TrumpCountAgent, VoidExploitAgent
from belote.evaluation import evaluate_against, play_episode  # noqa: F401 (play_episode réexporté)


def run_match(agent_a, agent_b, n_episodes, label_a, label_b):
    """Joue n_episodes en alternant qui occupe le siège 0 (toujours meneur du
    premier pli), pour ne pas biaiser la comparaison par cet avantage de siège."""
    start = time.perf_counter()
    result = evaluate_against(agent_a, agent_b, n_episodes)
    elapsed = time.perf_counter() - start

    print(f"\n=== {label_a} vs {label_b} ({n_episodes} épisodes, sièges alternés, {n_episodes / elapsed:.0f} épisodes/s) ===")
    print(f"Score moyen {label_a} : {result['avg_score_agent']:.2f}")
    print(f"Score moyen {label_b} : {result['avg_score_opponent']:.2f}")
    print(f"Victoires {label_a}   : {result['wins']} ({100 * result['win_rate']:.1f}%)")
    print(f"Victoires {label_b}   : {result['losses']} ({100 * result['losses'] / n_episodes:.1f}%)")
    print(f"Égalités              : {result['ties']} ({100 * result['ties'] / n_episodes:.1f}%)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    run_match(HeuristicAgent(), RandomAgent(), 10000, "HeuristicAgent", "RandomAgent")
    run_match(VoidExploitAgent(), RandomAgent(), 10000, "VoidExploitAgent", "RandomAgent")
    run_match(TrumpCountAgent(), RandomAgent(), 10000, "TrumpCountAgent", "RandomAgent")
    run_match(RandomAgent(), RandomAgent(), 10000, "RandomAgent_A", "RandomAgent_B")

