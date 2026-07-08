import sys

from belote.env import BeloteEnv, MAX_SCORE
from belote.networks import ActorCriticNetwork
from belote.ppo_agent import PPOAgent
from belote.self_play import collect_episode, collect_rollout
from test_env import belote_rebelote_bonus, total_dealt_points


def check_episode_shape_and_legality(n_episodes=200):
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())

    for i in range(n_episodes):
        transitions = collect_episode(env, agent, starting_player=i % 2)
        assert len(transitions) == 16, len(transitions)
        for t in transitions:
            assert t.legal_mask[t.action], "action illégale dans le buffer de self-play"


def check_reward_credit_matches_real_points(n_episodes=500):
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())

    for i in range(n_episodes):
        transitions = collect_episode(env, agent, starting_player=i % 2)
        # Le bonus terminal (+1/-1) est à somme nulle sur l'épisode entier, donc il
        # n'affecte pas ce total même non normalisé par MAX_SCORE.
        total_reward = sum(t.reward for t in transitions) * MAX_SCORE
        expected_total = total_dealt_points(env) + 10 + belote_rebelote_bonus(env)
        assert abs(total_reward - expected_total) < 1e-4, (total_reward, expected_total)


def check_collect_rollout_size_and_legality(n_episodes=50):
    env = BeloteEnv()
    agent = PPOAgent(ActorCriticNetwork())

    buffer = collect_rollout(env, agent, n_episodes=n_episodes)
    assert len(buffer) == n_episodes * 16, len(buffer)
    for t in buffer:
        assert t.legal_mask[t.action], "action illégale dans le rollout agrégé"


def main():
    check_episode_shape_and_legality()
    print("collect_episode : 16 transitions légales par manche : OK")

    check_reward_credit_matches_real_points()
    print("Somme des rewards crédités == points réels de la manche (crédit différé correct) : OK")

    check_collect_rollout_size_and_legality()
    print("collect_rollout : taille du buffer agrégé + légalité : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
