import numpy as np
import torch

from .ppo_agent import PPOAgent

CLIP_EPS = 0.2
VALUE_COEF = 0.5
ENTROPY_COEF = 0.01


def compute_ppo_loss(
    agent: PPOAgent,
    obs,
    legal_mask,
    actions,
    old_log_probs,
    advantages,
    returns,
    clip_eps: float = CLIP_EPS,
    value_coef: float = VALUE_COEF,
    entropy_coef: float = ENTROPY_COEF,
    normalize_advantages: bool = True,
):
    """Loss PPO (surrogate clippé + loss de valeur + bonus d'entropie) sur un
    batch (ou minibatch) de transitions déjà collectées. old_log_probs,
    advantages, returns viennent du buffer (log_prob au moment de la
    collecte, GAE) ; new_log_probs/values/entropy sont recalculés ici sous
    les paramètres actuels de agent.network via evaluate_actions, qui
    réutilise le même masque légal que la collecte."""
    new_log_probs, values, entropy = agent.evaluate_actions(obs, legal_mask, actions)

    advantages = torch.as_tensor(np.asarray(advantages), dtype=torch.float32)
    if normalize_advantages:
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)

    old_log_probs = torch.as_tensor(np.asarray(old_log_probs), dtype=torch.float32)
    log_ratio = new_log_probs - old_log_probs
    ratio = torch.exp(log_ratio)

    surrogate1 = ratio * advantages
    surrogate2 = torch.clamp(ratio, 1 - clip_eps, 1 + clip_eps) * advantages
    policy_loss = -torch.min(surrogate1, surrogate2).mean()

    returns = torch.as_tensor(np.asarray(returns), dtype=torch.float32)
    value_loss = ((values - returns) ** 2).mean()

    entropy_mean = entropy.mean()

    loss = policy_loss + value_coef * value_loss - entropy_coef * entropy_mean

    with torch.no_grad():
        approx_kl = ((ratio - 1) - log_ratio).mean()
        clip_fraction = (torch.abs(ratio - 1) > clip_eps).float().mean()

    metrics = {
        "loss": loss.item(),
        "policy_loss": policy_loss.item(),
        "value_loss": value_loss.item(),
        "entropy": entropy_mean.item(),
        "approx_kl": approx_kl.item(),
        "clip_fraction": clip_fraction.item(),
    }

    return loss, metrics
