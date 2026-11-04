"""Coinche à 4 dans le navigateur : le joueur humain est Sud, avec Nord comme
partenaire, contre Est et Ouest.

Le joueur choisit son nom, sa convention (jouée aussi par son partenaire
Nord : petit jeu, Papi Robert, AsR ou robots simples) et ses adversaires
(une convention, ou l'IA entraînée, qui affiche sa confiance à chaque coup).

Table enveloppe CoincheGame : chaque action du joueur répond tout de suite
(son coup seul) ; tant que state()["pending"] est vrai, le navigateur appelle
step(), qui fait jouer une seule autre place et renvoie ses événements. Le
navigateur demande le coup suivant pendant qu'il anime le précédent : le
calcul de l'IA se cache derrière l'animation (textes en anglais).

Mode à deux humains (configure_duo puis join) : Sud et Nord sont deux joueurs
sur deux navigateurs, contre Est et Ouest (l'IA ou une convention). Chacun voit
la table depuis sa place (sa main en bas) : state(viewer=...) fait tourner les
places. Tous les événements sont gardés dans self.feed (numérotés), pour que
chaque navigateur rattrape ceux de l'autre (state(since=...)).

Avec un GameLog (log=...), chaque donne (mains, annonces, plis, résultat) et
chaque partie (terminée ou abandonnée) est ajoutée au fichier JSONL ;
scripts.coinche_human_results en tire les résultats et les graphiques.
"""
import random
import time
import uuid
from itertools import permutations

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
from belote.core.cards import Suit, sort_hand
from belote.rl.env import CARD_INDEX, INDEX_CARD
from demo.game import SUIT_INFO, card_json

HUMAN = 0
PARTNER = 2
SEAT_KEYS = ("south", "west", "north", "east")  # sens des aiguilles d'une montre
TEAM_KEYS = ("you", "opponents")  # équipe Sud-Nord, équipe Est-Ouest (enregistrements)

BOT_KINDS = {"simple": CoincheBot, "petitjeu": PetitJeuBot, "papirobert": PapiRobertBot, "asr": AsRBot}
BOT_LABELS = {"simple": "Simple bots", "petitjeu": "Petit jeu", "papirobert": "Papi Robert", "asr": "AsR",
              "ai": "AI", "ai_search": "AI + search", "human": "Human"}
DUO_AI_NAMES = {1: "West AI", 3: "East AI"}
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
    "papirobert": {"label": "Papi Robert", "stars": 2, "text": "“Belote au miel”: 80 with two Aces, "
                                                              "90 looking for the second major, 100–120 by number of suits."},
    "petitjeu": {"label": "Petit jeu", "stars": 2, "text": "80 with the Jack or the 9 and two trumps, 90 with both, "
                                                          "100 to 120 when master of trump."},
    "simple": {"label": "Simple bots", "stars": 1, "text": "Hand-written test bots: they bid on a point count and "
                                                          "play without conventions."},
}
STYLES = ("petitjeu", "papirobert", "asr", "simple")
OPPONENTS = ("ai_search", "ai", "asr", "papirobert", "petitjeu", "simple")


class IllegalMove(Exception):
    pass


RED = {Suit.COEUR, Suit.CARREAU}
DISPLAY_ORDER = [Suit.PIQUE, Suit.COEUR, Suit.TREFLE, Suit.CARREAU]  # noir, rouge, noir, rouge


def suit_order(hand, trump=None):
    """Ordre d'affichage des couleurs de ma main : rouge et noir en alternance (le moins possible de
    couleurs de même teinte côte à côte), l'atout à gauche s'il est connu."""
    present = [s for s in DISPLAY_ORDER if any(c.suit == s for c in hand)]

    def key(order):
        same = sum((a in RED) == (b in RED) for a, b in zip(order, order[1:]))
        return (trump in present and order[0] != trump, same, [DISPLAY_ORDER.index(s) for s in order])

    best = list(min(permutations(present), key=key)) if present else []
    return best + [s for s in DISPLAY_ORDER if s not in best]


