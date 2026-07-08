import sys

import numpy as np
import torch

from belote.env import BeloteEnv
from belote.networks import ActorCriticNetwork
from belote.ppo_agent import PPOAgent
from belote.ppo_loss import compute_ppo_loss
from belote.self_play import collect_rollout, stack_transitions


def check_evaluate_actions_matches_act_and_evaluate():
    """evaluate_actions doit définir exactement la même distribution que
    act_and_evaluate sur le même (obs, legal_mask) : c'est la propriété qui
    rend le ratio pi_new/pi_old cohérent."""
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())
    obs, info = env.reset(seed=7)
    legal_mask = info["legal_actions"]

    with torch.no_grad():
        action, log_prob_sampled, _value, _entropy = agent.act_and_evaluate(obs, legal_mask)
        log_prob_evaluated, _value2, _entropy2 = agent.evaluate_actions(obs, legal_mask, [action])

    assert abs(log_prob_sampled.item() - log_prob_evaluated.item()) < 1e-6, (
        log_prob_sampled.item(), log_prob_evaluated.item()
    )


def check_value_and_entropy_formulas(n_episodes=10):
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())
    buffer = collect_rollout(env, agent, n_episodes=n_episodes)
    batch = stack_transitions(buffer)

    _loss, metrics = compute_ppo_loss(agent, **batch)

    with torch.no_grad():
        _log_probs, values, entropy = agent.evaluate_actions(batch["obs"], batch["legal_mask"], batch["actions"])
        returns = torch.as_tensor(batch["returns"], dtype=torch.float32)
        expected_value_loss = ((values - returns) ** 2).mean().item()
        expected_entropy = entropy.mean().item()

    assert abs(metrics["value_loss"] - expected_value_loss) < 1e-5, (metrics["value_loss"], expected_value_loss)
    assert abs(metrics["entropy"] - expected_entropy) < 1e-5, (metrics["entropy"], expected_entropy)


def check_clipping_is_active():
    """Avec un old_log_prob délibérément très éloigné de ce que le réseau
    produirait, le ratio sort largement de [1-eps, 1+eps] : la policy_loss
    doit correspondre à la version clippée de la formule, pas à la version
    non clippée."""
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())
    obs, info = env.reset(seed=11)
    legal_mask = info["legal_actions"]
    action = int(np.flatnonzero(legal_mask)[0])

    with torch.no_grad():
        new_log_prob, _value, _entropy = agent.evaluate_actions(obs, legal_mask, [action])

    old_log_prob = new_log_prob.item() - 5.0  # ratio = exp(5) >> 1 + eps
    advantage = 1.0  # positif connu, pas de normalisation pour garder ce nombre exact

    loss, metrics = compute_ppo_loss(
        agent,
        obs=[obs],
        legal_mask=[legal_mask],
        actions=[action],
        old_log_probs=[old_log_prob],
        advantages=[advantage],
        returns=[0.0],
        normalize_advantages=False,
        value_coef=0.0,
        entropy_coef=0.0,
    )

    ratio = np.exp(new_log_prob.item() - old_log_prob)
    clip_eps = 0.2
    unclipped = ratio * advantage
    clipped = np.clip(ratio, 1 - clip_eps, 1 + clip_eps) * advantage
    expected_policy_loss = -min(unclipped, clipped)

    assert clipped < unclipped, "le cas de test doit forcer le clipping à réduire l'objectif"
    assert abs(metrics["policy_loss"] - expected_policy_loss) < 1e-5, (metrics["policy_loss"], expected_policy_loss)
    assert abs(loss.item() - expected_policy_loss) < 1e-5  # value_coef=entropy_coef=0.0


def check_gradient_flow(n_episodes=10):
    env = BeloteEnv()
    network = ActorCriticNetwork()
    agent = PPOAgent(network)
    buffer = collect_rollout(env, agent, n_episodes=n_episodes)
    batch = stack_transitions(buffer)

    loss, _metrics = compute_ppo_loss(agent, **batch)
    assert loss.requires_grad, "la loss doit pouvoir backprop"

    params_before = [p.clone() for p in network.parameters()]

    optimizer = torch.optim.Adam(network.parameters(), lr=1e-3)
    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    changed = any(not torch.equal(before, after) for before, after in zip(params_before, network.parameters()))
    assert changed, "un pas d'optimiseur devrait modifier les poids du réseau"


def main():
    check_evaluate_actions_matches_act_and_evaluate()
    print("evaluate_actions cohérent avec act_and_evaluate (même distribution) : OK")

    check_value_and_entropy_formulas()
    print("Formules value_loss/entropy cohérentes avec evaluate_actions : OK")

    check_clipping_is_active()
    print("Surrogate clippé appliqué correctement quand le ratio sort de [1-eps, 1+eps] : OK")

    check_gradient_flow()
    print("Backward + pas d'optimiseur : la loss modifie bien les poids du réseau : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
