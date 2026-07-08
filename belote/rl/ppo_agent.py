import numpy as np
import torch
from torch.distributions import Categorical

from .networks import ActorCriticNetwork


class PPOAgent:
    """Enveloppe d'inférence autour d'un ActorCriticNetwork partagé, avec deux usages :

    - act(obs, legal_mask, info=None) -> action : même contrat que les agents
      de belote/agents.py (RandomAgent, HeuristicAgent, ...), pour rester
      branchable sur benchmark.py / watch_random_game.py.
    - act_and_evaluate(obs, legal_mask) -> (action, log_prob, value, entropy) :
      utilisé par la future boucle de self-play pour collecter les
      transitions nécessaires à l'entraînement PPO (laisse le contexte de
      gradient au choix de l'appelant : sans grad pendant la collecte de
      rollout, avec grad pendant l'update PPO).
    """

    def __init__(self, network: ActorCriticNetwork, deterministic: bool = False):
        self.network = network
        self.deterministic = deterministic

    def _masked_logits_and_value(self, obs, legal_mask):
        obs_tensor = torch.as_tensor(np.asarray(obs), dtype=torch.float32)
        mask_tensor = torch.as_tensor(np.asarray(legal_mask), dtype=torch.bool)
        logits, value = self.network(obs_tensor)
        masked_logits = logits.masked_fill(~mask_tensor, float("-inf"))
        return masked_logits, value

    def act(self, obs, legal_mask, info=None):
        with torch.no_grad():
            masked_logits, _ = self._masked_logits_and_value(obs, legal_mask)
            action = masked_logits.argmax() if self.deterministic else Categorical(logits=masked_logits).sample()
        return int(action.item())

    def act_and_evaluate(self, obs, legal_mask):
        masked_logits, value = self._masked_logits_and_value(obs, legal_mask)
        dist = Categorical(logits=masked_logits)
        action = dist.sample()
        return int(action.item()), dist.log_prob(action), value, dist.entropy()

    def evaluate_actions(self, obs, legal_mask, actions):
        """Évalue des (obs, legal_mask, action) déjà connus sous les paramètres
        actuels du réseau, pour la mise à jour PPO : contrairement à
        act_and_evaluate, n'échantillonne pas de nouvelle action, réutilise
        celle choisie pendant la collecte du rollout. Même masquage que
        act/act_and_evaluate (via _masked_logits_and_value), indispensable
        pour que le ratio π_new/π_old compare deux distributions au même
        support. Pas de torch.no_grad() ici : le contexte de gradient reste
        au choix de l'appelant (avec grad pendant l'update PPO)."""
        masked_logits, value = self._masked_logits_and_value(obs, legal_mask)
        dist = Categorical(logits=masked_logits)
        actions_tensor = torch.as_tensor(np.asarray(actions), dtype=torch.long)
        return dist.log_prob(actions_tensor), value, dist.entropy()
