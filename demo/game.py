"""Partie humain contre agent PPO pour la démo web (textes en anglais pour le jury).

GameSession enveloppe BeloteEnv (mêmes règles et même observation qu'à
l'entraînement) et produit, à chaque action, la liste des événements à
animer côté navigateur et l'état complet de la table.

Avec un modèle entraîné avec les annonces (models/ppo_bidding_2M.pt, par
défaut), chaque manche commence par les annonces : carte retournée, tour 1
(prendre ou passer), tour 2 (nommer une autre couleur ou passer), et le
preneur "dedans" s'il marque moins que l'adversaire. Un modèle sans annonces
joue avec un atout tiré au hasard, comme avant.

Parties contre des humains (point C) : chaque manche (donne, annonces, cartes,
points) et chaque partie (joueur, score, gagnant, abandon) sont écrites par
GameLog dans un fichier JSONL, une ligne par enregistrement. En mode étude
(study=True), la main de l'agent n'est jamais envoyée au navigateur ; hors
mode étude, une partie où le joueur l'a regardée est marquée "revealed".
"""
import json
import random
import threading
import time
import uuid

import torch

from belote.core.cards import Rank, Suit, sort_hand
from belote.core.engine import has_belote, legal_moves
from belote.rl.env import CARD_INDEX, INDEX_CARD, NAME_SUIT, PASS, SUIT_OF_ACTION, TAKE, BeloteEnv
from belote.rl.pimc import PIMCAgent
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