def sort_by_order(hand, order, trump):
    """Ma main rangée selon l'ordre des couleurs, chaque couleur de la plus faible à la plus forte."""
    return sorted(hand, key=lambda c: (order.index(c.suit), c.strength(trump)))


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
                 name=None, network=None, log=None, study=False, model=None):
        """partner : convention de Nord (la tienne) ; opponents : convention d'Est et Ouest, ou "ai"
        (réseau network). bots : les deux à la fois (ancienne option --bots). log : GameLog où
        enregistrer donnes et parties (None : rien) ; study : mains des autres jamais montrées ;
        model : chemin du modèle de l'IA, noté dans les enregistrements."""
        self.rng = random.Random(seed)
        self.target = target
        self.network = network
        self.log = log
        self.study = study
        self.model = model
        self.reveal = False
        self.game_id = None
        self.humans = {HUMAN: "You"}  # place -> nom ; deux humains en mode duo
        self.duo = False
        self.waiting = False  # duo : l'hôte attend son partenaire
        self.feed = []  # tous les événements, dans l'ordre (rattrapage en mode duo)
        self.ctx = (HUMAN, None)  # (place qui regarde, premier événement à renvoyer) : réglé par le serveur
        self.configure(name or "You", partner or bots, opponents or bots, start=False)
        self.configured = name is not None
        self.new_game()

    # ---------- réglages ----------
    def kinds(self):
        return [k for k in OPPONENTS if not k.startswith("ai") or self.network is not None]

    def configure(self, name, partner, opponents, start=True):
        name = self.clean_name(name) or "You"
        if partner not in STYLES:
            raise IllegalMove(f"Unknown style: {partner}")
        if opponents not in self.kinds():
            raise IllegalMove(f"Unknown opponents: {opponents}")
        if start and self.game_id is not None and not self.game.game_over and self.human_actions > 0:
            self._record_game("abandoned")  # avec les anciens réglages
            self.game_id = None
        self.name, self.partner, self.opponents = name, partner, opponents
        self.humans = {HUMAN: name}
        self.duo = self.waiting = False
        self._make_players()
        self.players[PARTNER] = BOT_KINDS[partner]()
        self.configured = True
        if start:
            return self.new_game()
        return None

    def _make_players(self):
        self.ai = (AIPlayer(self.network, SEARCH_SAMPLES if self.opponents == "ai_search" else 0)
                   if self.opponents.startswith("ai") else None)
        self.players = {}
        for seat in (1, 3):
            self.players[seat] = self.ai if self.ai is not None else BOT_KINDS[self.opponents]()

    @staticmethod
    def clean_name(name):
        return " ".join("".join(ch for ch in str(name or "") if ch not in "<>&\"'").split())[:20]

    def configure_duo(self, name, opponents):
        """Mode à deux humains : je suis Sud, mon partenaire Nord rejoindra avec le lien d'invitation."""
        if opponents not in self.kinds():
            raise IllegalMove(f"Unknown opponents: {opponents}")
        if self.game_id is not None and not self.game.game_over and self.human_actions > 0:
            self._record_game("abandoned")
            self.game_id = None
        self.name = self.clean_name(name) or "Player 1"
        self.partner, self.opponents = "human", opponents
        self.humans = {HUMAN: self.name}
        self.duo, self.waiting, self.reveal = True, True, False
        self.feed = []
        self.invite = None  # code d'invitation, donné par le serveur
        self._make_players()
        self.configured = True
        return self.state([])

    def join(self, name):
        """Le partenaire arrive en Nord : la partie commence."""
        if not self.duo or not self.waiting:
            raise IllegalMove("This invitation has already been used.")
        name = self.clean_name(name) or "Player 2"
        if name == self.name:
            name += " (2)"
        self.humans[PARTNER] = name
        self.waiting = False
        return self.new_game()

    def setup(self, payload):
        payload = payload or {}
        return self.configure(payload.get("name"), payload.get("partner"), payload.get("opponents"))

    # ---------- textes ----------
    def _you(self):
        return self.name == "You" and not self.duo

    def label(self, seat):
        if seat in self.humans:
            return self.humans[seat]
        return DUO_AI_NAMES.get(seat, "Your partner") if self.duo else SEAT_NAMES[seat]

    def _s(self, seat):
        """Accord du verbe : "You play", "Noa plays", "North plays"."""
        return "" if seat == HUMAN and self._you() else "s"

    def team_names(self):
        if self.duo:
            return (f"{self.humans[HUMAN]} & {self.humans.get(PARTNER, '…')}", "AI team" if self.ai else "Bots")
        return (f"{self.name} & North", "East & West")

    # ---------- actions du joueur ----------
    def new_game(self):
        if self.waiting:
            return self.state([])
        if self.game_id is not None and not self.game.game_over and self.human_actions > 0:
            self._record_game("abandoned")
        self.game_id = uuid.uuid4().hex[:12]
        self.started_at = time.time()
        self.human_actions = 0
        self.revealed = self.reveal
        self.game = CoincheGame(target=self.target, rng=random.Random(self.rng.random()))
        if self.ai is not None:
            self.ai.attach(self.game)
        self._reset_deal()
        events = [self._deal_event()]
        return self.state(events)

    def _reset_deal(self):
        # ordre des couleurs fixé avant les annonces, puis une seule fois quand l'atout est connu
        self.order = {h: suit_order(self.game.hands[h]) for h in self.humans}
        self.coinche_window = False
        self.last_trick = None
        self.calls = {}
        self.confidence = {}  # carte (index) -> confiance de l'IA, pour le pli affiché
        if self.ai is not None:
            self.ai.new_deal()

    def bid_human(self, payload, seat=None):
        seat = self.ctx[0] if seat is None else seat
        kind = (payload or {}).get("kind")
        if kind == "bid":
            suit = next((s for s in SUITS if SUIT_INFO[s][1] == payload.get("suit")), None)
            action = ("bid", int(payload.get("value", 0)), suit)
        else:
            action = (kind,)
        if self.waiting or seat not in self.humans or self.game.current != seat or action not in self.game.legal_bids(seat):
            raise IllegalMove("This bid is not allowed now.")
        self.human_actions += 1
        events = self._apply_bid(seat, action)
        return self.state(events)

    def coinche_now(self):
        """Coinche hors de mon tour, sur l'annonce de West, avant que Nord parle."""
        game = self.game
        if not self.coinche_window or self.duo:
            raise IllegalMove("Too late to coinche: someone has spoken since.")
        self.coinche_window = False
        self.human_actions += 1
        game.current = HUMAN  # la coinche coupe la parole à Nord ; ensuite, West parle
        events = self._apply_bid(HUMAN, ("coinche",))
        return self.state(events)

    def continue_bidding(self):
        """Pas de coinche : Nord parle, les annonces continuent."""
        self.coinche_window = False
        return self.state([])

    def _opens_coinche_window(self, seat, action):
        """West vient d'annoncer juste après moi : je peux le coincher avant que Nord parle."""
        game = self.game
        return (not self.duo and seat == (HUMAN + 1) % 4 and action[0] == "bid" and game.phase == "bidding"
                and game.contract["mult"] == 1 and team_of(game.contract["seat"]) != team_of(HUMAN)
                and game.current != HUMAN)

    def play_human(self, card_id, seat=None):
        seat = self.ctx[0] if seat is None else seat
        card = INDEX_CARD.get(int(card_id))
        if self.waiting or seat not in self.humans or self.game.current != seat or card not in self.game.legal_cards(seat):
            raise IllegalMove("This card is not allowed (follow suit; trump if your partner is not winning; "
                              "overtrump if you can).")
        self.human_actions += 1
        events = self._apply_card(seat, card)
        return self.state(events)

    def next_deal(self):
        if self.duo and (self.waiting or self.game.phase != "done"):
            return self.state([])  # mon partenaire a déjà lancé la donne suivante
        if self.game.phase != "done" or self.game.game_over:
            raise IllegalMove("The current deal is not finished.")
        self.game.new_deal()
        self._reset_deal()
        return self.state([self._deal_event()])

    def set_reveal(self, on):
        if (self.study or self.duo) and on:
            raise IllegalMove("The other hands stay hidden in this study.")
        self.reveal = bool(on)
        self.revealed = self.revealed or self.reveal
        return self.state([])

    # ---------- enregistrement ----------
    def _record(self, record):
        if self.log is not None and self.configured and not self.waiting:
            self.log.write(dict(record, game_id=self.game_id, player=self.name, partner=self.partner,
                                humans=len(self.humans), players={SEAT_KEYS[s]: n for s, n in self.humans.items()},
                                opponents=self.opponents,
                                search=SEARCH_SAMPLES if self.opponents == "ai_search" else 0,
                                model=self.model if self.opponents.startswith("ai") else None,
                                study=self.study, time=time.time()))

    def _record_deal(self):
        """Donne finie (ou redistribuée) : mains, annonces, plis et résultat."""
        game = self.game
        label = lambda c: card_json(c)["label"]
        record = {"type": "deal", "deal": game.deal_no, "dealer": SEAT_KEYS[game.dealer],
                  "redeal": game.phase == "redeal",
                  "hands": {SEAT_KEYS[s]: [label(c) for c in game.dealt[s]] for s in range(4)},
                  "bids": [{"seat": SEAT_KEYS[s], "label": bid_label(a)} for s, a in game.bids],
                  "revealed": self.revealed}
        if game.phase == "done":
            r = game.result
            c = r["contract"]
            record.update({
                "contract": {"seat": SEAT_KEYS[c["seat"]], "team": TEAM_KEYS[team_of(c["seat"])],
                             "value": "capot" if c["value"] == CAPOT else c["value"],
                             "suit": SUIT_INFO[c["suit"]][1], "mult": c["mult"]},
                "tricks": [{"cards": [[SEAT_KEYS[s], label(card)] for s, card in trick], "winner": SEAT_KEYS[w]}
                           for trick, w in game.tricks],
                "made": r["made"],
                "scores": dict(zip(TEAM_KEYS, r["scores"])),
                "trick_points": dict(zip(TEAM_KEYS, game.trick_points)),
                "tricks_won": dict(zip(TEAM_KEYS, r["tricks_won"])),
                "belote_team": TEAM_KEYS[r["belote_team"]] if r["belote_team"] is not None else None,
                "capot_team": TEAM_KEYS[r["capot_team"]] if r.get("capot_team") is not None else None,
                "totals": dict(zip(TEAM_KEYS, game.totals)),
            })
        self._record(record)

    def _record_game(self, status):
        """status : "finished" ou "abandoned" (nouvelle partie lancée avant la fin)."""
        totals = self.game.totals
        winner = None
        if status == "finished" and totals[0] != totals[1]:
            winner = TEAM_KEYS[0] if totals[0] > totals[1] else TEAM_KEYS[1]
        self._record({"type": "game", "status": status, "totals": dict(zip(TEAM_KEYS, totals)), "winner": winner,
                      "deals": len(self.game.history), "target": self.target, "revealed": self.revealed,
                      "started": self.started_at, "human_actions": self.human_actions})

    # ---------- déroulement ----------
    def _pending(self):
        """Un robot (ou l'IA) doit-il jouer avant le prochain coup humain ? Le navigateur appelle alors
        step() : un coup à la fois, pour l'afficher dès qu'il est calculé."""
        game = self.game
        if self.waiting:
            return False
        if game.phase == "redeal":
            return True
        if game.phase == "bidding" and not self.coinche_window and self._bot_volley() is not None:
            return True
        return game.phase in ("bidding", "play") and game.current not in self.humans and not self.coinche_window

    def _bot_step(self):
        """Un seul coup de robot (ou une redistribution) : ses événements, [] s'il n'y a rien à jouer."""
        game = self.game
        if not self._pending():
            return []
        if game.phase == "redeal":
            self._record_deal()
            game.new_deal()
            self._reset_deal()
            return [{"type": "message", "text": "Everybody passed: the cards are redealt (next dealer)."},
                    self._deal_event()]
        if game.phase == "bidding" and not self.coinche_window:
            seat = self._bot_volley()
            if seat is not None:
                return self._apply_bid(seat, ("coinche",), volley=True)
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
            events = self._apply_bid(seat, move, confidence)
            if self._opens_coinche_window(seat, move):
                self.coinche_window = True
            return events
        return self._apply_card(seat, move, confidence)

    def _run_bots(self):
        """Tous les coups des robots jusqu'au prochain coup humain (scripts et tests)."""
        events = []
        while self._pending():
            events += self._bot_step()
        return events

    def step(self):
        """Le coup suivant d'un robot ou de l'IA (le navigateur enchaîne les appels tant que pending)."""
        return self.state(self._bot_step())

    def _bot_volley(self):
        """Un robot adverse du contrat qui n'a pas la parole coinche à la volée (AsR, Papi Robert)."""
        for seat in self.game.volley_seats():
            player = self.players.get(seat)
            if hasattr(player, "volley_coinche") and player.volley_coinche(self.game, seat):
                return seat
        return None

    def _apply_bid(self, seat, action, confidence=None, volley=False):
        game = self.game
        if volley:
            game.coinche_out_of_turn(seat)
        else:
            game.bid(seat, action)
        event = {"type": "bid", "seat": SEAT_KEYS[seat], "label": bid_label(action),
                 "text": f"{self.label(seat)}: {bid_label(action)}" + (" (out of turn)" if volley else "")}
        if confidence is not None:
            event["confidence"] = round(100 * confidence)
            event["text"] += f" (confidence {event['confidence']}%)"
        events = [event]
        if game.phase == "play":
            self.order = {h: suit_order(game.hands[h], game.trump) for h in self.humans}
            event["hands"] = {h: [card_json(c, game.trump) for c in sort_by_order(game.hands[h], self.order[h], game.trump)]
                              for h in self.humans}
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
                self._record_deal()
                if game.game_over:
                    self._record_game("finished")
        return events

    def _deal_event(self):
        game = self.game
        first = (game.dealer + 1) % 4
        return {"type": "message", "deal": True,
                "text": f"Deal {game.deal_no}: {self.label(game.dealer)} deal{self._s(game.dealer)}, "
                        f"{self.label(first)} speak{self._s(first)} first.",
                "hands": {h: [card_json(c) for c in sort_by_order(game.hands[h], self.order[h], None)] for h in self.humans}}

    def _result_text(self):
        r = self.game.result
        c = r["contract"]
        teams = self.team_names()
        verdict = "made" if r["made"] else "failed"
        return (f"Contract {contract_label(c['value'], c['suit'])} {verdict} by {teams[team_of(c['seat'])]}: "
                f"{teams[0]} +{r['scores'][0]}, {teams[1]} +{r['scores'][1]}.")

    # ---------- état ----------
    def _bid_options(self, viewer):
        game = self.game
        if game.phase != "bidding" or game.current != viewer or self.waiting:
            return None
        legal = game.legal_bids(viewer)
        values = sorted({a[1] for a in legal if a[0] == "bid"})
        return {"values": [{"value": v, "label": "Capot" if v == CAPOT else str(v)} for v in values],
                "suits": [suit_json(s) for s in SUITS],
                "coinche": ("coinche",) in legal, "surcoinche": ("surcoinche",) in legal}

    @staticmethod
    def _rot(key, viewer):
        """Place vue depuis viewer : sa propre place est toujours en bas ("south")."""
        return SEAT_KEYS[(SEAT_KEYS.index(key) - viewer) % 4] if key in SEAT_KEYS else key

    def _view_event(self, event, viewer):
        ev = dict(event)
        for k in ("seat", "winner"):
            if k in ev:
                ev[k] = self._rot(ev[k], viewer)
        hands = ev.pop("hands", None)
        if hands is not None and viewer in hands:
            ev["hand"] = hands[viewer]
        return ev

    def state(self, events, viewer=None, since=None):
        """État de la table vu depuis la place viewer. Les nouveaux événements sont ajoutés au fil
        (self.feed) ; avec since, on renvoie tous les événements du fil à partir de ce numéro (ceux
        de mon partenaire compris), sinon seulement events."""
        if viewer is None:
            viewer, ctx_since = self.ctx
            since = ctx_since if since is None else since
        if self.duo:
            self.feed.extend(events)
        if since is not None and self.duo:
            events = self.feed[max(0, int(since)):]
        rot = lambda key: self._rot(key, viewer)
        game = self.game
        trump = game.trump
        teams = self.team_names()
        my_turn = game.phase == "play" and game.current == viewer and not self.waiting
        legal = {CARD_INDEX[c] for c in game.legal_cards(viewer)} if my_turn else set()
        hands = {}
        for seat in range(4):
            mine = seat == viewer
            order = self.order.get(seat) if mine else None
            cards = sort_by_order(game.hands[seat], order, trump) if order else sort_hand(game.hands[seat], trump)
            if mine or self.reveal:
                hands[rot(SEAT_KEYS[seat])] = [dict(card_json(c, trump), legal=CARD_INDEX[c] in legal) for c in cards]
            else:
                hands[rot(SEAT_KEYS[seat])] = [{"hidden": True} for _ in cards]
        c = game.contract
        contract = None
        if c is not None:
            contract = {"label": contract_label(c["value"], c["suit"]), "by": rot(SEAT_KEYS[c["seat"]]),
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
            entry = {"seat": rot(SEAT_KEYS[s]), "card": card_json(card, trump)}
            if CARD_INDEX[card] in self.calls:
                entry["announce"] = self.calls[CARD_INDEX[card]]
            if CARD_INDEX[card] in self.confidence:
                entry["confidence"] = self.confidence[CARD_INDEX[card]]
            return entry

        last_trick = None
        if self.last_trick:
            last_trick = dict(self.last_trick, winner=rot(self.last_trick["winner"]),
                              cards=[dict(t, seat=rot(t["seat"])) for t in self.last_trick["cards"]])
        partner_label = BOT_LABELS[self.partner]
        return {
            "events": [self._view_event(e, viewer) for e in events],
            "seq": len(self.feed),
            "configured": self.configured,
            "duo": self.duo,
            "waiting": self.waiting,
            "invite": getattr(self, "invite", None) if self.waiting else None,
            "setup": {"name": self.humans.get(viewer, self.name), "partner": self.partner, "opponents": self.opponents,
                      "partnerLabel": partner_label, "opponentsLabel": BOT_LABELS[self.opponents]},
            "players": {"styles": [dict(PLAYER_INFO[k], key=k) for k in STYLES],
                        "opponents": [dict(PLAYER_INFO[k], key=k) for k in self.kinds()]},
            "names": {rot(SEAT_KEYS[s]): self.label(s) for s in range(4)},
            "phase": game.phase,
            "dealNo": game.deal_no,
            "dealer": rot(SEAT_KEYS[game.dealer]),
            "current": rot(SEAT_KEYS[game.current]) if game.phase in ("bidding", "play") else None,
            "hands": hands,
            "reveal": self.reveal,
            "study": self.study,
            "bids": [{"seat": rot(SEAT_KEYS[s]), "label": bid_label(a)} for s, a in game.bids],
            "bidOptions": self._bid_options(viewer),
            "contract": contract,
            "trump": suit_json(trump) if trump is not None else None,
            "trick": [trick_entry(s, card) for s, card in game.trick],
            "lastTrick": last_trick,
            "trickPoints": game.trick_points,
            "tricksWon": game.tricks_won,
            "pending": self._pending(),  # le navigateur appelle /api/step pour le coup suivant
            "yourTurn": my_turn,
            "yourBid": game.phase == "bidding" and game.current == viewer and not self.waiting,
            "coincheWindow": self.coinche_window and viewer == HUMAN,
            "teams": teams,
            "totals": game.totals,
            "target": game.target,
            "result": result,
            "gameOver": game.game_over,
            "history": [{"deal": h["deal"], "contract": contract_label(h["contract"]["value"], h["contract"]["suit"]),
                         "by": self.label(h["contract"]["seat"]), "mult": h["contract"]["mult"],
                         "made": h["made"], "scores": h["scores"]} for h in game.history],
            "rules": RULES,
            "bots": (f"2 players · {BOT_LABELS[self.opponents]} opponents" if self.duo
                     else f"{partner_label} partner · {BOT_LABELS[self.opponents]} opponents"),
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
