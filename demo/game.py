"""Partie humain contre agent PPO pour la démo web (textes en anglais pour le jury).

GameSession enveloppe BeloteEnv (mêmes règles et même observation qu'à
l'entraînement) et produit, à chaque action, la liste des événements à
animer côté navigateur et l'état complet de la table.

Avec un modèle entraîné avec les annonces (models/ppo_bidding_2M.pt, par
défaut), chaque manche commence par les annonces : carte retournée, tour 1
(prendre ou passer), tour 2 (nommer une autre couleur ou passer), et le
preneur "dedans" s'il marque moins que l'adversaire. Un modèle sans annonces
joue avec un atout tiré au hasard, comme avant.
"""
import random

import torch

from belote.core.cards import Rank, Suit, sort_hand
from belote.core.engine import has_belote, legal_moves
from belote.rl.env import CARD_INDEX, INDEX_CARD, NAME_SUIT, PASS, SUIT_OF_ACTION, TAKE, BeloteEnv
from scripts.compare_checkpoints import load_agent

HUMAN, AGENT = 0, 1  # sièges dans BeloteEnv
DEFAULT_TARGET_SCORE = 501
DEFAULT_CHECKPOINT = "models/ppo_bidding_2M.pt"

RANK_LABEL = {
    Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9", Rank.TEN: "10",
    Rank.JACK: "J", Rank.QUEEN: "Q", Rank.KING: "K", Rank.ACE: "A",
}
SUIT_INFO = {
    Suit.PIQUE: ("♠", "spades", "black"),
    Suit.COEUR: ("♥", "hearts", "red"),
    Suit.CARREAU: ("♦", "diamonds", "red"),
    Suit.TREFLE: ("♣", "clubs", "black"),
}
SUIT_BY_NAME = {name: suit for suit, (_, name, _) in SUIT_INFO.items()}
BID_PHASES = ("bid1", "bid2")


class IllegalMove(Exception):
    pass


def seat_name(seat):
    return "you" if seat == HUMAN else "agent"


def suit_json(suit):
    symbol, name, color = SUIT_INFO[suit]
    return {"symbol": symbol, "name": name, "color": color}


def card_json(card, trump=None):
    symbol, name, color = SUIT_INFO[card.suit]
    data = {"id": CARD_INDEX[card], "rank": RANK_LABEL[card.rank], "suit": symbol, "suitName": name, "color": color,
            "label": f"{RANK_LABEL[card.rank]}{symbol}"}
    if trump is not None:
        data["points"] = card.points(trump)
        data["isTrump"] = card.suit == trump
    return data


def bid_label(action, turned_suit):
    if action == PASS:
        return "pass"
    suit = turned_suit if action == TAKE else SUIT_OF_ACTION[action]
    return f"{'take' if action == TAKE else 'name'} {SUIT_INFO[suit][0]}"


