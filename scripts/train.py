import argparse
import json
import os
import random
import sys

import numpy as np
import torch
from torch.utils.tensorboard import SummaryWriter

from belote.rl.agents import HeuristicAgent, TrumpCountAgent, VoidExploitAgent
from belote.rl.env import BeloteEnv
from belote.rl.evaluation import run_evaluation_suite
from belote.rl.networks import ActorCriticNetwork
from belote.rl.ppo_agent import PPOAgent
from belote.rl.ppo_update import ppo_update
from belote.rl.self_play import DEFAULT_ROLLOUT_EPISODES, collect_rollout

# Valeurs par défaut = meilleure configuration trouvée (C + A : reward sans
# bonus de victoire, lr 3e-4). L'apprentissage plafonne vers 1,5-2 millions
# de parties avec cette configuration (cf. scripts/compare_checkpoints.py).
TOTAL_GAMES = 2_000_000
ROLLOUT_EPISODES = DEFAULT_ROLLOUT_EPISODES
EVAL_EVERY_N_GAMES = 50_000
LR = 3e-4
ENTROPY_COEF = 0.01
WIN_BONUS = False
CHECKPOINT_DIR = "checkpoints"
LOG_DIR = "runs"


def log_optimization_metrics(writer, metrics, games_trained):
    for key, value in metrics.items():
        writer.add_scalar(f"train/{key}", value, games_trained)


def log_eval_results(writer, results, games_trained):
    for opponent_name, result in results.items():
        for key in ("win_rate", "win_rate_ci95", "avg_point_diff", "avg_point_diff_ci95"):
            writer.add_scalar(f"eval/{opponent_name}/{key}", result[key], games_trained)


def save_checkpoint(network, games_trained):
    path = os.path.join(CHECKPOINT_DIR, f"ppo_{games_trained:07d}.pt")
    torch.save(network.state_dict(), path)
    print(f"Checkpoint sauvegardé : {path}")


def train(
    total_games: int = TOTAL_GAMES,
    rollout_episodes: int = ROLLOUT_EPISODES,
    eval_every_n_games: int = EVAL_EVERY_N_GAMES,
    lr: float = LR,
    entropy_coef: float = ENTROPY_COEF,
    win_bonus: bool = WIN_BONUS,
    vs_heuristics: bool = False,
    seed: int | None = None,
):
    """vs_heuristics : au lieu du self-play, chaque manche d'entraînement
    oppose l'agent à un adversaire tiré au hasard parmi les heuristiques
    (étape 1 du curriculum). win_bonus=True : ajoute le +1/-1 final au reward.
    seed : graine aléatoire (donnes, initialisation du réseau, échantillonnage)
    pour pouvoir refaire un entraînement avec une autre graine."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    config = {
        "total_games": total_games, "rollout_episodes": rollout_episodes,
        "eval_every_n_games": eval_every_n_games, "lr": lr, "entropy_coef": entropy_coef,
        "win_bonus": win_bonus, "vs_heuristics": vs_heuristics, "seed": seed,
    }
    with open("config.json", "w") as f:
        json.dump(config, f, indent=2)

    env = BeloteEnv(win_bonus=win_bonus)
    opponents = [HeuristicAgent(), VoidExploitAgent(), TrumpCountAgent()] if vs_heuristics else None
    network = ActorCriticNetwork()
    agent = PPOAgent(network)
    eval_agent = PPOAgent(network, deterministic=True)
    optimizer = torch.optim.Adam(network.parameters(), lr=lr)
    writer = SummaryWriter(LOG_DIR)

    games_trained = 0
    next_eval_at = 0

    print(f"=== Entraînement PPO : {total_games} parties, éval toutes les {eval_every_n_games} parties ===")
    print(f"Config : {config}")

    while True:
        if games_trained >= next_eval_at:
            print(f"\n--- Évaluation à {games_trained} parties d'entraînement ---")
            results = run_evaluation_suite(eval_agent)
            log_eval_results(writer, results, games_trained)
            save_checkpoint(network, games_trained)
            next_eval_at += eval_every_n_games

        if games_trained >= total_games:
            break

        buffer = collect_rollout(env, agent, n_episodes=rollout_episodes, opponents=opponents)
        metrics = ppo_update(agent, optimizer, buffer, entropy_coef=entropy_coef)
        games_trained += rollout_episodes
        log_optimization_metrics(writer, metrics, games_trained)

    writer.close()
    print("\n=== Entraînement terminé ===")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Entraînement PPO belote 2 joueurs.")
    parser.add_argument("--total-games", type=int, default=TOTAL_GAMES)
    parser.add_argument("--eval-every", type=int, default=EVAL_EVERY_N_GAMES)
    parser.add_argument("--lr", type=float, default=LR)
    parser.add_argument("--entropy-coef", type=float, default=ENTROPY_COEF)
    parser.add_argument("--win-bonus", action=argparse.BooleanOptionalAction, default=WIN_BONUS,
                        help="ajoute le +1/-1 de victoire au reward (désactivé par défaut)")
    parser.add_argument("--vs-heuristics", action="store_true", help="adversaires heuristiques au lieu du self-play")
    parser.add_argument("--seed", type=int, help="graine aléatoire (reproductibilité)")
    parser.add_argument("--out-dir", default=".", help="dossier où écrire checkpoints/, runs/ et config.json")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    os.chdir(args.out_dir)
    train(
        total_games=args.total_games,
        eval_every_n_games=args.eval_every,
        lr=args.lr,
        entropy_coef=args.entropy_coef,
        win_bonus=args.win_bonus,
        vs_heuristics=args.vs_heuristics,
        seed=args.seed,
    )
