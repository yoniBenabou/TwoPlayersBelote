import random
import sys
import time

import numpy as np

from belote.rl.agents import TrumpCountAgent
from belote.rl.env import BeloteEnv
from belote.rl.evaluation import play_episode
from belote.rl.pimc import PIMCAgent
from scripts.compare_checkpoints import load_agent

MODEL = "models/ppo_bidding_2M.pt"


def positions(n, seed=0):
    """Positions de jeu réelles (agent au trait pendant le jeu de la carte), agent contre TrumpCount."""
    random.seed(seed)
    np.random.seed(seed)
    base, opponent = load_agent(MODEL), TrumpCountAgent()
    env = BeloteEnv(bidding=True)
    found = []
    while len(found) < n:
        obs, info = env.reset(options={"starting_player": random.randint(0, 1)})
        me = random.randint(0, 1)
        done = False
        while not done:
            if env.phase == "play" and env.current_idx == me and info["legal_actions"].sum() > 1 and random.random() < 0.3:
                found.append(env.clone())
            agent = base if env.current_idx == me else opponent
            obs, _, done, info = env.step(agent.act(obs, info["legal_actions"], info))
    return found


def check_clone_is_independent():
    env = BeloteEnv(bidding=True)
    env.reset(options={"starting_player": 0})
    twin = env.clone()
    assert twin.deal is None, "la copie ne doit pas emporter la donne d'origine"
    hand0 = list(env.players[0].hand)
    twin.step(int(np.flatnonzero(twin._legal_action_mask())[0]))
    while twin.phase != "play" and not twin.done:
        twin.step(int(np.flatnonzero(twin._legal_action_mask())[-1]))
    if not twin.done:
        twin.step(int(np.flatnonzero(twin._legal_action_mask())[0]))
    assert env.players[0].hand == hand0 and env.phase == "bid1" and not any(env.played_public), \
        "jouer dans la copie ne doit pas modifier la vraie partie"


def check_sampled_hands_are_consistent(n=300):
    """La vraie main de l'adversaire est toujours parmi les cartes possibles, et les
    mains imaginées ne contiennent jamais une carte vue (ma main, tombée, retournée)."""
    agent = PIMCAgent(load_agent(MODEL), n_samples=5)
    for env in positions(n):
        agent.attach_env(env)
        me, opp = env.current_idx, 1 - env.current_idx
        possible, n_opp, opp_played = agent._public(me)
        true_hand = set(env.players[opp].hand)
        assert true_hand <= set(possible), "une déduction a exclu une carte que l'adversaire a vraiment"
        assert n_opp == len(true_hand) and len(possible) >= n_opp
        seen = set(env.players[me].hand) | {env.turned_card}
        assert not seen & set(possible), "une carte vue ne peut pas être chez l'adversaire"
        assert sorted(opp_played, key=str) == sorted(
            [c for c in env.players[opp].dealt_hand if c not in true_hand], key=str)


def check_no_peeking(n=40):
    """Remplacer la vraie main de l'adversaire par une autre main compatible avec
    l'information publique ne change ni la décision ni les gains estimés."""
    for k, env in enumerate(positions(n, seed=1)):
        me, opp = env.current_idx, 1 - env.current_idx
        obs, mask = env._observe(me), env._legal_action_mask()
        first = PIMCAgent(load_agent(MODEL), n_samples=8, seed=k)
        first.attach_env(env)
        action, values = first.act(obs, mask, {"phase": "play"}), first.last_values

        possible, n_opp, opp_played = first._public(me)
        other = env.clone()
        swap = random.Random(k).sample(possible, n_opp)
        other.players[opp].hand = list(swap)
        other.players[opp].dealt_hand = list(swap) + opp_played
        second = PIMCAgent(load_agent(MODEL), n_samples=8, seed=k)
        second.attach_env(other)
        assert second.act(obs, mask, {"phase": "play"}) == action and second.last_values == values, \
            "la décision dépend de la vraie main de l'adversaire"


def check_plays_full_rounds(n=30):
    agent, opponent = PIMCAgent(load_agent(MODEL), n_samples=10), TrumpCountAgent()
    env = BeloteEnv(bidding=True)
    start = time.time()
    for k in range(n):
        seats = (agent, opponent) if k % 2 == 0 else (opponent, agent)
        points = play_episode(env, *seats)
        assert len(points) == 2
    return (time.time() - start) / n


def main():
    check_clone_is_independent()
    print("Copie de la partie : indépendante, sans la donne d'origine : OK")

    check_sampled_hands_are_consistent()
    print("Mains imaginées compatibles avec l'information publique (300 positions) : OK")

    check_no_peeking()
    print("Pas de triche : décision identique si on change la vraie main de l'adversaire (40 positions) : OK")

    seconds = check_plays_full_rounds()
    print(f"30 manches complètes contre TrumpCount (10 mains imaginées) : OK, {seconds:.2f} s par manche")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
