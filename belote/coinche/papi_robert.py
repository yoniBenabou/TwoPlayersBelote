"""Robot "Papi Robert" pour la Coinche à 4 : fiche "Belote au miel" (version mise à jour).
Majeures = Valet et 9 d'atout. "+10 par As" compte toujours les As hors atout, jamais l'As d'atout.

Force à l'atout (couleur avec le plus de majeures, puis la plus forte) :
- 90 : au moins 3 atouts avec le Valet ou le 9, et au moins un As hors atout ;
- 100 : au moins 3 atouts avec Valet, 9 et As d'atout, ou au moins 4 atouts avec Valet et 9, et les
  4 couleurs ; jeu nul à côté (aucun As hors atout) : on reste timide à 90 ;
- 110 : même force que 100, jeu tricolore ; 120 : même force, jeu bicolore.
Ouverture : 110 ou 120 directement si le jeu les vaut ; sinon 80 avec 2 As (l'As d'atout compte) et au
moins 2 atouts dont le Valet ou le 9 (sans eux, exceptionnellement : 4 atouts avec la belote, ou 5 ou 6
atouts) ; sinon la force à l'atout (90 ou 100). Ouvert à 80 avec un jeu de 100 : on remonte à 100 au
tour suivant si les enchères le permettent (pas si le partenaire a changé d'atout).

Réponses du partenaire (une fois) :
- sur 80 : avec un jeu d'au moins 100 ailleurs, je l'annonce chez moi ; sinon avec le complément, +10
  par majeure (Valet, 9) et +10 par As ; sinon je change d'atout si j'ai une ouverture (90) ailleurs ;
- sur 90 : +10 avec la deuxième majeure, puis +10 par As ; sans elle, rien au premier tour ; si un
  adversaire a parlé et que j'ai des As, au tour suivant : 90 + 10 par As si c'est encore possible ;
- sur 100 : +10 par As ;
- sur 110 : rien avec un As, +10 avec deux, +20 avec trois ; sur 120 : +10 seulement avec les trois ;
- sur 110 ou 120 avec les trois As et un 10 derrière un As : capot (le partenaire a 4 atouts, il me
  fait la passe).
Relances de l'ouvreur (une fois) : 110 ou 120, le partenaire a montré les trois As : capot avec 5 atouts
ou un 10 second hors atout ;
90 avec 5 atouts et une majeure, le partenaire a montré la deuxième : +10 par As, jusqu'à 130.
Belote : jamais annoncée, sauf si mon partenaire a annoncé un vrai 100 ou plus (jusqu'à 160), que je
n'ai rien répondu et que l'adversaire a monté de 10 : je dis exactement 20 de plus que mon partenaire,
jamais plus.

Après une annonce adverse : sur 80, mon annonce vaut sa valeur exacte ; sur 90 ou plus, j'annonce 10 de
plus que ma vraie valeur (collage +10 ou saut +20 : lu 10 de moins), et je passe si ma vraie valeur est
sous l'annonce adverse. Le partenaire lit l'annonce 10 de moins et répond par-dessus ce qui a été dit.
Sortie (comme AsR, partie en 1 500) : pas de contrat qui, fait tout juste, ferait sortir les adversaires
devant nous ; si leur contrat les fait sortir, on monte juste au-dessus dans une vraie couleur d'atout,
sinon on contre.
Coinche : même règle que CoincheBot. Pas de surcoinche.

Jeu :
- attaque : on retire les atouts adverses. Partenaire qui a annoncé l'atout le premier : je lui rends la
  main (petit atout, ou sans atout la couleur qu'il a appelée, sinon une petite carte) ; sinon atouts forts
  d'abord, puis les As ; sans atout (adversaires encore à l'atout), une petite carte plutôt que les As ;
  exception : mon dernier atout, je le garde si un atout adverse est encore dehors, que ma main est faible
  (aucune carte maîtresse hors atout) et que mon partenaire n'a pas annoncé de grande force (moins de 110) ;
- défense : avec au moins 2 As hors atout, je les joue d'abord, puis je rejoue une de ces couleurs pour
  faire couper ; sinon la défense d'AsR (faire couper le preneur, pas d'entame atout) ;
- appels (équipe qui a pris, comme AsR) : sur l'atout du partenaire, appel direct (une carte de la
  couleur) dans la famille de l'atout, appel indirect (couleur sœur) sinon ; le partenaire rejoue la couleur ;
- contrat coinché : on garde ses atouts (pas d'entame atout) ;
- on ne défausse jamais un As sans le 10 et le Roi derrière, sauf si on n'a pas le choix.
Le reste du jeu en second, troisième ou quatrième est celui de CoincheBot.
"""
from ..core.cards import Rank, Suit
from .asr import AsRBot
from .bots import CoincheBot, wants_coinche
from .engine import CAPOT, SUITS, partner_of, team_of

