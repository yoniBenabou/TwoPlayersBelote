"""Partie humain contre agent PPO pour la démo web (textes en anglais pour le jury).

GameSession enveloppe BeloteEnv (mêmes règles et même observation qu'à
l'entraînement) et produit, à chaque action, la liste des événements à
animer côté navigateur et l'état complet de la table.
"""
import random

import torch

from belote.core.cards import Rank, Suit, sort_hand
from belote.core.engine import has_belote, legal_moves
from belote.rl.env import CARD_INDEX, INDEX_CARD, BeloteEnv
from scripts.compare_checkpoints import load_agent

HUMAN, AGENT = 0, 1  # sièges dans BeloteEnv
DEFAULT_TARGET_SCORE = 501

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


class IllegalMove(Exception):
    pass


def card_json(card, trump=None):
    symbol, name, color = SUIT_INFO[card.suit]
    data = {"id": CARD_INDEX[card], "rank": RANK_LABEL[card.rank], "suit": symbol, "suitName": name, "color": color,
            "label": f"{RANK_LABEL[card.rank]}{symbol}"}
    if trump is not None:
        data["points"] = card.points(trump)
        data["isTrump"] = card.suit == trump
    return data


class GameSession:
    def __init__(self, checkpoint, target=DEFAULT_TARGET_SCORE, seed=None):
        self.agent = load_agent(checkpoint)
        if self.agent.uses_bidding:
            raise SystemExit("Ce modèle utilise les annonces, pas encore gérées par cette interface.")
        self.env = BeloteEnv(**self.agent.env_kwargs())
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
        self.obs, self.info = self.env.reset(options={"starting_player": self.leader})
        self.round_no += 1
        self.trick, self.last_trick, self.round_result = [], None, None
        self.trick_no = 1
        trump_symbol, trump_name, _ = SUIT_INFO[self.env.trump_suit]
        who = "You lead" if self.leader == HUMAN else "The agent leads"
        events = [{"type": "message", "text": f"Round {self.round_no} — trump is {trump_name} {trump_symbol}. {who}."}]
        events += self._agent_turns()
        return self.state(events)

    def play_human(self, card_id):
        if self.round_result is not None or self.env.current_idx != HUMAN:
            raise IllegalMove("It is not your turn.")
        card = INDEX_CARD.get(int(card_id))
        if card is None or card not in self._legal_cards():
            raise IllegalMove("This card is not allowed: follow suit, trump if you can't, over-trump when trump is led.")
        events = self._apply(CARD_INDEX[card], HUMAN)
        events += self._agent_turns()
        return self.state(events)

    def next_round(self):
        if self.round_result is None:
            raise IllegalMove("The current round is not finished.")
        return self.start_round()

    # ---------- interne ----------
    def _legal_cards(self):
        return legal_moves(self.env.players[self.env.current_idx].hand, self.env.led_card, self.env.trump_suit)

    def _agent_turns(self):
        events = []
        while self.round_result is None and self.env.current_idx == AGENT:
            legal_mask = self.info["legal_actions"]
            action = self.agent.act(self.obs, legal_mask, self.info)
            with torch.no_grad():
                logits, _value = self.agent._masked_logits_and_value(self.obs, legal_mask)
                probs = torch.softmax(logits, dim=-1)
            confidence = probs[action].item()
            events += self._apply(action, AGENT, confidence)
        return events

    def _apply(self, action, seat, confidence=None):
        trump = self.env.trump_suit
        card = INDEX_CARD[action]
        play = {"type": "play", "seat": "you" if seat == HUMAN else "agent", "card": card_json(card, trump)}
        if confidence is not None:
            play["confidence"] = round(confidence * 100)
        events = [play]
        self.trick.append((seat, card))
        self.obs, _rewards, done, self.info = self.env.step(action)

        if len(self.trick) == 2:
            winner = self.env.trick_winners[self.trick_no - 1]
            points = sum(c.points(trump) for _, c in self.trick) + (10 if self.trick_no == 8 else 0)
            self.last_trick = {
                "cards": [{"seat": "you" if s == HUMAN else "agent", "card": card_json(c, trump)} for s, c in self.trick],
                "winner": "you" if winner == HUMAN else "agent", "points": points, "trickNo": self.trick_no,
            }
            text = f"{'You win' if winner == HUMAN else 'The agent wins'} trick {self.trick_no} (+{points} pts)"
            if self.trick_no == 8:
                text += " — includes +10 for the last trick"
            events.append({"type": "trick", "winner": self.last_trick["winner"], "points": points, "text": text})
            self.trick, self.trick_no = [], self.trick_no + 1

        if done:
            events += self._finish_round()
        return events

    def _finish_round(self):
        trump = self.env.trump_suit
        human_points, agent_points = self.env.final_points
        self.totals[HUMAN] += human_points
        self.totals[AGENT] += agent_points
        belote = [who for seat, who in ((HUMAN, "you"), (AGENT, "agent"))
                  if has_belote(self.env.players[seat].dealt_hand, trump)]
        self.round_result = {"you": human_points, "agent": agent_points, "belote": belote}
        self.history.append({"round": self.round_no, "trump": SUIT_INFO[trump][0], "you": human_points, "agent": agent_points})
        self.leader = AGENT if self.leader == HUMAN else HUMAN

        text = f"Round {self.round_no} over: you {human_points} — agent {agent_points}."
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

    def state(self, events):
        env, trump = self.env, self.env.trump_suit
        my_turn = self.round_result is None and env.current_idx == HUMAN
        legal = set(CARD_INDEX[c] for c in self._legal_cards()) if my_turn else set()
        hand = [dict(card_json(c, trump), legal=CARD_INDEX[c] in legal) for c in sort_hand(env.players[HUMAN].hand, trump)]
        trump_symbol, trump_name, trump_color = SUIT_INFO[trump]
        return {
            "events": events,
            "round": self.round_no,
            "trump": {"symbol": trump_symbol, "name": trump_name, "color": trump_color},
            "hand": hand,
            "agentHand": [card_json(c, trump) for c in sort_hand(env.players[AGENT].hand, trump)],
            "table": [{"seat": "you" if s == HUMAN else "agent", "card": card_json(c, trump)} for s, c in self.trick],
            "lastTrick": self.last_trick,
            "yourTurn": my_turn,
            # en cours de manche : points des plis ; une fois finie : total avec dix de der et belote
            "roundPoints": ({"you": self.round_result["you"], "agent": self.round_result["agent"]} if self.round_result
                            else {"you": env.players[HUMAN].manche_points(trump), "agent": env.players[AGENT].manche_points(trump)}),
            "totals": {"you": self.totals[HUMAN], "agent": self.totals[AGENT]},
            "target": self.target,
            "roundResult": self.round_result,
            "gameOver": self.game_over,
            "history": self.history,
        }
