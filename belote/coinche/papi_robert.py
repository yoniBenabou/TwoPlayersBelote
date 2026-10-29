"""Robot "Papi Robert" pour la Coinche à 4 : le jeu aux As de Papi Robert
(fiche "Belote au miel"). Majeures = Valet et 9 d'atout ; les As comptés sont
ceux des couleurs autres que l'atout.

Ouvertures (on choisit d'abord la couleur avec le plus de majeures) :
- 80, "jeu aux As" : 2 ou 3 atouts dont le Valet ou le 9 (ou la belote), et
  2 As ; on choisit la couleur la plus forte (points des atouts, belote, As) ;
- 90 (toujours avec un As, d'atout ou à côté) : Valet troisième, ou 9 (ou
  Valet) quatrième ; ou les deux majeures en 3 atouts avec un As mais un jeu "light"
  à côté (rien à côté avec l'As d'atout ; un seul As et pas de 10 sinon) ;
- 100 : 3 atouts dont les deux majeures et un As (l'As d'atout ou un As à
  côté) ; ou maître à l'atout : 4 atouts dont les deux majeures et un As, ou
  5 atouts dont les deux majeures (Valet, 9, 10, Roi, Dame) ; jamais 100 sans
  les deux majeures ;
- 110 : maître à l'atout et tricolore, ou 5 atouts dont les deux majeures ;
- 120 : comme 100 avec 4 atouts (ou plus) mais bicolore.

Réponses du partenaire (une seule fois) :
- sur 80 : il change l'atout en s'appuyant sur les As de l'ouvreur : dans sa
  couleur qui a le plus de majeures (Valet ou 9, au moins 3 cartes), +10, +20
  avec un As, +30 avec deux As ;
- sur 90 : seulement avec la deuxième majeure (même avec des As) : +10, puis
  +10 par As ;
- sur 100 et 110 : +10 par As ;
- sur 120 : rien avec 1 As, +10 avec 2 As, +20 avec 3 As.
Relances de l'ouvreur (une fois) : ouvert à 110 avec 5 atouts et le
partenaire a ajouté 20 ou plus : capot ; ouvert à 90 avec 5 atouts (ou plus)
et une majeure, le partenaire a montré la deuxième : +10 par As, jusqu'à 130.
Coinche : même règle que CoincheBot. Pas de surcoinche. La fiche ne dit rien
des adversaires : si l'annonce n'est plus possible, on passe.

Jeu :
- l'équipe qui a pris joue atout quand elle a la main, tant que les
  adversaires peuvent en avoir, en commençant fort (le plus gros) ; puis ses As, puis la couleur que le partenaire a appelée, puis la
  plus petite carte ;
- en défense : la couleur appelée par le partenaire, puis les As, puis la plus
  petite carte ;
- appel indirect : quand le partenaire entame atout et que je n'en ai plus, je
  défausse une petite carte dans la couleur sœur (même teinte) de celle de mon
  As ; le partenaire rejoue ensuite la couleur de l'As.
On ne défausse jamais un As sans le 10 et le Roi derrière, sauf si on n'a pas
le choix. Le reste du jeu en second, troisième ou quatrième est celui de CoincheBot.
"""
from ..core.cards import Rank, Suit
from .bots import CoincheBot, wants_coinche
from .engine import CAPOT, SUITS, partner_of, team_of

SISTER = {Suit.PIQUE: Suit.TREFLE, Suit.TREFLE: Suit.PIQUE, Suit.COEUR: Suit.CARREAU, Suit.CARREAU: Suit.COEUR}
SMALL = (Rank.SEVEN, Rank.EIGHT, Rank.NINE, Rank.QUEEN, Rank.KING, Rank.JACK)  # hors atout : pas As ni 10
MAX_RELAUNCH = 130


def side_aces(hand, trump):
    return sum(c.rank == Rank.ACE and c.suit != trump for c in hand)


def majors(hand, suit):
    return sum(c.suit == suit and c.rank in (Rank.JACK, Rank.NINE) for c in hand)


