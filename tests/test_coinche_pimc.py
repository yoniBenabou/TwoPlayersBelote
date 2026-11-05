"""Recherche PIMC à 4 : mains tirées compatibles avec les déductions, annonces revues comme le réseau les a vues,
pas de triche, parties complètes."""
import random
import sys

import numpy as np

from belote.coinche.conventions import CONVENTIONS, ConventionTracker, auction_steps
from belote.coinche.pimc import CoinchePIMC, clone_env, make_world, play_log_likelihoods, play_steps, sample_hidden_hands
from belote.coinche.rl_env import CARD_INDEX, NUM_ACTIONS_BIDDING, OFFSET, CoincheEnv
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


def check_auction_replay():
    """Les annonces revues par la recherche (avec la vraie main) donnent l'observation et les annonces
    légales que le joueur avait au moment d'annoncer."""
    rng = random.Random(4)
    n = 0
    for k in range(200):
        env = CoincheEnv(bidding=True, seed=900 + k)
        env.reset()
        seen = []
        while env.game.phase == "bidding" and not env.done:
            legal = np.flatnonzero(env.legal_mask())
            seen.append((env.game.current, env._observe(), env.legal_mask()))
            env.step(int(rng.choice(legal)))
        if env.game.phase != "play":
            continue
        me = rng.randrange(4)
        steps = auction_steps(env, me)
        expected = [x for x in seen if x[0] != me]
        assert len(steps) == len(expected)
        for st, (seat2, obs2, mask2) in zip(steps, expected):
            obs = st.obs.copy()
            for c in env.game.dealt[st.seat]:
                obs[OFFSET["hand"] + CARD_INDEX[c]] = 1
            assert st.seat == seat2 and np.array_equal(obs, obs2) and np.array_equal(st.mask, mask2)
            assert not st.volley
            g = st.game
            assert all(h == [] for h in g.hands), "une main reste visible dans la copie"
            n += 1
    return n


def check_volley_step():
    """Une coinche à la volée (hors de son tour) est reconnue comme telle."""
    for k in range(200):
        env = CoincheEnv(bidding=True, seed=2000 + k)
        env.reset()
        game = env.game
        if game.phase != "bidding":
            continue
        game.bid(game.current, ("bid", 80, game.hands[game.current][0].suit))
        late = [s for s in game.volley_seats() if s != game.current]
        if not late:
            continue
        game.coinche_out_of_turn(late[0])
        steps = auction_steps(env)
        assert [st.volley for st in steps] == [False, True] and steps[1].bid == ("coinche",)
        return
    raise AssertionError("pas de coinche à la volée possible")


def check_tracker_learns(network):
    """Quatre robots aux conventions différentes : après quelques donnes, le suivi reconnaît chacun."""
    seats = ["asr", "papirobert", "petitjeu", "asr"]
    bots = [CONVENTIONS[n]() for n in seats]
    tracker = ConventionTracker(network)
    rng = random.Random(6)
    deals = 0
    while deals < 25:
        env = CoincheEnv(bidding=True, seed=rng.randrange(10 ** 6))
        env.reset()
        game = env.game
        while game.phase == "bidding":
            game.bid(game.current, bots[game.current].bid(game, game.current))
        if game.phase != "play":
            continue
        tracker.end_deal(env, {s: list(game.dealt[s]) for s in range(4)})
        deals += 1
    found = [next(iter(tracker.beliefs(s))) for s in range(4)]
    assert found == seats, (found, [tracker.beliefs(s) for s in range(4)])
    assert all(max(tracker.beliefs(s).values()) < 0.99 for s in range(4)), "jamais tout à fait certain"
    return found


def check_auction_weights(network):
    """Poids finis ; la vraie répartition n'est jamais impossible."""
    tracker = ConventionTracker(network)
    rng = random.Random(5)
    for k in range(20):
        env = play_until(CoincheEnv(bidding=True, seed=300 + k), rng, rng.randrange(0, 20))
        if env is None:
            continue
        me = env.game.current
        true = {s: list(env.game.hands[s]) for s in range(4) if s != me}
        pool = [sample_hidden_hands(env, me, rng) for _ in range(10)] + [true]
        pool = [{s: h + env.game.played[s] for s, h in hands.items()} for hands in pool]
        logw = tracker.log_weights(env, me, pool)
        assert logw.shape == (11,) and np.all(np.isfinite(logw)) and np.all(logw <= 0)


