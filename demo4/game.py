"""Coinche à 4 dans le navigateur : le joueur humain est Sud, avec Nord comme
partenaire, contre Est et Ouest. Les trois autres places sont jouées par
belote.coinche.bots.CoincheBot (règles simples, pas d'apprentissage).

Table enveloppe CoincheGame : à chaque action du joueur, elle fait jouer les
robots jusqu'à son tour (ou la fin de la donne) et renvoie la liste des
événements à animer et l'état complet de la table (textes en anglais).
"""
import random

from belote.coinche.bots import CoincheBot
from belote.coinche.asr import AsRBot
from belote.coinche.papi_robert import PapiRobertBot
from belote.coinche.petit_jeu import PetitJeuBot
from belote.coinche.engine import (
    CAPOT, CONTRACTS, DEFAULT_TARGET, RULES, SEAT_NAMES, SUITS, CoincheGame, team_of,
)
from belote.core.cards import sort_hand
from belote.rl.env import CARD_INDEX, INDEX_CARD
from demo.game import SUIT_INFO, card_json

HUMAN = 0
SEAT_KEYS = ("south", "west", "north", "east")  # sens des aiguilles d'une montre
TEAM_NAMES = ("You & North", "East & West")


BOT_KINDS = {"simple": CoincheBot, "petitjeu": PetitJeuBot, "papirobert": PapiRobertBot, "asr": AsRBot}
BOT_LABELS = {"simple": "simple bots", "petitjeu": "Petit jeu", "papirobert": "Papi Robert", "asr": "AsR"}


class IllegalMove(Exception):
    pass


def seat_label(seat):
    return "You" if seat == HUMAN else SEAT_NAMES[seat]


def suit_json(suit):
    symbol, name, color = SUIT_INFO[suit]
    return {"symbol": symbol, "name": name, "color": color}


def contract_label(value, suit):
    return f"{'Capot' if value == CAPOT else value} {SUIT_INFO[suit][0]}"


def bid_label(action):
    kind = action[0]
    if kind == "bid":
        return contract_label(action[1], action[2])
    return {"pass": "Pass", "coinche": "Coinche!", "surcoinche": "Surcoinche!"}[kind]


