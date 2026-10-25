import random
import sys

import numpy as np
import torch

from belote.core.engine import has_belote
from belote.rl.agents import HeuristicAgent, RandomAgent, TrumpCountAgent, VoidExploitAgent
from belote.rl.env import (
    CARD_INDEX, MAX_SCORE, NAME_SUIT, NUM_ACTIONS_BIDDING, NUM_CARDS, OBS_SIZE, PASS, SUITS, TAKE, BeloteEnv,
)
from belote.rl.networks import ActorCriticNetwork
from belote.rl.ppo_agent import PPOAgent
from belote.rl.ppo_update import ppo_update
from belote.rl.self_play import collect_rollout

BASE_MODEL = "models/ppo_CA_3M.pt"


def legal(info):
    return {i for i, ok in enumerate(info["legal_actions"]) if ok}


def check_first_speaker_takes():
    env = BeloteEnv(bidding=True)
    obs, info = env.reset(options={"starting_player": 1})
    hand0, hand1, turned = env.deal
    assert turned not in hand0 and turned not in hand1, "la carte retournée vient des cartes non distribuées"
    assert env.trump_suit is None and info["phase"] == "bid1" and env.current_idx == 1
    assert legal(info) == {TAKE, PASS}
    assert obs.shape == (env.obs_size,) and env.num_actions == NUM_ACTIONS_BIDDING

    obs, rewards, done, info = env.step(TAKE)
    assert not done and rewards == {"0": 0.0, "1": 0.0}
    assert env.trump_suit == turned.suit and env.taker == 1 and info["phase"] == "play"
    assert env.current_idx == 1, "celui qui parle en premier mène le premier pli"
    assert all(a < NUM_CARDS for a in legal(info)), "pendant le jeu, seules des cartes sont jouables"


def check_second_speaker_takes():
    env = BeloteEnv(bidding=True)
    env.reset(options={"starting_player": 0})
    _, _, done, info = env.step(PASS)
    assert not done and env.current_idx == 1 and info["phase"] == "bid1"
    _, _, done, info = env.step(TAKE)
    assert env.taker == 1 and env.trump_suit == env.turned_card.suit
    assert env.current_idx == 0 and info["phase"] == "play", "le premier à parler mène, même s'il n'a pas pris"


def check_second_round_and_redeal():
    env = BeloteEnv(bidding=True)
    env.reset(options={"starting_player": 0})
    env.step(PASS)
    _, _, _, info = env.step(PASS)
    assert info["phase"] == "bid2" and env.current_idx == 0
    expected = {PASS} | {NAME_SUIT[s] for s in SUITS if s != env.turned_card.suit}
    assert legal(info) == expected, "au tour 2, une des 3 autres couleurs ou passer"
    try:
        env.step(NAME_SUIT[env.turned_card.suit])
        raise AssertionError("nommer la couleur retournée au tour 2 doit être refusé")
    except ValueError:
        pass
    other_suit = next(s for s in SUITS if s != env.turned_card.suit)
    env.step(PASS)
    _, _, _, info = env.step(NAME_SUIT[other_suit])
    assert env.trump_suit == other_suit and env.taker == 1 and info["phase"] == "play"

    # Les deux passent deux fois : redistribution, aucun point.
    env.reset(options={"starting_player": 1})
    for _ in range(3):
        env.step(PASS)
    _, rewards, done, info = env.step(PASS)
    assert done and info["redeal"] and info["final_points"] == (0, 0) and rewards == {"0": 0.0, "1": 0.0}
    try:
        env.step(PASS)
        raise AssertionError("jouer après une redistribution doit être refusé")
    except RuntimeError:
        pass

    # Annonces interdites au tour 1.
    env.reset()
    for illegal in (NAME_SUIT[SUITS[0]], 0):
        try:
            env.step(illegal)
            raise AssertionError(f"action {illegal} acceptée au tour 1")
        except ValueError:
            pass


def check_contract_and_rewards(n_episodes=3000, dedans_rule=True):
    """Sur des manches aléatoires : la règle du "dedans" est appliquée
    exactement (recalcul à partir des plis), et la somme des rewards de chaque
    joueur vaut toujours ses points finaux. dedans_rule=False : la règle
    n'est jamais appliquée (expérience de contrôle)."""
    env = BeloteEnv(bidding=True, win_bonus=False, dedans=dedans_rule)
    dedans = played = 0
    for g in range(n_episodes):
        obs, info = env.reset(options={"starting_player": g % 2})
        totals = {"0": 0.0, "1": 0.0}
        done = False
        while not done:
            obs, rewards, done, info = env.step(random.choice(sorted(legal(info))))
            totals["0"] += rewards["0"]
            totals["1"] += rewards["1"]
        if info["redeal"]:
            continue
        played += 1
        trump, taker = env.trump_suit, env.taker
        raw = {i: env.players[i].manche_points(trump) for i in (0, 1)}
        raw[env.trick_winners[7]] += 10
        belote = {i: 20 if has_belote(env.players[i].dealt_hand, trump) else 0 for i in (0, 1)}
        expected = {i: raw[i] + belote[i] for i in (0, 1)}
        if dedans_rule and expected[taker] < expected[1 - taker]:
            dedans += 1
            assert info["dedans"]
            expected = {taker: belote[taker], 1 - taker: raw[0] + raw[1] + belote[1 - taker]}
        else:
            assert not info["dedans"]
        assert info["final_points"] == (expected[0], expected[1]), (info["final_points"], expected)
        for i in (0, 1):
            assert abs(totals[str(i)] * MAX_SCORE - expected[i]) < 1e-6
    assert (dedans > 0) == dedans_rule and played > 0.9 * n_episodes


