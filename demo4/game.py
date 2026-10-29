"""Coinche à 4 dans le navigateur : le joueur humain est Sud, avec Nord comme
partenaire, contre Est et Ouest.

Le joueur choisit son nom, sa convention (jouée aussi par son partenaire
Nord : petit jeu, Papi Robert, AsR ou robots simples) et ses adversaires
(une convention, ou l'IA entraînée, qui affiche sa confiance à chaque coup).

Table enveloppe CoincheGame : à chaque action du joueur, elle fait jouer les
autres places jusqu'à son tour (ou la fin de la donne) et renvoie la liste des
événements à animer et l'état complet de la table (textes en anglais).
"""
import random

import torch

from belote.coinche.asr import AsRBot
from belote.coinche.bots import CoincheBot
from belote.coinche.engine import (
    CAPOT, CONTRACTS, DEFAULT_TARGET, RULES, SEAT_NAMES, SUITS, CoincheGame, team_of,
)
from belote.coinche.papi_robert import PapiRobertBot
from belote.coinche.petit_jeu import PetitJeuBot
from belote.coinche.pimc import CoinchePIMC
from belote.coinche.rl_env import NUM_ACTIONS_BIDDING, CoincheEnv, action_to_bid
from belote.core.cards import sort_hand
from belote.rl.env import CARD_INDEX, INDEX_CARD
from demo.game import SUIT_INFO, card_json

HUMAN = 0
PARTNER = 2
SEAT_KEYS = ("south", "west", "north", "east")  # sens des aiguilles d'une montre

BOT_KINDS = {"simple": CoincheBot, "petitjeu": PetitJeuBot, "papirobert": PapiRobertBot, "asr": AsRBot}
BOT_LABELS = {"simple": "Simple bots", "petitjeu": "Petit jeu", "papirobert": "Papi Robert", "asr": "AsR",
              "ai": "AI", "ai_search": "AI + search"}
SEARCH_SAMPLES = 20  # mains imaginées par la recherche avant chaque carte
# présentation dans l'écran d'accueil (étoiles choisies par Noa)
PLAYER_INFO = {
    "ai": {"label": "AI", "stars": 5, "text": "Our trained network: it taught itself by playing millions of deals. "
                                              "Shows its confidence at every move."},
    "ai_search": {"label": "AI + search", "stars": 5,
                  "text": "The same network, but before each card it imagines 20 possible deals of the hidden cards "
                          "and plays them out. Bids like the AI."},
    "asr": {"label": "AsR", "stars": 4, "text": "80 shows two Aces, 90 asks for the other major, 110–140 ask for "
                                                "precise Aces and 10s, discard calls, belote parity signal."},
    "papirobert": {"label": "Papi Robert", "stars": 2, "text": "The “jeu aux As”: 80 with two Aces, "
                                                              "90 looking for the second major, never 100 without both."},
    "petitjeu": {"label": "Petit jeu", "stars": 2, "text": "80 with the Jack or the 9 and two trumps, 90 with both, "
                                                          "100 to 120 when master of trump."},
    "simple": {"label": "Simple bots", "stars": 1, "text": "Hand-written test bots: they bid on a point count and "
                                                          "play without conventions."},
}
STYLES = ("petitjeu", "papirobert", "asr", "simple")
OPPONENTS = ("ai_search", "ai", "asr", "papirobert", "petitjeu", "simple")


class IllegalMove(Exception):
    pass


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


class AIPlayer:
    """L'IA entraînée à une place : observation construite comme pendant l'entraînement (CoincheEnv
    branché sur la partie de la table, avec ses déductions sur les mains cachées)."""

    def __init__(self, network, search=0):
        self.network = network
        self.env = CoincheEnv(bidding=True)
        self.search = CoinchePIMC(network, n_samples=search, seed=random.randrange(2**31)) if search else None

    def attach(self, game):
        self.env.game = game
        self.new_deal()

    def new_deal(self):
        self.env.voids = [set() for _ in range(4)]
        self.env.trump_cap = [None] * 4
        self.env.belote_seen = None
        self.env.done = False  # utilisé par la recherche (copies de la partie)
        self.env.bid_seats = set(range(4))

    def before_card(self, seat, card):
        """À appeler avant chaque carte jouée (toutes les places) : met à jour les déductions."""
        self.env._update_belief(seat, card)
        if self.env.game.belote_call(seat, card):
            self.env.belote_seen = seat

    def act(self):
        """(action du jeu, confiance) : le coup le plus probable du réseau et sa probabilité."""
        obs = self.env._observe()
        mask = torch.as_tensor(self.env.legal_mask())
        with torch.no_grad():
            logits, _value = self.network(torch.as_tensor(obs))
            probs = torch.softmax(logits.masked_fill(~mask, float("-inf")), dim=-1)
        action = int(probs.argmax())
        if self.search is not None and self.env.game.phase == "play":
            action = self.search.act(self.env)  # confiance : probabilité du réseau pour la carte choisie
        move = action_to_bid(action) if self.env.game.phase == "bidding" else INDEX_CARD[action]
        return move, float(probs[action])


