"""Robot "petit jeu" pour la Coinche à 4 : annonces et entames selon les règles
données par Noa (convention du "petit jeu").

Annonces (majeures = Valet et 9 d'atout ; "maître à l'atout" = Valet, 9, As
et au moins un autre atout, ou Valet, 9 et au moins trois autres atouts) :
- 80 : le Valet ou le 9, plus deux autres atouts ;
- 90 : le Valet et le 9, plus un autre atout ;
- 100 : maître à l'atout ; 110 : maître et tricolore (3 couleurs en main) ;
  120 : maître et bicolore (2 couleurs).
Réponses du partenaire (une seule fois, dans la couleur annoncée ; les As
comptés sont ceux des couleurs autres que l'atout) :
- sur 80 : seulement avec la deuxième majeure accompagnée (pas de Valet ou de
  9 sec) : +10, puis +10 par As ;
- sur 90 et 100 : +10 par As ;
- sur 110 : +10 avec deux As, +20 avec les trois ;
- sur 120 : +10 avec les trois As.
Si un adversaire a parlé avant nous, une annonce de 80 ou 90 (ou une réponse
à 80 ou 90) peut monter de 10 si nécessaire ; à partir de 100, on ne monte pas.
Le partenaire qui lit une annonce faite après un adversaire suppose qu'elle a
été majorée (90 lue comme 80, 100 comme 90 : même réponse que sur 100).
Coinche : même règle que CoincheBot. Pas de surcoinche.

Entames : en attaque, atouts (le maître s'il est maître, sinon le plus petit)
tant que des atouts restent dehors, puis les cartes maîtresses (As d'abord),
puis la couleur la plus longue ; en défense, les cartes maîtresses (As), puis
un singleton, puis la couleur la plus longue, les atouts en dernier. Le jeu
en second, troisième ou quatrième est celui de CoincheBot.
"""
from ..core.cards import Card, Rank
from .bots import CoincheBot, wants_coinche
from .engine import SUITS, partner_of, team_of

MAX_BID = 160


def is_master_trump(ranks):
    """Maître à l'atout : Valet, 9, As + un autre atout, ou Valet, 9 + trois autres atouts."""
    if Rank.JACK not in ranks or Rank.NINE not in ranks:
        return False
    return (Rank.ACE in ranks and len(ranks) >= 4) or len(ranks) >= 5


def opening_value(hand, suit):
    """Annonce d'ouverture permise avec cet atout (80 à 120), ou None."""
    ranks = {c.rank for c in hand if c.suit == suit}
    if is_master_trump(ranks):
        colours = len({c.suit for c in hand})
        return 120 if colours <= 2 else 110 if colours == 3 else 100
    if Rank.JACK in ranks and Rank.NINE in ranks and len(ranks) >= 3:
        return 90
    if (Rank.JACK in ranks or Rank.NINE in ranks) and len(ranks) >= 3:
        return 80
    return None


def best_opening(hand):
    """(valeur, couleur) de la meilleure ouverture, ou None."""
    options = []
    for suit in SUITS:
        value = opening_value(hand, suit)
        if value is not None:
            trumps = [c for c in hand if c.suit == suit]
            options.append((value, len(trumps), sum(c.strength(suit) for c in trumps), suit))
    if not options:
        return None
    value, _n, _s, suit = max(options, key=lambda o: o[:3])
    return value, suit


def side_aces(hand, trump):
    return sum(c.rank == Rank.ACE and c.suit != trump for c in hand)


def response_increment(hand, level, suit):
    """Points ajoutés par le partenaire à une annonce de niveau level dans suit."""
    aces = side_aces(hand, suit)
    ranks = {c.rank for c in hand if c.suit == suit}
    if level == 80:
        if (Rank.JACK in ranks or Rank.NINE in ranks) and len(ranks) >= 2:
            return 10 + 10 * aces
        return 0
    if level in (90, 100):
        return 10 * aces
    if level == 110:
        return 20 if aces >= 3 else 10 if aces == 2 else 0
    if level == 120:
        return 10 if aces >= 3 else 0
    return 0


