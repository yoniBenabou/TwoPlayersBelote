"""Coinche à 4 joueurs : moteur de règles (annonces, cartes jouables, plis, score).

Places : 0 = Sud, 1 = Est, 2 = Nord, 3 = Ouest. Le jeu tourne dans le sens
inverse des aiguilles d'une montre, comme en France (Sud, puis Est à sa
droite, Nord, Ouest). Équipes : Sud-Nord (0, 2) contre Est-Ouest (1, 3).

Règles retenues (cf. RULES, affichées aussi dans la page web) :
- 32 cartes, 8 par joueur ; le joueur après le donneur parle en premier et
  entame le premier pli ; le donneur change à chaque donne.
- Annonces : contrat de 80 à 160 (par 10) ou capot (250) avec une couleur
  d'atout, chaque annonce plus haute que la précédente ; un adversaire de
  l'équipe qui a le contrat peut coincher (×2), puis l'équipe du contrat peut
  surcoincher (×3). Après une coinche, on ne peut plus que surcoincher ou
  passer. Fin des annonces : 3 passes après la dernière annonce (ou
  surcoinche) ; 4 passes sans annonce : on redistribue.
- Jeu : fournir à la couleur demandée ; à l'atout, toujours monter si on peut
  (même sur son partenaire). Sans la couleur demandée : si le partenaire est
  maître du pli, carte libre ; sinon couper, en montant sur l'atout déjà posé
  si possible, sinon en mettant quand même un atout (sous-couper) ; sans
  atout, carte libre.
- Points : 152 dans les cartes + 10 de der = 162 ; capot (tous les plis) =
  250 au lieu de 162 ; belote-rebelote (Roi + Dame d'atout dans la même
  main) = 20, toujours marquée par l'équipe qui l'a.
- Contrat réussi si l'équipe qui prend fait au moins son contrat (belote
  comprise) ; capot : tous les plis.
- Barème (donné par Noa) :
    réussi, non coinché : attaque = contrat + ses points arrondis à la dizaine
                          (supérieure si l'unité >= 5) + 20 si belote ;
                          défense = ses points arrondis + 20 si belote ;
    chuté, non coinché  : défense = contrat + 160 + 20 par belote (la sienne et
                          celle de l'attaque) ; attaque 0 ;
    coinché (×2) ou surcoinché (×3) : contrat × 2 (ou × 3) + 160 pour
                          l'attaque si réussi, pour la défense si chuté ;
                          réussi : +20 si l'attaque a la belote et qu'elle
                          n'a pas servi à réussir, +0 si elle a servi ;
                          chuté : +20 pour la défense si la belote était à
                          l'attaque ; la belote de la défense ne compte pas.
- Partie en 1 500 points (target).
"""
import random

from ..core.cards import Card, Rank, Suit, build_deck

SEAT_NAMES = ("South", "East", "North", "West")
SUITS = list(Suit)
CONTRACTS = list(range(80, 170, 10)) + [250]  # 250 = capot
CAPOT = 250
DEFAULT_TARGET = 1500

RULES = [
    "4 players, 2 teams: South-North against East-West. 32 cards, 8 each. Play goes counter-clockwise "
    "(South, East, North, West).",
    "The player after the dealer speaks first and leads the first trick. The dealer changes every deal.",
    "Bidding: a contract from 80 to 160 (in steps of 10) or capot (250, all the tricks), with a trump suit. "
    "Each bid must be higher than the previous one.",
    "An opponent of the bidding team can coinche (×2); the bidding team can then surcoinche (×3). After a "
    "coinche, players can only surcoinche or pass.",
    "Bidding ends after 3 passes following the last bid (or right after a surcoinche). If all 4 players pass "
    "without bidding, the cards are redealt.",
    "Follow suit if you can. When trump is led, you must play a higher trump if you can, even over your partner.",
    "If you cannot follow suit: when your partner is winning the trick, you may play any card. Otherwise you "
    "must trump, higher than a trump already played if you can, or a lower trump if you cannot (undertrump). "
    "With no trump, any card.",
    "Trump order: J, 9, A, 10, K, Q, 8, 7 (J 20, 9 14, A 11, 10 10, K 4, Q 3). Other suits: A, 10, K, Q, J, 9, 8, 7 "
    "(A 11, 10 10, K 4, Q 3, J 2).",
    "Each deal holds 162 points (152 in the cards + 10 for the last trick). A team that takes every trick (capot) "
    "scores 250 instead of 162. King + Queen of trump in the same hand: belote-rebelote, worth 20.",
    "The contract is made if the bidding team scores at least its contract (belote included). Capot: all 8 tricks.",
    "Made: the bidding team scores contract + its points + 20 for its belote; the defence scores its points "
    "+ 20 for its belote. Points are rounded to the nearest 10, up from 5 (84 gives 80, 85 gives 90).",
    "Failed: the defence scores contract + 160 + 20 for each belote (its own and the bidding team's); "
    "the bidding team scores 0.",
    "Coinched (×2) or surcoinched (×3): contract × 2 (or × 3) + 160, for the bidding team if made, for the "
    "defence if failed; the other team scores 0. Only the bidding team's belote counts: if made, +20 for the "
    "bidding team only if the belote was not needed to make the contract; if failed, +20 for the defence.",
    "The first team to reach 1,500 points wins the game.",
]


