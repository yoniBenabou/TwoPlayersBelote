"""Environnement d'apprentissage pour la Coinche à 4 (au-dessus de CoincheGame).

Une épisode = une donne. Les 4 places sont jouées à tour de rôle ; l'appelant
décide qui joue chaque place (le même réseau pour les 4 en self-play, ou des
robots CoincheBot pour certaines places). L'observation est toujours vue de
la place qui doit jouer, avec les autres places en position relative :
0 = moi, 1 = mon adversaire de gauche (joue après moi), 2 = mon partenaire,
3 = mon adversaire de droite.

Deux modes :
- bidding=False (étape 1) : les annonces sont faites par des robots
  CoincheBot, l'agent ne joue que les cartes (32 actions) ;
- bidding=True : l'agent fait aussi les annonces (75 actions : 32 cartes,
  passer, 40 contrats valeur x couleur, coinche, surcoinche).

Reward : uniquement en fin de donne, (score de mon équipe - score de l'autre
équipe) / REWARD_SCALE, avec le vrai barème (contrat, coinche, belote,
capot). 4 passes sans annonce (mode bidding) : la donne s'arrête à 0.
"""
import random

import numpy as np

from ..core.cards import build_deck
from ..rl.env import CARD_INDEX, INDEX_CARD, NUM_CARDS
from .bots import CoincheBot
from .engine import CONTRACTS, SUITS, CoincheGame, partner_of, team_of, trick_winner

SUIT_INDEX = {s: i for i, s in enumerate(SUITS)}
REWARD_SCALE = 500.0

# Actions
PASS = NUM_CARDS
BID0 = PASS + 1
COINCHE = BID0 + len(CONTRACTS) * len(SUITS)
SURCOINCHE = COINCHE + 1
NUM_ACTIONS_PLAY = NUM_CARDS
NUM_ACTIONS_BIDDING = SURCOINCHE + 1  # 75


def bid_to_action(bid):
    kind = bid[0]
    if kind == "pass":
        return PASS
    if kind == "coinche":
        return COINCHE
    if kind == "surcoinche":
        return SURCOINCHE
    return BID0 + CONTRACTS.index(bid[1]) * len(SUITS) + SUIT_INDEX[bid[2]]


