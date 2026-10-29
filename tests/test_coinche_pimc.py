"""Recherche PIMC à 4 : mains tirées compatibles avec les déductions, pas de triche, parties complètes."""
import random
import sys

import numpy as np

from belote.coinche.pimc import CoinchePIMC, clone_env, make_world, sample_hidden_hands
from belote.coinche.rl_env import CARD_INDEX, NUM_ACTIONS_BIDDING, CoincheEnv
from belote.rl.networks import ActorCriticNetwork


def play_until(env, rng, steps):
    """Partie au hasard (coups légaux) pendant steps coups de jeu ; None si la donne finit avant."""
    env.reset()
    while env.game.phase == "bidding" and not env.done:
        legal = np.flatnonzero(env.legal_mask())
        env.step(int(rng.choice(legal)))
    for _ in range(steps):
        if env.done:
            return None
        env.step(int(rng.choice(np.flatnonzero(env.legal_mask()))))
    return None if env.done else env


def check_samples():
    rng = random.Random(0)
    n = 0
    for k in range(300):
        env = play_until(CoincheEnv(bidding=True, seed=k), rng, rng.randrange(1, 28))
        if env is None:
            continue
        me = env.game.current
        unseen = env._unseen(me)
        for _ in range(5):
            hands = sample_hidden_hands(env, me, rng)
            pool = sorted(CARD_INDEX[c] for h in hands.values() for c in h)
            assert pool == sorted(np.flatnonzero(unseen).tolist())          # exactement les cartes cachées
            for s, h in hands.items():
                assert len(h) == len(env.game.hands[s])                     # le bon nombre de cartes
                allowed = env._possible_mask(unseen, s)
                assert all(allowed[CARD_INDEX[c]] for c in h), "déduction violée"
            n += 1
    return n


def check_clone_independent():
    rng = random.Random(1)
    env = play_until(CoincheEnv(bidding=True, seed=3), rng, 5)
    before = [list(h) for h in env.game.hands]
    sim = clone_env(env)
    while not sim.done:
        sim.step(int(rng.choice(np.flatnonzero(sim.legal_mask()))))
    assert env.game.hands == before and not env.done and env.game.phase == "play"


def check_no_cheating(network):
    """Même graine : la décision ne change pas si on échange les cartes cachées des autres joueurs."""
    rng = random.Random(2)
    tested = 0
    for k in range(40):
        env = play_until(CoincheEnv(bidding=True, seed=100 + k), rng, rng.randrange(0, 20))
        if env is None or len(np.flatnonzero(env.legal_mask())) < 2:
            continue
        me = env.game.current
        a1 = CoinchePIMC(network, n_samples=6, seed=7).act(env)
        others = [s for s in range(4) if s != me]
        pool = [c for s in others for c in env.game.hands[s]]
        rng.shuffle(pool)
        i = 0
        for s in others:
            m = len(env.game.hands[s])
            env.game.hands[s] = pool[i:i + m]
            i += m
        a2 = CoinchePIMC(network, n_samples=6, seed=7).act(env)
        assert a1 == a2, "la recherche dépend des cartes cachées"
        tested += 1
    return tested


def check_full_deals(network, n=5):
    search = CoinchePIMC(network, n_samples=4, seed=0)
    for k in range(n):
        env = CoincheEnv(bidding=True, seed=500 + k)
        env.reset()
        while not env.done:
            env.step(search.act(env))


def main():
    network = ActorCriticNetwork(obs_size=CoincheEnv(bidding=True).obs_size, num_actions=NUM_ACTIONS_BIDDING,
                                 hidden_size=32)
    network.eval()
    n = check_samples()
    check_clone_independent()
    t = check_no_cheating(network)
    check_full_deals(network)
    print(f"Recherche PIMC à 4 ({n} tirages conformes aux déductions, {t} décisions sans triche, donnes complètes) : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
