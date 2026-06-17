import numpy as np

from .env import CARD_INDEX, INDEX_CARD, NUM_CARDS, SUITS


def _beats(card, led_card, trump_suit):
    if card.suit == led_card.suit:
        return card.strength(trump_suit) > led_card.strength(trump_suit)
    return card.suit == trump_suit


class RandomAgent:
    """Choisit une carte légale au hasard."""

    def act(self, obs, legal_mask, info=None):
        legal_indices = np.where(legal_mask)[0]
        return int(np.random.choice(legal_indices))


class HeuristicAgent:
    """Stratégie simple, sans apprentissage :

    - En tant que meneur : joue le plus fort atout en main, ou à défaut
      sa carte la plus forte.
    - En tant que second : s'il peut gagner le pli, joue la plus petite
      carte qui le lui permet (économise ses grosses cartes) ; sinon
      se défausse de sa plus petite carte.
    """

    def act(self, obs, legal_mask, info=None):
        legal_indices = np.where(legal_mask)[0]
        legal_cards = [INDEX_CARD[i] for i in legal_indices]

        trump_onehot = obs[NUM_CARDS * 2: NUM_CARDS * 2 + len(SUITS)]
        trump_suit = SUITS[int(np.argmax(trump_onehot))]

        led_card_idx = info.get("led_card") if info else None
        led_card = INDEX_CARD[led_card_idx] if led_card_idx is not None else None

        if led_card is None:
            trumps = [c for c in legal_cards if c.suit == trump_suit]
            if trumps:
                best = max(trumps, key=lambda c: c.strength(trump_suit))
            else:
                best = max(legal_cards, key=lambda c: c.strength(trump_suit))
            return CARD_INDEX[best]

        winning_cards = [c for c in legal_cards if _beats(c, led_card, trump_suit)]
        if winning_cards:
            best = min(winning_cards, key=lambda c: c.strength(trump_suit))
        else:
            best = min(legal_cards, key=lambda c: c.strength(trump_suit))
        return CARD_INDEX[best]
