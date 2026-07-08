import random

from .cards import shuffled_deck, sort_hand, SUIT_SYMBOLS
from .engine import deal_round, random_trump, legal_moves, trick_winner, has_belote
from .player import Player

DEFAULT_TARGET_SCORE = 501


def format_hand(sorted_hand, legal_choices=None):
    parts = []
    for i, card in enumerate(sorted_hand):
        if legal_choices is None:
            marker = ""
        else:
            marker = "" if card in legal_choices else " (interdit)"
        parts.append(f"[{i}] {card}{marker}")
    return "  ".join(parts)


def print_history(history, p1, p2):
    if not history:
        return
    print("\n=== Historique des manches précédentes ===")
    for h in history:
        winner_text = f"{h['winner_name']} en tête" if h["winner_name"] else "Égalité"
        print(
            f"Manche {h['manche']} (atout {SUIT_SYMBOLS[h['trump']]}) : "
            f"{p1.name} = {h['points1']} | {p2.name} = {h['points2']} -> {winner_text}"
        )
    print("=" * 50)


def ask_card(p1, p2, active_player, led_card, trump_suit):
    other_player = p2 if active_player is p1 else p1
    while True:
        choices = legal_moves(active_player.hand, led_card, trump_suit)
        active_sorted = sort_hand(active_player.hand, trump_suit)
        other_sorted = sort_hand(other_player.hand, trump_suit)

        print(f"\nAtout : {SUIT_SYMBOLS[trump_suit]}")
        if led_card is not None:
            print(f"Carte jouée par {other_player.name} : {led_card}")
        print(f"Main de {other_player.name} : {format_hand(other_sorted)}")
        print(f"Main de {active_player.name} (à toi de jouer) : {format_hand(active_sorted, choices)}")

        raw = input(f"\n{active_player.name}, choisis une carte (numéro) : ").strip()
        if not raw.isdigit():
            print("Entrée invalide.")
            continue
        idx = int(raw)
        if idx < 0 or idx >= len(active_sorted):
            print("Numéro invalide.")
            continue
        card = active_sorted[idx]
        if card not in choices:
            print("Coup non autorisé : il faut suivre la couleur, couper à l'atout, ou monter à l'atout si possible.")
            continue
        return card


def play_manche(p1, p2, leader, manche_no):
    deck = shuffled_deck()
    hand1, hand2 = deal_round(deck)
    p1.reset_for_manche(hand1)
    p2.reset_for_manche(hand2)
    trump_suit = random_trump()

    print(f"\n=== Manche {manche_no} ===")
    print(f"Atout de cette manche : {SUIT_SYMBOLS[trump_suit]}")

    current_leader, current_follower = (p1, p2) if leader is p1 else (p2, p1)
    last_trick_winner = None

    for trick_no in range(1, 9):
        print(f"\n--- Pli {trick_no}/8 ---")
        led_card = ask_card(p1, p2, current_leader, None, trump_suit)
        current_leader.hand.remove(led_card)

        follow_card = ask_card(p1, p2, current_follower, led_card, trump_suit)
        current_follower.hand.remove(follow_card)

        result = trick_winner(led_card, follow_card, trump_suit)
        winner = current_leader if result == "leader" else current_follower
        loser = current_follower if result == "leader" else current_leader

        print(f"{current_leader.name} a joué {led_card} | {current_follower.name} a joué {follow_card}")
        print(f"=> {winner.name} remporte le pli {trick_no}.")
        winner.pile.extend([led_card, follow_card])
        last_trick_winner = winner

        current_leader, current_follower = winner, loser

    points1 = p1.manche_points(trump_suit)
    points2 = p2.manche_points(trump_suit)

    if last_trick_winner is p1:
        points1 += 10
    else:
        points2 += 10

    if has_belote(p1.dealt_hand, trump_suit):
        points1 += 20
    if has_belote(p2.dealt_hand, trump_suit):
        points2 += 20

    print(f"\n=== Résultat de la manche {manche_no} ===")
    print(f"{last_trick_winner.name} a remporté le dernier pli (+10, dix de der).")
    if has_belote(p1.dealt_hand, trump_suit):
        print(f"{p1.name} avait Roi + Dame d'atout (+20, Belote-Rebelote).")
    if has_belote(p2.dealt_hand, trump_suit):
        print(f"{p2.name} avait Roi + Dame d'atout (+20, Belote-Rebelote).")

    print(f"Points de la manche : {p1.name} = {points1} | {p2.name} = {points2}")

    p1.score += points1
    p2.score += points2

    if points1 > points2:
        winner_name = p1.name
    elif points2 > points1:
        winner_name = p2.name
    else:
        winner_name = None

    if winner_name:
        print(f"{winner_name} remporte la manche. Chacun garde les points qu'il a faits.")
    else:
        print("Égalité sur cette manche. Chacun garde les points qu'il a faits.")

    return {
        "manche": manche_no,
        "trump": trump_suit,
        "points1": points1,
        "points2": points2,
        "winner_name": winner_name,
    }


def run():
    print("=== Belote à deux joueurs ===\n")
    name1 = input("Nom du joueur 1 : ").strip() or "Joueur 1"
    name2 = input("Nom du joueur 2 : ").strip() or "Joueur 2"
    target_raw = input(f"Score cible pour gagner la partie (défaut {DEFAULT_TARGET_SCORE}) : ").strip()
    target = int(target_raw) if target_raw.isdigit() else DEFAULT_TARGET_SCORE

    p1, p2 = Player(name1), Player(name2)
    leader = random.choice([p1, p2])
    manche_no = 1
    history = []

    while p1.score < target and p2.score < target:
        print_history(history, p1, p2)
        manche_result = play_manche(p1, p2, leader, manche_no)
        history.append(manche_result)
        print(f"\nScores cumulés : {p1.name} = {p1.score} | {p2.name} = {p2.score} (objectif : {target})")
        leader = p2 if leader is p1 else p1
        manche_no += 1

    print_history(history, p1, p2)
    winner = p1 if p1.score >= target else p2
    print(f"\n*** {winner.name} remporte la partie avec {winner.score} points ! ***")
