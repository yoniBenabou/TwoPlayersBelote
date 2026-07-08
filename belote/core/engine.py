import random

from .cards import Suit, Rank


def deal_round(deck):
    """8 cartes chacun, les 16 restantes ne sont pas utilisées cette manche."""
    return deck[0:8], deck[8:16]


def random_trump():
    return random.choice(list(Suit))


def legal_moves(hand, led_card, trump_suit):
    """Carte(s) que le joueur a le droit de jouer."""
    if led_card is None:
        return list(hand)

    led_suit = led_card.suit
    same_suit = [c for c in hand if c.suit == led_suit]

    if same_suit:
        if led_suit == trump_suit:
            # L'atout a été demandé : il faut monter dessus si possible.
            stronger = [c for c in same_suit if c.strength(trump_suit) > led_card.strength(trump_suit)]
            return stronger if stronger else same_suit
        return same_suit

    trump_cards = [c for c in hand if c.suit == trump_suit]
    if trump_cards:
        return trump_cards

    return list(hand)


def trick_winner(leader_card, follower_card, trump_suit):
    """Retourne 'leader' ou 'follower'."""
    if leader_card.suit == follower_card.suit:
        if follower_card.strength(trump_suit) > leader_card.strength(trump_suit):
            return "follower"
        return "leader"

    if follower_card.suit == trump_suit:
        return "follower"
    return "leader"


def has_belote(hand, trump_suit):
    """Roi + Dame d'atout dans la main distribuée."""
    trump_ranks = {c.rank for c in hand if c.suit == trump_suit}
    return Rank.KING in trump_ranks and Rank.QUEEN in trump_ranks
