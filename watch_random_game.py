import argparse
import random
import sys

from belote.cards import SUIT_SYMBOLS, sort_hand
from belote.env import BeloteEnv, INDEX_CARD, MAX_SCORE


def format_hand(hand, trump_suit):
    return "  ".join(str(card) for card in sort_hand(hand, trump_suit))


def play_and_show(env):
    obs, info = env.reset()
    trump_suit = env.trump_suit
    print(f"\nAtout : {SUIT_SYMBOLS[trump_suit]}")
    print(f"Main Joueur 0 : {format_hand(env.players[0].dealt_hand, trump_suit)}")
    print(f"Main Joueur 1 : {format_hand(env.players[1].dealt_hand, trump_suit)}")

    trick_no = 1
    trick_cards = []
    cumulative = {"0": 0.0, "1": 0.0}

    while True:
        player_idx = env.current_idx
        legal = [i for i, ok in enumerate(info["legal_actions"]) if ok]
        action = random.choice(legal)
        card = INDEX_CARD[action]

        obs, rewards, done, info = env.step(action)
        cumulative["0"] += rewards["0"]
        cumulative["1"] += rewards["1"]
        trick_cards.append((player_idx, card))

        if len(trick_cards) == 2:
            (p_a, c_a), (p_b, c_b) = trick_cards
            winner = env.trick_winners[trick_no - 1]
            trick_points = c_a.points(trump_suit) + c_b.points(trump_suit)
            if trick_no == 8:
                trick_points += 10  # dix de der
            print(
                f"Pli {trick_no} : Joueur {p_a} joue {c_a} | Joueur {p_b} joue {c_b}"
                f"  -> gagné par Joueur {winner} ({trick_points} pts)"
            )
            trick_cards = []
            trick_no += 1

        if done:
            p0 = cumulative["0"] * MAX_SCORE
            p1 = cumulative["1"] * MAX_SCORE
            print(f"Score final : Joueur 0 = {p0:.0f} | Joueur 1 = {p1:.0f}")
            return


def main(n_games):
    env = BeloteEnv()
    for i in range(1, n_games + 1):
        print(f"=== Partie {i}/{n_games} ===")
        play_and_show(env)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Affiche le détail de parties jouées par deux agents aléatoires.")
    parser.add_argument("--games", type=int, default=1, help="Nombre de parties à afficher.")
    args = parser.parse_args()
    main(args.games)
