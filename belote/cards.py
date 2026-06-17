import random
from enum import Enum


class Suit(Enum):
    PIQUE = "Pique"
    COEUR = "Coeur"
    CARREAU = "Carreau"
    TREFLE = "Trefle"


SUIT_SYMBOLS = {
    Suit.PIQUE: "♠",
    Suit.COEUR: "♥",
    Suit.CARREAU: "♦",
    Suit.TREFLE: "♣",
}


class Rank(Enum):
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "10"
    JACK = "Valet"
    QUEEN = "Dame"
    KING = "Roi"
    ACE = "As"


# Ordre de force, du plus faible au plus fort.
NONTRUMP_ORDER = [
    Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.JACK,
    Rank.QUEEN, Rank.KING, Rank.TEN, Rank.ACE,
]
TRUMP_ORDER = [
    Rank.SEVEN, Rank.EIGHT, Rank.QUEEN, Rank.KING,
    Rank.TEN, Rank.ACE, Rank.NINE, Rank.JACK,
]

NONTRUMP_POINTS = {
    Rank.SEVEN: 0, Rank.EIGHT: 0, Rank.NINE: 0, Rank.JACK: 2,
    Rank.QUEEN: 3, Rank.KING: 4, Rank.TEN: 10, Rank.ACE: 11,
}
TRUMP_POINTS = {
    Rank.SEVEN: 0, Rank.EIGHT: 0, Rank.QUEEN: 3, Rank.KING: 4,
    Rank.TEN: 10, Rank.ACE: 11, Rank.NINE: 14, Rank.JACK: 20,
}


class Card:
    def __init__(self, suit: Suit, rank: Rank):
        self.suit = suit
        self.rank = rank

    def __repr__(self):
        return f"{self.rank.value}{SUIT_SYMBOLS[self.suit]}"

    def __eq__(self, other):
        return isinstance(other, Card) and self.suit == other.suit and self.rank == other.rank

    def __hash__(self):
        return hash((self.suit, self.rank))

    def points(self, trump_suit: Suit) -> int:
        table = TRUMP_POINTS if self.suit == trump_suit else NONTRUMP_POINTS
        return table[self.rank]

    def strength(self, trump_suit: Suit) -> int:
        order = TRUMP_ORDER if self.suit == trump_suit else NONTRUMP_ORDER
        return order.index(self.rank)


def sort_hand(hand, trump_suit):
    """Trie une main : atout d'abord, puis les autres couleurs, chacune
    classée du plus faible au plus fort selon l'ordre de force réel
    (différent à l'atout et hors atout)."""
    suit_order = [trump_suit] + [s for s in Suit if s != trump_suit]

    def key(card):
        return suit_order.index(card.suit), card.strength(trump_suit)

    return sorted(hand, key=key)


def build_deck():
    return [Card(suit, rank) for suit in Suit for rank in Rank]


def shuffled_deck():
    deck = build_deck()
    random.shuffle(deck)
    return deck
