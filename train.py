import os
import sys

import torch
from torch.utils.tensorboard import SummaryWriter

from belote.env import BeloteEnv
from belote.evaluation import run_evaluation_suite
from belote.networks import ActorCriticNetwork
from belote.ppo_agent import PPOAgent
from belote.ppo_update import ppo_update
from belote.self_play import DEFAULT_ROLLOUT_EPISODES, collect_rollout

TOTAL_GAMES = 200_000
ROLLOUT_EPISODES = DEFAULT_ROLLOUT_EPISODES
EVAL_EVERY_N_GAMES = 5_000
CHECKPOINT_DIR = "checkpoints"
LOG_DIR = "runs"


def log_optimization_metrics(writer, metrics, games_trained):
    for key, value in metrics.items():
        writer.add_scalar(f"train/{key}", value, games_trained)


def log_eval_results(writer, results, games_trained):
    for opponent_name, result in results.items():
        for key in ("win_rate", "win_rate_ci95", "avg_score_agent", "avg_score_opponent"):
            writer.add_scalar(f"eval/{opponent_name}/{key}", result[key], games_trained)


def save_checkpoint(network, games_trained):
    path = os.path.join(CHECKPOINT_DIR, f"ppo_{games_trained:07d}.pt")
    torch.save(network.state_dict(), path)
    print(f"Checkpoint sauvegardé : {path}")


def train(
    total_games: int = TOTAL_GAMES,
    rollout_episodes: int = ROLLOUT_EPISODES,
    eval_every_n_games: int = EVAL_EVERY_N_GAMES,
):
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    env = BeloteEnv()
    network = ActorCriticNetwork()
    agent = PPOAgent(network)
    eval_agent = PPOAgent(network, deterministic=True)
    optimizer = torch.optim.Adam(network.parameters(), lr=1e-3)
    writer = SummaryWriter(LOG_DIR)

    games_trained = 0
    next_eval_at = 0

    print(f"=== Entraînement PPO : {total_games} parties, éval toutes les {eval_every_n_games} parties ===")

    while True:
        if games_trained >= next_eval_at:
            print(f"\n--- Évaluation à {games_trained} parties d'entraînement ---")
            results = run_evaluation_suite(eval_agent)
            log_eval_results(writer, results, games_trained)
            save_checkpoint(network, games_trained)
            next_eval_at += eval_every_n_games

        if games_trained >= total_games:
            break

        buffer = collect_rollout(env, agent, n_episodes=rollout_episodes)
        metrics = ppo_update(agent, optimizer, buffer)
        games_trained += rollout_episodes
        log_optimization_metrics(writer, metrics, games_trained)

    writer.close()
    print("\n=== Entraînement terminé ===")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    train()