def team_of(seat):
    return seat % 2


def partner_of(seat):
    return (seat + 2) % 4


def trick_winner(trick, trump):
    """trick : liste de (place, carte) dans l'ordre joué. Retourne l'index gagnant dans trick."""
    led_suit = trick[0][1].suit
    best = 0
    for i in range(1, len(trick)):
        card, top = trick[i][1], trick[best][1]
        if card.suit == top.suit:
            if card.strength(trump) > top.strength(trump):
                best = i
        elif card.suit == trump and top.suit != trump:
            best = i
        # sinon (défausse, ou couleur demandée sous un atout) : ne prend pas
    assert trick[best][1].suit in (led_suit, trump)
    return best


def legal_cards(hand, trick, trump, seat):
    """Cartes jouables par seat (main hand) dans le pli en cours trick."""
    if not trick:
        return list(hand)
    led_suit = trick[0][1].suit
    same = [c for c in hand if c.suit == led_suit]
    trumps_in_trick = [c for _, c in trick if c.suit == trump]
    best_trump = max(trumps_in_trick, key=lambda c: c.strength(trump)) if trumps_in_trick else None

    if same:
        if led_suit == trump:
            higher = [c for c in same if c.strength(trump) > best_trump.strength(trump)]
            return higher or same  # à l'atout : toujours monter si possible
        return same

    winner_seat = trick[trick_winner(trick, trump)][0]
    if winner_seat == partner_of(seat):
        return list(hand)  # partenaire maître : carte libre
    my_trumps = [c for c in hand if c.suit == trump]
    if not my_trumps:
        return list(hand)
    if best_trump is not None:
        higher = [c for c in my_trumps if c.strength(trump) > best_trump.strength(trump)]
        return higher or my_trumps  # monter sur l'atout, sinon sous-couper
    return my_trumps


def has_belote(hand, trump):
    ranks = {c.rank for c in hand if c.suit == trump}
    return Rank.KING in ranks and Rank.QUEEN in ranks


def round_points(points):
    """Arrondi à la dizaine, supérieure si l'unité vaut 5 ou plus (87 -> 90, 84 -> 80)."""
    return (points + 5) // 10 * 10


def score_deal(contract, tricks_won, belote_team, trick_points):
    """Barème de la table (cf. RULES). contract : dict(seat, value, suit, mult) ;
    tricks_won[t] = plis de l'équipe t ; belote_team : équipe qui a la
    belote-rebelote ou None ; trick_points[t] : points des plis (cartes + 10 de
    der). Retourne (scores par équipe, contrat réussi ?, détail)."""
    att = team_of(contract["seat"])
    dfn = 1 - att
    value, mult = contract["value"], contract["mult"]
    points = list(trick_points)
    capot_team = next((t for t in (0, 1) if tricks_won[t] == 8), None)
    if capot_team is not None:
        points[capot_team], points[1 - capot_team] = CAPOT, 0
    belote = [20 if belote_team == t else 0 for t in (0, 1)]
    total = [points[t] + belote[t] for t in (0, 1)]

    def reaches(att_total):
        if value == CAPOT:
            return tricks_won[att] == 8
        return att_total >= value

    made = reaches(total[att])
    belote_needed = made and belote[att] > 0 and not reaches(points[att])
    scores = [0, 0]
    if mult == 1:
        if made:
            scores[att] = value + round_points(points[att]) + belote[att]
            scores[dfn] = round_points(points[dfn]) + belote[dfn]
        else:
            scores[dfn] = value + 160 + belote[att] + belote[dfn]
    else:
        base = value * mult + 160
        # coinché : seule la belote de l'attaque compte
        if made:
            scores[att] = base + (0 if belote_needed else belote[att])
        else:
            scores[dfn] = base + belote[att]
    detail = {"points": points, "belote": belote, "total": total, "capot_team": capot_team,
              "belote_needed": belote_needed}
    return scores, made, detail