class PetitJeuBot(CoincheBot):
    name = "petit jeu"

    # ---------- annonces ----------
    def bid(self, game, seat):
        legal = game.legal_bids(seat)
        contract = game.contract
        hand = game.hands[seat]
        if ("surcoinche",) in legal:
            return ("pass",)
        if ("coinche",) in legal and wants_coinche(hand, contract):
            return ("coinche",)
        if any(s == seat and a[0] == "bid" for s, a in game.bids):
            return ("pass",)  # une seule annonce (ouverture ou réponse) par donne
        partner = partner_of(seat)
        partner_bids = [(i, a) for i, (s, a) in enumerate(game.bids) if s == partner and a[0] == "bid"]
        if partner_bids:
            return self._respond(game, seat, legal, *partner_bids[-1])
        opening = best_opening(hand)
        if opening is None:
            return ("pass",)
        value, suit = opening
        if contract is not None and team_of(contract["seat"]) != team_of(seat) \
                and value <= contract["value"] and value in (80, 90):
            value += 10  # un adversaire a parlé avant nous
        action = ("bid", value, suit)
        return action if action in legal else ("pass",)

    def _respond(self, game, seat, legal, index, partner_bid):
        _kind, value, suit = partner_bid
        opponent_before = any(a[0] == "bid" and team_of(s) != team_of(seat) for s, a in game.bids[:index])
        level = value - 10 if opponent_before and value in (90, 100) else value
        increment = response_increment(game.hands[seat], level, suit)
        if increment == 0:
            return ("pass",)
        target = value + increment
        contract = game.contract
        if team_of(contract["seat"]) != team_of(seat) and target <= contract["value"] and level in (80, 90):
            target += 10  # un adversaire a parlé avant notre réponse
        action = ("bid", min(target, MAX_BID), suit)
        return action if action in legal else ("pass",)

    # ---------- entames ----------
    def lead(self, game, seat, legal):
        trump = game.trump
        gone = {c for cards in game.played for c in cards}
        hand = game.hands[seat]
        attacking = team_of(game.contract["seat"]) == team_of(seat)
        trumps = [c for c in legal if c.suit == trump]
        side = [c for c in legal if c.suit != trump]
        masters = sorted((c for c in side if self._is_master(c, trump, gone, hand)),
                         key=lambda c: -c.points(trump))
        if attacking:
            outstanding = [c for c in self._all_trumps(trump) if c not in gone and c not in hand]
            if trumps and outstanding:
                top = max(trumps, key=lambda c: c.strength(trump))
                if all(top.strength(trump) > c.strength(trump) for c in outstanding):
                    return top
                return min(trumps, key=lambda c: c.strength(trump))
            if masters:
                return masters[0]
            return self._from_longest(side or legal, trump)
        if masters:
            return masters[0]
        singletons = [c for c in side if sum(d.suit == c.suit for d in hand) == 1]
        if singletons:
            return min(singletons, key=lambda c: c.points(trump))
        if side:
            return self._from_longest(side, trump)
        return min(legal, key=lambda c: c.strength(trump))

    @staticmethod
    def _is_master(card, trump, gone, hand):
        """Plus aucune carte plus forte de sa couleur hors de ma main."""
        higher = [Card(card.suit, r) for r in Rank if Card(card.suit, r).strength(trump) > card.strength(trump)]
        return all(c in gone or c in hand for c in higher)

    @staticmethod
    def _from_longest(cards, trump):
        """Petite carte de la couleur la plus longue."""
        longest = max({c.suit for c in cards}, key=lambda s: sum(c.suit == s for c in cards))
        return min((c for c in cards if c.suit == longest), key=lambda c: c.strength(trump))