def check_heuristics_bid_and_play(n_episodes=300):
    """Les agents de référence annoncent puis jouent ; TrumpCountAgent compte
    ses atouts une fois l'atout connu (pas pendant les annonces)."""
    env = BeloteEnv(bidding=True)
    for agent_cls in (RandomAgent, HeuristicAgent, VoidExploitAgent, TrumpCountAgent):
        a, b = agent_cls(), agent_cls()
        for g in range(n_episodes):
            obs, info = env.reset(options={"starting_player": g % 2})
            done = False
            while not done:
                agent = a if env.current_idx == 0 else b
                action = agent.act(obs, info["legal_actions"], info)
                assert info["legal_actions"][action], f"{agent_cls.__name__} : action illégale {action}"
                obs, _, done, info = env.step(action)
            if agent_cls is TrumpCountAgent and not info["redeal"]:
                trumps = sum(c.suit == env.trump_suit for c in env.players[0].dealt_hand)
                assert a._mode == ("attack" if trumps > TrumpCountAgent.TRUMP_THRESHOLD else "ace_longest")


def check_warm_start_plays_like_base_model(n_states=200):
    """Démarrage à chaud : pendant le jeu, le nouveau réseau donne exactement
    les mêmes scores de cartes que l'ancien ; les annonces partent à égalité."""
    base = ActorCriticNetwork.from_checkpoint(BASE_MODEL)
    env = BeloteEnv(bidding=True)
    net = ActorCriticNetwork(obs_size=env.obs_size, num_actions=env.num_actions)
    net.init_from(BASE_MODEL)
    assert net.env_kwargs() == {"belief": False, "bidding": True}
    checked = 0
    while checked < n_states:
        obs, info = env.reset()
        done = False
        while not done:
            with torch.no_grad():
                logits, value = net(torch.as_tensor(obs))
                if info["phase"] == "play":
                    base_logits, base_value = base(torch.as_tensor(obs[:OBS_SIZE]))
                    assert torch.allclose(logits[:NUM_CARDS], base_logits, atol=1e-5)
                    assert torch.allclose(value, base_value, atol=1e-5)
                    checked += 1
                else:
                    assert torch.all(logits[NUM_CARDS:] == 0), "les annonces démarrent sans préférence"
            obs, _, done, info = env.step(random.choice(sorted(legal(info))))


def check_ppo_loop_with_bidding():
    """Self-play + mise à jour PPO de bout en bout avec les annonces, et
    l'agent ne choisit que des actions légales (cartes et annonces)."""
    env = BeloteEnv(bidding=True, win_bonus=False)
    net = ActorCriticNetwork(obs_size=env.obs_size, num_actions=env.num_actions)
    agent = PPOAgent(net)
    buffer = collect_rollout(env, agent, n_episodes=32)
    assert all(t.legal_mask[t.action] for t in buffer)
    assert any(t.action >= NUM_CARDS for t in buffer), "des annonces doivent figurer dans le rollout"
    optimizer = torch.optim.Adam(net.parameters(), lr=3e-4)
    metrics = ppo_update(agent, optimizer, buffer)
    assert all(np.isfinite(v) for v in metrics.values())
    buffer = collect_rollout(env, agent, n_episodes=8, opponents=[TrumpCountAgent()])
    assert all(t.legal_mask[t.action] for t in buffer)


def main():
    random.seed(0)
    np.random.seed(0)
    torch.manual_seed(0)

    check_first_speaker_takes()
    print("Tour 1 : le premier à parler prend, atout = couleur retournée, il mène : OK")

    check_second_speaker_takes()
    print("Tour 1 : le second prend, le premier à parler mène quand même : OK")

    check_second_round_and_redeal()
    print("Tour 2 (3 autres couleurs), redistribution, annonces interdites refusées : OK")

    check_contract_and_rewards()
    print("Contrat « dedans » exact et rewards == points finaux sur 3000 manches : OK")

    check_contract_and_rewards(dedans_rule=False)
    print("Contrôle sans la règle du dedans : jamais appliquée : OK")

    check_heuristics_bid_and_play()
    print("Agents de référence : annonces puis jeu, comptage d'atouts après l'annonce : OK")

    check_warm_start_plays_like_base_model()
    print("Démarrage à chaud : joue les cartes exactement comme le modèle de départ : OK")

    check_ppo_loop_with_bidding()
    print("Self-play + PPO avec annonces (et contre heuristique) : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