class Table:
    def __init__(self, target=DEFAULT_TARGET, seed=None, bots="simple", partner=None, opponents=None,
                 name=None, network=None):
        """partner : convention de Nord (la tienne) ; opponents : convention d'Est et Ouest, ou "ai"
        (réseau network). bots : les deux à la fois (ancienne option --bots)."""
        self.rng = random.Random(seed)
        self.target = target
        self.network = network
        self.reveal = False
        self.configure(name or "You", partner or bots, opponents or bots, start=False)
        self.configured = name is not None
        self.new_game()

    # ---------- réglages ----------
    def kinds(self):
        return [k for k in OPPONENTS if not k.startswith("ai") or self.network is not None]

    def configure(self, name, partner, opponents, start=True):
        name = " ".join("".join(ch for ch in str(name or "") if ch not in "<>&\"'").split())[:20] or "You"
        if partner not in STYLES:
            raise IllegalMove(f"Unknown style: {partner}")
        if opponents not in self.kinds():
            raise IllegalMove(f"Unknown opponents: {opponents}")
        self.name, self.partner, self.opponents = name, partner, opponents
        self.ai = (AIPlayer(self.network, SEARCH_SAMPLES if opponents == "ai_search" else 0)
                   if opponents.startswith("ai") else None)
        self.players = {PARTNER: BOT_KINDS[partner]()}
        for seat in (1, 3):
            self.players[seat] = self.ai if self.ai is not None else BOT_KINDS[opponents]()
        self.configured = True
        if start:
            return self.new_game()
        return None

    def setup(self, payload):
        payload = payload or {}
        return self.configure(payload.get("name"), payload.get("partner"), payload.get("opponents"))

    # ---------- textes ----------
    def _you(self):
        return self.name == "You"

    def label(self, seat):
        return self.name if seat == HUMAN else SEAT_NAMES[seat]

    def _s(self, seat):
        """Accord du verbe : "You play", "Noa plays", "North plays"."""
        return "" if seat == HUMAN and self._you() else "s"

    def team_names(self):
        return (f"{self.name} & North", "East & West")

    # ---------- actions du joueur ----------
    def new_game(self):
        self.game = CoincheGame(target=self.target, rng=random.Random(self.rng.random()))
        if self.ai is not None:
            self.ai.attach(self.game)
        self._reset_deal()
        events = [self._deal_event()]
        return self.state(events + self._run_bots())

    def _reset_deal(self):
        self.last_trick = None
        self.calls = {}
        self.confidence = {}  # carte (index) -> confiance de l'IA, pour le pli affiché
        if self.ai is not None:
            self.ai.new_deal()

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
        self._reset_deal()
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
                self._reset_deal()
                events.append(self._deal_event())
                continue
            if game.phase not in ("bidding", "play") or game.current == HUMAN:
                return events
            seat = game.current
            player = self.players[seat]
            confidence = None
            if isinstance(player, AIPlayer):
                move, confidence = player.act()
            elif game.phase == "bidding":
                move = player.bid(game, seat)
            else:
                move = player.play(game, seat)
            if game.phase == "bidding":
                events += self._apply_bid(seat, move, confidence)
            else:
                events += self._apply_card(seat, move, confidence)

    def _apply_bid(self, seat, action, confidence=None):
        game = self.game
        game.bid(seat, action)
        event = {"type": "bid", "seat": SEAT_KEYS[seat], "label": bid_label(action),
                 "text": f"{self.label(seat)}: {bid_label(action)}"}
        if confidence is not None:
            event["confidence"] = round(100 * confidence)
            event["text"] += f" (confidence {event['confidence']}%)"
        events = [event]
        if game.phase == "play":
            c = game.contract
            mult = {1: "", 2: ", coinched", 3: ", surcoinched"}[c["mult"]]
            events.append({"type": "message", "contract": True,
                           "text": f"Contract: {contract_label(c['value'], c['suit'])} by {self.label(c['seat'])}{mult}. "
                                   f"{self.label(game.current)} lead{self._s(game.current)}."})
        return events

    def _apply_card(self, seat, card, confidence=None):
        game = self.game
        if self.ai is not None:
            self.ai.before_card(seat, card)
        call = game.belote_call(seat, card)
        if call:
            self.calls[CARD_INDEX[card]] = call
        if confidence is not None:
            self.confidence[CARD_INDEX[card]] = round(100 * confidence)
        done = game.play(seat, card)
        event = {"type": "play", "seat": SEAT_KEYS[seat], "card": card_json(card, game.trump),
                 "text": f"{self.label(seat)} play{self._s(seat)} {card_json(card)['label']}"}
        if confidence is not None:
            event["confidence"] = round(100 * confidence)
            event["text"] += f" (confidence {event['confidence']}%)"
        if call:
            event["announce"] = call
            event["text"] += f" — {call}"
        events = [event]
        if done:
            trick, winner, points = done
            self.last_trick = {"cards": [{"seat": SEAT_KEYS[s], "card": card_json(c, game.trump)} for s, c in trick],
                               "winner": SEAT_KEYS[winner], "points": points, "trickNo": len(game.tricks)}
            text = f"{self.label(winner)} win{self._s(winner)} trick {len(game.tricks)} (+{points})"
            if len(game.tricks) == 8:
                text += ", including 10 for the last trick"
            events.append({"type": "trick", "winner": SEAT_KEYS[winner], "text": text})
            if game.phase == "done":
                events.append({"type": "message", "text": self._result_text()})
        return events

    def _deal_event(self):
        game = self.game
        first = (game.dealer + 1) % 4
        return {"type": "message", "deal": True,
                "text": f"Deal {game.deal_no}: {self.label(game.dealer)} deal{self._s(game.dealer)}, "
                        f"{self.label(first)} speak{self._s(first)} first.",
                "hand": [card_json(c) for c in sort_hand(game.hands[HUMAN], None)]}

    def _result_text(self):
        r = self.game.result
        c = r["contract"]
        teams = self.team_names()
        verdict = "made" if r["made"] else "failed"
        return (f"Contract {contract_label(c['value'], c['suit'])} {verdict} by {teams[team_of(c['seat'])]}: "
                f"{teams[0]} +{r['scores'][0]}, {teams[1]} +{r['scores'][1]}.")

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
        teams = self.team_names()
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
                        "byLabel": self.label(c["seat"]), "team": teams[team_of(c["seat"])],
                        "mult": c["mult"], "suit": suit_json(c["suit"])}
        result = None
        if game.phase == "done":
            r = game.result
            result = {"made": r["made"], "scores": r["scores"], "points": r["points"], "belote": r["belote"],
                      "beloteNeeded": r["belote_needed"], "mult": r["contract"]["mult"],
                      "total": r["total"], "tricksWon": r["tricks_won"],
                      "capot": teams[r["capot_team"]] if r["capot_team"] is not None else None,
                      "text": self._result_text()}

        def trick_entry(s, card):
            entry = {"seat": SEAT_KEYS[s], "card": card_json(card, trump)}
            if CARD_INDEX[card] in self.calls:
                entry["announce"] = self.calls[CARD_INDEX[card]]
            if CARD_INDEX[card] in self.confidence:
                entry["confidence"] = self.confidence[CARD_INDEX[card]]
            return entry

        return {
            "events": events,
            "configured": self.configured,
            "setup": {"name": self.name, "partner": self.partner, "opponents": self.opponents,
                      "partnerLabel": BOT_LABELS[self.partner], "opponentsLabel": BOT_LABELS[self.opponents]},
            "players": {"styles": [dict(PLAYER_INFO[k], key=k) for k in STYLES],
                        "opponents": [dict(PLAYER_INFO[k], key=k) for k in self.kinds()]},
            "names": {"south": self.name, "west": "West", "north": "North", "east": "East"},
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
            "trick": [trick_entry(s, card) for s, card in game.trick],
            "lastTrick": self.last_trick,
            "trickPoints": game.trick_points,
            "tricksWon": game.tricks_won,
            "yourTurn": my_turn,
            "yourBid": game.phase == "bidding" and game.current == HUMAN,
            "teams": teams,
            "totals": game.totals,
            "target": game.target,
            "result": result,
            "gameOver": game.game_over,
            "history": [{"deal": h["deal"], "contract": contract_label(h["contract"]["value"], h["contract"]["suit"]),
                         "by": self.label(h["contract"]["seat"]), "mult": h["contract"]["mult"],
                         "made": h["made"], "scores": h["scores"]} for h in game.history],
            "rules": RULES,
            "bots": f"{BOT_LABELS[self.partner]} partner · {BOT_LABELS[self.opponents]} opponents",
            "contracts": CONTRACTS,
        }


def load_network(path):
    """Réseau de l'IA (75 actions : cartes et annonces), ou None si le fichier manque."""
    from belote.rl.networks import ActorCriticNetwork
    try:
        network = ActorCriticNetwork.from_checkpoint(path)
    except FileNotFoundError:
        return None
    if network.num_actions != NUM_ACTIONS_BIDDING:
        raise ValueError(f"{path} : le modèle doit faire les annonces (75 actions), il en a {network.num_actions}")
    network.eval()
    return network