def check_play_replay(network):
    """Les cartes revues par la recherche (avec la vraie main) donnent l'observation que le joueur avait
    au moment de jouer ; avec les vraies mains, aucune carte jouée n'est impossible."""
    rng = random.Random(8)
    n = 0
    for k in range(60):
        env = CoincheEnv(bidding=True, seed=4000 + k)
        env.reset()
        while env.game.phase == "bidding" and not env.done:
            env.step(int(rng.choice(np.flatnonzero(env.legal_mask()))))
        if env.done:
            continue
        seen = []
        for _ in range(rng.randrange(1, 30)):
            seen.append((env.game.current, env._observe()))
            env.step(int(rng.choice(np.flatnonzero(env.legal_mask()))))
            if env.done:
                break
        if env.done:
            continue
        me = env.game.current
        steps = play_steps(env, me)
        expected = [x for x in seen if x[0] != me]
        assert len(steps) == len(expected)
        for (seat, k2, obs, _trick, _card), (seat2, obs2) in zip(steps, expected):
            obs = obs.copy()
            hand = [c for c in env.game.dealt[seat] if c not in env.game.played[seat][:k2]]
            for c in hand:
                obs[OFFSET["hand"] + CARD_INDEX[c]] = 1
                for r in range(3):
                    obs[OFFSET["possible"] + r * 32 + CARD_INDEX[c]] = 0
            assert seat == seat2 and np.array_equal(obs, obs2), "carte revue différente"
            n += 1
        true = {s: list(env.game.dealt[s]) for s in range(4) if s != me}
        ll = play_log_likelihoods(network, env, me, [true])
        assert np.isfinite(ll[0]) and ll[0] > -1e3, "une carte vraiment jouée jugée impossible"
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
    """Même graine : la décision ne change pas si on échange les cartes cachées des autres joueurs
    (pendant le jeu, avec la lecture des cartes jouées, et pendant les annonces)."""
    rng = random.Random(2)
    tested = 0
    for k in range(60):
        if k % 3 == 2:  # pendant les annonces
            env = CoincheEnv(bidding=True, seed=100 + k)
            env.reset()
            for _ in range(rng.randrange(0, 4)):
                if env.game.phase == "bidding":
                    env.step(int(rng.choice(np.flatnonzero(env.legal_mask()))))
            if env.game.phase != "bidding":
                continue
        else:
            env = play_until(CoincheEnv(bidding=True, seed=100 + k), rng, rng.randrange(0, 20))
        if env is None or len(np.flatnonzero(env.legal_mask())) < 2:
            continue
        me = env.game.current
        make = lambda: CoinchePIMC(network, n_samples=6, seed=7, read_plays=True, bid_search=True, bid_samples=4)
        a1 = make().act(env)
        others = [s for s in range(4) if s != me]
        pool = [c for s in others for c in env.game.hands[s]]
        rng.shuffle(pool)
        i = 0
        for s in others:
            m = len(env.game.hands[s])
            env.game.hands[s] = pool[i:i + m]
            env.game.dealt[s] = env.game.hands[s] + env.game.played[s]
            i += m
        a2 = make().act(env)
        assert a1 == a2, "la recherche dépend des cartes cachées"
        tested += 1
    return tested


def check_full_deals(network, n=5):
    search = CoinchePIMC(network, n_samples=4, seed=0, read_plays=True, bid_search=True, bid_samples=4)
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
    b = check_auction_replay()
    check_volley_step()
    check_auction_weights(network)
    found = check_tracker_learns(network)
    p = check_play_replay(network)
    check_clone_independent()
    t = check_no_cheating(network)
    check_full_deals(network)
    print(f"Recherche PIMC à 4 ({n} tirages conformes aux déductions, {b} annonces revues à l'identique, "
          f"{p} cartes revues à l'identique, {t} décisions sans triche, conventions reconnues {found}, donnes complètes) : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