SISTER = {Suit.PIQUE: Suit.TREFLE, Suit.TREFLE: Suit.PIQUE, Suit.COEUR: Suit.CARREAU, Suit.CARREAU: Suit.COEUR}
MAX_RELAUNCH = 130
MAX_BID = 160
GREAT_STRENGTH = 110  # "grande force" du partenaire


def side_aces(hand, trump):
    return sum(c.rank == Rank.ACE and c.suit != trump for c in hand)


def majors(hand, suit):
    return sum(c.suit == suit and c.rank in (Rank.JACK, Rank.NINE) for c in hand)


def _ranks(hand, suit):
    return {c.rank for c in hand if c.suit == suit}


def trump_value(hand, suit):
    """Force à l'atout dans cette couleur (90 à 120), sans le jeu aux As, ou None."""
    r = _ranks(hand, suit)
    n = len(r)
    jack, nine = Rank.JACK in r, Rank.NINE in r
    if jack and nine and (n >= 4 or (n >= 3 and Rank.ACE in r)):
        colours = len({c.suit for c in hand})
        if colours <= 2:
            return 120
        if colours == 3:
            return 110
        return 100 if side_aces(hand, suit) else 90  # jeu nul à côté : timide
    if (jack or nine) and n >= 3 and side_aces(hand, suit) >= 1:
        return 90
    return None


def eighty_trumps(hand, suit):
    """Atouts d'un 80 : au moins 2 avec le Valet ou le 9 ; sans eux, 4 avec la belote ou 5 et plus."""
    n = sum(c.suit == suit for c in hand)
    if majors(hand, suit):
        return n >= 2
    return n >= 5 or (n == 4 and has_belote(hand, suit))


def opening_value(hand, suit):
    """Ouverture de Papi Robert avec cet atout (80 à 120), ou None."""
    value = trump_value(hand, suit)
    if value is not None and value >= 110:
        return value
    if sum(c.rank == Rank.ACE for c in hand) >= 2 and eighty_trumps(hand, suit):
        return 80  # 2 As (l'As d'atout compte)
    return value


def has_belote(hand, suit):
    return all(any(c.suit == suit and c.rank == r for c in hand) for r in (Rank.KING, Rank.QUEEN))


def strength_score(hand, suit):
    """Force d'une couleur d'atout : points des atouts, belote (20) et As à côté."""
    return (sum(c.points(suit) for c in hand if c.suit == suit) + 20 * has_belote(hand, suit)
            + 11 * side_aces(hand, suit))


def _best(hand, value_of):
    """(valeur, couleur) : la plus haute valeur ; à égalité, une vraie couleur d'atout, le plus de
    majeures, puis la couleur la plus forte."""
    options = []
    for suit in SUITS:
        value = value_of(hand, suit)
        if value is not None:
            options.append((value, trump_value(hand, suit) or 0, majors(hand, suit), strength_score(hand, suit),
                            sum(c.suit == suit for c in hand), suit))
    if not options:
        return None
    best = max(options, key=lambda o: o[:5])
    return best[0], best[-1]


def best_opening(hand):
    return _best(hand, opening_value)


def best_trump(hand):
    """Meilleure force à l'atout (sans le jeu aux As)."""
    return _best(hand, trump_value)


def second_ten(hand, trump):
    """Un 10 second hors atout (le 10 et une autre carte : elle tombe sous l'As du partenaire)."""
    return any(any(c.suit == s and c.rank == Rank.TEN for c in hand) and sum(c.suit == s for c in hand) == 2
               for s in SUITS if s != trump)