class GameLog:
    """Ajoute des enregistrements JSON (un par ligne) à un fichier, sans jamais
    réécrire les précédents ; partagé entre toutes les parties du serveur."""

    def __init__(self, path):
        self.path = path
        self._lock = threading.Lock()

    def write(self, record):
        line = json.dumps(record, ensure_ascii=False)
        with self._lock, open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
            f.flush()


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
    def __init__(self, checkpoint=DEFAULT_CHECKPOINT, target=DEFAULT_TARGET_SCORE, seed=None,
                 agent=None, log=None, study=False, player=None, search=0):
        """agent : agent déjà chargé (partagé entre les parties du serveur),
        sinon chargé depuis checkpoint. log : GameLog, ou None pour ne rien
        enregistrer. study : la main de l'agent reste cachée. search : nombre
        de mains adverses imaginées par la recherche PIMC avant chaque carte
        (0 = réseau seul) ; la confiance affichée reste celle du réseau."""
        self.checkpoint = checkpoint
        self.network_agent = agent or load_agent(checkpoint)
        self.search = search
        self.agent = PIMCAgent(self.network_agent, n_samples=search, seed=random.randrange(2**31)) if search else self.network_agent
        self.env = BeloteEnv(**self.network_agent.env_kwargs())
        if hasattr(self.agent, "attach_env"):
            self.agent.attach_env(self.env)
        self.bidding = self.env.bidding
        self.rng = random.Random(seed)
        self.target = target
        self.log = log
        self.study = study
        self.player = player
        self.game_id = None
        self.new_game()

    # ---------- enregistrement ----------
    def set_player(self, name):
        name = (name or "").strip()[:40]
        if not name:
            raise IllegalMove("Please enter your name.")
        self.player = name
        return self.state([])

    def reveal(self, on):
        if self.study:
            raise IllegalMove("The agent's hand stays hidden in this study.")
        self.revealing = bool(on)
        self.revealed = self.revealed or self.revealing
        return self.state([])

    def _record(self, record):
        if self.log is not None:
            self.log.write(dict(record, game_id=self.game_id, player=self.player, time=time.time()))

    def _record_game(self, status):
        """status : "finished" ou "abandoned" (nouvelle partie lancée avant la fin)."""
        human, agent = self.totals[HUMAN], self.totals[AGENT]
        self._record({"type": "game", "status": status, "you": human, "agent": agent,
                      "winner": None if status != "finished" or human == agent else ("you" if human > agent else "agent"),
                      "rounds": len(self.history), "target": self.target, "checkpoint": self.checkpoint,
                      "bidding": self.bidding, "study": self.study, "search": self.search, "revealed": self.revealed,
                      "started": self.started_at, "human_actions": self.human_actions})

    def _record_round(self, redeal=False):
        env = self.env
        hand_labels = lambda cards: [card_json(c)["label"] for c in cards]
        self._record({
            "type": "round", "round": self.round_no, "redeal": redeal, "first_speaker": seat_name(self.round_leader),
            "deal": {"you": hand_labels(env.deal[HUMAN]), "agent": hand_labels(env.deal[AGENT]),
                     "turned": card_json(env.turned_card)["label"] if env.turned_card is not None else None},
            "bids": self.bids, "plays": self.plays,
            "trump": SUIT_INFO[env.trump_suit][1] if env.trump_suit is not None else None,
            "taker": seat_name(env.taker) if env.taker is not None else None,
            "dedans": env.dedans, "points": None if redeal else {"you": env.final_points[HUMAN], "agent": env.final_points[AGENT]},
            "revealed": self.revealed})

    # ---------- déroulement ----------
    def new_game(self):
        if self.game_id is not None and not self.game_over and self.human_actions > 0:
            self._record_game("abandoned")
        self.game_id = uuid.uuid4().hex[:12]
        self.started_at = time.time()
        self.human_actions = 0
        self.revealed = self.revealing = False
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
        self.plays = []
        self.calls = {}  # carte -> "Belote!" / "Rebelote!" pour la manche en cours
        self.round_leader = self.leader
        if self.bidding:
            turned = self.env.turned_card
            who = "You speak first" if self.leader == HUMAN else "The agent speaks first"
            # "deal" : le navigateur repart de cette donne (nouvelle main, carte retournée)
            events.append({"type": "message", "deal": True,
                           "text": f"Round {self.round_no} — turned card: {card_json(turned)['label']}. {who}.",
                           "turnedCard": card_json(turned), "firstSpeaker": seat_name(self.leader),
                           "hand": [card_json(c) for c in sort_hand(self.env.players[HUMAN].hand, turned.suit)],
                           "agentHand": self._agent_hand_json(None, turned.suit)})
        else:
            trump_symbol, trump_name, _ = SUIT_INFO[self.env.trump_suit]
            who = "You lead" if self.leader == HUMAN else "The agent leads"
            events.append({"type": "message", "text": f"Round {self.round_no} — trump is {trump_name} {trump_symbol}. {who}."})
        return self._continue(events)

    def _continue(self, events):
        """Fait jouer l'agent jusqu'au tour de l'humain ou la fin de la manche."""
        events += self._agent_turns()
        if self.info.get("redeal"):
            self._record_round(redeal=True)
            events.append({"type": "message", "text": "Both players passed twice: the cards are redealt."})
            return self._deal(events)
        return self.state(events)

    def play_human(self, card_id):
        if self.round_result is not None or self.env.current_idx != HUMAN or self.env.phase != "play":
            raise IllegalMove("It is not your turn to play a card.")
        card = INDEX_CARD.get(int(card_id))
        if card is None or card not in self._legal_cards():
            raise IllegalMove("This card is not allowed: follow suit, trump if you can't, over-trump when trump is led.")
        self.human_actions += 1
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
        self.human_actions += 1
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
                logits, _value = self.network_agent._masked_logits_and_value(self.obs, legal_mask)
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
        call = self._belote_call(seat, card)
        if call:
            play["announce"] = call
            self.calls[CARD_INDEX[card]] = call
        events = [play]
        self.plays.append([seat_name(seat), card_json(card)["label"]])
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

    def _belote_call(self, seat, card):
        """"Belote!" à la première carte posée du Roi et de la Dame d'atout, "Rebelote!" à la
        seconde, si le joueur avait les deux dans sa main de départ (les points, +20, sont
        comptés en fin de manche par BeloteEnv)."""
        trump = self.env.trump_suit
        if card.suit != trump or card.rank not in (Rank.KING, Rank.QUEEN) \
                or not has_belote(self.env.players[seat].dealt_hand, trump):
            return None
        other = Rank.QUEEN if card.rank == Rank.KING else Rank.KING
        already = any(s == seat_name(seat) and lbl == card_json(type(card)(trump, other))["label"] for s, lbl in self.plays)
        return "Rebelote!" if already else "Belote!"

    def _apply_bid(self, action, seat, confidence=None):
        turned_suit = self.env.turned_card.suit
        label = bid_label(action, turned_suit)
        self.bids.append({"seat": seat_name(seat), "round": 1 if self.env.phase == "bid1" else 2, "label": label,
                          "suit": None if action == PASS else SUIT_INFO[turned_suit if action == TAKE else SUIT_OF_ACTION[action]][1]})
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
        self._record_round()
        if max(self.totals.values()) >= self.target:
            self.game_over = True
            if self.totals[HUMAN] == self.totals[AGENT]:
                final = "It's a draw!"
            else:
                final = "You win the game!" if self.totals[HUMAN] > self.totals[AGENT] else "The agent wins the game."
            events.append({"type": "game", "text": f"{final} Final score: you {self.totals[HUMAN]} — agent {self.totals[AGENT]}."})
            self._record_game("finished")
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

    def _agent_hand_json(self, trump, sort_suit):
        """Main de l'agent si le joueur a demandé à la voir, sinon des dos de cartes (rien d'autre n'est envoyé)."""
        hand = sort_hand(self.env.players[AGENT].hand, sort_suit)
        if self.revealing:
            return [card_json(c, trump) for c in hand]
        return [{"hidden": True} for _ in hand]

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
            "agentHand": self._agent_hand_json(trump, sort_suit),
            "study": self.study,
            "player": self.player,
            "revealing": self.revealing,
            "table": [dict({"seat": seat_name(s), "card": card_json(c, trump)},
                           **({"announce": self.calls[CARD_INDEX[c]]} if CARD_INDEX[c] in self.calls else {}))
                      for s, c in self.trick],
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