def opening_value(hand, suit):
    """Ouverture de Papi Robert avec cet atout (80 à 120), ou None."""
    n = sum(c.suit == suit for c in hand)
    m = majors(hand, suit)
    aces = side_aces(hand, suit)
    if m == 2:
        trump_ace = any(c.suit == suit and c.rank == Rank.ACE for c in hand)
        if n >= 4 and (aces >= 1 or trump_ace or n >= 5):  # maître à l'atout
            colours = len({c.suit for c in hand})
            return 120 if colours <= 2 else 110 if (colours == 3 or n >= 5) else 100
        if n == 3 and (aces >= 1 or trump_ace):
            tens = sum(c.rank == Rank.TEN and c.suit != suit for c in hand)
            return 90 if aces + tens <= (0 if trump_ace else 1) else 100  # jeu light à côté : on reste à 90
        if n == 2 and aces >= 2:
            return 80
        return None  # Valet et 9 sans aucun As : 90 oblige d'avoir un As
    if m == 1:
        jack = any(c.suit == suit and c.rank == Rank.JACK for c in hand)
        any_ace = aces >= 1 or any(c.suit == suit and c.rank == Rank.ACE for c in hand)
        if n >= 4 and any_ace:
            return 90  # Valet ou 9 quatrième et un As (d'atout ou à côté)
        if n == 3 and jack and any_ace and aces < 2:
            return 90  # Valet troisième et un As (d'atout ou à côté)
        if n in (2, 3) and aces >= 2:
            return 80
    if m == 0 and n in (2, 3) and aces >= 2 and has_belote(hand, suit):
        return 80  # jeu aux As : la belote à l'atout et 2 As à côté
    return None


def has_belote(hand, suit):
    return all(any(c.suit == suit and c.rank == r for c in hand) for r in (Rank.KING, Rank.QUEEN))


def strength_score(hand, suit):
    """Force d'une couleur d'atout : points des atouts, belote (20) et As à côté."""
    return (sum(c.points(suit) for c in hand if c.suit == suit) + 20 * has_belote(hand, suit)
            + 11 * side_aces(hand, suit))


def best_opening(hand):
    """(valeur, couleur) : la plus haute annonce ; à égalité, la couleur avec le plus
    de majeures (à 80, jeu aux As : la couleur la plus forte, belote comprise)."""
    options = []
    for suit in SUITS:
        value = opening_value(hand, suit)
        if value is not None:
            m = majors(hand, suit) if value > 80 else 0
            options.append((value, m, strength_score(hand, suit), sum(c.suit == suit for c in hand), suit))
    if not options:
        return None
    value, _m, _s, _n, suit = max(options, key=lambda o: o[:4])
    return value, suit


def response(hand, value, suit):
    """Réponse à une ouverture du partenaire (value, suit) : (valeur, couleur) ou None."""
    if value == 80:  # jeu aux As : on change l'atout, appuyé sur ses As
        options = [(majors(hand, s), sum(c.suit == s for c in hand), s) for s in SUITS
                   if majors(hand, s) >= 1 and sum(c.suit == s for c in hand) >= 3]
        if not options:
            return None
        new = max(options, key=lambda o: o[:2])[2]
        return 90 + 10 * min(side_aces(hand, new), 2), new
    aces = side_aces(hand, suit)
    if value == 90:
        return (100 + 10 * aces, suit) if majors(hand, suit) >= 1 else None
    if value in (100, 110):
        return (value + 10 * aces, suit) if aces else None
    if value == 120:
        return (140, suit) if aces >= 3 else (130, suit) if aces == 2 else None
    return None


