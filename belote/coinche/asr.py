"""Robot "AsR" pour la Coinche à 4 : conventions du document "Belote —
conventions d'annonces et stratégie de jeu" (version consolidée).

Familles : rouge = cœur et carreau, noir = pique et trèfle. La "couleur sœur"
d'une couleur est l'autre couleur de sa famille ; la "famille opposée" à
l'atout, ce sont les deux couleurs de l'autre famille. Majeures = Valet et 9
d'atout.

Ouvertures (couleur choisie : la plus forte structure d'atout, puis la plus
forte couleur) :
- maîtrise forte (Valet + 9 et 5 atouts, ou Valet + 9 + As et 4 atouts) : on
  annonce directement sa force, sous forme de demande : 110 (As de la famille
  opposée) s'il en manque un, sinon 120 (As de la couleur sœur), sinon 130
  (10 de la famille opposée), sinon 140 (10 de la couleur sœur) ;
- avec au moins deux As (atout compris) : 80, pour les signaler, même sans
  atout ; on surenchérira à 100 avec une vraie main de 100 ;
- maîtrise (Valet + 9 + As, ou Valet + 9 quatrièmes) : 100 ;
- Valet au moins troisième ou 9 au moins quatrième, avec au moins un As
  (d'atout ou à côté) : 90 ; jamais 90 sans As.
Réponses (une fois, puis relances prévues par le document) :
- sur 80, même couleur : 90 avec le Valet ou le 9 (et au moins un As),
  100 avec les deux, +10 par As hors atout ; autre couleur : 100 avec une
  maîtrise, 110 avec une maîtrise forte. L'ouvreur à 80 : sur 90 dans sa
  couleur, s'il a le complément, 100, +10 si ses deux As (déjà annoncés
  par le 80) sont hors atout, +10 par As hors atout en plus ; sur 100 dans
  une autre couleur, +10 avec deux As hors de cet atout, +10 par As en plus ;
  sur 110 dans une autre couleur, +10 par As ; sans réponse, 100 s'il a une
  vraie main de 100 ;
- sur 90 : +10 pour le complément (le Valet, ou le 9 au moins second) et +10
  par As ; rien sans complément ; le 9 sec ne se signale pas au premier tour,
  au second tour seulement (+10) avec un As à côté ou si l'équipe est très en
  retard (500 points) ;
- sur 100 : +10 par As hors atout ; capot avec quatre plis maîtres ;
- sur 110 : +10 par As de la famille opposée ; 110 -> 120 -> 130 : l'ouvreur
  qui a l'autre As noir dit 130, le partenaire ajoute +10 par pli
  supplémentaire dans la famille opposée (sans recompter son As) ;
- sur 120 : +10 avec l'As de la couleur sœur ; sur 130 (demande initiale) :
  +10 par 10 de la famille opposée ; sur 140 : +10 avec le 10 sœur.
Capot de l'ouvreur : après 100 et +30 avec 5 atouts ; après les réponses sur
110, si ses plis attendus (atouts, As, plis signalés) font 8.
Collage : sur un 90 adverse, une main de 90 dit 100 (le partenaire la lit
comme un 90 et ne répond que le complément) ; une main de 100 saute à 110 (le
partenaire reste prudent : il passe) ; sur un 100 adverse, une vraie main de
100 dit 110 (lue comme un 100).
Coinche : même règle que CoincheBot. Pas de surcoinche.

Jeu :
- contrée (coinchée ou surcoinchée), l'équipe qui a pris n'entame pas atout ;
- sinon, l'équipe qui a pris joue atout tant que les adversaires peuvent en avoir, en
  séparant le Valet et le 9 de l'équipe : avec le 9 sans le Valet, petit atout
  d'abord (le Valet du partenaire prend, ou celui de l'adversaire tombe) ; avec
  le Valet quand le partenaire a montré le 9, le Valet puis un petit atout ;
  on garde son dernier atout s'il n'en reste qu'un dehors, plus fort ;
- signal de belote : celui qui a la belote dans l'équipe qui a pris joue le Roi
  en premier s'il a un nombre pair d'atouts (carte jouée comprise), la Dame
  s'il est impair ; le partenaire en déduit, quand c'est sûr, que les
  adversaires n'ont plus d'atout ;
- appels : quand le partenaire joue atout et que je n'en ai plus, je défausse
  pour demander la couleur de mon As : une carte de cette couleur si elle est
  de la famille de l'atout (appel direct), sinon une carte de sa couleur sœur
  (appel indirect) ; jeter l'As lui-même annonce la longue maîtresse (au moins
  As-10-Roi) ; le partenaire rejoue la couleur demandée (petite carte) avant
  d'encaisser ses As ; seulement dans l'équipe qui a pris ;
- ensuite : les cartes maîtresses (As, 10, Roi...), le Roi d'un Roi-10 quand
  l'As n'est pas tombé, puis la couleur la plus longue ;
- défense (pas d'appels en défense) : contre 140 ou plus, d'abord les cartes
  maîtresses ; sinon faire couper le preneur en jouant notre couleur la plus
  longue (celle qu'il n'a plus s'il l'a déjà montré, même au prix d'un As ou
  d'un 10) ; pas d'entame atout sauf s'il ne reste que ça ;
- on ne défausse jamais un As sans le 10 et le Roi derrière, sauf si on n'a pas
  le choix ;
- partenaire maître : on ne donne pas un 10 accompagné (il peut faire un pli),
  un 10 sec oui ; en troisième, avec l'As et une plus petite carte qui prend,
  on joue l'As si le 10 peut être derrière (on capture un 10 sec).
Le reste du jeu est celui de CoincheBot.
"""
from ..core.cards import Card, Rank, Suit
from .bots import CoincheBot, wants_coinche
from .engine import CAPOT, SUITS, partner_of, team_of, trick_winner

