import argparse
import glob
import os
import re
import sys

from belote.rl.evaluation import evaluate_against
from belote.rl.networks import ActorCriticNetwork
from belote.rl.ppo_agent import PPOAgent


def load_agent(path):
    network = ActorCriticNetwork.from_checkpoint(path)
    network.eval()
    return PPOAgent(network, deterministic=True)


def games_of(path):
    return int(re.search(r"ppo_(\d+)\.pt", path).group(1))


def main():
    parser = argparse.ArgumentParser(
        description="Fait jouer le dernier checkpoint d'un entraînement contre ses versions "
                    "précédentes (donnes dupliquées), pour vérifier qu'il progresse aussi contre lui-même."
    )
    parser.add_argument("checkpoint_dir", help="dossier checkpoints/ d'un entraînement")
    parser.add_argument("--games", type=int, nargs="+",
                        default=[0, 250_000, 500_000, 1_000_000, 1_500_000, 2_000_000, 2_500_000],
                        help="nombres de parties des versions précédentes à affronter (checkpoint le plus proche)")
    parser.add_argument("--deals", type=int, default=1000, help="donnes dupliquées par match (2 parties chacune)")
    args = parser.parse_args()

    checkpoints = sorted(glob.glob(os.path.join(args.checkpoint_dir, "ppo_*.pt")), key=games_of)
    final_path = checkpoints[-1]
    final_agent = load_agent(final_path)
    print(f"Agent final : {os.path.basename(final_path)} ({games_of(final_path):,} parties)\n")

    print(f"{'Adversaire':<28} {'Écart points':>16} {'Win rate':>16}")
    for target in args.games:
        path = min(checkpoints, key=lambda p: abs(games_of(p) - target))
        result = evaluate_against(final_agent, load_agent(path), args.deals)
        print(
            f"version à {games_of(path):>9,} parties  "
            f"{result['avg_point_diff']:+6.1f} (±{result['avg_point_diff_ci95']:.1f})  "
            f"{result['win_rate'] * 100:6.1f}% (±{result['win_rate_ci95'] * 100:.1f}pp)"
        )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
