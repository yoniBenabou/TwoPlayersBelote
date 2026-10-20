import sys
import time

from belote.rl.agents import HeuristicAgent, RandomAgent, TrumpCountAgent, VoidExploitAgent
from belote.rl.evaluation import evaluate_against, play_episode  # noqa: F401 (play_episode réexporté)


def run_match(agent_a, agent_b, n_deals, label_a, label_b):
    """Joue n_deals donnes dupliquées (chaque donne jouée deux fois en
    échangeant les mains, cf. evaluation.evaluate_against), soit
    2 * n_deals parties : la chance de la donne s'annule."""
    start = time.perf_counter()
    result = evaluate_against(agent_a, agent_b, n_deals)
    elapsed = time.perf_counter() - start
    n_games = result["n_games"]

    print(f"\n=== {label_a} vs {label_b} ({n_deals} donnes dupliquées = {n_games} parties, {n_games / elapsed:.0f} parties/s) ===")
    print(f"Points moyens {label_a} : {result['avg_points_agent']:.2f}")
    print(f"Points moyens {label_b} : {result['avg_points_opponent']:.2f}")
    print(f"Écart de points        : {result['avg_point_diff']:+.2f} (±{result['avg_point_diff_ci95']:.2f})")
    print(f"Win rate {label_a}      : {100 * result['win_rate']:.1f}% (±{100 * result['win_rate_ci95']:.1f}pp)")
    print(f"Victoires / défaites / égalités : {result['wins']} / {result['losses']} / {result['ties']}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    run_match(HeuristicAgent(), RandomAgent(), 5000, "HeuristicAgent", "RandomAgent")
    run_match(VoidExploitAgent(), RandomAgent(), 5000, "VoidExploitAgent", "RandomAgent")
    run_match(TrumpCountAgent(), RandomAgent(), 5000, "TrumpCountAgent", "RandomAgent")
    run_match(TrumpCountAgent(), HeuristicAgent(), 5000, "TrumpCountAgent", "HeuristicAgent")
    run_match(RandomAgent(), RandomAgent(), 5000, "RandomAgent_A", "RandomAgent_B")