RED = {Suit.COEUR, Suit.CARREAU}
SISTER = {Suit.PIQUE: Suit.TREFLE, Suit.TREFLE: Suit.PIQUE, Suit.COEUR: Suit.CARREAU, Suit.CARREAU: Suit.COEUR}
MAX_BID = 160
BEHIND = 500  # "très en retard au score"
ORDER = [Rank.ACE, Rank.TEN, Rank.KING, Rank.QUEEN, Rank.JACK, Rank.NINE, Rank.EIGHT, Rank.SEVEN]  # hors atout


def opposite(suit):
    """Les deux couleurs de la famille opposée."""
    return [s for s in SUITS if (s in RED) != (suit in RED)]


def ranks_in(hand, suit):
    return {c.rank for c in hand if c.suit == suit}


def has(hand, suit, rank):
    return any(c.suit == suit and c.rank == rank for c in hand)


def all_aces(hand):
    return sum(c.rank == Rank.ACE for c in hand)


def side_aces(hand, trump):
    return sum(c.rank == Rank.ACE and c.suit != trump for c in hand)


def trump_type(hand, suit):
    """Structure d'atout : "strong", "100", "90" ou None (90 exige un As, d'atout ou à côté)."""
    r = ranks_in(hand, suit)
    n = len(r)
    if Rank.JACK in r and Rank.NINE in r:
        if n >= 5 or (n >= 4 and Rank.ACE in r):
            return "strong"
        if Rank.ACE in r or n >= 4:
            return "100"
    if ((Rank.JACK in r and n >= 3) or (Rank.NINE in r and n >= 4)) and all_aces(hand) >= 1:
        return "90"
    return None


TYPE_RANK = {"strong": 3, "100": 2, "90": 1, None: 0}
TYPE_VALUE = {"100": 100, "90": 90}


def strength_score(hand, suit):
    belote = has(hand, suit, Rank.KING) and has(hand, suit, Rank.QUEEN)
    return sum(c.points(suit) for c in hand if c.suit == suit) + 20 * belote + 11 * side_aces(hand, suit)


def ask_value(hand, suit):
    """Demande d'une maîtrise forte : 110, 120, 130 ou 140 selon ce qui manque."""
    opp = opposite(suit)
    if not all(has(hand, s, Rank.ACE) for s in opp):
        return 110
    if not has(hand, SISTER[suit], Rank.ACE):
        return 120
    if not all(has(hand, s, Rank.TEN) for s in opp):
        return 130
    return 140


def best_suit(hand):
    """(type, couleur) : la meilleure structure d'atout, puis la couleur la plus forte."""
    return max(((trump_type(hand, s), s) for s in SUITS),
               key=lambda o: (TYPE_RANK[o[0]], strength_score(hand, o[1])))


