import sys

from belote.env import BeloteEnv
from belote.gae import compute_gae
from belote.networks import ActorCriticNetwork
from belote.ppo_agent import PPOAgent
from belote.self_play import Transition, collect_rollout


def make_transition(reward, value):
    return Transition(obs=None, legal_mask=None, action=0, log_prob=0.0, value=value, reward=reward)


def make_episode(rewards, values):
    return [make_transition(r, v) for r, v in zip(rewards, values)]


def check_monte_carlo_case():
    """Avec gamma=1, lambda=1 (valeurs par défaut), le calcul doit se réduire
    à un retour Monte-Carlo pur : advantage_t = somme des rewards restants -
    value_t, return_t = somme des rewards restants."""
    rewards = [0.1, 0.0, 0.05, 0.0, 0.2, 0.0, 0.0, 0.3, 0.0, 0.1, 0.0, 0.0, 0.15, 0.0, 0.0, 1.0]
    values = [0.4, 0.3, 0.35, 0.2, 0.5, 0.1, 0.0, 0.6, 0.2, 0.3, 0.1, 0.05, 0.4, 0.2, 0.1, 0.9]
    assert len(rewards) == len(values) == 16

    episode = make_episode(rewards, values)
    compute_gae(episode)

    for t in range(len(episode)):
        remaining = sum(rewards[t:])
        expected_advantage = remaining - values[t]
        expected_return = remaining
        assert abs(episode[t].advantage - expected_advantage) < 1e-9, (t, episode[t].advantage, expected_advantage)
        assert abs(episode[t].return_ - expected_return) < 1e-9, (t, episode[t].return_, expected_return)


def check_terminal_has_no_bootstrap():
    """La dernière transition d'une manche ne doit bénéficier d'aucun
    bootstrap : son advantage/return_ ne dépend que de son propre reward et
    de sa propre value, jamais d'une valeur au-delà de la manche."""
    rewards = [0.0] * 15 + [0.42]
    values = [0.0] * 15 + [0.17]
    episode = make_episode(rewards, values)
    compute_gae(episode)

    assert abs(episode[-1].advantage - (0.42 - 0.17)) < 1e-9, episode[-1].advantage
    assert abs(episode[-1].return_ - 0.42) < 1e-9, episode[-1].return_


def check_no_leak_between_episodes():
    """compute_gae ne doit être appelé que sur une seule manche à la fois :
    calculer une manche A avant une manche B ne doit avoir aucune influence
    sur le résultat de B (pas de fuite de bootstrap au-delà de sa propre
    manche)."""
    rewards_a = [0.05] * 16
    values_a = [0.3] * 16
    rewards_b = [0.02, 0.0, 0.1, 0.0, 0.0, 0.4, 0.0, 0.0, 0.0, 0.05, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9]
    values_b = [0.2, 0.1, 0.3, 0.15, 0.1, 0.5, 0.2, 0.1, 0.05, 0.2, 0.1, 0.05, 0.1, 0.1, 0.05, 0.8]

    episode_b_alone = make_episode(rewards_b, values_b)
    compute_gae(episode_b_alone)

    episode_a = make_episode(rewards_a, values_a)
    episode_b_after_a = make_episode(rewards_b, values_b)
    compute_gae(episode_a)
    compute_gae(episode_b_after_a)

    for t in range(16):
        assert episode_b_alone[t].advantage == episode_b_after_a[t].advantage, t
        assert episode_b_alone[t].return_ == episode_b_after_a[t].return_, t


def check_integration_with_real_rollout(n_episodes=20):
    """Sur un vrai rollout self-play, vérifie l'identité de base
    return_ == advantage + value (valable quels que soient gamma/lambda) et
    que le calcul a bien été effectué (pas de valeurs par défaut à 0.0
    partout)."""
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())
    buffer = collect_rollout(env, agent, n_episodes=n_episodes)

    assert len(buffer) == n_episodes * 16

    any_nonzero_advantage = False
    for t in buffer:
        assert abs(t.return_ - (t.advantage + t.value)) < 1e-6, (t.return_, t.advantage, t.value)
        if t.advantage != 0.0:
            any_nonzero_advantage = True

    assert any_nonzero_advantage, "toutes les advantages sont à 0.0, GAE n'a probablement pas été appliqué"


def main():
    check_monte_carlo_case()
    print("Cas Monte-Carlo (gamma=1, lambda=1) : OK")

    check_terminal_has_no_bootstrap()
    print("Dernière transition d'une manche : pas de bootstrap résiduel : OK")

    check_no_leak_between_episodes()
    print("Pas de fuite de bootstrap entre deux manches distinctes : OK")

    check_integration_with_real_rollout()
    print("Intégration avec collect_rollout (identité return_ == advantage + value) : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
