from collections import Counter

import numpy as np

from .cards import Rank
from .env import CARD_INDEX, INDEX_CARD, NUM_CARDS, SUITS


def _beats(card, led_card, trump_suit):
    if card.suit == led_card.suit:
        return card.strength(trump_suit) > led_card.strength(trump_suit)
    return card.suit == trump_suit


def _decode_trump_suit(obs):
    trump_onehot = obs[NUM_CARDS * 2: NUM_CARDS * 2 + len(SUITS)]
    return SUITS[int(np.argmax(trump_onehot))]


def _decode_own_hand(obs):
    return [INDEX_CARD[i] for i in range(NUM_CARDS) if obs[i] > 0.5]


def _decode_led_card(info):
    led_card_idx = info.get("led_card") if info else None
    return INDEX_CARD[led_card_idx] if led_card_idx is not None else None


def _strongest_in_longest_suit(legal_cards, trump_suit):
    suit_counts = Counter(c.suit for c in legal_cards)
    longest_suit = max(suit_counts, key=lambda s: suit_counts[s])
    same_suit_cards = [c for c in legal_cards if c.suit == longest_suit]
    return max(same_suit_cards, key=lambda c: c.strength(trump_suit))


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
        trump_suit = _decode_trump_suit(obs)
        led_card = _decode_led_card(info)

        if led_card is None:
            best = self._choose_lead_card(legal_cards, trump_suit)
        else:
            best = self._choose_follow_card(legal_cards, led_card, trump_suit)
        return CARD_INDEX[best]

    def _choose_lead_card(self, legal_cards, trump_suit):
        trumps = [c for c in legal_cards if c.suit == trump_suit]
        if trumps:
            return max(trumps, key=lambda c: c.strength(trump_suit))
        return max(legal_cards, key=lambda c: c.strength(trump_suit))

    def _choose_follow_card(self, legal_cards, led_card, trump_suit):
        winning_cards = [c for c in legal_cards if _beats(c, led_card, trump_suit)]
        if winning_cards:
            return min(winning_cards, key=lambda c: c.strength(trump_suit))
        return min(legal_cards, key=lambda c: c.strength(trump_suit))


class VoidExploitAgent(HeuristicAgent):
    """Comme HeuristicAgent, mais en tant que meneur applique l'ordre de
    priorité suivant :
    1. Joue l'atout le plus fort s'il en a.
    2. Sinon, exploite une couleur dont il a déduit que l'adversaire est
       démuni (déduit en observant si l'adversaire a suivi ou non ses
       propres couleurs menées lors des plis précédents de la manche).
    3. Sinon, joue sa carte la plus forte dans la couleur où il a le plus
       de cartes.
    Garde la même stratégie que HeuristicAgent en tant que second."""

    def __init__(self):
        self._opponent_void_suits = set()
        self._pending_led_suit = None
        self._my_last_card_idx = None
        self._last_played = None

    def _update_void_knowledge(self, obs):
        current_played = {i for i in range(NUM_CARDS) if obs[NUM_CARDS + i] > 0.5}

        if self._last_played is None or len(current_played) < len(self._last_played):
            # Nouvelle manche (ou premier appel) : on oublie tout.
            self._opponent_void_suits = set()
            self._pending_led_suit = None
            self._my_last_card_idx = None
            self._last_played = current_played
            self._on_new_manche(obs)
            return

        new_cards = current_played - self._last_played
        opponent_card_idx = next((i for i in new_cards if i != self._my_last_card_idx), None)

        if opponent_card_idx is not None and self._pending_led_suit is not None:
            opponent_card = INDEX_CARD[opponent_card_idx]
            if opponent_card.suit != self._pending_led_suit:
                self._opponent_void_suits.add(self._pending_led_suit)

        self._last_played = current_played

    def _on_new_manche(self, obs):
        """Hook pour les sous-classes : appelé une fois au tout début de chaque manche
        (à ce moment, la main encore complète dans obs est la main de départ)."""

    def act(self, obs, legal_mask, info=None):
        self._update_void_knowledge(obs)

        legal_indices = np.where(legal_mask)[0]
        legal_cards = [INDEX_CARD[i] for i in legal_indices]
        trump_suit = _decode_trump_suit(obs)
        led_card = _decode_led_card(info)

        if led_card is None:
            best = self._choose_lead_card(legal_cards, trump_suit)
            self._pending_led_suit = best.suit
        else:
            best = self._choose_follow_card(legal_cards, led_card, trump_suit)
            self._pending_led_suit = None

        self._my_last_card_idx = CARD_INDEX[best]
        return CARD_INDEX[best]

    def _choose_lead_card(self, legal_cards, trump_suit):
        trumps = [c for c in legal_cards if c.suit == trump_suit]
        if trumps:
            return max(trumps, key=lambda c: c.strength(trump_suit))

        exploit_cards = [c for c in legal_cards if c.suit in self._opponent_void_suits]
        if exploit_cards:
            return min(exploit_cards, key=lambda c: c.strength(trump_suit))

        return _strongest_in_longest_suit(legal_cards, trump_suit)


class TrumpCountAgent(VoidExploitAgent):
    """Comme VoidExploitAgent, mais le style de jeu en tant que meneur dépend
    du nombre d'atouts dans la main de départ (compté une seule fois, au
    tout début de la manche) :

    - Plus de 3 atouts au départ (mode "attaque") : joue l'atout le plus
      fort, sinon une couleur connue démunie chez l'adversaire, sinon un
      As ou un 10, sinon sa carte la plus forte dans sa couleur la plus
      longue.
    - 3 atouts ou moins au départ (mode "as puis longue") : garde ses
      atouts pour la défense. Joue un As s'il en a, sinon sa carte la plus
      forte dans sa couleur la plus longue. Pas d'exploitation de vide
      dans ce mode.

    Garde la même stratégie que HeuristicAgent en tant que second.
    """

    TRUMP_THRESHOLD = 3  # strictement plus de 3 atouts => mode attaque

    def __init__(self):
        super().__init__()
        self._mode = None

    def _on_new_manche(self, obs):
        own_hand = _decode_own_hand(obs)
        trump_suit = _decode_trump_suit(obs)
        trump_count = sum(1 for c in own_hand if c.suit == trump_suit)
        self._mode = "attack" if trump_count > self.TRUMP_THRESHOLD else "ace_longest"

    def _choose_lead_card(self, legal_cards, trump_suit):
        if self._mode == "attack":
            trumps = [c for c in legal_cards if c.suit == trump_suit]
            if trumps:
                return max(trumps, key=lambda c: c.strength(trump_suit))

            exploit_cards = [c for c in legal_cards if c.suit in self._opponent_void_suits]
            if exploit_cards:
                return min(exploit_cards, key=lambda c: c.strength(trump_suit))

            ace_or_ten = [c for c in legal_cards if c.rank in (Rank.ACE, Rank.TEN)]
            if ace_or_ten:
                return max(ace_or_ten, key=lambda c: c.strength(trump_suit))

            return _strongest_in_longest_suit(legal_cards, trump_suit)

        # Mode "as puis longue" : moins de 4 atouts au départ, on les garde pour la défense.
        aces = [c for c in legal_cards if c.rank == Rank.ACE]
        if aces:
            return max(aces, key=lambda c: c.strength(trump_suit))

        return _strongest_in_longest_suit(legal_cards, trump_suit)