class PapiRobertBot(CoincheBot):
    name = "Papi Robert"

    # ---------- annonces ----------
    def bid(self, game, seat):
        legal = game.legal_bids(seat)
        hand = game.hands[seat]
        if ("surcoinche",) in legal:
            return ("pass",)
        if ("coinche",) in legal and wants_coinche(hand, game.contract):
            return ("coinche",)
        partner = partner_of(seat)
        mine = [i for i, (s, a) in enumerate(game.bids) if s == seat and a[0] == "bid"]
        partner_bids = [(i, a) for i, (s, a) in enumerate(game.bids) if s == partner and a[0] == "bid"]
        action = None
        if not mine:
            if partner_bids:
                answer = response(hand, *partner_bids[-1][1][1:])
                action = answer and ("bid", min(answer[0], 160), answer[1])
            else:
                opening = best_opening(hand)
                action = opening and ("bid", opening[0], opening[1])
        elif len(mine) == 1 and partner_bids and partner_bids[-1][0] > mine[0]:
            action = self._relaunch(hand, game.bids[mine[0]][1], partner_bids[-1][1])
        return action if action in legal else ("pass",)

    @staticmethod
    def _relaunch(hand, opening, answer):
        """Seconde annonce de l'ouvreur après la réponse du partenaire."""
        _k, value, suit = opening
        _k, partner_value, partner_suit = answer
        if partner_suit != suit:
            return None
        n = sum(c.suit == suit for c in hand)
        if value == 110 and n >= 5 and majors(hand, suit) == 2 and partner_value - value >= 20:
            return ("bid", CAPOT, suit)
        if value == 90 and n >= 5 and majors(hand, suit) == 1:
            target = min(partner_value + 10 * side_aces(hand, suit), MAX_RELAUNCH)
            if target > partner_value:
                return ("bid", target, suit)
        return None

    # ---------- jeu ----------
    def play(self, game, seat):
        legal = game.legal_cards(seat)
        trick, trump = game.trick, game.trump
        if trick and trick[0][0] == partner_of(seat) and trick[0][1].suit == trump \
                and not any(c.suit == trump for c in game.hands[seat]):
            call = self._indirect_call(game.hands[seat], legal, trump)
            if call is not None:
                return call
        return super().play(game, seat, self._allowed_discards(game, seat, legal))

    @staticmethod
    def _allowed_discards(game, seat, legal):
        """Jamais défausser un As sans le 10 et le Roi derrière, sauf si on n'a pas le choix."""
        trick, trump = game.trick, game.trump
        if not trick:
            return legal
        led = trick[0][1].suit
        hand = game.hands[seat]

        def protected(c):
            return all(any(d.suit == c.suit and d.rank == r for d in hand) for r in (Rank.TEN, Rank.KING))

        allowed = [c for c in legal if not (c.rank == Rank.ACE and c.suit not in (led, trump) and not protected(c))]
        return allowed or legal

    @staticmethod
    def _indirect_call(hand, legal, trump):
        """Petite carte dans la couleur sœur de celle d'un de mes As (sans atout, sur entame atout)."""
        for ace in (c for c in hand if c.rank == Rank.ACE and c.suit != trump):
            small = [c for c in legal if c.suit == SISTER[ace.suit] and c.rank in SMALL]
            if small:
                return min(small, key=lambda c: c.strength(trump))
        return None

    def lead(self, game, seat, legal):
        trump = game.trump
        attacking = team_of(game.contract["seat"]) == team_of(seat)
        called = [c for c in legal if c.suit in self._called_suits(game, seat)]
        called_lead = min(called, key=lambda c: c.strength(trump)) if called else None
        if not attacking:
            return called_lead or super().lead(game, seat, legal)
        trumps = [c for c in legal if c.suit == trump]
        if trumps and self._opponents_may_have_trumps(game, seat):
            # on a pris : atout tant que les adversaires en ont, en commençant fort
            return max(trumps, key=lambda c: c.strength(trump))
        aces = [c for c in legal if c.rank == Rank.ACE and c.suit != trump]
        if aces:
            return aces[0]
        if called_lead:
            return called_lead
        return min(legal, key=lambda c: (c.suit == trump, c.points(trump), c.strength(trump)))

    @staticmethod
    def _called_suits(game, seat):
        """Couleurs que le partenaire m'a demandées par appel indirect sur mes entames atout."""
        partner = partner_of(seat)
        calls = set()
        for trick, _winner in game.tricks:
            if trick[0][0] != seat or trick[0][1].suit != game.trump:
                continue
            card = dict(trick)[partner]
            if card.suit != game.trump and card.rank in SMALL:
                calls.add(SISTER[card.suit])
        return calls

    @staticmethod
    def _opponents_may_have_trumps(game, seat):
        """Reste-t-il des atouts dehors, chez un adversaire qui n'a pas montré qu'il n'en a plus ?"""
        trump = game.trump
        gone = {c for cards in game.played for c in cards} | {c for _, c in game.trick}
        outstanding = [c for c in CoincheBot._all_trumps(trump) if c not in gone and c not in game.hands[seat]]
        if not outstanding:
            return False
        void = set()
        for trick, _winner in game.tricks:
            if trick[0][1].suit == trump:
                void |= {s for s, c in trick if c.suit != trump}
        return any(opp not in void for opp in ((seat + 1) % 4, (seat + 3) % 4))
