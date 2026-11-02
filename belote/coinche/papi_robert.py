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
Réponse par-dessus l'adversaire (même règle qu'AsR, voir asr.contested_answer) : mon partenaire annonce,
l'adversaire suivant surenchérit, je n'ai pas encore parlé : sur 90, complément (Valet, ou 9 au moins
second) -> 110 sur 100, 120 sur 110 (+10 par As au-delà du premier), 130 sur 120 avec un As (complément
troisième : 130 +10 par As) ; sur 100 : son annonce +10 par As sur 110 ou 120, 140 sur 130 avec les 3 As ;
sur 110 ou 120 : ma réponse habituelle comptée par-dessus l'annonce adverse. Ensuite l'ouvreur se tait.
Monter sur mon partenaire dans ma couleur (règle en plus, seulement quand je n'ai pas de réponse ; le
complément et les réponses passent d'abord) : sur son 90, mon vrai 100 se dit 110 (+10), un énorme 90
(Valet cinquième, ou 9 sixième avec la belote) se dit 100 ; sur son 100 ou plus, ma vraie valeur si elle
dépasse son annonce (il dit 100, je dis 120 : un vrai 120). Mon partenaire lit 10 de moins sur son 90
(110 = un 100, 100 = un énorme 90), la vraie valeur au-dessus, et me répond comme d'habitude.
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
sinon on contre ; cette enchère forcée n'est faite que par le dernier à parler (avant lui, on ne coinche
que si la main le justifie).
Coinche : même règle que CoincheBot à mon tour ; à la volée, seulement quasi sûr de la chute, belote
adverse comprise (même règle qu'AsR).
Pas de surcoinche.

Jeu :
- attaque : on retire les atouts adverses. Partenaire qui a annoncé l'atout le premier : je lui rends la
  main (petit atout, ou sans atout la couleur qu'il a appelée, sinon une petite carte) ; sinon atouts forts
  d'abord quand le plus gros est maître ; sinon : seul atout, le 9 sec jamais, l'As ou plus petit oui ;
  avec d'autres, je garde le plus gros et j'entame la carte qui fait monter le joueur suivant le plus haut
  (9-As-10-7, Valet dehors : le 10), si je peux me permettre de perdre le pli, sinon la suivante, sinon la
  plus petite ; puis les As ; sans atout (adversaires encore à l'atout), une petite carte plutôt que les As ;
  exception : mon dernier atout, je le garde si un atout adverse est encore dehors, que ma main est faible
  (aucune carte maîtresse hors atout) et que mon partenaire n'a pas annoncé de grande force (moins de 110) ;
- défense, sur le pli de mon partenaire dans une couleur hors atout : si l'attaque peut encore avoir de
  l'atout, je mets mon As (sinon il risque d'être coupé au tour suivant), sauf si l'attaquant qui joue
  après moi va couper ;
- défense : avec au moins 2 As hors atout, je les joue d'abord, puis je rejoue une de ces couleurs pour
  faire couper ; sinon la défense d'AsR (faire couper le preneur, pas d'entame atout) ;
- signal de belote du partenaire (Roi d'abord : nombre pair d'atouts, Dame : impair), lu comme AsR : je le
  recoupe avec la suite et j'arrête l'atout quand les adversaires n'en ont sûrement plus ;
- appels (équipe qui a pris, comme AsR) : sur l'atout du partenaire, appel direct (une carte de la
  couleur) dans la famille de l'atout, appel indirect (couleur sœur) sinon ; le partenaire rejoue la couleur ;