class GameSession:
    def __init__(self, checkpoint=DEFAULT_CHECKPOINT, target=DEFAULT_TARGET_SCORE, seed=None):
        self.agent = load_agent(checkpoint)
        self.env = BeloteEnv(**self.agent.env_kwargs())
        self.bidding = self.env.bidding
        self.rng = random.Random(seed)
        self.target = target
        self.new_game()

    # ---------- déroulement ----------
    def new_game(self):
        self.totals = {HUMAN: 0, AGENT: 0}
        self.round_no = 0
        self.history = []
        self.game_over = False
        self.leader = self.rng.choice([HUMAN, AGENT])
        return self.start_round()

    def start_round(self):
        if self.game_over:
            return self.state([])
        self.round_no += 1
        return self._deal([])

    def _deal(self, events):
        """Nouvelle donne pour la manche en cours (aussi après une redistribution)."""
        self.obs, self.info = self.env.reset(options={"starting_player": self.leader})
        self.trick, self.last_trick, self.round_result = [], None, None
        self.trick_no = 1
        self.bids = []
        if self.bidding:
            turned = self.env.turned_card
            who = "You speak first" if self.leader == HUMAN else "The agent speaks first"
            # "deal" : le navigateur repart de cette donne (nouvelle main, carte retournée)
            events.append({"type": "message", "deal": True,
                           "text": f"Round {self.round_no} — turned card: {card_json(turned)['label']}. {who}.",
                           "turnedCard": card_json(turned), "firstSpeaker": seat_name(self.leader),
                           "hand": [card_json(c) for c in sort_hand(self.env.players[HUMAN].hand, turned.suit)],
                           "agentHand": [card_json(c) for c in sort_hand(self.env.players[AGENT].hand, turned.suit)]})
        else:
            trump_symbol, trump_name, _ = SUIT_INFO[self.env.trump_suit]
            who = "You lead" if self.leader == HUMAN else "The agent leads"
            events.append({"type": "message", "text": f"Round {self.round_no} — trump is {trump_name} {trump_symbol}. {who}."})
        return self._continue(events)

    def _continue(self, events):
        """Fait jouer l'agent jusqu'au tour de l'humain ou la fin de la manche."""
        events += self._agent_turns()
        if self.info.get("redeal"):
            events.append({"type": "message", "text": "Both players passed twice: the cards are redealt."})
            return self._deal(events)
        return self.state(events)

    def play_human(self, card_id):
        if self.round_result is not None or self.env.current_idx != HUMAN or self.env.phase != "play":
            raise IllegalMove("It is not your turn to play a card.")
        card = INDEX_CARD.get(int(card_id))
        if card is None or card not in self._legal_cards():
            raise IllegalMove("This card is not allowed: follow suit, trump if you can't, over-trump when trump is led.")
        return self._continue(self._apply(CARD_INDEX[card], HUMAN))

    def bid_human(self, bid):
        """bid : "take", "pass" ou le nom anglais d'une couleur (tour 2)."""
        if self.round_result is not None or self.env.current_idx != HUMAN or self.env.phase not in BID_PHASES:
            raise IllegalMove("It is not your turn to bid.")
        if bid == "take":
            action = TAKE
        elif bid == "pass":
            action = PASS
        elif bid in SUIT_BY_NAME:
            action = NAME_SUIT[SUIT_BY_NAME[bid]]
        else:
            raise IllegalMove(f"Unknown bid: {bid!r}.")
        if not self.info["legal_actions"][action]:
            raise IllegalMove("This bid is not allowed now (round 2: name one of the 3 other suits, or pass).")
        return self._continue(self._apply(action, HUMAN))

    def next_round(self):
        if self.round_result is None:
            raise IllegalMove("The current round is not finished.")
        return self.start_round()

    # ---------- interne ----------
    def _legal_cards(self):
        if self.env.phase != "play":
            return []
        return legal_moves(self.env.players[self.env.current_idx].hand, self.env.led_card, self.env.trump_suit)

    def _agent_turns(self):
        events = []
        while self.round_result is None and not self.env.done and self.env.current_idx == AGENT:
            legal_mask = self.info["legal_actions"]
            action = self.agent.act(self.obs, legal_mask, self.info)
            with torch.no_grad():
                logits, _value = self.agent._masked_logits_and_value(self.obs, legal_mask)
                probs = torch.softmax(logits, dim=-1)
            events += self._apply(action, AGENT, probs[action].item())
        return events

    def _apply(self, action, seat, confidence=None):
        if self.env.phase in BID_PHASES:
            return self._apply_bid(action, seat, confidence)
        trump = self.env.trump_suit
        card = INDEX_CARD[action]
        play = {"type": "play", "seat": seat_name(seat), "card": card_json(card, trump)}
        if confidence is not None:
            play["confidence"] = round(confidence * 100)
        events = [play]
        self.trick.append((seat, card))
        self.obs, _rewards, done, self.info = self.env.step(action)

        if len(self.trick) == 2:
            winner = self.env.trick_winners[self.trick_no - 1]
            points = sum(c.points(trump) for _, c in self.trick) + (10 if self.trick_no == 8 else 0)
            self.last_trick = {
                "cards": [{"seat": seat_name(s), "card": card_json(c, trump)} for s, c in self.trick],
                "winner": seat_name(winner), "points": points, "trickNo": self.trick_no,
            }
            text = f"{'You win' if winner == HUMAN else 'The agent wins'} trick {self.trick_no} (+{points} pts)"
            if self.trick_no == 8:
                text += " — includes +10 for the last trick"
            events.append({"type": "trick", "winner": self.last_trick["winner"], "points": points, "text": text})
            self.trick, self.trick_no = [], self.trick_no + 1

        if done:
            events += self._finish_round()
        return events

    def _apply_bid(self, action, seat, confidence=None):
        turned_suit = self.env.turned_card.suit
        label = bid_label(action, turned_suit)
        self.bids.append({"seat": seat_name(seat), "round": 1 if self.env.phase == "bid1" else 2, "label": label})
        who = "You" if seat == HUMAN else "The agent"
        if action == PASS:
            text = f"{who} {'pass' if seat == HUMAN else 'passes'}"
        else:
            suit = turned_suit if action == TAKE else SUIT_OF_ACTION[action]
            verb = ("take" if seat == HUMAN else "takes") if action == TAKE else ("choose" if seat == HUMAN else "chooses")
            text = f"{who} {verb} {SUIT_INFO[suit][1]} {SUIT_INFO[suit][0]} as trump"
        event = {"type": "bid", "seat": seat_name(seat), "round": self.bids[-1]["round"], "label": label, "text": text}
        if action != PASS:
            event["trump"] = suit_json(turned_suit if action == TAKE else SUIT_OF_ACTION[action])
        if confidence is not None:
            event["confidence"] = round(confidence * 100)
            event["text"] += f" (confidence {event['confidence']}%)"
        events = [event]
        self.obs, _rewards, _done, self.info = self.env.step(action)
        event["nextPhase"] = self.env.phase
        if self.env.phase == "play":
            lead = "You lead" if self.leader == HUMAN else "The agent leads"
            events.append({"type": "message",
                           "text": f"{'You are' if self.env.taker == HUMAN else 'The agent is'} the taker. {lead}."})
        return events

    def _finish_round(self):
        trump = self.env.trump_suit
        human_points, agent_points = self.env.final_points
        self.totals[HUMAN] += human_points
        self.totals[AGENT] += agent_points
        belote = [seat_name(seat) for seat in (HUMAN, AGENT) if has_belote(self.env.players[seat].dealt_hand, trump)]
        taker = seat_name(self.env.taker) if self.env.taker is not None else None
        self.round_result = {"you": human_points, "agent": agent_points, "belote": belote,
                             "taker": taker, "dedans": self.env.dedans}
        self.history.append({"round": self.round_no, "trump": SUIT_INFO[trump][0], "you": human_points,
                             "agent": agent_points, "taker": taker, "dedans": self.env.dedans})
        self.leader = AGENT if self.leader == HUMAN else HUMAN

        text = f"Round {self.round_no} over: you {human_points} — agent {agent_points}."
        if self.env.dedans:
            text += (" You took and are set (\"dedans\"): the agent scores all the trick points." if taker == "you"
                     else " The agent took and is set (\"dedans\"): you score all the trick points.")
        if belote:
            text += " " + " and ".join("You" if w == "you" else "The agent" for w in belote) + " scored belote-rebelote (+20)."
        events = [{"type": "round", "text": text}]
        if max(self.totals.values()) >= self.target:
            self.game_over = True
            if self.totals[HUMAN] == self.totals[AGENT]:
                final = "It's a draw!"
            else:
                final = "You win the game!" if self.totals[HUMAN] > self.totals[AGENT] else "The agent wins the game."
            events.append({"type": "game", "text": f"{final} Final score: you {self.totals[HUMAN]} — agent {self.totals[AGENT]}."})
        return events

    def _bid_options(self):
        """Annonces possibles pour l'humain, ou None si ce n'est pas à lui d'annoncer."""
        env = self.env
        if self.round_result is not None or env.phase not in BID_PHASES or env.current_idx != HUMAN:
            return None
        mask = self.info["legal_actions"]
        options = []
        if mask[TAKE]:
            options.append(dict(suit_json(env.turned_card.suit), bid="take", label=f"Take {SUIT_INFO[env.turned_card.suit][0]}"))
        for suit, action in NAME_SUIT.items():
            if mask[action]:
                options.append(dict(suit_json(suit), bid=SUIT_INFO[suit][1], label=SUIT_INFO[suit][0]))
        options.append({"bid": "pass", "label": "Pass"})
        return options

    def state(self, events):
        env, trump = self.env, self.env.trump_suit
        bidding_now = env.phase in BID_PHASES and self.round_result is None
        my_turn = self.round_result is None and not env.done and env.current_idx == HUMAN
        legal = set(CARD_INDEX[c] for c in self._legal_cards()) if my_turn else set()
        sort_suit = trump if trump is not None else (env.turned_card.suit if env.turned_card else None)
        hand = [dict(card_json(c, trump), legal=CARD_INDEX[c] in legal) for c in sort_hand(env.players[HUMAN].hand, sort_suit)]
        return {
            "events": events,
            "round": self.round_no,
            "bidding": self.bidding,
            "phase": "done" if self.round_result is not None else env.phase,
            "turnedCard": card_json(env.turned_card) if env.turned_card is not None else None,
            "bidOptions": self._bid_options(),
            "bids": self.bids,
            "taker": seat_name(env.taker) if env.taker is not None else None,
            "firstSpeaker": seat_name(self.leader) if self.round_result is None else None,
            "trump": suit_json(trump) if trump is not None else None,
            "hand": hand,
            "agentHand": [card_json(c, trump) for c in sort_hand(env.players[AGENT].hand, sort_suit)],
            "table": [{"seat": seat_name(s), "card": card_json(c, trump)} for s, c in self.trick],
            "lastTrick": self.last_trick,
            "yourTurn": my_turn and not bidding_now,
            "yourBid": my_turn and bidding_now,
            # en cours de manche : points des plis ; une fois finie : total avec dix de der et belote
            "roundPoints": ({"you": self.round_result["you"], "agent": self.round_result["agent"]} if self.round_result
                            else {"you": env.players[HUMAN].manche_points(trump) if trump is not None else 0,
                                  "agent": env.players[AGENT].manche_points(trump) if trump is not None else 0}),
            "totals": {"you": self.totals[HUMAN], "agent": self.totals[AGENT]},
            "target": self.target,
            "roundResult": self.round_result,
            "gameOver": self.game_over,
            "history": self.history,
        }
