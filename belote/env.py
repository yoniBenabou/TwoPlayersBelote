import random

import numpy as np
import gymnasium as gym
from gymnasium import spaces

from .cards import build_deck, shuffled_deck, Suit
from .engine import deal_round, random_trump, legal_moves, trick_winner, has_belote
from .player import Player

_CANONICAL_DECK = build_deck()
CARD_INDEX = {card: i for i, card in enumerate(_CANONICAL_DECK)}
INDEX_CARD = {i: card for card, i in CARD_INDEX.items()}
NUM_CARDS = len(_CANONICAL_DECK)  # 32

SUITS = list(Suit)
SUIT_INDEX = {suit: i for i, suit in enumerate(SUITS)}

MAX_SCORE = 182  # 152 points de cartes + 10 (dix de der) + 20 (belote-rebelote), pour normaliser
OBS_SIZE = NUM_CARDS * 2 + len(SUITS) + 2 + 8


class BeloteEnv(gym.Env):
    """Environnement 2 joueurs pour entraîner des agents RL en self-play.

    Un épisode = une manche de 8 plis (16 actions). L'observation est
    toujours du point de vue du joueur actif (information imparfaite :
    la main de l'adversaire n'est jamais exposée).

    reset(options={"starting_player": 0 ou 1}) -> (observation, {"legal_actions": mask})
        starting_player choisit qui mène le premier pli (0 par défaut) ;
        l'alternance d'une manche à l'autre est à la charge de l'appelant.
    step(action) -> (observation, {"0": r0, "1": r1}, done, info)
    """

    metadata = {"render_modes": []}

    def __init__(self):
        super().__init__()
        self.action_space = spaces.Discrete(NUM_CARDS)
        self.observation_space = spaces.Box(low=-1.0, high=1.0, shape=(OBS_SIZE,), dtype=np.float32)

        self.players = [Player("Joueur 0"), Player("Joueur 1")]
        self.trump_suit = None
        self.played_public = None
        self.led_card = None
        self.current_idx = None
        self.trick_no = None
        self.trick_winners = None
        self.done = False
        self._trick_cards = []

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        if seed is not None:
            random.seed(seed)

        deck = shuffled_deck()
        hand1, hand2 = deal_round(deck)
        self.players[0].reset_for_manche(hand1)
        self.players[1].reset_for_manche(hand2)

        self.trump_suit = random_trump()
        self.played_public = [False] * NUM_CARDS
        self.led_card = None
        self.current_idx = (options or {}).get("starting_player", 0)
        self.trick_no = 1
        self.trick_winners = [-1] * 8
        self.done = False
        self._trick_cards = []

        observation = self._observe(self.current_idx)
        info = {"legal_actions": self._legal_action_mask(), "current_player": self.current_idx, "led_card": None}
        return observation, info

    def _legal_action_mask(self):
        player = self.players[self.current_idx]
        mask = np.zeros(NUM_CARDS, dtype=bool)
        for card in legal_moves(player.hand, self.led_card, self.trump_suit):
            mask[CARD_INDEX[card]] = True
        return mask

    def _observe(self, player_idx):
        obs = np.zeros(OBS_SIZE, dtype=np.float32)
        offset = 0

        player = self.players[player_idx]
        opponent = self.players[1 - player_idx]

        for card in player.hand:
            obs[offset + CARD_INDEX[card]] = 1.0
        offset += NUM_CARDS

        for i, played in enumerate(self.played_public):
            obs[offset + i] = 1.0 if played else 0.0
        offset += NUM_CARDS

        obs[offset + SUIT_INDEX[self.trump_suit]] = 1.0
        offset += len(SUITS)

        obs[offset] = player.manche_points(self.trump_suit) / MAX_SCORE
        obs[offset + 1] = opponent.manche_points(self.trump_suit) / MAX_SCORE
        offset += 2

        for i, winner in enumerate(self.trick_winners):
            if winner == -1:
                obs[offset + i] = 0.0  # pli pas encore joué
            elif winner == player_idx:
                obs[offset + i] = 1.0  # moi
            else:
                obs[offset + i] = -1.0  # adversaire
        offset += 8

        return obs

    def step(self, action):
        if self.done:
            raise RuntimeError("Épisode terminé : appelez reset() avant de rejouer.")

        card = INDEX_CARD[int(action)]
        player_idx = self.current_idx
        player = self.players[player_idx]

        legal_cards = legal_moves(player.hand, self.led_card, self.trump_suit)
        if card not in legal_cards:
            raise ValueError(f"Action illégale pour le joueur {player_idx} : {card} n'est pas jouable.")

        player.hand.remove(card)
        self.played_public[CARD_INDEX[card]] = True
        self._trick_cards.append((player_idx, card))

        rewards = {0: 0.0, 1: 0.0}

        if self.led_card is None:
            self.led_card = card
            self.current_idx = 1 - player_idx
        else:
            leader_idx, leader_card = self._trick_cards[0]
            follower_idx, follower_card = self._trick_cards[1]
            result = trick_winner(leader_card, follower_card, self.trump_suit)
            winner_idx = leader_idx if result == "leader" else follower_idx

            trick_points = leader_card.points(self.trump_suit) + follower_card.points(self.trump_suit)
            if self.trick_no == 8:
                trick_points += 10  # dix de der

            self.players[winner_idx].pile.extend([leader_card, follower_card])
            rewards[winner_idx] = trick_points / MAX_SCORE
            self.trick_winners[self.trick_no - 1] = winner_idx

            if self.trick_no == 8:
                self.done = True

                final_points = {i: self.players[i].manche_points(self.trump_suit) for i in (0, 1)}
                final_points[winner_idx] += 10  # dix de der
                for i in (0, 1):
                    if has_belote(self.players[i].dealt_hand, self.trump_suit):
                        final_points[i] += 20
                        rewards[i] += 20 / MAX_SCORE

                if final_points[0] > final_points[1]:
                    rewards[0] += 1.0
                    rewards[1] -= 1.0
                elif final_points[1] > final_points[0]:
                    rewards[1] += 1.0
                    rewards[0] -= 1.0
            else:
                self.trick_no += 1
                self.led_card = None
                self._trick_cards = []
                self.current_idx = winner_idx

        if self.done:
            observation = self._observe(self.current_idx)
            info = {"legal_actions": None, "current_player": None, "led_card": None}
        else:
            observation = self._observe(self.current_idx)
            led_card_idx = CARD_INDEX[self.led_card] if self.led_card is not None else None
            info = {
                "legal_actions": self._legal_action_mask(),
                "current_player": self.current_idx,
                "led_card": led_card_idx,
            }

        return observation, {"0": rewards[0], "1": rewards[1]}, self.done, info
