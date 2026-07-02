import math
import sys

import torch

from belote.env import BeloteEnv
from belote.networks import ActorCriticNetwork
from belote.ppo_agent import PPOAgent
from belote.ppo_update import ppo_update
from belote.self_play import collect_rollout

EXPECTED_METRIC_KEYS = {"loss", "policy_loss", "value_loss", "entropy", "approx_kl", "clip_fraction"}


def _all_finite(metrics):
    return all(math.isfinite(v) for v in metrics.values())


def check_basic_run_returns_finite_metrics(n_episodes=20):
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())
    optimizer = torch.optim.Adam(agent.network.parameters(), lr=1e-3)

    buffer = collect_rollout(env, agent, n_episodes=n_episodes)
    metrics = ppo_update(agent, optimizer, buffer, n_epochs=2, minibatch_size=64)

    assert set(metrics.keys()) == EXPECTED_METRIC_KEYS, metrics.keys()
    assert _all_finite(metrics), metrics


def check_weights_actually_change(n_episodes=20):
    env = BeloteEnv()
    network = ActorCriticNetwork()
    agent = PPOAgent(network)
    optimizer = torch.optim.Adam(network.parameters(), lr=1e-3)

    buffer = collect_rollout(env, agent, n_episodes=n_episodes)
    params_before = [p.clone() for p in network.parameters()]

    ppo_update(agent, optimizer, buffer, n_epochs=2, minibatch_size=64)

    changed = any(not torch.equal(before, after) for before, after in zip(params_before, network.parameters()))
    assert changed, "ppo_update devrait modifier les poids du réseau"


def check_legal_mask_respected_after_update(n_episodes=20, n_eval_episodes=50):
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())
    optimizer = torch.optim.Adam(agent.network.parameters(), lr=1e-3)

    buffer = collect_rollout(env, agent, n_episodes=n_episodes)
    ppo_update(agent, optimizer, buffer, n_epochs=2, minibatch_size=64)

    for i in range(n_eval_episodes):
        obs, info = env.reset(options={"starting_player": i % 2})
        done = False
        while not done:
            action = agent.act(obs, info["legal_actions"], info)
            assert info["legal_actions"][action], "action illégale choisie après ppo_update"
            obs, _rewards, done, info = env.step(action)


def check_optimizer_state_persists_across_calls(n_episodes=20):
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())
    optimizer = torch.optim.Adam(agent.network.parameters(), lr=1e-3)

    buffer1 = collect_rollout(env, agent, n_episodes=n_episodes)
    metrics1 = ppo_update(agent, optimizer, buffer1, n_epochs=2, minibatch_size=64)
    assert _all_finite(metrics1), metrics1

    buffer2 = collect_rollout(env, agent, n_episodes=n_episodes)
    metrics2 = ppo_update(agent, optimizer, buffer2, n_epochs=2, minibatch_size=64)
    assert _all_finite(metrics2), metrics2


def main():
    check_basic_run_returns_finite_metrics()
    print("ppo_update : métriques finies avec les bonnes clés : OK")

    check_weights_actually_change()
    print("ppo_update modifie bien les poids du réseau : OK")

    check_legal_mask_respected_after_update()
    print("Masque légal toujours respecté après ppo_update : OK")

    check_optimizer_state_persists_across_calls()
    print("État de l'optimiseur persiste correctement entre deux appels : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
