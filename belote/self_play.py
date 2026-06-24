from dataclasses import dataclass

import numpy as np
import torch

from .env import BeloteEnv
from .ppo_agent import PPOAgent


@dataclass
class Transition:
    obs: np.ndarray
    legal_mask: np.ndarray
    action: int
    log_prob: float
    value: float
    reward: float = 0.0


def collect_episode(env: BeloteEnv, agent: PPOAgent, starting_player: int = 0) -> list[Transition]:
    """Joue une manche complète en self-play : le même agent (réseau partagé)
    choisit l'action à chaque pas, quel que soit le siège actif. Retourne la
    liste chronologique des transitions, sans distinction de siège.

    Le reward d'un pli n'est connu qu'au coup du second joueur (le suiveur) ;
    s'il revient au meneur, il doit être crédité rétroactivement à l'action
    que celui-ci a jouée au pas précédent. last_transition_idx garde la trace
    de la dernière transition de chaque siège physique pour lui appliquer ce
    crédit dès qu'il est connu.
    """
    obs, info = env.reset(options={"starting_player": starting_player})
    buffer: list[Transition] = []
    last_transition_idx = {0: None, 1: None}

    done = False
    while not done:
        legal_mask = info["legal_actions"]
        player_idx = env.current_idx

        with torch.no_grad():
            action, log_prob, value, _entropy = agent.act_and_evaluate(obs, legal_mask)

        buffer.append(Transition(
            obs=obs,
            legal_mask=legal_mask,
            action=action,
            log_prob=log_prob.item(),
            value=value.item(),
        ))
        last_transition_idx[player_idx] = len(buffer) - 1

        obs, rewards, done, info = env.step(action)

        for i in (0, 1):
            idx = last_transition_idx[i]
            if idx is not None:
                buffer[idx].reward += rewards[str(i)]

    return buffer


# Une manche fait toujours 16 transitions (8 plis x 2 joueurs). 128 manches
# = 2048 transitions par rollout, la taille standard d'un rollout PPO pour un
# seul environnement (ex. valeur par défaut de stable-baselines3) ; mesurée à
# ~1s de collecte avec ce réseau sur CPU, donc largement abordable ici.
DEFAULT_ROLLOUT_EPISODES = 128


def collect_rollout(env: BeloteEnv, agent: PPOAgent, n_episodes: int = DEFAULT_ROLLOUT_EPISODES) -> list[Transition]:
    """Enchaîne n_episodes manches en self-play, en alternant qui mène le
    premier pli d'une manche à l'autre (même principe que benchmark.run_match
    pour ne pas biaiser les données par l'avantage structurel du meneur)."""
    buffer: list[Transition] = []
    for i in range(n_episodes):
        buffer.extend(collect_episode(env, agent, starting_player=i % 2))
    return buffer
