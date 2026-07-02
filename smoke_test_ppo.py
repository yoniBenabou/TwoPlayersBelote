import math
import sys

import torch

from belote.agents import RandomAgent
from belote.env import BeloteEnv
from belote.networks import ActorCriticNetwork
from belote.ppo_agent import PPOAgent
from belote.ppo_update import ppo_update
from belote.self_play import collect_rollout
from benchmark import run_match

N_ITERATIONS = 50
ROLLOUT_EPISODES = 64
EVAL_EVERY = 10
EVAL_EPISODES = 200
PRINT_EVERY = 5


def check_metrics_are_finite(metrics, iteration):
    for key, value in metrics.items():
        if not math.isfinite(value):
            raise AssertionError(f"Métrique non finie à l'itération {iteration} : {key}={value}")


def check_legal_mask_respected(env, agent, n_episodes=20):
    for i in range(n_episodes):
        obs, info = env.reset(options={"starting_player": i % 2})
        done = False
        while not done:
            action = agent.act(obs, info["legal_actions"], info)
            assert info["legal_actions"][action], "action illégale choisie après update"
            obs, _rewards, done, info = env.step(action)


def evaluate(eval_agent, label):
    print(f"\n--- Éval {label} ---")
    run_match(eval_agent, RandomAgent(), EVAL_EPISODES, "PPO", "Random")


def main():
    env = BeloteEnv()
    network = ActorCriticNetwork()
    agent = PPOAgent(network)
    eval_agent = PPOAgent(network, deterministic=True)
    optimizer = torch.optim.Adam(network.parameters(), lr=1e-3)

    print(f"=== Smoke test PPO : {N_ITERATIONS} itérations, {ROLLOUT_EPISODES} manches/rollout ===")

    evaluate(eval_agent, "initiale (avant entraînement)")

    for iteration in range(1, N_ITERATIONS + 1):
        buffer = collect_rollout(env, agent, n_episodes=ROLLOUT_EPISODES)
        metrics = ppo_update(agent, optimizer, buffer)
        check_metrics_are_finite(metrics, iteration)

        if iteration % PRINT_EVERY == 0 or iteration == 1:
            print(
                f"[iter {iteration:3d}] loss={metrics['loss']:+.4f} "
                f"policy={metrics['policy_loss']:+.4f} value={metrics['value_loss']:.4f} "
                f"entropy={metrics['entropy']:.4f} kl={metrics['approx_kl']:.5f} "
                f"clip_frac={metrics['clip_fraction']:.3f}"
            )

        if iteration % EVAL_EVERY == 0:
            check_legal_mask_respected(env, agent)
            evaluate(eval_agent, f"itération {iteration}")

    evaluate(eval_agent, "finale")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