class Table:
    def __init__(self, target=DEFAULT_TARGET, seed=None, bots="simple"):
        """bots : règles des trois robots ("simple" : CoincheBot ; "petitjeu" : convention du petit jeu ;
        "papirobert" : jeu aux As de Papi Robert ;
        "asr" : conventions AsR)."""
        self.rng = random.Random(seed)
        self.target = target
        self.bot = BOT_KINDS[bots]()
        self.bots = bots
        self.reveal = False
        self.new_game()

    # ---------- actions du joueur ----------
    def new_game(self):
        self.game = CoincheGame(target=self.target, rng=random.Random(self.rng.random()))
        self.last_trick = None
        self.calls = {}
        events = [self._deal_event()]
        return self.state(events + self._run_bots())

    def bid_human(self, payload):
        kind = (payload or {}).get("kind")
        if kind == "bid":
            suit = next((s for s in SUITS if SUIT_INFO[s][1] == payload.get("suit")), None)
            action = ("bid", int(payload.get("value", 0)), suit)
        else:
            action = (kind,)
        if self.game.current != HUMAN or action not in self.game.legal_bids(HUMAN):
            raise IllegalMove("This bid is not allowed now.")
        events = self._apply_bid(HUMAN, action)
        return self.state(events + self._run_bots())

    def play_human(self, card_id):
        card = INDEX_CARD.get(int(card_id))
        if self.game.current != HUMAN or card not in self.game.legal_cards(HUMAN):
            raise IllegalMove("This card is not allowed (follow suit; trump if your partner is not winning; "
                              "overtrump if you can).")
        events = self._apply_card(HUMAN, card)
        return self.state(events + self._run_bots())

    def next_deal(self):
        if self.game.phase != "done" or self.game.game_over:
            raise IllegalMove("The current deal is not finished.")
        self.game.new_deal()
        self.last_trick = None
        self.calls = {}
        return self.state([self._deal_event()] + self._run_bots())

    def set_reveal(self, on):
        self.reveal = bool(on)
        return self.state([])

    # ---------- déroulement ----------
    def _run_bots(self):
        events = []
        game = self.game
        while True:
            if game.phase == "redeal":
                events.append({"type": "message", "text": "Everybody passed: the cards are redealt (next dealer)."})
                game.new_deal()
                self.last_trick, self.calls = None, {}
                events.append(self._deal_event())
                continue
            if game.phase not in ("bidding", "play") or game.current == HUMAN:
                return events
            seat = game.current
            if game.phase == "bidding":
                events += self._apply_bid(seat, self.bot.bid(game, seat))
            else:
                events += self._apply_card(seat, self.bot.play(game, seat))

    def _apply_bid(self, seat, action):
        game = self.game
        game.bid(seat, action)
        events = [{"type": "bid", "seat": SEAT_KEYS[seat], "label": bid_label(action),
                   "text": f"{seat_label(seat)}: {bid_label(action)}"}]
        if game.phase == "play":
            c = game.contract
            mult = {1: "", 2: ", coinched", 3: ", surcoinched"}[c["mult"]]
            events.append({"type": "message", "contract": True,
                           "text": f"Contract: {contract_label(c['value'], c['suit'])} by {seat_label(c['seat'])}{mult}. "
                                   f"{seat_label(game.current)} lead{'' if game.current == HUMAN else 's'}."})
        return events

    def _apply_card(self, seat, card):
        game = self.game
        call = game.belote_call(seat, card)
        if call:
            self.calls[CARD_INDEX[card]] = call
        done = game.play(seat, card)
        event = {"type": "play", "seat": SEAT_KEYS[seat], "card": card_json(card, game.trump),
                 "text": f"{seat_label(seat)} play{'' if seat == HUMAN else 's'} {card_json(card)['label']}"}
        if call:
            event["announce"] = call
            event["text"] += f" — {call}"
        events = [event]
        if done:
            trick, winner, points = done
            self.last_trick = {"cards": [{"seat": SEAT_KEYS[s], "card": card_json(c, game.trump)} for s, c in trick],
                               "winner": SEAT_KEYS[winner], "points": points, "trickNo": len(game.tricks)}
            text = f"{seat_label(winner)} win{'' if winner == HUMAN else 's'} trick {len(game.tricks)} (+{points})"
            if len(game.tricks) == 8:
                text += ", including 10 for the last trick"
            events.append({"type": "trick", "winner": SEAT_KEYS[winner], "text": text})
            if game.phase == "done":
                events.append({"type": "message", "text": self._result_text()})
        return events

    def _deal_event(self):
        game = self.game
        return {"type": "message", "deal": True,
                "text": f"Deal {game.deal_no}: {seat_label(game.dealer)} deal{'' if game.dealer == HUMAN else 's'}, "
                        f"{seat_label((game.dealer + 1) % 4)} speak{'' if (game.dealer + 1) % 4 == HUMAN else 's'} first.",
                "hand": [card_json(c) for c in sort_hand(game.hands[HUMAN], None)]}

    def _result_text(self):
        r = self.game.result
        c = r["contract"]
        who = TEAM_NAMES[team_of(c["seat"])]
        verdict = "made" if r["made"] else "failed"
        return (f"Contract {contract_label(c['value'], c['suit'])} {verdict} by {who}: "
                f"{TEAM_NAMES[0]} +{r['scores'][0]}, {TEAM_NAMES[1]} +{r['scores'][1]}.")

    # ---------- état ----------
    def _bid_options(self):
        game = self.game
        if game.phase != "bidding" or game.current != HUMAN:
            return None
        legal = game.legal_bids(HUMAN)
        values = sorted({a[1] for a in legal if a[0] == "bid"})
        return {"values": [{"value": v, "label": "Capot" if v == CAPOT else str(v)} for v in values],
                "suits": [suit_json(s) for s in SUITS],
                "coinche": ("coinche",) in legal, "surcoinche": ("surcoinche",) in legal}

    def state(self, events):
        game = self.game
        trump = game.trump
        my_turn = game.phase == "play" and game.current == HUMAN
        legal = {CARD_INDEX[c] for c in game.legal_cards(HUMAN)} if my_turn else set()
        hands = {}
        for seat in range(4):
            cards = sort_hand(game.hands[seat], trump)
            if seat == HUMAN or self.reveal:
                hands[SEAT_KEYS[seat]] = [dict(card_json(c, trump), legal=CARD_INDEX[c] in legal) for c in cards]
            else:
                hands[SEAT_KEYS[seat]] = [{"hidden": True} for _ in cards]
        c = game.contract
        contract = None
        if c is not None:
            contract = {"label": contract_label(c["value"], c["suit"]), "by": SEAT_KEYS[c["seat"]],
                        "byLabel": seat_label(c["seat"]), "team": TEAM_NAMES[team_of(c["seat"])],
                        "mult": c["mult"], "suit": suit_json(c["suit"])}
        result = None
        if game.phase == "done":
            r = game.result
            result = {"made": r["made"], "scores": r["scores"], "points": r["points"], "belote": r["belote"],
                      "beloteNeeded": r["belote_needed"], "mult": r["contract"]["mult"],
                      "total": r["total"], "tricksWon": r["tricks_won"],
                      "capot": TEAM_NAMES[r["capot_team"]] if r["capot_team"] is not None else None,
                      "text": self._result_text()}
        return {
            "events": events,
            "phase": game.phase,
            "dealNo": game.deal_no,
            "dealer": SEAT_KEYS[game.dealer],
            "current": SEAT_KEYS[game.current] if game.phase in ("bidding", "play") else None,
            "hands": hands,
            "reveal": self.reveal,
            "bids": [{"seat": SEAT_KEYS[s], "label": bid_label(a)} for s, a in game.bids],
            "bidOptions": self._bid_options(),
            "contract": contract,
            "trump": suit_json(trump) if trump is not None else None,
            "trick": [dict({"seat": SEAT_KEYS[s], "card": card_json(card, trump)},
                           **({"announce": self.calls[CARD_INDEX[card]]} if CARD_INDEX[card] in self.calls else {}))
                      for s, card in game.trick],
            "lastTrick": self.last_trick,
            "trickPoints": game.trick_points,
            "tricksWon": game.tricks_won,
            "yourTurn": my_turn,
            "yourBid": game.phase == "bidding" and game.current == HUMAN,
            "teams": TEAM_NAMES,
            "totals": game.totals,
            "target": game.target,
            "result": result,
            "gameOver": game.game_over,
            "history": [{"deal": h["deal"], "contract": contract_label(h["contract"]["value"], h["contract"]["suit"]),
                         "by": seat_label(h["contract"]["seat"]), "mult": h["contract"]["mult"],
                         "made": h["made"], "scores": h["scores"]} for h in game.history],
            "rules": RULES,
            "bots": BOT_LABELS[self.bots],
            "contracts": CONTRACTS,
        }
