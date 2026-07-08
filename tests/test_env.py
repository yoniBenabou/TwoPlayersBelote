import random
import sys
import time

import numpy as np

from belote.engine import has_belote
from belote.env import CARD_INDEX, BeloteEnv, MAX_SCORE, NUM_CARDS, NUM_TRICKS, SUITS

TRICK_WINNERS_OFFSET = NUM_CARDS * 2 + len(SUITS) + 2
TRICK_HISTORY_OFFSET = TRICK_WINNERS_OFFSET + NUM_TRICKS
TRICK_HISTORY_STRIDE = NUM_CARDS * 2 + 1


def total_dealt_points(env):
    """Points de toutes les cartes distribuées cette manche (indépendant des plis joués)."""
    return sum(
        card.points(env.trump_suit)
        for player in env.players
        for card in player.dealt_hand
    )


def belote_rebelote_bonus(env):
    return sum(20 for player in env.players if has_belote(player.dealt_hand, env.trump_suit))


def check_illegal_action_is_rejected():
    env = BeloteEnv()
    obs, info = env.reset(seed=1)
    illegal_action = next(i for i, ok in enumerate(info["legal_actions"]) if not ok)
    try:
        env.step(illegal_action)
    except ValueError:
        return
    raise AssertionError("Une action illégale aurait dû lever une ValueError.")


def check_trick_winners_are_relative_to_viewer(n_episodes=200):
    """trick_winners dans l'observation doit être encodé du point de vue du
    joueur actif (1.0 = moi, -1.0 = adversaire, 0.0 = pas encore joué), et
    non par siège absolu."""
    env = BeloteEnv()
    for _ in range(n_episodes):
        obs, info = env.reset()
        while True:
            legal = [i for i, ok in enumerate(info["legal_actions"]) if ok]
            action = random.choice(legal)
            obs, _, done, info = env.step(action)
            if done:
                break
            viewer = env.current_idx
            for i, winner in enumerate(env.trick_winners):
                expected = 0.0 if winner == -1 else (1.0 if winner == viewer else -1.0)
                encoded = obs[TRICK_WINNERS_OFFSET + i]
                assert encoded == expected, (i, winner, viewer, encoded, expected)


def check_trick_history_matches_actual_play(n_episodes=200):
    """Le bloc d'historique des plis dans l'observation (ma carte / carte
    adverse / qui a mené, par pli) doit correspondre exactement à ce qui a
    été réellement joué, y compris pour le pli en cours (cas du suiveur qui
    doit voir la carte que le meneur vient de jouer avant même la fin du
    pli)."""
    env = BeloteEnv()
    for _ in range(n_episodes):
        obs, info = env.reset()
        while True:
            legal = [i for i, ok in enumerate(info["legal_actions"]) if ok]
            action = random.choice(legal)
            obs, _, done, info = env.step(action)
            viewer = env.current_idx

            for i in range(NUM_TRICKS):
                base = TRICK_HISTORY_OFFSET + i * TRICK_HISTORY_STRIDE
                my_block = obs[base: base + NUM_CARDS]
                opp_block = obs[base + NUM_CARDS: base + 2 * NUM_CARDS]
                leader_flag = obs[base + 2 * NUM_CARDS]

                leader = env._trick_leader_card[i]
                follower = env._trick_follower_card[i]

                expected_my = np.zeros(NUM_CARDS, dtype=np.float32)
                expected_opp = np.zeros(NUM_CARDS, dtype=np.float32)
                for played in (leader, follower):
                    if played is None:
                        continue
                    played_idx, played_card = played
                    target = expected_my if played_idx == viewer else expected_opp
                    target[CARD_INDEX[played_card]] = 1.0

                assert (my_block == expected_my).all(), (i, "my_block", my_block, expected_my)
                assert (opp_block == expected_opp).all(), (i, "opp_block", opp_block, expected_opp)

                if leader is None:
                    expected_leader_flag = 0.0
                else:
                    expected_leader_flag = 1.0 if leader[0] == viewer else -1.0
                assert leader_flag == expected_leader_flag, (i, leader_flag, expected_leader_flag)

            if done:
                break


def check_starting_player_option():
    env = BeloteEnv()

    obs, info = env.reset()
    assert env.current_idx == 0, "comportement par défaut inchangé : le joueur 0 commence"
    assert info["current_player"] == 0

    obs, info = env.reset(options={"starting_player": 1})
    assert env.current_idx == 1
    assert info["current_player"] == 1

    obs, info = env.reset(options={"starting_player": 0})
    assert env.current_idx == 0
    assert info["current_player"] == 0


def run_episode(env):
    obs, info = env.reset()
    cumulative = {"0": 0.0, "1": 0.0}
    while True:
        legal = [i for i, ok in enumerate(info["legal_actions"]) if ok]
        action = random.choice(legal)
        obs, rewards, done, info = env.step(action)
        cumulative["0"] += rewards["0"]
        cumulative["1"] += rewards["1"]
        if done:
            return cumulative


def main(n_episodes=2000):
    check_illegal_action_is_rejected()
    print("Rejet des actions illégales : OK")

    check_trick_winners_are_relative_to_viewer()
    print("Encodage relatif de trick_winners (moi/adversaire) : OK")

    check_trick_history_matches_actual_play()
    print("Historique des plis dans l'observation (ma carte/carte adverse/meneur) : OK")

    check_starting_player_option()
    print("Option reset(options={'starting_player': ...}) : OK")

    env = BeloteEnv()
    wins = [0, 0, 0]  # joueur 0, joueur 1, égalité
    total_points = [0.0, 0.0]

    start = time.perf_counter()
    for _ in range(n_episodes):
        cumulative = run_episode(env)
        p0 = cumulative["0"] * MAX_SCORE
        p1 = cumulative["1"] * MAX_SCORE

        dealt_points = total_dealt_points(env)
        expected_total = dealt_points + 10 + belote_rebelote_bonus(env)  # dix de der + belote-rebelote
        assert abs((p0 + p1) - expected_total) < 1e-6, (p0, p1, dealt_points, expected_total)

        total_points[0] += p0
        total_points[1] += p1
        if p0 > p1:
            wins[0] += 1
        elif p1 > p0:
            wins[1] += 1
        else:
            wins[2] += 1
    elapsed = time.perf_counter() - start

    print(f"Cohérence des scores sur {n_episodes} épisodes : OK")
    print(f"\n{n_episodes} épisodes en {elapsed:.2f}s ({n_episodes / elapsed:.0f} épisodes/s)")
    print(f"Score moyen joueur 0 : {total_points[0] / n_episodes:.2f}")
    print(f"Score moyen joueur 1 : {total_points[1] / n_episodes:.2f}")
    print(f"Victoires joueur 0   : {wins[0]} ({100 * wins[0] / n_episodes:.1f}%)")
    print(f"Victoires joueur 1   : {wins[1]} ({100 * wins[1] / n_episodes:.1f}%)")
    print(f"Égalités             : {wins[2]} ({100 * wins[2] / n_episodes:.1f}%)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