- contrat coinché : on garde ses atouts (pas d'entame atout) ;
- sur l'entame atout de mon partenaire (en deuxième ou troisième), je prends avec le plus petit atout qui
  bat tous ceux qui peuvent encore venir derrière moi (comme AsR) ;
- As-10 dans la couleur demandée, sur un pli adverse que je peux prendre : je prends d'abord avec l'As ;
- pas d'impasse sur un pli adverse hors atout (comme AsR) : coupé, ma plus petite ; avec l'As en deuxième ou
  troisième, l'As ; sans l'As (pas tombé) : en dernier la plus grosse qui prend, avant la plus petite, ou une
  carte moyenne si mon partenaire, après moi, a appelé la couleur ;
- après les atouts (attaque) : mes As, puis mes cartes maîtresses, puis la couleur appelée, puis la plus
  petite carte ;
- un appel se lit seulement si mon partenaire m'a annoncé des As, et pas si j'ai l'As de la couleur
  demandée (jeter un As est toujours un appel : la longue) ;
- on ne défausse jamais un As sans le 10 et le Roi derrière, sauf si on n'a pas le choix.
Le reste du jeu en second, troisième ou quatrième est celui de CoincheBot.
"""
from ..core.cards import Card, Rank, Suit
from .asr import AsRBot, answered_over_opponent, contested_answer, last_to_speak, volley_coinche_ok
from .bots import CoincheBot, wants_coinche
from .engine import CAPOT, SUITS, partner_of, team_of, trick_winner
from .inference import may_hold, shown_voids, trump_ceilings

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


_ASR = []


def _asr():
    """Un robot AsR pour reprendre ses règles de jeu (il n'a pas d'état)."""
    if not _ASR:
        _ASR.append(AsRBot())
    return _ASR[0]


def huge_ninety(hand, suit):
    """Énorme 90 : le Valet cinquième ou plus, ou le 9 sixième ou plus avec la belote."""
    r, n = _ranks(hand, suit), sum(c.suit == suit for c in hand)
    return (Rank.JACK in r and n >= 5) or (Rank.NINE in r and n >= 6 and has_belote(hand, suit))


def over_partner(hand, value, true, suit):
    """Monter sur l'annonce de mon partenaire dans ma couleur (seulement quand je n'ai pas de réponse) :
    - sur son 90 : mon vrai 100 (ou plus) se dit 10 de plus (110) ; un énorme 90 se dit 100 ;
    - sur son 100 ou plus : ma vraie valeur, si elle dépasse son annonce.
    Sur 80, rien de plus (règles du 80)."""
    if true < 90:
        return None
    options = [(trump_value(hand, s), majors(hand, s), strength_score(hand, s), s) for s in SUITS
               if s != suit and trump_value(hand, s)]
    if not options:
        return None
    mine, _m, _st, new = max(options, key=lambda o: o[:3])
    if true == 90:
        if mine >= 100 or huge_ninety(hand, new):
            return ("bid", mine + 10, new)
        return None
    return ("bid", mine, new) if mine > value else None


class PapiRobertBot(CoincheBot):
    name = "Papi Robert"

    @property
    def _asr(self):
        return _asr()

    @staticmethod
    def volley_coinche(game, seat):
        """Coinche à la volée (hors de mon tour) : seulement quasi sûr de la chute (comme AsR)."""
        return volley_coinche_ok(game.hands[seat], game.contract)

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
            over = self._over_opponent(game, seat, i, value, true, suit)
            if over is not False:
                return over
            answer = response(hand, true, suit)
            if answer is None:
                return over_partner(hand, value, true, suit)  # pas de réponse : je monte chez moi si je peux
            answer, new = answer
            if answer == CAPOT:
                return ("bid", CAPOT, new)
            if new == suit:
                return ("bid", value + answer - true, suit)
            opp = game.contract if team_of(game.contract["seat"]) != team_of(seat) else None
            if opp is not None and opp["value"] >= 90:
                return ("bid", answer + 10, new) if answer >= opp["value"] else None  # collage
            return ("bid", answer, new)  # je change d'atout
        if answered_over_opponent(game, seat):
            return None  # mon partenaire a répondu par-dessus l'adversaire : je me tais
        if len(mine) == 1:
            _k, value, suit = bids[mine[0]][1]
            other_suit = any(a[2] != suit for i, a in partner_bids if i > mine[0])
            if value == 80 and trump_value(hand, suit) == 100 and not other_suit:
                return ("bid", 100, suit)  # ouvert à 80 avec un jeu de 100 : je remonte si c'est possible
            if partner_bids and partner_bids[-1][0] > mine[0]:
                relaunch = self._relaunch(hand, bids[mine[0]][1], partner_bids[-1][1])
                if relaunch is not None:
                    return relaunch
                return self._answer_jump(game, hand, mine[0], partner_bids[-1])
        return None

    @staticmethod
    def _over_opponent(game, seat, index, value, true, suit):
        """Un adversaire a surenchéri juste après l'annonce d'indice index de mon partenaire : ma réponse
        par-dessus lui (action, ou None pour passer) ; False si la règle ne s'applique pas."""
        contract = game.contract
        opp_after = any(team_of(s) != team_of(seat) and a[0] == "bid" for s, a in game.bids[index + 1:])
        if (not opp_after or contract is None or team_of(contract["seat"]) == team_of(seat)
                or CAPOT in (value, contract["value"]) or true < 90):
            return False
        hand, cur = game.hands[seat], contract["value"]
        if true in (90, 100):
            v = contested_answer(hand, true, suit, cur)
            return ("bid", v, suit) if v is not None else None
        normal = _response(hand, true, suit)
        if normal == CAPOT:
            return ("bid", CAPOT, suit)
        return ("bid", cur + normal - true, suit) if isinstance(normal, int) else None

    def _answer_jump(self, game, hand, my_index, partner_bid):
        """Mon partenaire est monté sur mon annonce dans sa couleur : sur mon 90, je lis 10 de moins (110 = un
        100, 100 = un énorme 90) ; sur mon 100 ou plus, la vraie valeur ; je réponds comme d'habitude."""
        _k, value, suit = game.bids[my_index][1]
        _i, (_k2, pv, ps) = partner_bid
        if ps == suit or value < 90 or pv == CAPOT:
            return None
        true = pv - 10 if self._true_value(game, my_index) == 90 else pv
        answer = response(hand, true, ps)
        if answer is None or answer[1] != ps:
            return None
        return ("bid", CAPOT if answer[0] == CAPOT else pv + answer[0] - true, ps)

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
        contrat les fait sortir, une vraie annonce si j'en ai une ; sinon, seulement si je suis le dernier à
        parler, on monte juste au-dessus dans une vraie couleur d'atout, sinon on contre."""
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
                or (action is not None and action in legal and action[0] != "pass")
                or not last_to_speak(game, seat)):
            return action
        hand = game.hands[seat]
        suits = [s for s in SUITS if s != contract["suit"] and trump_value(hand, s)]
        if suits and value < MAX_BID:
            return ("bid", value + 10, max(suits, key=lambda s: (trump_value(hand, s), strength_score(hand, s))))
        return ("coinche",)

    # ---------- jeu ----------
    def play(self, game, seat):
        legal = game.legal_cards(seat)
        card = self._play(game, seat, legal)
        return self._asr._belote_signal(game, seat, legal, card)  # signal de belote (Roi pair, Dame impair)

    def _play(self, game, seat, legal):
        trick, trump, hand = game.trick, game.trump, game.hands[seat]
        if not trick:
            return self.lead(game, seat, legal)
        asr = self._asr
        partner = partner_of(seat)
        attacking = team_of(game.contract["seat"]) == team_of(seat)
        led = trick[0][1].suit
        winner = trick[trick_winner(trick, trump)][0]
        if attacking and trick[0][0] == partner and led == trump and not any(c.suit == trump for c in hand):
            call = AsRBot._call_discard(hand, self._allowed_discards(game, seat, legal), trump)
            if call is not None:
                return call
        if attacking and trick[0][0] == partner and led == trump and len(trick) < 3:
            # sur l'entame atout du partenaire, le plus petit atout qui bat tous ceux qui peuvent encore venir
            # derrière moi (comme AsR) : je prends la main pour faire tomber les atouts
            sure = asr._sure_trump(game, seat, legal)
            if sure is not None:
                return sure
        kings = asr._guarded_kings(game, seat)
        if kings and not any(c.suit == led for c in legal):
            legal = [c for c in legal if c.suit not in kings] or legal  # je ne défausse pas la garde du Roi
        if winner == partner and len(hand) == 2 and len(legal) == 2:
            card = asr._give_lost_card(game, seat, legal)  # avant-dernier pli : je garde la carte qui peut gagner
            if card is not None:
                return card
        if led in kings and winner == partner:
            small = [c for c in legal if c.rank != Rank.KING]
            if small:
                return min(small, key=lambda c: c.strength(trump))  # je garde mon Roi troisième
        card = self._defence_ace(game, seat, legal) if not attacking else self._attack_ace(game, seat, legal)
        if card is not None:
            return card
        card = self._last_on_partner(game, seat, legal)
        if card is not None:
            return card
        card = self._ace_before_ten(game, seat, legal)
        if card is not None:
            return card
        card = self._no_finesse(game, seat, legal)
        if card is not None:
            return card
        if attacking and winner == partner and not any(c.suit == led for c in legal):
            card = self._ace_call(game, seat, legal)
            if card is not None:
                return card
        legal = self._allowed_discards(game, seat, legal)
        if winner == partner:
            # partenaire sûr de faire le pli : d'abord mon 10 sec ; un 10 accompagné, je le garde seulement s'il
            # fera un autre pli (comme AsR) ; pas de 10 du tout si le pli n'est pas sûr
            sure = asr._partner_sure(game, seat)
            dry = [c for c in legal if c.rank == Rank.TEN and c.suit != trump and sum(d.suit == c.suit for d in hand) == 1]
            if dry and sure:
                return dry[0]
            keep_ten = asr._keep_accompanied_ten(game, seat)  # 10 accompagné gardé seulement s'il fera un pli
            keep = [c for c in legal if not (c.rank == Rank.TEN and c.suit != trump
                                             and (not sure or (keep_ten and sum(d.suit == c.suit for d in hand) > 1)))]
            legal = keep or legal
        return super().play(game, seat, legal)

    @staticmethod
    def _attack_ace(game, seat, legal):
        """Attaque, pli du partenaire dans une couleur hors atout, j'ai l'As : je le mets si la carte de mon
        partenaire n'est pas maître (un joueur après moi peut encore la battre), sauf si l'adversaire qui joue
        après moi va couper."""
        trick, trump, hand = game.trick, game.trump, game.hands[seat]
        led = trick[0][1].suit
        best = trick[trick_winner(trick, trump)]
        ace = Card(led, Rank.ACE)
        if led == trump or best[0] != partner_of(seat) or best[1].suit == trump or ace not in legal:
            return None
        later = [s for s in range(4) if s != seat and all(t != s for t, _c in trick)]
        gone = {c for cards in game.played for c in cards} | {c for _s, c in trick}
        voids, ceilings = shown_voids(game), trump_ceilings(game)
        beaters = [Card(led, r) for r in Rank if Card(led, r).strength(trump) > best[1].strength(trump)
                   and Card(led, r) not in gone and Card(led, r) not in hand]
        if not any(may_hold(game, s, c, voids, ceilings) for s in later for c in beaters):
            return None  # sa carte est maître : je garde mon As
        nxt = (seat + 1) % 4
        unseen = [Card(trump, r) for r in Rank if Card(trump, r) not in gone and Card(trump, r) not in hand]
        if nxt in later and led in voids[nxt] and any(may_hold(game, nxt, c, voids, ceilings) for c in unseen):
            return min((c for c in legal if c.suit == led), key=lambda c: (c.points(trump), c.strength(trump)))
        return ace

    @staticmethod
    def _last_on_partner(game, seat, legal):
        """Atouts tombés, je joue en dernier sur le pli de mon partenaire dans une couleur hors atout : ma carte
        maîtresse, je la garde s'il reste au moins 3 cartes de la couleur dehors (je donne la plus chère des
        autres), sinon je la donne ; un 10 non maître (As pas tombé) est donné (comme AsR)."""
        trick, trump, hand = game.trick, game.trump, game.hands[seat]
        led = trick[0][1].suit
        if len(trick) != 3 or led == trump or trick[trick_winner(trick, trump)][0] != partner_of(seat):
            return None
        cards = [c for c in legal if c.suit == led]
        gone = {c for cards_ in game.played for c in cards_} | {c for _s, c in trick}
        if not cards or any(Card(trump, r) not in gone and Card(trump, r) not in hand for r in Rank):
            return None
        value = lambda c: (c.points(trump), c.strength(trump))
        masters = [c for c in cards if AsRBot._is_master(c, trump, gone, hand)]
        others = [c for c in cards if c not in masters]
        out = [Card(led, r) for r in Rank if Card(led, r) not in gone and Card(led, r) not in hand]
        if masters and others and len(out) >= 3:
            return max(others, key=value)
        if masters:
            return max(masters, key=value)
        ten, ace = Card(led, Rank.TEN), Card(led, Rank.ACE)
        if ten in cards and ace not in gone and ace not in hand:
            return ten  # 10 non maître : je le donne, l'As le prendrait plus tard
        return None

    @staticmethod
    def _ace_call(game, seat, legal):
        """Je ne fournis pas sur le pli de mon partenaire : j'ai As-10-Roi dans une couleur, je jette l'As
        (appel : j'ai la longue dans cette couleur)."""
        trump, hand = game.trump, game.hands[seat]
        for ace in (c for c in legal if c.rank == Rank.ACE and c.suit != trump):
            if all(any(d.suit == ace.suit and d.rank == r for d in hand) for r in (Rank.TEN, Rank.KING)):
                return ace
        return None

    def _no_finesse(self, game, seat, legal):
        """Pas d'impasse quand je fournis une couleur hors atout sur un pli adverse :
        - déjà coupé par l'adversaire : ma plus petite carte ;
        - j'ai l'As, en deuxième ou troisième : l'As tout de suite ;
        - je n'ai pas l'As et il n'est pas tombé : en dernier, ma plus grosse carte qui prend (le 10), sinon la
          plus petite ; avant, ma plus petite, ou une carte moyenne (Roi, Dame, Valet) si mon partenaire, qui
          joue après moi, a appelé la couleur (il a l'As : l'adversaire entre nous doit mettre une grosse carte).
        None : la règle générale (l'As est tombé, ou j'ai l'As en dernier)."""
        trick, trump, hand = game.trick, game.trump, game.hands[seat]
        led = trick[0][1].suit
        cards = [c for c in legal if c.suit == led]
        best = trick[trick_winner(trick, trump)]
        if led == trump or not cards or best[0] == partner_of(seat):
            return None
        strength = lambda c: c.strength(trump)
        small = min(cards, key=lambda c: (c.points(trump), strength(c)))
        if best[1].suit == trump:
            return small  # déjà coupé
        last = len(trick) == 3
        ace = Card(led, Rank.ACE)
        gone = {c for cards_ in game.played for c in cards_} | {c for _s, c in trick}
        if ace in cards:
            return None if last else ace
        if ace in gone:
            return None
        winners = [c for c in cards if trick_winner(trick + [(seat, c)], trump) == len(trick)]
        if last:
            return max(winners, key=strength) if winners else small
        partner_after = all(s != partner_of(seat) for s, _c in trick)
        if partner_after and led in self._called_suits(game, seat):
            mids = [c for c in cards if c.rank in (Rank.KING, Rank.QUEEN, Rank.JACK)]
            if mids:
                return max(mids, key=strength)
        return small

    @staticmethod
    def _ace_before_ten(game, seat, legal):
        """As-10 dans la couleur demandée (hors atout), pli adverse que je peux prendre : je prends d'abord
        avec l'As (pas avec le 10)."""
        trick, trump = game.trick, game.trump
        led = trick[0][1].suit
        ace, ten = Card(led, Rank.ACE), Card(led, Rank.TEN)
        if led == trump or ace not in legal or ten not in legal:
            return None
        if trick[trick_winner(trick, trump)][0] == partner_of(seat):
            return None
        return ace if trick_winner(trick + [(seat, ace)], trump) == len(trick) else None

    @staticmethod
    def _defence_ace(game, seat, legal):
        """Défense, pli du partenaire dans une couleur hors atout, j'ai l'As et l'attaque peut encore avoir de
        l'atout : je mets mon As (au tour suivant il risque d'être coupé). Sauf si l'attaquant qui joue après
        moi va couper (il n'a plus la couleur et peut avoir de l'atout) : ma plus petite carte."""
        trick, trump, hand = game.trick, game.trump, game.hands[seat]
        led = trick[0][1].suit
        winner = trick[trick_winner(trick, trump)]
        ace = Card(led, Rank.ACE)
        if led == trump or winner[0] != partner_of(seat) or winner[1].suit == trump or ace not in legal:
            return None
        gone = {c for cards in game.played for c in cards}
        unseen = [Card(trump, r) for r in Rank if Card(trump, r) not in gone and Card(trump, r) not in hand]
        voids, ceilings = shown_voids(game), trump_ceilings(game)
        attackers = [s for s in range(4) if team_of(s) != team_of(seat)]
        if not any(may_hold(game, a, c, voids, ceilings) for a in attackers for c in unseen):
            return None  # atouts tombés : la règle générale
        nxt = (seat + 1) % 4
        if len(trick) < 3 and led in voids[nxt] and any(may_hold(game, nxt, c, voids, ceilings) for c in unseen):
            return min((c for c in legal if c.suit == led), key=lambda c: (c.points(trump), c.strength(trump)))
        return ace

    @staticmethod
    def _allowed_discards(game, seat, legal):
        """Jamais défausser un As, sauf avec le 10 et le Roi derrière sur le pli de mon partenaire (c'est un
        appel : j'ai la longue), ou si on n'a pas le choix."""
        trick, trump = game.trick, game.trump
        if not trick:
            return legal
        led = trick[0][1].suit
        hand = game.hands[seat]
        partner_wins = trick[trick_winner(trick, trump)][0] == partner_of(seat)

        def protected(c):
            return partner_wins and all(any(d.suit == c.suit and d.rank == r for d in hand)
                                        for r in (Rank.TEN, Rank.KING))

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
        contract = game.contract
        last_one = (contract["mult"] == 1 or contract["value"] == CAPOT) and self._asr._last_opponent_trump(game, seat)
        if last_one and len(trumps) >= 2:
            # un seul atout dehors et j'en ai un plus fort qui n'est pas mon dernier : je le fais tomber avec le
            # plus petit de ceux-là (comme AsR)
            gone = {c for cards in game.played for c in cards}
            unseen = next(c for c in CoincheBot._all_trumps(trump) if c not in gone and c not in game.hands[seat])
            higher = [c for c in trumps if c.strength(trump) > unseen.strength(trump)]
            if higher:
                return min(higher, key=lambda c: c.strength(trump))
        if last_one and side != legal:
            no_trump_lead = True  # sinon je ne le fais pas tomber : je le fais couper
            trumps = []
        if game.contract["mult"] > 1:
            legal = side  # coinché : on garde ses atouts pour couper
        elif trumps and opponents_trumps:
            if len(trumps) == 1 and side != legal and self._keep_last_trump(game, seat):
                no_trump_lead = True
            elif gives_lead:
                return min(trumps, key=lambda c: c.strength(trump))  # je rends la main à mon partenaire
            else:
                choice = self._trump_choice(game, seat, trumps)
                if choice is not None:
                    return choice
                no_trump_lead = True  # le 9 sec : je ne l'entame jamais
        if opponents_trumps and no_trump_lead:
            # sans atout (ou je garde le dernier) : la couleur appelée, sinon une petite carte plutôt que les As
            if called_lead:
                return called_lead
            if last_one:
                ruff = self._asr._force_ruff(game, seat, side)  # une couleur que l'adversaire n'a plus
                if ruff is not None:
                    return ruff
            return min(side, key=lambda c: (c.points(trump), c.strength(trump)))
        aces = [c for c in legal if c.rank == Rank.ACE and c.suit != trump]
        if aces:
            return aces[0]
        gone = {c for cards in game.played for c in cards}
        masters = [c for c in legal if c.suit != trump and AsRBot._is_master(c, trump, gone, game.hands[seat])]
        if masters:
            return max(masters, key=lambda c: (c.points(trump), c.strength(trump)))  # mes cartes maîtresses
        if called_lead:
            return called_lead
        return min(legal, key=lambda c: (c.suit == trump, c.points(trump), c.strength(trump)))

    @staticmethod
    def _trump_choice(game, seat, trumps):
        """Quel atout entamer (attaque, les adversaires peuvent en avoir) :
        - mon plus gros atout est maître : je le joue ;
        - sinon, c'est mon seul atout : le 9 sec jamais (None), l'As ou plus petit je le joue ;
        - sinon je garde le plus gros et je choisis parmi les autres, d'abord la carte qui oblige le joueur
          suivant à monter le plus haut (le plus petit atout dehors au-dessus d'elle est le plus fort possible ;
          à égalité la moins chère), si je peux me permettre de perdre le pli (ma carte, le plus gros atout
          dehors et 10 points : les adversaires restent sous ce qui nous ferait chuter) ; sinon la suivante ;
          sinon mon plus petit atout."""
        trump, hand = game.trump, game.hands[seat]
        strength = lambda c: c.strength(trump)
        gone = {c for cards in game.played for c in cards} | {c for _s, c in game.trick}
        outside = [Card(trump, r) for r in Rank if Card(trump, r) not in gone and Card(trump, r) not in hand]
        top = max(trumps, key=strength)
        if all(strength(top) > strength(o) for o in outside):
            return top
        if len(trumps) == 1:
            return None if top.rank == Rank.NINE else top
        others = [c for c in trumps if c != top]

        def forced(c):  # l'atout le moins cher que le suivant peut mettre pour monter
            return min((strength(o) for o in outside if strength(o) > strength(c)), default=99)

        team, contract = team_of(seat), game.contract
        partner = partner_of(seat)
        ours = game.belote_seat == seat or (game.belote_seat == partner and any(
            c.suit == trump and c.rank in (Rank.KING, Rank.QUEEN) for c in game.played[partner]))
        limit = -1 if contract["value"] == CAPOT else 162 - contract["value"] + (20 if ours else 0)
        biggest = max((o.points(trump) for o in outside), default=0)
        for c in sorted(others, key=lambda c: (-forced(c), strength(c))):
            if game.trick_points[1 - team] + c.points(trump) + biggest + 10 <= limit:
                return c
        return min(trumps, key=strength)

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
        """Couleurs dont chaque joueur a montré qu'il n'en a plus (voir inference.py)."""
        return shown_voids(game)

    @staticmethod
    def _called_suits(game, seat):
        """Couleurs que le partenaire m'a demandées :
        - en défaussant sur mes entames atout (appel direct ou indirect, comme AsR), seulement s'il m'a annoncé
          des As pendant les enchères, et pas si l'As de la couleur demandée est chez moi (ce n'était pas un
          appel, il a juste défaussé) ;
        - en jetant un As (il a la longue), sur mon entame atout ou sur un pli que j'ai gagné."""
        trump, partner = game.trump, partner_of(seat)
        showed_aces = AsRBot._partner_showed_aces(game, seat)
        mine = set(game.hands[seat]) | set(game.played[seat])
        calls = set()
        for trick, _w in game.tricks:
            if trick[0][0] != seat or trick[0][1].suit != trump:
                continue
            card = dict(trick)[partner]
            if card.suit == trump:
                continue
            if card.rank == Rank.ACE:
                calls.add(card.suit)
                continue
            target = card.suit if card.suit == SISTER[trump] else SISTER[card.suit]
            if showed_aces and Card(target, Rank.ACE) not in mine:
                calls.add(target)
        for trick, winner in game.tricks:
            card = dict(trick)[partner]
            if winner == seat and card.rank == Rank.ACE and card.suit not in (trump, trick[0][1].suit):
                calls.add(card.suit)
        return calls

    @staticmethod
    def _opponents_may_have_trumps(game, seat):
        """Reste-t-il un atout dehors qu'un adversaire peut encore avoir (ni chicane, ni plafond trop bas) ?"""
        trump = game.trump
        gone = {c for cards in game.played for c in cards} | {c for _, c in game.trick}
        outstanding = [c for c in CoincheBot._all_trumps(trump) if c not in gone and c not in game.hands[seat]]
        if not outstanding:
            return False
        if AsRBot._belote_says_none(game, seat):
            return False  # signal de belote du partenaire recoupé avec la suite (comme AsR)
        voids, ceilings = shown_voids(game), trump_ceilings(game)
        return any(may_hold(game, opp, c, voids, ceilings) for opp in ((seat + 1) % 4, (seat + 3) % 4)
                   for c in outstanding)
