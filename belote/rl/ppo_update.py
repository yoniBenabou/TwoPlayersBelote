import numpy as np
import torch

from .ppo_agent import PPOAgent
from .ppo_loss import compute_ppo_loss
from .self_play import Transition, stack_transitions

N_EPOCHS = 4
MINIBATCH_SIZE = 256
MAX_GRAD_NORM = 0.5


def ppo_update(
    agent: PPOAgent,
    optimizer: torch.optim.Optimizer,
    buffer: list[Transition],
    n_epochs: int = N_EPOCHS,
    minibatch_size: int = MINIBATCH_SIZE,
    max_grad_norm: float = MAX_GRAD_NORM,
    **loss_kwargs,
) -> dict[str, float]:
    """Met à jour agent.network sur n_epochs passes du buffer, par minibatchs
    mélangés à chaque epoch. optimizer est construit et possédé par
    l'appelant (son état, ex. moments Adam, doit persister d'un appel à
    l'autre au fil de l'entraînement). Retourne la moyenne des métriques de
    compute_ppo_loss sur tous les minibatchs de cet appel, pour un seul log
    par update."""
    n = len(buffer)
    metrics_history = []

    for _epoch in range(n_epochs):
        indices = np.random.permutation(n)
        for start in range(0, n, minibatch_size):
            minibatch_indices = indices[start: start + minibatch_size]
            minibatch = [buffer[i] for i in minibatch_indices]
            batch = stack_transitions(minibatch)

            loss, metrics = compute_ppo_loss(agent, **batch, **loss_kwargs)

            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(agent.network.parameters(), max_grad_norm)
            optimizer.step()

            metrics_history.append(metrics)

    return {key: float(np.mean([m[key] for m in metrics_history])) for key in metrics_history[0]}