def natural_opening(hand):
    """(valeur, couleur, type) de l'ouverture AsR, ou None."""
    kind, suit = best_suit(hand)
    if kind == "strong":
        return ask_value(hand, suit), suit, kind
    if all_aces(hand) >= 2:
        return 80, suit, kind
    if kind in TYPE_VALUE:
        return TYPE_VALUE[kind], suit, kind
    return None


def top_tricks(hand, suit, above=()):
    """Plis maîtres d'une couleur hors atout : les cartes qui se suivent depuis le haut (les cartes de
    above, tenues par le partenaire, comptent comme déjà là mais ne sont pas des plis pour moi)."""
    mine = ranks_in(hand, suit)
    count = 0
    for r in ORDER:
        if r in above:
            continue
        if r not in mine:
            break
        count += 1
    return count


def master_tricks(hand, trump):
    return sum(top_tricks(hand, s) for s in SUITS if s != trump)


class AsRBot(CoincheBot):
    name = "AsR"

    # ================= annonces =================
    def bid(self, game, seat):
        legal = game.legal_bids(seat)
        hand = game.hands[seat]
        if ("surcoinche",) in legal:
            return ("pass",)
        if ("coinche",) in legal and wants_coinche(hand, game.contract):
            return ("coinche",)
        partner = partner_of(seat)
        mine = [(i, a) for i, (s, a) in enumerate(game.bids) if s == seat and a[0] == "bid"]
        theirs = [(i, a) for i, (s, a) in enumerate(game.bids) if s == partner and a[0] == "bid"]
        if not mine:
            action = self._respond(game, seat, theirs[-1]) if theirs else self._open(game, seat)
        else:
            action = self._rebid(game, seat, mine, theirs)
        if action is not None and action[0] == "bid" and action[1] != CAPOT:
            action = ("bid", min(action[1], MAX_BID), action[2])
        return action if action in legal else ("pass",)

    @staticmethod
    def _opponent_value(game, seat, before=None):
        """Valeur du contrat adverse en cours (avant l'annonce d'indice before), ou None."""
        bids = game.bids if before is None else game.bids[:before]
        last = next(((s, a) for s, a in reversed(bids) if a[0] == "bid"), None)
        if last is None or team_of(last[0]) == team_of(seat):
            return None
        return last[1][1]

    def _open(self, game, seat):
        hand = game.hands[seat]
        opening = natural_opening(hand)
        if opening is None:
            return None
        value, suit, kind = opening
        opp = self._opponent_value(game, seat)
        if opp is None:
            return ("bid", value, suit)
        # un adversaire a parlé : collage et sauts
        if kind == "90" and opp == 90:
            return ("bid", 100, suit)
        if kind in ("100", "strong") and opp in (90, 100):
            return ("bid", 110, suit)
        real = ask_value(hand, suit) if kind == "strong" else TYPE_VALUE.get(kind)
        return ("bid", real, suit) if real is not None and real > opp else None

    def _respond(self, game, seat, partner_bid):
        """Première réponse à une annonce du partenaire (je n'ai pas encore annoncé)."""
        hand = game.hands[seat]
        index, (_k, value, suit) = partner_bid
        over = self._opponent_value(game, seat, before=index)
        passed_since = any(s == seat for s, _a in game.bids[index + 1:])
        r = ranks_in(hand, suit)
        if over == 90 and value == 100:  # collage : lu comme un 90, on ne répond que le complément
            return ("bid", 110, suit) if self._complement(r) else None
        if over == 90 and value == 110:  # saut : on reste prudent
            return None
        level = 100 if (over == 100 and value == 110) else value
        if level == 80:
            return self._answer_80(hand, suit)
        if level == 90:
            if self._complement(r):
                return ("bid", value + 10 + 10 * all_aces(hand), suit)
            if r == {Rank.NINE} and passed_since and (side_aces(hand, suit) >= 1 or self._behind(game, seat)):
                return ("bid", game.contract["value"] + 10, suit)  # 9 sec signalé au second tour
            return None
        if level == 100:
            if master_tricks(hand, suit) >= 4:
                return ("bid", CAPOT, suit)
            inc = 10 * side_aces(hand, suit)
        elif level == 110:
            inc = 10 * sum(has(hand, s, Rank.ACE) for s in opposite(suit))
        elif level == 120:
            inc = 10 * has(hand, SISTER[suit], Rank.ACE)
        elif level == 130:
            inc = 10 * sum(has(hand, s, Rank.TEN) for s in opposite(suit))
        elif level == 140:
            inc = 10 * has(hand, SISTER[suit], Rank.TEN)
        else:
            inc = 0
        return ("bid", value + inc, suit) if inc else None

    @staticmethod
    def _complement(ranks):
        """Complément d'un 90 : le Valet, ou le 9 au moins second."""
        return Rank.JACK in ranks or (Rank.NINE in ranks and len(ranks) >= 2)

    @staticmethod
    def _behind(game, seat):
        t = team_of(seat)
        return game.totals[1 - t] - game.totals[t] >= BEHIND

    @staticmethod
    def _answer_80(hand, suit):
        r = ranks_in(hand, suit)
        if Rank.JACK in r and Rank.NINE in r:
            return ("bid", 100 + 10 * side_aces(hand, suit), suit)
        kind, other = max(((trump_type(hand, s), s) for s in SUITS if s != suit),
                          key=lambda o: (TYPE_RANK[o[0]], strength_score(hand, o[1])))
        if kind == "strong":
            return ("bid", 110, other)
        if kind == "100":
            return ("bid", 100, other)
        if (Rank.JACK in r or Rank.NINE in r) and all_aces(hand) >= 1:
            return ("bid", 90, suit)
        return None

    def _rebid(self, game, seat, mine, theirs):
        hand = game.hands[seat]
        first_i, (_k, first_value, first_suit) = mine[0]
        last_i = mine[-1][0]
        answer = next(((i, a) for i, a in reversed(theirs) if i > last_i), None)
        if answer is None:
            # pas de réponse : l'ouvreur à 80 surenchérit avec une vraie main de 100
            if len(mine) == 1 and first_value == 80:
                kind, suit = best_suit(hand)
                if kind in ("100", "strong"):
                    opp = self._opponent_value(game, seat)
                    return ("bid", 110 if opp == 100 else 100, suit)
            return None
        _i, (_k, value, suit) = answer
        partner_opened = bool(theirs) and theirs[0][0] < first_i
        if partner_opened:
            # je suis le répondant : séquence 110 -> 120 -> 130
            p_first = theirs[0][1]
            if p_first[1] == 110 and len(mine) == 1 and mine[0][1][1] == 120 and value == 130:
                ace_suit = next((s for s in opposite(suit) if has(hand, s, Rank.ACE)), None)
                if ace_suit is None:  # mon 120 ne signalait pas un As de la famille opposée
                    return None
                other = next(s for s in opposite(suit) if s != ace_suit)
                extra = (top_tricks(hand, ace_suit) - 1) + top_tricks(hand, other, above={Rank.ACE})
                return ("bid", 130 + 10 * extra, suit) if extra > 0 else None
            return None
        if len(mine) >= 2 and not (first_value == 110 and len(mine) == 2 and mine[1][1][1] == 130):
            return None
        n = len(ranks_in(hand, suit))
        if first_value == 80:
            if suit == first_suit and value == 90 and self._complement_of_90(ranks_in(hand, suit)):
                # mes deux As sont déjà annoncés par le 80 : +10 s'ils sont hors atout, +10 par As hors atout en plus
                return ("bid", 100 + 10 * max(0, side_aces(hand, suit) - 1), suit)
            if suit != first_suit and value == 100:
                k = side_aces(hand, suit)
                return ("bid", 100 + 10 * (k - 1), suit) if k >= 2 else None
            if suit != first_suit and value == 110:
                k = side_aces(hand, suit)
                return ("bid", 110 + 10 * k, suit) if k else None
            if suit != first_suit and value == 90:
                r = ranks_in(hand, suit)
                return ("bid", 100 + 10 * all_aces(hand), suit) if self._complement(r) else None
            return None
        if suit != first_suit:
            return None
        if first_value == 100 and value - first_value >= 30 and n >= 5:
            return ("bid", CAPOT, suit)
        if first_value == 110:
            opp = opposite(suit)
            if value == 120 and len(mine) == 1:
                missing = [s for s in opp if not has(hand, s, Rank.ACE)]
                if len(missing) == 1:
                    return ("bid", 130, suit)  # j'ai l'autre As de la famille opposée
                return None
            partner_aces = 2 if value == 130 and len(mine) == 1 else 1
            extra = (value - 130) // 10 if len(mine) == 2 else 0
            held = {s for s in opp if has(hand, s, Rank.ACE)}
            expected = n + side_aces(hand, suit) + partner_aces + extra
            if len(mine) == 1:  # les deux As chez le partenaire : mes cartes derrière deviennent maîtresses
                expected += sum(top_tricks(hand, s, above={Rank.ACE}) for s in opp if s not in held)
            if expected >= 8:
                return ("bid", CAPOT, suit)
        return None

    @staticmethod
    def _complement_of_90(ranks):
        """L'ouvreur à 80 qui a le complément du Valet ou du 9 annoncé par le partenaire."""
        return (Rank.JACK in ranks) != (Rank.NINE in ranks)

    # ================= jeu de la carte =================
    def play(self, game, seat):
        legal = game.legal_cards(seat)
        trick, trump = game.trick, game.trump
        hand = game.hands[seat]
        if not trick:
            card = self.lead(game, seat, legal)
        else:
            card = self._follow(game, seat, legal)
        return self._belote_signal(game, seat, legal, card)

    def _follow(self, game, seat, legal):
        trick, trump = game.trick, game.trump
        hand = game.hands[seat]
        led = trick[0][1].suit
        partner = partner_of(seat)
        legal = self._keep_aces(game, seat, legal)
        # appel par défausse quand le partenaire joue atout et que je n'en ai plus
        attacking = team_of(game.contract["seat"]) == team_of(seat)
        if attacking and trick[0][0] == partner and led == trump and not any(c.suit == trump for c in hand):
            call = self._call_discard(hand, legal, trump)
            if call is not None:
                return call
        winning = trick[trick_winner(trick, trump)]
        # en troisième : l'As plutôt qu'une plus petite carte si un 10 peut être derrière
        if len(trick) == 2 and led != trump and winning[0] != partner:
            winners = [c for c in legal if trick_winner(trick + [(seat, c)], trump) == 2]
            ace = Card(led, Rank.ACE)
            ten = Card(led, Rank.TEN)
            gone = {c for cards in game.played for c in cards} | {c for _, c in trick}
            if ace in winners and len(winners) > 1 and ten not in gone and ten not in hand:
                return ace
        if winning[0] == partner:
            # partenaire maître : on ne donne pas un 10 accompagné
            keep = [c for c in legal if not (c.rank == Rank.TEN and c.suit != trump
                                             and sum(d.suit == c.suit for d in hand) > 1)]
            return super().play(game, seat, keep or legal)
        return super().play(game, seat, legal)

    def _keep_aces(self, game, seat, legal):
        """On ne défausse jamais un As sans le 10 et le Roi derrière, sauf si on n'a pas le choix."""
        trump, led = game.trump, game.trick[0][1].suit
        hand = game.hands[seat]

        def bad(card):
            if card.rank != Rank.ACE or card.suit in (led, trump):
                return False
            return not (has(hand, card.suit, Rank.TEN) and has(hand, card.suit, Rank.KING))

        keep = [c for c in legal if not bad(c)]
        return keep or legal

    @staticmethod
    def _call_discard(hand, legal, trump):
        """Appel direct (couleur de la famille de l'atout) ou indirect (couleur sœur) vers un de mes As.
        Jeter l'As lui-même = j'ai la longue maîtresse dans cette couleur (au moins As-10-Roi)."""
        for ace in (c for c in legal if c.rank == Rank.ACE and c.suit != trump):
            if has(hand, ace.suit, Rank.TEN) and has(hand, ace.suit, Rank.KING):
                return ace
        for ace in (c for c in hand if c.rank == Rank.ACE and c.suit != trump):
            target = ace.suit if ace.suit == SISTER[trump] else SISTER[ace.suit]
            small = [c for c in legal if c.suit == target and c.rank not in (Rank.ACE, Rank.TEN)]
            if small:
                return min(small, key=lambda c: c.strength(trump))
        return None

    @staticmethod
    def _called_suits(game, seat):
        """Couleurs demandées par le partenaire en défaussant sur mes entames atout."""
        trump, partner = game.trump, partner_of(seat)
        calls = set()
        for trick, _w in game.tricks:
            if trick[0][0] != seat or trick[0][1].suit != trump:
                continue
            card = dict(trick)[partner]
            if card.suit == trump:
                continue
            if card.rank == Rank.ACE:
                calls.add(card.suit)
            else:
                calls.add(card.suit if card.suit == SISTER[trump] else SISTER[card.suit])
        return calls

    def _belote_signal(self, game, seat, legal, card):
        """Belote dans l'équipe qui a pris : Roi en premier si nombre pair d'atouts, Dame si impair."""
        trump = game.trump
        if card.suit != trump or card.rank not in (Rank.KING, Rank.QUEEN) or game.belote_seat != seat:
            return card
        if team_of(game.contract["seat"]) != team_of(seat):
            return card
        king, queen = Card(trump, Rank.KING), Card(trump, Rank.QUEEN)
        if king not in legal or queen not in legal:
            return card
        count = sum(c.suit == trump for c in game.hands[seat])
        return king if count % 2 == 0 else queen

    # ---------- entames ----------
    def lead(self, game, seat, legal):
        trump = game.trump
        contract = game.contract
        attacking = team_of(contract["seat"]) == team_of(seat)
        side = [c for c in legal if c.suit != trump]
        gone = {c for cards in game.played for c in cards}
        hand = game.hands[seat]
        masters = sorted((c for c in side if self._is_master(c, trump, gone, hand)), key=lambda c: -c.points(trump))
        if not attacking:
            return self.defence_lead(game, seat, legal)
        trumps = [c for c in legal if c.suit == trump]
        if contract["mult"] > 1 and side:
            trumps = []  # contrés : on n'entame pas atout, on garde ses atouts
        if trumps and self._opponents_may_have_trumps(game, seat):
            choice = self._trump_lead(game, seat, trumps)
            if choice is not None:
                return choice
        called = [c for c in side if c.suit in self._called_suits(game, seat)]
        if called:
            return min(called, key=lambda c: c.strength(trump))  # donner la main au partenaire qui a appelé
        if masters:
            return masters[0]
        for suit in {c.suit for c in side}:
            ace = Card(suit, Rank.ACE)
            if ace not in gone and ace not in hand and Card(suit, Rank.KING) in hand and Card(suit, Rank.TEN) in hand:
                return Card(suit, Rank.KING)  # faire tomber l'As pour rendre le 10 maître
        if side:
            return self._from_longest(side, trump, gone, hand)
        return min(legal, key=lambda c: c.strength(trump))

    def defence_lead(self, game, seat, legal):
        """Entame en défense (pas d'appels en défense) : contre 140 ou plus, les cartes maîtresses ;
        sinon faire couper le preneur : la couleur qu'il n'a plus (la plus longue si plusieurs), sinon
        notre couleur la plus longue ; atout seulement s'il ne reste que ça."""
        trump = game.trump
        side = [c for c in legal if c.suit != trump]
        gone = {c for cards in game.played for c in cards}
        hand = game.hands[seat]
        masters = sorted((c for c in side if self._is_master(c, trump, gone, hand)), key=lambda c: -c.points(trump))
        if game.contract["value"] >= 140 and masters:
            return masters[0]
        ruff = self._ruff_lead(game, side)
        if ruff is not None:
            return ruff
        if side:
            return self._from_longest(side, trump, gone, hand)
        return min(legal, key=lambda c: c.strength(trump))

    def _trump_lead(self, game, seat, trumps):
        trump = game.trump
        hand = game.hands[seat]
        gone = {c for cards in game.played for c in cards}
        outstanding = [c for c in self._all_trumps(trump) if c not in gone and c not in hand]
        jack, nine = Card(trump, Rank.JACK), Card(trump, Rank.NINE)
        partner = self._partner_majors(game, seat)
        strength = lambda c: c.strength(trump)
        top = max(trumps, key=strength)
        top_is_master = all(strength(top) > strength(c) for c in outstanding)
        # garder son dernier atout s'il n'en reste qu'un dehors, plus fort
        if len(trumps) == 1 and len(outstanding) == 1 and not top_is_master:
            return None
        if nine in trumps and jack not in trumps and jack not in gone:
            low = [c for c in trumps if c != nine]
            return min(low, key=strength) if low else None  # faire tomber le Valet avant d'exposer le 9
        if jack in gone and nine not in gone and nine not in hand and Rank.NINE in partner:
            low = [c for c in trumps if c != nine]
            if low:
                return min(low, key=strength)  # donner la main au 9 du partenaire
        return top if top_is_master else min(trumps, key=strength)

    def _partner_majors(self, game, seat):
        """Majeures (Valet, 9) d'atout que le partenaire a montrées pendant les annonces."""
        trump, partner = game.trump, partner_of(seat)
        majors = {Rank.JACK, Rank.NINE}
        mine = ranks_in(game.dealt[seat], trump) & majors
        ours = [(i, s, a) for i, (s, a) in enumerate(game.bids)
                if a[0] == "bid" and a[2] == trump and team_of(s) == team_of(seat)]
        shown = set()
        for i, s, a in ours:
            if s != partner:
                continue
            my_before = [b for j, t, b in ours if j < i and t == seat]
            if not my_before:
                if a[1] >= 100 and self._opponent_value(game, seat, before=i) != 90:
                    shown |= majors  # ouverture à 100 ou plus : maîtrise
            elif my_before[-1][1] == 90 and a[1] >= 100:
                shown |= majors - mine  # complément de mon 90
            elif my_before[-1][1] == 80:
                if a[1] >= 100:
                    shown |= majors
                elif len(mine) == 1:
                    shown |= majors - mine  # 90 : le Valet ou le 9, celui que je n'ai pas
        return shown

    def _opponents_may_have_trumps(self, game, seat):
        from .papi_robert import PapiRobertBot
        if not PapiRobertBot._opponents_may_have_trumps(game, seat):
            return False
        return not self._belote_says_none(game, seat)

    @staticmethod
    def _belote_says_none(game, seat):
        """Signal de belote du partenaire : si les atouts inconnus à ce moment étaient tous chez lui."""
        trump, partner = game.trump, partner_of(seat)
        if game.belote_seat != partner:
            return False
        seq = [x for t, _w in game.tricks for x in t] + list(game.trick)
        k = next((i for i, (s, c) in enumerate(seq) if s == partner and c.suit == trump
                  and c.rank in (Rank.KING, Rank.QUEEN)), None)
        if k is None:
            return False
        before, after = seq[:k], seq[k + 1:]
        my_then = sum(c.suit == trump for c in game.hands[seat]) + sum(s == seat and c.suit == trump for s, c in after)
        unknown = 8 - sum(c.suit == trump for _s, c in before) - my_then
        even = seq[k][1].rank == Rank.KING
        return (even and unknown == 2) or (not even and unknown == 3)

    @staticmethod
    def _ruff_lead(game, side):
        """Défense : la plus petite carte d'une couleur que le preneur n'a plus (s'il peut avoir de l'atout)."""
        from .papi_robert import PapiRobertBot
        voids = PapiRobertBot._shown_voids(game)
        taker = game.contract["seat"]
        if game.trump in voids[taker]:
            return None
        cards = [c for c in side if c.suit in voids[taker]]  # un As ou un 10 peut être sacrifié
        if not cards:
            return None
        longest = max({c.suit for c in cards}, key=lambda s: (sum(c.suit == s for c in side), s.value))
        return min((c for c in cards if c.suit == longest), key=lambda c: (c.points(game.trump), c.strength(game.trump)))

    @staticmethod
    def _is_master(card, trump, gone, hand):
        higher = [Card(card.suit, r) for r in Rank if Card(card.suit, r).strength(trump) > card.strength(trump)]
        return all(c in gone or c in hand for c in higher)

    def _from_longest(self, cards, trump, gone, hand):
        """Couleur la plus longue : sa carte maîtresse si elle l'est, sinon la plus petite."""
        longest = max({c.suit for c in cards}, key=lambda s: (sum(c.suit == s for c in cards), s.value))
        suit_cards = [c for c in cards if c.suit == longest]
        top = max(suit_cards, key=lambda c: c.strength(trump))
        if self._is_master(top, trump, gone, hand):
            return top
        return min(suit_cards, key=lambda c: c.strength(trump))
