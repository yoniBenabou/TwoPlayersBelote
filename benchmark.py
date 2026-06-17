import sys
import time

from belote.agents import HeuristicAgent, RandomAgent, TrumpCountAgent, VoidExploitAgent
from belote.env import BeloteEnv, MAX_SCORE


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


def run_match(agent_a, agent_b, n_episodes, label_a, label_b):
    """Joue n_episodes en alternant qui occupe le siège 0 (toujours meneur du
    premier pli), pour ne pas biaiser la comparaison par cet avantage de siège."""
    env = BeloteEnv()
    wins = {label_a: 0, label_b: 0, "égalité": 0}
    total = {label_a: 0.0, label_b: 0.0}

    start = time.perf_counter()
    for i in range(n_episodes):
        if i % 2 == 0:
            score_a, score_b = play_episode(env, agent_a, agent_b)
        else:
            score_b, score_a = play_episode(env, agent_b, agent_a)

        total[label_a] += score_a
        total[label_b] += score_b
        if score_a > score_b:
            wins[label_a] += 1
        elif score_b > score_a:
            wins[label_b] += 1
        else:
            wins["égalité"] += 1
    elapsed = time.perf_counter() - start

    print(f"\n=== {label_a} vs {label_b} ({n_episodes} épisodes, sièges alternés, {n_episodes / elapsed:.0f} épisodes/s) ===")
    print(f"Score moyen {label_a} : {total[label_a] / n_episodes:.2f}")
    print(f"Score moyen {label_b} : {total[label_b] / n_episodes:.2f}")
    print(f"Victoires {label_a}   : {wins[label_a]} ({100 * wins[label_a] / n_episodes:.1f}%)")
    print(f"Victoires {label_b}   : {wins[label_b]} ({100 * wins[label_b] / n_episodes:.1f}%)")
    print(f"Égalités              : {wins['égalité']} ({100 * wins['égalité'] / n_episodes:.1f}%)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    run_match(HeuristicAgent(), RandomAgent(), 10000, "HeuristicAgent", "RandomAgent")
    run_match(VoidExploitAgent(), RandomAgent(), 10000, "VoidExploitAgent", "RandomAgent")
    run_match(TrumpCountAgent(), RandomAgent(), 10000, "TrumpCountAgent", "RandomAgent")
    run_match(RandomAgent(), RandomAgent(), 10000, "RandomAgent_A", "RandomAgent_B")