def tens_behind_aces(hand, trump):
    return sum(any(c.suit == s and c.rank == Rank.ACE for c in hand)
               and any(c.suit == s and c.rank == Rank.TEN for c in hand) for s in SUITS if s != trump)


def response(hand, value, suit):
    """Réponse à la vraie valeur value du partenaire dans suit : (valeur, couleur) (valeur CAPOT possible),
    ou None."""
    answer = _response(hand, value, suit)
    if isinstance(answer, tuple) or answer is None:
        return answer
    return answer, suit


def _response(hand, value, suit):
    aces = side_aces(hand, suit)
    if value == 80:
        # un jeu d'au moins 100 : je l'annonce chez moi ; sinon le complément ; sinon je change d'atout
        mine = [(trump_value(hand, s), s) for s in SUITS if s != suit and trump_value(hand, s)]
        best = max(mine, key=lambda o: (o[0], majors(hand, o[1]), strength_score(hand, o[1])), default=None)
        if best and best[0] >= 100:
            return best
        if majors(hand, suit):
            return 80 + 10 * majors(hand, suit) + 10 * aces
        return best
    if value == 90:
        return 100 + 10 * aces if majors(hand, suit) else None
    if value == 100:
        return 100 + 10 * aces if aces else None
    if value in (110, 120) and aces >= 3 and tens_behind_aces(hand, suit):
        return CAPOT  # le partenaire a 4 atouts : il me fait la passe, mes As et mes 10 sont maîtres
    if value == 110:  # rien avec un As, +10 avec deux, +20 avec trois
        return 130 if aces >= 3 else 120 if aces == 2 else None
    if value == 120:  # seulement avec les trois As : +10
        return 130 if aces >= 3 else None
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
        action = self._choose_bid(game, seat)
        action = self._near_exit(game, seat, action, legal)
        if action is not None and action[0] == "bid" and action[1] != CAPOT:
            action = ("bid", min(action[1], MAX_BID), action[2])
        return action if action in legal else ("pass",)

    def _choose_bid(self, game, seat):
        hand, bids = game.hands[seat], game.bids
        partner = partner_of(seat)
        mine = [i for i, (s, a) in enumerate(bids) if s == seat and a[0] == "bid"]
        partner_bids = [(i, a) for i, (s, a) in enumerate(bids) if s == partner and a[0] == "bid"]
        if not mine:
            if not partner_bids:
                return self._open(game, seat)
            i, (_k, value, suit) = partner_bids[-1]
            true = self._true_value(game, i)
            already_spoke = any(s == seat for s, _a in bids[partner_bids[0][0] + 1:])
            if already_spoke:
                return self._second_turn(game, seat, i, value, true, suit)
            answer = response(hand, true, suit)
            if answer is None:
                return None
            answer, new = answer
            if answer == CAPOT:
                return ("bid", CAPOT, new)
            if new == suit:
                return ("bid", value + answer - true, suit)
            opp = game.contract if team_of(game.contract["seat"]) != team_of(seat) else None
            if opp is not None and opp["value"] >= 90:
                return ("bid", answer + 10, new) if answer >= opp["value"] else None  # collage
            return ("bid", answer, new)  # je change d'atout
        if len(mine) == 1:
            _k, value, suit = bids[mine[0]][1]
            other_suit = any(a[2] != suit for i, a in partner_bids if i > mine[0])
            if value == 80 and trump_value(hand, suit) == 100 and not other_suit:
                return ("bid", 100, suit)  # ouvert à 80 avec un jeu de 100 : je remonte si c'est possible
            if partner_bids and partner_bids[-1][0] > mine[0]:
                return self._relaunch(hand, bids[mine[0]][1], partner_bids[-1][1])
        return None

    @staticmethod
    def _true_value(game, index):
        """Vraie valeur de l'annonce d'indice index : 10 de moins si elle passe par-dessus une annonce
        adverse d'au moins 90."""
        seat, (_k, value, _suit) = game.bids[index]
        before = next((a for s, a in reversed(game.bids[:index]) if a[0] == "bid"), None)
        last_seat = next((s for s, a in reversed(game.bids[:index]) if a[0] == "bid"), None)
        if before is not None and team_of(last_seat) != team_of(seat) and before[1] >= 90:
            return value - 10
        return value

    def _open(self, game, seat):
        hand = game.hands[seat]
        contract = game.contract
        if contract is None:
            opening = best_opening(hand)
            return opening and ("bid", opening[0], opening[1])
        best = best_trump(hand)  # un adversaire a parlé : plus de jeu aux As
        if best is None:
            return None
        value, suit = best
        opp = contract["value"]
        if opp == 80:
            return ("bid", value, suit)  # valeur exacte
        return ("bid", value + 10, suit) if value >= opp else None  # collage (+10) ou saut (+20) : lu 10 de moins

    def _second_turn(self, game, seat, index, value, true, suit):
        """Je n'ai pas répondu à mon partenaire et un adversaire a parlé depuis."""
        hand = game.hands[seat]
        opp_after = any(team_of(s) != team_of(seat) and a[0] == "bid" for s, a in game.bids[index + 1:])
        if not opp_after:
            return None
        if true >= 100 and has_belote(hand, suit):
            # exactement 20 de plus : ma belote ; jamais plus (l'adversaire a dû monter de 10 seulement)
            return ("bid", value + 20, suit) if value + 20 <= MAX_BID else None
        aces = side_aces(hand, suit)
        if true == 90 and not majors(hand, suit) and aces:
            return ("bid", value + 10 * aces, suit)  # sans la deuxième majeure : mes As au second tour
        return None

    @staticmethod
    def _relaunch(hand, opening, answer):
        """Seconde annonce de l'ouvreur après la réponse du partenaire."""
        _k, value, suit = opening
        _k, partner_value, partner_suit = answer
        if partner_suit != suit:
            return None
        n = sum(c.suit == suit for c in hand)
        three_aces = (value == 110 and partner_value - value >= 20) or (value == 120 and partner_value - value >= 10)
        if three_aces and (n >= 5 or second_ten(hand, suit)):
            return ("bid", CAPOT, suit)  # le partenaire a les 3 As : gros jeu, capot
        if value == 90 and n >= 5 and majors(hand, suit) == 1:
            target = min(partner_value + 10 * side_aces(hand, suit), MAX_RELAUNCH)
            if target > partner_value:
                return ("bid", target, suit)
        return None

    @staticmethod
    def _near_exit(game, seat, action, legal):
        """Sortie (comme AsR) : pas de contrat qui ferait sortir les adversaires devant nous ; si leur
        contrat les fait sortir, on monte juste au-dessus dans une vraie couleur d'atout, sinon on contre."""
        team, contract = team_of(seat), game.contract
        if not any(team_of(s) != team and a[0] == "bid" for s, a in game.bids):
            if action is not None and action[0] == "bid":
                value = action[1] if action[1] == CAPOT else min(action[1], MAX_BID)
                if AsRBot._wins_if_made(game, team, value) == 1 - team:
                    return ("pass",)
            return action
        if contract is None or team_of(contract["seat"]) == team or contract["mult"] != 1:
            return action
        value = contract["value"]
        if (AsRBot._wins_if_made(game, 1 - team, value) != 1 - team
                or (action is not None and action in legal and action[0] != "pass")):
            return action
        hand = game.hands[seat]
        suits = [s for s in SUITS if s != contract["suit"] and trump_value(hand, s)]
        if suits and value < MAX_BID:
            return ("bid", value + 10, max(suits, key=lambda s: (trump_value(hand, s), strength_score(hand, s))))
        return ("coinche",)

    # ---------- jeu ----------
    def play(self, game, seat):
        legal = game.legal_cards(seat)
        trick, trump = game.trick, game.trump
        attacking = trick and team_of(game.contract["seat"]) == team_of(seat)
        if attacking and trick[0][0] == partner_of(seat) and trick[0][1].suit == trump \
                and not any(c.suit == trump for c in game.hands[seat]):
            call = AsRBot._call_discard(game.hands[seat], self._allowed_discards(game, seat, legal), trump)
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

    def lead(self, game, seat, legal):
        trump = game.trump
        if team_of(game.contract["seat"]) != team_of(seat):
            return self._defence_lead(game, seat, legal)
        called = [c for c in legal if c.suit in self._called_suits(game, seat)]
        called_lead = min(called, key=lambda c: c.strength(trump)) if called else None
        side = [c for c in legal if c.suit != trump] or legal
        trumps = [c for c in legal if c.suit == trump]
        opponents_trumps = self._opponents_may_have_trumps(game, seat)
        gives_lead = AsRBot._partner_first_announcer(game, seat)
        no_trump_lead = not trumps  # je n'ai pas d'atout, ou je garde mon dernier
        if game.contract["mult"] > 1:
            legal = side  # coinché : on garde ses atouts pour couper
        elif trumps and opponents_trumps:
            if len(trumps) == 1 and side != legal and self._keep_last_trump(game, seat):
                no_trump_lead = True
            elif gives_lead:
                return min(trumps, key=lambda c: c.strength(trump))  # je rends la main à mon partenaire
            else:
                return max(trumps, key=lambda c: c.strength(trump))  # atouts forts d'abord
        if opponents_trumps and no_trump_lead:
            # sans atout (ou je garde le dernier) : la couleur appelée, sinon une petite carte plutôt que les As
            if called_lead:
                return called_lead
            return min(side, key=lambda c: (c.points(trump), c.strength(trump)))
        aces = [c for c in legal if c.rank == Rank.ACE and c.suit != trump]
        if aces:
            return aces[0]
        if called_lead:
            return called_lead
        return min(legal, key=lambda c: (c.suit == trump, c.points(trump), c.strength(trump)))

    def _keep_last_trump(self, game, seat):
        """Mon dernier atout : je le garde pour couper plus tard si ma main est faible (aucune carte maîtresse
        hors atout en ce moment) et que mon partenaire n'a pas annoncé de grande force."""
        hand, trump = game.hands[seat], game.trump
        gone = {c for cards in game.played for c in cards} | {c for _s, c in game.trick}
        if any(c.suit != trump and AsRBot._is_master(c, trump, gone, hand) for c in hand):
            return False
        partner = partner_of(seat)
        shown = [self._true_value(game, i) for i, (s, a) in enumerate(game.bids)
                 if s == partner and a[0] == "bid" and a[1] != CAPOT]
        capot = any(s == partner and a[0] == "bid" and a[1] == CAPOT for s, a in game.bids)
        return not capot and max(shown, default=0) < GREAT_STRENGTH

    def _defence_lead(self, game, seat, legal):
        """Défense : avec au moins 2 As hors atout, je les joue d'abord, puis je rejoue une de leurs couleurs
        pour faire couper (celle que le preneur n'a plus, sinon celle où il reste le moins de cartes dehors) ;
        sinon la défense d'AsR."""
        trump = game.trump
        side = [c for c in legal if c.suit != trump]
        aces = [c for c in side if c.rank == Rank.ACE]
        led_aces = {t[0][1].suit for t, _w in game.tricks
                    if t[0][0] == seat and t[0][1].rank == Rank.ACE and t[0][1].suit != trump}
        if len(aces) + len(led_aces) >= 2:
            if aces:
                return max(aces, key=lambda c: (sum(d.suit == c.suit for d in side), c.suit.value))
            again = [c for c in side if c.suit in led_aces]
            if again:
                voids = self._shown_voids(game)
                attackers = [s for s in range(4) if team_of(s) == team_of(game.contract["seat"])]
                gone = [c for cards in game.played for c in cards]

                def ruff_chance(s):
                    return (any(s in voids[a] and trump not in voids[a] for a in attackers),
                            sum(c.suit == s for c in gone) + sum(c.suit == s for c in game.hands[seat]), s.value)

                suit = max({c.suit for c in again}, key=ruff_chance)
                return min((c for c in again if c.suit == suit), key=lambda c: (c.points(trump), c.strength(trump)))
        return AsRBot().defence_lead(game, seat, legal)

    @staticmethod
    def _shown_voids(game):
        """Couleurs dont chaque joueur a montré qu'il n'en a plus (il n'a pas fourni)."""
        voids = [set() for _ in range(4)]
        for trick in [t for t, _w in game.tricks] + ([game.trick] if game.trick else []):
            led = trick[0][1].suit
            for s, c in trick[1:]:
                if c.suit != led:
                    voids[s].add(led)
        return voids

    @staticmethod
    def _called_suits(game, seat):
        """Couleurs que le partenaire m'a demandées en défaussant sur mes entames atout (comme AsR)."""
        return AsRBot._called_suits(game, seat)

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