def action_to_bid(action):
    if action == PASS:
        return ("pass",)
    if action == COINCHE:
        return ("coinche",)
    if action == SURCOINCHE:
        return ("surcoinche",)
    k = action - BID0
    return ("bid", CONTRACTS[k // len(SUITS)], SUITS[k % len(SUITS)])


SUIT_MASK = np.array([[INDEX_CARD[i].suit == s for i in range(NUM_CARDS)] for s in SUITS])
# force d'une carte quand sa couleur est l'atout (même ordre que Card.strength)
TRUMP_STRENGTH = np.array([INDEX_CARD[i].strength(INDEX_CARD[i].suit) for i in range(NUM_CARDS)])

# Observation : (taille de chaque bloc)
OBS_BLOCKS = [
    ("hand", NUM_CARDS),
    ("trick", 3 * NUM_CARDS),          # carte posée dans le pli en cours par les places relatives 1, 2, 3
    ("played", 4 * NUM_CARDS),         # cartes jouées dans les plis finis, par place relative 0..3
    ("possible", 3 * NUM_CARDS),       # cartes que les places relatives 1, 2, 3 peuvent encore avoir
    ("trump", 4),
    ("taker", 4),                      # place relative du preneur
    ("value", len(CONTRACTS)),
    ("mult", 3),
    ("bids", 4 * 6),                   # par place relative : dernière couleur annoncée (4), valeur, a coinché
    ("trick_no", 8),
    ("points", 2),                     # points de plis de mon équipe / de l'autre (sur 162)
    ("leader", 4),                     # place relative qui a entamé le pli en cours
    ("winning", 4),                    # place relative maîtresse du pli en cours
    ("belote", 4),                     # place relative qui a annoncé belote
    ("phase", 1),                      # 1 pendant les annonces
]
OBS_SIZE = sum(size for _, size in OBS_BLOCKS)
OFFSET = {}
_o = 0
for _name, _size in OBS_BLOCKS:
    OFFSET[_name] = _o
    _o += _size


class CoincheEnv:
    def __init__(self, bidding=False, seed=None):
        self.bidding = bidding
        self.num_actions = NUM_ACTIONS_BIDDING if bidding else NUM_ACTIONS_PLAY
        self.obs_size = OBS_SIZE
        self.rng = random.Random(seed)
        self.bot = CoincheBot()
        self.game = CoincheGame(rng=random.Random(self.rng.random()))

    # ---------- donne ----------
    def reset(self, deal=None, bid_seats=None):
        """deal = (mains, donneur) impose la donne (évaluation en donnes dupliquées).
        bid_seats : places dont les annonces sont faites par l'appelant (mode
        bidding) ; les autres sont annoncées par CoincheBot. Par défaut : toutes
        en mode bidding, aucune sinon. Sans annonce (mode bidding=False) : on
        redonne tant que les robots passent tous."""
        self.bid_seats = set(range(4) if bid_seats is None else bid_seats) if self.bidding else set()
        while True:
            self._new_deal(deal)
            self._run_bot_bids()
            if self.game.phase != "redeal" or self.bidding:
                break
            if deal is not None:
                raise ValueError("Donne imposée sans contrat (tous les robots passent)")
        self.done = self.game.phase == "redeal"
        return self._observe() if not self.done else None

    def _new_deal(self, deal):
        game = self.game
        game.totals = [0, 0]
        game.history = []
        game.game_over = False
        game.new_deal()
        if deal is not None:
            hands, dealer = deal
            game.hands = [list(h) for h in hands]
            game.dealt = [list(h) for h in hands]
            game.dealer = dealer
            game.current = (dealer + 1) % 4
        self.voids = [set() for _ in range(4)]
        self.trump_cap = [None] * 4  # force maximale possible de leur atout (n'a pas pu monter)
        self.belote_seen = None

    def random_deal(self):
        deck = build_deck()
        self.rng.shuffle(deck)
        return [deck[8 * i: 8 * i + 8] for i in range(4)], self.rng.randrange(4)

    def _run_bot_bids(self):
        game = self.game
        while game.phase == "bidding" and game.current not in self.bid_seats:
            game.bid(game.current, self.bot.bid(game, game.current))

    @property
    def current(self):
        return self.game.current

    @property
    def phase(self):
        return self.game.phase

    # ---------- pas ----------
    def legal_mask(self):
        mask = np.zeros(self.num_actions, dtype=bool)
        game = self.game
        if game.phase == "bidding":
            for b in game.legal_bids(game.current):
                mask[bid_to_action(b)] = True
        else:
            for c in game.legal_cards(game.current):
                mask[CARD_INDEX[c]] = True
        return mask

    def step(self, action):
        """Joue l'action de la place courante. Retourne (obs, rewards[4], done)."""
        game = self.game
        seat = game.current
        if game.phase == "bidding":
            game.bid(seat, action_to_bid(action))
            self._run_bot_bids()
        else:
            card = INDEX_CARD[action]
            self._update_belief(seat, card)
            if game.belote_call(seat, card):
                self.belote_seen = seat
            game.play(seat, card)
        rewards = [0.0] * 4
        if game.phase in ("done", "redeal"):
            self.done = True
            if game.phase == "done":
                scores = game.result["scores"]
                for s in range(4):
                    t = team_of(s)
                    rewards[s] = (scores[t] - scores[1 - t]) / REWARD_SCALE
            return None, rewards, True
        return self._observe(), rewards, False

    def play_bot(self):
        """Coup (annonce ou carte) de CoincheBot pour la place courante, en action."""
        game = self.game
        if game.phase == "bidding":
            return bid_to_action(self.bot.bid(game, game.current))
        return CARD_INDEX[self.bot.play(game, game.current)]

    # ---------- déductions sur les mains cachées ----------
    def _update_belief(self, seat, card):
        game = self.game
        trick, trump = game.trick, game.trump
        if not trick:
            return
        led = trick[0][1].suit
        trumps = [c for _, c in trick if c.suit == trump]
        best = max(trumps, key=lambda c: c.strength(trump)) if trumps else None
        if card.suit == led:
            if led == trump and card.strength(trump) < best.strength(trump):
                self._cap(seat, best.strength(trump))
            return
        self.voids[seat].add(led)
        if led == trump:
            self.voids[seat].add(trump)
            return
        partner_winning = trick[trick_winner(trick, trump)][0] == partner_of(seat)
        if partner_winning:
            return
        if best is None:
            if card.suit != trump:
                self.voids[seat].add(trump)  # adversaire maître sans atout dans le pli : couper obligatoire
        elif card.suit != trump or card.strength(trump) < best.strength(trump):
            self._cap(seat, best.strength(trump))  # pas pu monter (pas d'obligation de sous-couper)

    def _cap(self, seat, strength):
        cap = self.trump_cap[seat]
        self.trump_cap[seat] = strength if cap is None else min(cap, strength)

    def possible_cards(self, me, other):
        """Cartes que other peut encore avoir, vu de me (liste de cartes)."""
        return [INDEX_CARD[i] for i in np.flatnonzero(self._possible_mask(self._unseen(me), other))]

    def _unseen(self, me):
        game = self.game
        unseen = np.ones(NUM_CARDS, dtype=bool)
        unseen[[CARD_INDEX[c] for c in game.hands[me]]] = False
        for cards in game.played:
            if cards:
                unseen[[CARD_INDEX[c] for c in cards]] = False
        return unseen

    def _possible_mask(self, unseen, other):
        mask = unseen.copy()
        for suit in self.voids[other]:
            mask &= ~SUIT_MASK[SUIT_INDEX[suit]]
        cap = self.trump_cap[other]
        if cap is not None:
            t = SUIT_INDEX[self.game.trump]
            mask &= ~(SUIT_MASK[t] & (TRUMP_STRENGTH > cap))
        return mask

    # ---------- observation ----------
    def _observe(self):
        game = self.game
        me = game.current
        rel = lambda s: (s - me) % 4
        obs = np.zeros(OBS_SIZE, dtype=np.float32)
        for c in game.hands[me]:
            obs[OFFSET["hand"] + CARD_INDEX[c]] = 1
        # plis finis
        for trick, _winner in game.tricks:
            for s, c in trick:
                obs[OFFSET["played"] + rel(s) * NUM_CARDS + CARD_INDEX[c]] = 1
        if game.phase == "play":
            for s, c in game.trick:
                obs[OFFSET["trick"] + (rel(s) - 1) * NUM_CARDS + CARD_INDEX[c]] = 1
            unseen = self._unseen(me)
            for r in (1, 2, 3):
                start = OFFSET["possible"] + (r - 1) * NUM_CARDS
                obs[start: start + NUM_CARDS] = self._possible_mask(unseen, (me + r) % 4)
            obs[OFFSET["trump"] + SUIT_INDEX[game.trump]] = 1
            obs[OFFSET["trick_no"] + len(game.tricks)] = 1
            obs[OFFSET["points"]] = game.trick_points[team_of(me)] / 162
            obs[OFFSET["points"] + 1] = game.trick_points[1 - team_of(me)] / 162
            if game.trick:
                obs[OFFSET["leader"] + rel(game.trick[0][0])] = 1
                obs[OFFSET["winning"] + rel(game.trick[trick_winner(game.trick, game.trump)][0])] = 1
            if self.belote_seen is not None:
                obs[OFFSET["belote"] + rel(self.belote_seen)] = 1
        else:
            obs[OFFSET["phase"]] = 1
        c = game.contract
        if c is not None:
            obs[OFFSET["taker"] + rel(c["seat"])] = 1
            obs[OFFSET["value"] + CONTRACTS.index(c["value"])] = 1
            obs[OFFSET["mult"] + c["mult"] - 1] = 1
            if game.phase == "bidding":
                obs[OFFSET["trump"] + SUIT_INDEX[c["suit"]]] = 1  # couleur du contrat en cours
        for s, b in game.bids:
            base = OFFSET["bids"] + rel(s) * 6
            if b[0] == "bid":
                obs[base: base + 4] = 0
                obs[base + SUIT_INDEX[b[2]]] = 1
                obs[base + 4] = b[1] / 250
            elif b[0] in ("coinche", "surcoinche"):
                obs[base + 5] = 1
        return obs
