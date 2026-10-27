"""Environnement d'apprentissage Coinche à 4 : coups légaux, déductions sur les
mains cachées jamais fausses, rewards à somme nulle, collecte par lots."""
import random
import sys

import numpy as np

from belote.coinche.rl_env import CoincheEnv, action_to_bid, bid_to_action, NUM_ACTIONS_BIDDING
from belote.rl.networks import ActorCriticNetwork
from belote.rl.ppo_agent import PPOAgent
from scripts.train_coinche import collect_rollout, evaluate


def check_bid_encoding():
    for a in range(32, NUM_ACTIONS_BIDDING):
        assert bid_to_action(action_to_bid(a)) == a


def check_random_deals(bidding, n=500):
    env = CoincheEnv(bidding=bidding, seed=0)
    rng = random.Random(0)
    for _ in range(n):
        env.reset()
        done = env.done
        rewards = [0.0] * 4
        while not done:
            me = env.current
            if env.phase == "play":
                for r in (1, 2, 3):
                    other = (me + r) % 4
                    assert set(env.game.hands[other]) <= set(env.possible_cards(me, other)), "déduction fausse"
            mask = env.legal_mask()
            action = int(rng.choice(np.flatnonzero(mask))) if rng.random() < 0.5 else env.play_bot()
            assert mask[action]
            _obs, rewards, done = env.step(action)
        assert abs(sum(rewards)) < 1e-9 and rewards[0] == rewards[2]


def check_rollout(bidding):
    envs = [CoincheEnv(bidding=bidding, seed=i) for i in range(8)]
    agent = PPOAgent(ActorCriticNetwork(envs[0].obs_size, envs[0].num_actions, 64))
    buffer = collect_rollout(envs, agent, 20, vs_bots_share=0.5)
    assert all(t.legal_mask[t.action] for t in buffer)
    assert len({id(t) for t in buffer}) == len(buffer)
    evaluate(PPOAgent(agent.network, deterministic=True), bidding, n_deals=20, n_games=2)


def main():
    check_bid_encoding()
    for bidding in (False, True):
        check_random_deals(bidding)
        check_rollout(bidding)
    print("Environnement Coinche à 4 (encodage des annonces, déductions, rewards, collecte, évaluation) : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