class CoincheGame:
    """Une partie de Coinche, donne par donne. Les joueurs agissent quand
    current est leur place : bid(seat, action) pendant les annonces,
    play(seat, card) pendant le jeu.

    Annonces (action) : ("pass",), ("bid", valeur, couleur), ("coinche",), ("surcoinche",)."""

    def __init__(self, target=DEFAULT_TARGET, rng=None):
        self.target = target
        self.rng = rng or random.Random()
        self.totals = [0, 0]
        self.dealer = self.rng.randrange(4)
        self.deal_no = 0
        self.history = []  # une entrée par donne jouée
        self.game_over = False
        self.new_deal()

    # ---------- donne ----------
    def new_deal(self):
        """Nouvelle donne ; le donneur avance d'une place (aussi après 4 passes)."""
        self.dealer = (self.dealer + 1) % 4
        self.deal_no += 1
        deck = build_deck()
        self.rng.shuffle(deck)
        self.hands = [deck[8 * i: 8 * i + 8] for i in range(4)]
        self.dealt = [list(h) for h in self.hands]
        self.phase = "bidding"
        self.current = (self.dealer + 1) % 4
        self.bids = []  # (place, action)
        self.contract = None  # dict(seat, value, suit, mult)
        self.passes = 0
        self.coinche_seat = None
        self.trump = None
        self.trick = []
        self.tricks = []  # [(pli, gagnant)]
        self.trick_points = [0, 0]
        self.tricks_won = [0, 0]
        self.played = [[] for _ in range(4)]
        self.result = None

    # ---------- annonces ----------
    def legal_bids(self, seat):
        if self.phase != "bidding" or seat != self.current:
            return []
        actions = [("pass",)]
        c = self.contract
        if c is None or c["mult"] == 1:
            floor = c["value"] if c else 0
            actions += [("bid", v, s) for v in CONTRACTS if v > floor for s in SUITS]
        if c is not None and c["mult"] == 1 and team_of(seat) != team_of(c["seat"]):
            actions.append(("coinche",))
        if c is not None and c["mult"] == 2 and team_of(seat) == team_of(c["seat"]):
            actions.append(("surcoinche",))
        return actions

    def bid(self, seat, action):
        action = tuple(action)
        if action not in self.legal_bids(seat):
            raise ValueError(f"Bid not allowed for {SEAT_NAMES[seat]}: {action}")
        self.bids.append((seat, action))
        kind = action[0]
        if kind == "pass":
            self.passes += 1
            if self.contract is None and self.passes == 4:
                self.result = {"redeal": True}
                self.phase = "redeal"
                return
            if self.contract is not None and self.passes == 3:
                return self._start_play()
        elif kind == "bid":
            self.contract = {"seat": seat, "value": action[1], "suit": action[2], "mult": 1}
            self.passes = 0
        elif kind == "coinche":
            self.contract["mult"] = 2
            self.coinche_seat = seat
            self.passes = 0
        elif kind == "surcoinche":
            self.contract["mult"] = 3
            return self._start_play()
        self.current = (self.current + 1) % 4

    def _start_play(self):
        self.phase = "play"
        self.trump = self.contract["suit"]
        self.current = (self.dealer + 1) % 4
        self.belote_seat = next((s for s in range(4) if has_belote(self.hands[s], self.trump)), None)

    # ---------- jeu ----------
    def legal_cards(self, seat):
        if self.phase != "play" or seat != self.current:
            return []
        return legal_cards(self.hands[seat], self.trick, self.trump, seat)

    def belote_call(self, seat, card):
        """"Belote" ou "Rebelote" si cette carte est le Roi ou la Dame d'atout du détenteur de la belote."""
        if seat != self.belote_seat or card.suit != self.trump or card.rank not in (Rank.KING, Rank.QUEEN):
            return None
        other = Rank.QUEEN if card.rank == Rank.KING else Rank.KING
        return "Rebelote!" if Card(self.trump, other) in self.played[seat] else "Belote!"

    def play(self, seat, card):
        if card not in self.legal_cards(seat):
            raise ValueError(f"Card not allowed for {SEAT_NAMES[seat]}: {card}")
        self.hands[seat].remove(card)
        self.played[seat].append(card)
        self.trick.append((seat, card))
        if len(self.trick) < 4:
            self.current = (seat + 1) % 4
            return None
        winner = self.trick[trick_winner(self.trick, self.trump)][0]
        points = sum(c.points(self.trump) for _, c in self.trick) + (10 if len(self.tricks) == 7 else 0)
        self.trick_points[team_of(winner)] += points
        self.tricks_won[team_of(winner)] += 1
        self.tricks.append((self.trick, winner))
        done_trick = (self.trick, winner, points)
        self.trick = []
        self.current = winner
        if len(self.tricks) == 8:
            self._finish_deal()
        return done_trick

    def _finish_deal(self):
        belote_team = team_of(self.belote_seat) if self.belote_seat is not None else None
        scores, made, detail = score_deal(self.contract, self.tricks_won, belote_team, self.trick_points)
        for t in (0, 1):
            self.totals[t] += scores[t]
        self.phase = "done"
        self.result = {"redeal": False, "scores": scores, "made": made, "contract": dict(self.contract),
                       "tricks_won": list(self.tricks_won), "belote_team": belote_team, **detail}
        self.history.append({"deal": self.deal_no, **self.result})
        if max(self.totals) >= self.target and self.totals[0] != self.totals[1]:
            self.game_over = True
