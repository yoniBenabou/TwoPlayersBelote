"""Robot "AsR" pour la Coinche à 4 : conventions du document "Belote —
conventions d'annonces et stratégie de jeu" (version consolidée).

Familles : rouge = cœur et carreau, noir = pique et trèfle. La "couleur sœur"
d'une couleur est l'autre couleur de sa famille ; la "famille opposée" à
l'atout, ce sont les deux couleurs de l'autre famille. Majeures = Valet et 9
d'atout.

Ouvertures (couleur choisie : la plus forte structure d'atout, puis la plus
forte couleur), dans cet ordre :
1. maîtrise forte (Valet + 9 et 5 atouts, ou Valet + 9 + As et 4 atouts) : on
   annonce directement sa force, sous forme de demande : 100 si je cherche au moins un As rouge et
   un As noir, sinon 110 (As de la famille opposée) s'il en manque un, sinon 120 (As de la couleur
   sœur), sinon 130 (10 de la famille opposée), sinon 140 (10 de la couleur sœur) ;
2. maîtrise (Valet + 9 + As, ou Valet + 9 quatrièmes) qui ne cherche des As que dans une famille :
   la demande directe, comme la maîtrise forte : 110 s'il ne me manque que des As de la famille
   opposée, 120 s'il ne me manque que l'As sœur (130/140 s'il ne manque aucun As) ;
3. avec au moins deux As (atout compris) : 80, pour les signaler, même sans
   atout ;
4. maîtrise qui cherche au moins un As rouge et au moins un As noir (il me manque l'As de la couleur
   sœur et au moins un As de la famille opposée, ou les trois As) : 100 ;
5. Valet au moins troisième ou 9 au moins quatrième, avec au moins un As
   (d'atout ou à côté) : 90 ; jamais 90 sans As.
Réponses (une fois, puis relances prévues par le document). Dans toutes les réponses, "+10 par As"
compte seulement les As hors atout, jamais l'As d'atout :
- sur 80, même couleur : 90 avec le Valet ou le 9 au moins second (même sans As : seule l'ouverture à
  90 en exige un), 100 avec les deux, +10 par As hors atout ; autre couleur, avec la maîtrise dans
  cette couleur, comme à l'ouverture : 100 si je cherche des As rouges et noirs, sinon la demande
  directe (110 si je ne cherche que des As de la famille opposée, 120 si je ne cherche que l'As sœur).
  L'ouvreur à 80 : sur 90 dans sa
  couleur, s'il a le complément, 100, +10 si ses deux As (déjà annoncés
  par le 80) sont hors atout, +10 par As hors atout en plus ; sur 100 dans
  une autre couleur, +10 avec deux As hors de cet atout, +10 par As en plus ;
  sur 110/120/130/140 dans une autre couleur, il répond à la demande (+10 par As de la famille opposée
  sur 110, +10 avec l'As sœur sur 120, les 10 sur 130/140) ; sur 90 dans une autre couleur, avec le
  complément, 100, +10 par As ; sans réponse (un adversaire a parlé), 100 avec au moins le Valet
  quatrième et un As hors atout (ou une maîtrise) ;
- sur 90 : +10 pour le complément (le Valet, ou le 9 au moins second) et +10
  par As ; rien sans complément ; le 9 sec ne se signale pas au premier tour,
  au second tour seulement (+10) avec un As à côté ou si l'équipe est très en
  retard (500 points) ;
- sur 100 : +10 par As hors atout (jamais l'As d'atout). Avec quatre plis maîtres hors atout : si
  l'ouvreur a la partance, capot ; si c'est moi, capot avec au moins un atout, sinon +10 par As ; si
  c'est un adversaire, capot avec un atout et les trois As hors atout, sinon +10 par As. 100 -> 110/120/130 :
  si l'équipe a les trois As hors atout (ceux du partenaire et les miens), l'ouvreur remonte de +10
  pour demander les autres plis maîtres ; le partenaire ajoute +10 par pli maître après les As (son
  As compris dans la couleur ne compte pas, et derrière l'As de l'ouvreur son 10 est maître) ; sans
  les trois As, l'ouvreur ne remonte pas (ce serait une fausse information) ;
- sur 110 : +10 par As de la famille opposée ; 110 -> 120 -> 130 : l'ouvreur
  qui a l'autre As de la famille opposée dit 130, le partenaire ajoute +10 par pli
  supplémentaire dans la famille opposée (sans recompter son As) ;
- sur 120 : +10 avec l'As de la couleur sœur ; sur 130 (demande initiale) :
  +10 par 10 de la famille opposée ; sur 140 : +10 avec le 10 sœur.
Capot de l'ouvreur : après 100 et +30 avec 5 atouts ; après 100, les trois As et les plis maîtres
annoncés, si ses plis attendus font au moins 8 (tous les plis) ; après les réponses sur 110, si ses
plis attendus (atouts, As, plis signalés) font au moins 8.
Collage : sur un 90 adverse, une main de 90 (donc avec un As) dit 100 (le partenaire la lit
comme un 90 et ne répond que le complément) ; une main de 100 saute à 110 (le
partenaire reste prudent : il passe) ; sur un 100 adverse, une vraie main de
100 dit 110 (lue comme un 100).
Coinche : même règle que CoincheBot. Surcoinche : seulement le preneur, quand sa main assure déjà
80 % des points de l'annonce (plis sûrs : atouts maîtres depuis le Valet, puis dans chaque autre
couleur les cartes qui se suivent depuis l'As ; chacun compté avec ma carte plus 10 points pour les
cartes des trois autres ; la belote en plus).

Jeu :
- quand mon partenaire a annoncé l'atout le premier, à 100 ou plus (maîtrise), et que nous avons pris
  (lui, ou moi qui lui ai répondu, par exemple 100 -> 110), si j'entame le premier pli avec de l'atout
  (sans le Valet ni le 9), j'entame petit atout : je lui donne la main, il fait tomber les atouts
  adverses avant que nos As soient joués ; pas si c'est contré ;
- contrée (coinchée ou surcoinchée), l'équipe qui a pris n'entame pas atout (sauf au capot) ;
- preneur très faible à l'atout (2 atouts dont le Valet, 3 dont le 9, ou moins) que le partenaire n'a
  pas soutenu dans l'atout : il n'entame pas atout, il garde ses atouts pour la fin, et surtout le
  plus fort (le Valet) pour être sûr de faire le dernier pli : s'il doit jouer atout, il met le plus petit ;
- quand le partenaire a montré le Valet et le 9 (100), j'entame atout dès que j'ai la main, avec mon plus
  petit (pas si c'est contré, sauf au capot) : il fait tomber les atouts adverses, puis me rend la main
  dans la couleur de mon appel ;
- sinon, l'équipe qui a pris joue atout tant que les adversaires peuvent en avoir, en
  séparant le Valet et le 9 de l'équipe : avec le 9 sans le Valet, petit atout
  d'abord (le Valet du partenaire prend, ou celui de l'adversaire tombe) ; avec
  le Valet quand le partenaire a montré le 9, le Valet puis un petit atout ;
  on garde son dernier atout s'il n'en reste qu'un dehors, quelle que soit sa force ;
- sur l'entame atout du partenaire (en deuxième ou troisième), je prends avec le plus petit atout
  qui bat tous ceux qui restent dehors ;
- signal de belote : celui qui a la belote dans l'équipe qui a pris joue le Roi
  en premier s'il a un nombre pair d'atouts (carte jouée comprise), la Dame
  s'il est impair ; le partenaire en déduit, quand c'est sûr, que les
  adversaires n'ont plus d'atout ;
- appels : quand le partenaire joue atout et que je n'en ai plus, je défausse
  pour demander la couleur de mon As : une carte de cette couleur si elle est
  de la famille de l'atout (appel direct), sinon une carte de sa couleur sœur
  (appel indirect) ; jeter l'As lui-même annonce la longue maîtresse (au moins
  As-10-Roi, pas au capot) ; le partenaire rejoue la couleur demandée (petite carte) avant
  d'encaisser ses As ; seulement dans l'équipe qui a pris ;
- on garde son dernier atout pour le dernier pli (pas d'entame de son dernier atout) ; s'il ne reste
  qu'un atout dehors et que j'ai un atout plus fort qui n'est pas mon dernier, je le fais tomber avec le
  plus petit de ceux-là (pas si c'est contré, sauf au capot) ; sinon on ne le fait pas tomber : on joue une carte
  d'une couleur que cet adversaire n'a plus, pour le faire couper (sauf au capot) : la plus faible de
  mes cartes maîtresses de cette couleur (son partenaire ne peut pas prendre le pli à sa place), sinon
  la plus petite ;
- ensuite : les cartes maîtresses (As, 10, Roi...), le Roi d'un Roi-10 quand
  l'As n'est pas tombé, puis la couleur la plus longue ;
- défense (pas d'appels en défense) : contre 140 ou plus, d'abord les cartes
  maîtresses ; sinon faire couper le preneur en jouant notre couleur la plus
  longue (celle qu'il n'a plus s'il l'a déjà montré : la plus faible de mes
  cartes maîtresses de cette couleur, sinon la plus petite) ; au premier pli, d'abord un As hors atout ; après avoir gagné un
  pli que j'ai entamé, je rejoue la même couleur avec ma plus grosse carte ;
  pas d'entame atout sauf s'il ne reste que ça ;
- on ne défausse jamais un As (ni ne le donne sur la coupe du partenaire) sans une carte maîtresse derrière lui
  dans sa couleur (le 10, ou la suivante si le 10 est tombé), sauf si on n'a pas le choix ;
- partenaire maître : s'il est sûr de faire le pli (je joue en dernier, ou sa carte est maîtresse et
  l'adversaire qui joue après moi ne peut pas couper), on lui donne en priorité son 10 sec (sinon l'As
  adverse le prendrait) ; jamais un 10 accompagné (il peut faire un pli) ;
- pas d'impasse, quand je fournis une couleur hors atout (à l'entame : cartes maîtresses d'abord) :
  - pli adverse déjà coupé : ma plus petite carte ;
  - pli adverse, j'ai l'As : l'As en deuxième ou troisième ; en dernier, l'As s'il reste plus de 2
    atouts dans le jeu, sinon la plus grosse carte qui prend sans l'As (l'As si lui seul prend) ;
  - pli adverse, l'As n'est ni chez moi ni sorti : en dernier, la plus grosse carte qui prend (le 10),
    sinon la plus petite ; avant, ma plus petite carte, ou une carte moyenne (Roi, Dame, Valet) si mon
    partenaire, qui joue après moi, a appelé la couleur (il a l'As) ;
  - pli du partenaire gagné dans la couleur, j'ai l'As : l'As (après le 10 sec, prioritaire), sauf si
    l'adversaire qui joue après moi va forcément couper (il n'a plus la couleur et peut avoir de
    l'atout) : ma plus petite ; s'il a coupé, pas d'As sans carte maîtresse derrière ;
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
    """Demande d'une maîtrise : 100 si je cherche un As rouge et un As noir, sinon 110, 120, 130 ou 140
    selon ce qui manque."""
    opp = opposite(suit)
    if missing_both_families(hand, suit):
        return 100
    if not all(has(hand, s, Rank.ACE) for s in opp):
        return 110
    if not has(hand, SISTER[suit], Rank.ACE):
        return 120
    if not all(has(hand, s, Rank.TEN) for s in opp):
        return 130
    return 140


def missing_both_families(hand, suit):
    """Il me manque un As dans chaque famille : l'As sœur et au moins un As de la famille opposée."""
    return not has(hand, SISTER[suit], Rank.ACE) and not all(has(hand, s, Rank.ACE) for s in opposite(suit))


def best_suit(hand):
    """(type, couleur) : la meilleure structure d'atout, puis la couleur la plus forte."""
    return max(((trump_type(hand, s), s) for s in SUITS),
               key=lambda o: (TYPE_RANK[o[0]], strength_score(hand, o[1])))


def natural_opening(hand):
    """(valeur, couleur, type) de l'ouverture AsR, ou None."""
    kind, suit = best_suit(hand)
    if kind == "strong":
        return ask_value(hand, suit), suit, kind
    if kind == "100" and not missing_both_families(hand, suit):
        # maîtrise, mais je ne cherche des As que dans une famille : je le demande directement
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


TRUMP_TOP = [Rank.JACK, Rank.NINE, Rank.ACE, Rank.TEN, Rank.KING, Rank.QUEEN, Rank.EIGHT, Rank.SEVEN]
OTHERS_PER_TRICK = 10  # estimation des points que les trois autres jettent sur un pli sûr


def sure_points(hand, trump):
    """Points assurés : les plis sûrs (atouts maîtres depuis le Valet, puis dans chaque autre couleur
    les cartes qui se suivent depuis l'As), chacun compté avec ma carte plus une estimation des cartes
    des trois autres ; la belote en plus."""
    tricks = []
    for r in TRUMP_TOP:
        if not has(hand, trump, r):
            break
        tricks.append(Card(trump, r))
    for s in SUITS:
        if s != trump:
            tricks += [Card(s, r) for r in ORDER[:top_tricks(hand, s)]]
    belote = 20 if has(hand, trump, Rank.KING) and has(hand, trump, Rank.QUEEN) else 0
    return sum(c.points(trump) + OTHERS_PER_TRICK for c in tricks) + belote


def master_tricks(hand, trump):
    return sum(top_tricks(hand, s) for s in SUITS if s != trump)


class AsRBot(CoincheBot):
    name = "AsR"

    # ================= annonces =================
    def bid(self, game, seat):
        legal = game.legal_bids(seat)
        hand = game.hands[seat]
        if ("surcoinche",) in legal:
            return ("surcoinche",) if self._wants_surcoinche(game, seat) else ("pass",)
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
    def _wants_surcoinche(game, seat):
        """Seul le preneur surcoinche, quand sa main assure déjà 80 % des points de l'annonce."""
        contract = game.contract
        if contract["seat"] != seat:
            return False
        value = contract["value"]
        return sure_points(game.hands[seat], contract["suit"]) >= 0.8 * value

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
                return ("bid", value + 10 + 10 * side_aces(hand, suit), suit)
            if r == {Rank.NINE} and passed_since and (side_aces(hand, suit) >= 1 or self._behind(game, seat)):
                return ("bid", game.contract["value"] + 10, suit)  # 9 sec signalé au second tour
            return None
        if level == 100:
            if master_tricks(hand, suit) >= 4:
                action = self._four_masters_on_100(game, seat, suit)
                if action is not None:
                    return action
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
    def _four_masters_on_100(game, seat, trump):
        """Réponse au 100 du partenaire avec quatre plis maîtres hors atout, selon qui a la partance.
        None : on répond normalement, +10 par As hors atout."""
        hand = game.hands[seat]
        leader = (game.dealer + 1) % 4
        has_trump = any(c.suit == trump for c in hand)
        if leader == partner_of(seat):
            return ("bid", CAPOT, trump)
        if leader == seat:
            return ("bid", CAPOT, trump) if has_trump else None
        if has_trump and side_aces(hand, trump) == 3:  # un adversaire a la partance
            return ("bid", CAPOT, trump)
        return None

    @staticmethod
    def _extra_masters(hand, trump):
        """Plis maîtres hors atout en plus des As, quand l'équipe a les trois As : dans une couleur où
        j'ai l'As, les cartes qui le suivent ; sinon (l'As est chez le partenaire), celles qui suivent son As."""
        return sum(top_tricks(hand, s) - 1 if has(hand, s, Rank.ACE) else top_tricks(hand, s, above={Rank.ACE})
                   for s in SUITS if s != trump)

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
        if kind == "strong" or (kind == "100" and not missing_both_families(hand, other)):
            return ("bid", ask_value(hand, other), other)  # maîtrise : la demande des As qui me manquent
        if kind == "100":
            return ("bid", 100, other)  # je cherche des As rouges et noirs
        if Rank.JACK in r or (Rank.NINE in r and len(r) >= 2):
            # le Valet, ou le 9 au moins second ; en réponse, pas besoin d'As (seule l'ouverture à 90 en exige un)
            return ("bid", 90, suit)
        return None

    def _rebid(self, game, seat, mine, theirs):
        hand = game.hands[seat]
        first_i, (_k, first_value, first_suit) = mine[0]
        last_i = mine[-1][0]
        answer = next(((i, a) for i, a in reversed(theirs) if i > last_i), None)
        if answer is None:
            # pas de réponse : l'ouvreur à 80 remonte à 100 avec au moins le Valet quatrième et un As hors atout
            if len(mine) == 1 and first_value == 80:
                kind, suit = best_suit(hand)
                if kind not in ("100", "strong"):
                    jacks = [s for s in SUITS if has(hand, s, Rank.JACK) and len(ranks_in(hand, s)) >= 4
                             and side_aces(hand, s) >= 1]
                    suit = max(jacks, key=lambda s: strength_score(hand, s)) if jacks else None
                if suit is not None:
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
            # 100 -> +10 par As -> l'ouvreur remonte de 10 : on a les trois As, j'annonce mes autres plis maîtres
            if (p_first[1] == 100 and p_first[2] == suit and len(mine) == 1 and mine[0][1][2] == suit
                    and self._opponent_value(game, seat, before=theirs[0][0]) is None
                    and 110 <= mine[0][1][1] <= 130 and value == mine[0][1][1] + 10):
                extra = self._extra_masters(hand, suit)
                return ("bid", value + 10 * extra, suit) if extra > 0 else None
            return None
        n = len(ranks_in(hand, suit))
        if (first_value == 100 and suit == first_suit and value != CAPOT
                and self._opponent_value(game, seat, before=first_i) is None):
            action = self._rebid_100(hand, suit, mine, theirs, value, n)
            if action is not False:
                return action
        if len(mine) >= 2 and not (first_value == 110 and len(mine) == 2 and mine[1][1][1] == 130):
            return None
        if first_value == 80:
            if suit == first_suit and value == 90 and self._complement_of_90(ranks_in(hand, suit)):
                # mes deux As sont déjà annoncés par le 80 : +10 s'ils sont hors atout, +10 par As hors atout en plus
                return ("bid", 100 + 10 * max(0, side_aces(hand, suit) - 1), suit)
            if suit != first_suit and value == 100:
                k = side_aces(hand, suit)
                return ("bid", 100 + 10 * (k - 1), suit) if k >= 2 else None
            if suit != first_suit and value in (110, 120, 130, 140):
                # demande du partenaire dans sa couleur : comme une réponse à son ouverture
                k = {110: sum(has(hand, s, Rank.ACE) for s in opposite(suit)),
                     120: int(has(hand, SISTER[suit], Rank.ACE)),
                     130: sum(has(hand, s, Rank.TEN) for s in opposite(suit)),
                     140: int(has(hand, SISTER[suit], Rank.TEN))}[value]
                return ("bid", value + 10 * k, suit) if k else None
            if suit != first_suit and value == 90:
                r = ranks_in(hand, suit)
                return ("bid", 100 + 10 * side_aces(hand, suit), suit) if self._complement(r) else None
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
    def _rebid_100(hand, suit, mine, theirs, value, n):
        """Ouvreur à 100 : remonter de 10 si l'équipe a les trois As hors atout, puis capot si les plis
        attendus font 8. Renvoie False quand la séquence ne s'applique pas."""
        partner_bids = [a[1] for _i, a in theirs if a[2] == suit]
        if len(mine) == 1:
            aces = (value - 100) // 10  # +10 par As hors atout
            if aces >= 3 and n >= 5:
                return ("bid", CAPOT, suit)
            if 1 <= aces <= 3 and aces + side_aces(hand, suit) == 3:
                return ("bid", value + 10, suit)  # on a les trois As : annonce tes autres plis maîtres
            return None
        if len(mine) == 2 and len(partner_bids) >= 2:
            aces = (partner_bids[0] - 100) // 10
            if mine[1][1][1] != partner_bids[0] + 10 or aces + side_aces(hand, suit) != 3:
                return False
            extra = (value - mine[1][1][1]) // 10
            mine_tricks = AsRBot._extra_masters(hand, suit) + side_aces(hand, suit)
            if n + mine_tricks + aces + extra >= 8:
                return ("bid", CAPOT, suit)
            return None
        return False

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
        card = self._keep_top_trump(game, seat, legal, card)
        return self._belote_signal(game, seat, legal, card)

    def _keep_top_trump(self, game, seat, legal, card):
        """Preneur très faible à l'atout : son atout le plus fort est gardé pour le dernier pli ; s'il doit
        jouer atout et qu'il a le choix, il met le plus petit."""
        trump = game.trump
        if card.suit != trump or not self._weak_alone(game, seat):
            return card
        strength = lambda c: c.strength(trump)
        top = max((c for c in game.hands[seat] if c.suit == trump), key=strength)
        lower = [c for c in legal if c.suit == trump and c != top]
        return min(lower, key=strength) if card == top and lower else card

    def _follow(self, game, seat, legal):
        trick, trump = game.trick, game.trump
        hand = game.hands[seat]
        led = trick[0][1].suit
        partner = partner_of(seat)
        legal = self._keep_aces(game, seat, legal)
        # appel par défausse quand le partenaire joue atout et que je n'en ai plus
        attacking = team_of(game.contract["seat"]) == team_of(seat)
        if attacking and trick[0][0] == partner and led == trump and not any(c.suit == trump for c in hand):
            call = self._call_discard(hand, legal, trump, long_ok=game.contract["value"] != CAPOT)
            if call is not None:
                return call
        winning = trick[trick_winner(trick, trump)]
        if attacking and trick[0][0] == partner and led == trump and len(trick) < 3:
            sure = self._sure_trump(game, seat, legal)
            if sure is not None:
                return sure
        if led != trump and any(c.suit == led for c in legal):
            card = self._follow_side(game, seat, legal, winning)
            if card is not None:
                return card
        if winning[0] == partner:
            # partenaire sûr de prendre le pli : d'abord mon 10 sec (il serait pris par l'As) ; jamais un 10 accompagné
            dry = [c for c in legal if c.rank == Rank.TEN and c.suit != trump
                   and sum(d.suit == c.suit for d in hand) == 1]
            sure = self._partner_sure(game, seat)
            if dry and sure:
                return dry[0]
            # pli pas assuré : aucun 10 ; assuré : pas de 10 accompagné
            keep = [c for c in legal if not (c.rank == Rank.TEN and c.suit != trump
                                             and (not sure or sum(d.suit == c.suit for d in hand) > 1))]
            return super().play(game, seat, keep or legal)
        return super().play(game, seat, legal)

    def _follow_side(self, game, seat, legal, winning):
        """Je fournis une couleur hors atout (pas d'impasse) :
        - pli adverse déjà coupé : ma plus petite carte ;
        - pli adverse, j'ai l'As : l'As en deuxième ou troisième ; en dernier, l'As s'il reste plus de 2 atouts
          dans le jeu, sinon la plus grosse carte qui prend sans l'As (l'As si lui seul prend) ;
        - pli adverse, pas l'As et l'As pas sorti : en dernier, la plus grosse carte qui prend (le 10), sinon la
          plus petite ; avant, la plus petite, ou une carte moyenne (Roi, Dame, Valet) si le partenaire, qui joue
          après moi, a l'As (il l'a appelé) ;
        - pli du partenaire, j'ai l'As : l'As, sauf si l'adversaire qui joue après moi va forcément couper
          (il n'a plus la couleur et il peut avoir de l'atout) : ma plus petite carte.
        Renvoie None quand la règle générale s'applique (l'As est déjà sorti, par exemple)."""
        from .papi_robert import PapiRobertBot
        trick, trump, hand = game.trick, game.trump, game.hands[seat]
        led = trick[0][1].suit
        cards = [c for c in legal if c.suit == led]
        strength = lambda c: c.strength(trump)
        small = min(cards, key=strength)
        last = len(trick) == 3
        ace = Card(led, Rank.ACE)
        gone = {c for cards_ in game.played for c in cards_} | {c for _s, c in trick}
        trumps_left = [c for c in self._all_trumps(trump) if c not in gone]
        if winning[0] == partner_of(seat):
            if ace not in cards or winning[1].suit == trump:
                return None  # partenaire qui a coupé : pas d'As sans maîtresse derrière (_keep_aces)
            nxt = (seat + 1) % 4
            voids = PapiRobertBot._shown_voids(game)[nxt]
            outside = [c for c in trumps_left if c not in hand]
            if not last and led in voids and trump not in voids and outside:
                return small  # l'adversaire derrière moi va couper
            return ace
        if winning[1].suit == trump:
            return small  # déjà coupé
        winners = [c for c in cards if trick_winner(trick + [(seat, c)], trump) == len(trick)]
        if ace in cards:
            if not last or len(trumps_left) > 2:
                return ace
            others = [c for c in winners if c != ace]
            return max(others, key=strength) if others else ace
        if ace in gone:
            return None
        if last:
            return max(winners, key=strength) if winners else small
        attacking = team_of(game.contract["seat"]) == team_of(seat)
        if len(trick) == 1 and attacking and led in self._called_suits(game, seat):
            mids = [c for c in cards if c.rank in (Rank.KING, Rank.QUEEN, Rank.JACK)]
            if mids:
                return max(mids, key=strength)
        return small

    def _partner_sure(self, game, seat):
        """Le pli du partenaire est assuré : je joue en dernier, ou sa carte est maîtresse et l'adversaire
        qui joue après moi ne peut pas couper (il n'a plus d'atout, ou il n'en reste plus dehors)."""
        from .papi_robert import PapiRobertBot
        trick, trump, hand = game.trick, game.trump, game.hands[seat]
        if len(trick) == 3:
            return True
        best = trick[trick_winner(trick, trump)][1]
        seen = {c for cards in game.played for c in cards} | {c for _s, c in trick} | set(hand)
        unseen = [Card(best.suit, r) for r in Rank if Card(best.suit, r) not in seen]
        if any(c.strength(trump) > best.strength(trump) for c in unseen):
            return False
        if best.suit == trump:
            return True
        last = (seat + 1) % 4
        no_trump_left = all(c in seen for c in self._all_trumps(trump))
        return no_trump_left or trump in PapiRobertBot._shown_voids(game)[last]

    def _sure_trump(self, game, seat, legal):
        """Sur l'entame atout du partenaire : le plus petit atout qui bat tous ceux qui peuvent encore
        venir derrière moi (je prends la main pour faire tomber les atouts)."""
        trump, hand = game.trump, game.hands[seat]
        seen = {c for cards in game.played for c in cards} | {c for _s, c in game.trick} | set(hand)
        outside = [c for c in self._all_trumps(trump) if c not in seen]
        strength = lambda c: c.strength(trump)
        best_now = max((c for _s, c in game.trick if c.suit == trump), key=strength)
        sure = [c for c in legal if c.suit == trump and strength(c) > strength(best_now)
                and all(strength(c) > strength(o) for o in outside)]
        return min(sure, key=strength) if sure else None

    def _keep_aces(self, game, seat, legal):
        """On ne défausse jamais un As sans avoir derrière lui une carte maîtresse dans sa couleur (As-10 :
        sinon on rend maître le 10 adverse) ; sauf si on n'a pas le choix. L'As de la couleur demandée est
        réglé par _follow_side."""
        trump, trick = game.trump, game.trick
        led = trick[0][1].suit
        hand = game.hands[seat]
        gone = {c for cards in game.played for c in cards} | {c for _, c in trick}
        best = trick[trick_winner(trick, trump)]
        ruffed_by_partner = best[0] == partner_of(seat) and best[1].suit == trump and led != trump

        def master_after(suit):
            nxt = next((r for r in ORDER[1:] if Card(suit, r) not in gone), None)
            return nxt is not None and has(hand, suit, nxt)

        def bad(card):
            if card.rank != Rank.ACE or card.suit == trump:
                return False
            if card.suit == led and not ruffed_by_partner:
                return False  # couleur demandée, pli pas coupé : voir _follow_side
            return not master_after(card.suit)

        keep = [c for c in legal if not bad(c)]
        return keep or legal

    @staticmethod
    def _call_discard(hand, legal, trump, long_ok=True):
        """Appel direct (couleur de la famille de l'atout) ou indirect (couleur sœur) vers un de mes As.
        Jeter l'As lui-même = j'ai la longue maîtresse dans cette couleur (au moins As-10-Roi) ; pas au
        capot (l'As serait un pli perdu) : on appelle avec une petite carte."""
        for ace in (c for c in legal if c.rank == Rank.ACE and c.suit != trump):
            if long_ok and has(hand, ace.suit, Rank.TEN) and has(hand, ace.suit, Rank.KING):
                return ace
        for ace in (c for c in hand if c.rank == Rank.ACE and c.suit != trump):
            target = ace.suit if ace.suit == SISTER[trump] else SISTER[ace.suit]
            masters = set(ORDER[:top_tricks(hand, target)]) if not long_ok else set()  # au capot, garder ses plis
            small = [c for c in legal if c.suit == target and c.rank not in (Rank.ACE, Rank.TEN) and c.rank not in masters]
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
        if (trumps and not game.tricks and contract["mult"] == 1 and self._partner_announced(game, seat)
                and not ranks_in(hand, trump) & {Rank.JACK, Rank.NINE}):
            # j'entame le premier pli et mon partenaire a annoncé l'atout : je lui donne la main en atout ;
            # il fait tomber les atouts adverses et mes As ne risquent plus d'être coupés
            return min(trumps, key=lambda c: c.strength(trump))
        majors = {Rank.JACK, Rank.NINE}
        if (trumps and self._opponents_may_have_trumps(game, seat) and self._partner_majors(game, seat) >= majors
                and not ranks_in(hand, trump) & majors and (contract["mult"] == 1 or contract["value"] == CAPOT)):
            # le partenaire a montré le Valet et le 9 (100) : je lui donne la main en atout, il fait tomber
            # les atouts adverses (ils ne coupent pas mes plis maîtres) et me rend la main sur mon appel
            return min(trumps, key=lambda c: c.strength(trump))
        if contract["mult"] > 1 and side and contract["value"] != CAPOT:
            trumps = []  # contrés : on n'entame pas atout, on garde ses atouts
        if side and self._weak_alone(game, seat):
            trumps = []  # très faible à l'atout, sans soutien : on garde ses atouts pour la fin
        last_one = self._last_opponent_trump(game, seat)
        if last_one and sum(c.suit == trump for c in legal) >= 2 and not (contract["mult"] > 1 and contract["value"] != CAPOT):
            # un seul atout dehors et j'en ai un plus fort qui n'est pas mon dernier : je le fais tomber
            gone_now = gone | {c for _s, c in game.trick}
            unseen = next(c for c in self._all_trumps(trump) if c not in gone_now and c not in hand)
            higher = [c for c in legal if c.suit == trump and c.strength(trump) > unseen.strength(trump)]
            if higher:
                return min(higher, key=lambda c: c.strength(trump))
        if side and contract["value"] != CAPOT and (len(trumps) == 1 or last_one):
            # mon dernier atout reste pour le dernier pli ; le dernier atout adverse, on ne le fait pas
            # tomber avec un atout, on essaie de le faire couper
            trumps = []
        if trumps and self._opponents_may_have_trumps(game, seat):
            choice = self._trump_lead(game, seat, trumps)
            if choice is not None:
                return choice
        called = [c for c in side if c.suit in self._called_suits(game, seat)]
        if called:
            aces = [c for c in called if c.rank == Rank.ACE]
            if aces:
                return aces[0]  # l'As de la couleur demandée est chez moi : je le joue d'abord
            return min(called, key=lambda c: c.strength(trump))  # donner la main au partenaire qui a appelé
        if last_one:
            ruff = self._force_ruff(game, seat, side)
            if ruff is not None:
                return ruff
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
        """Entame en défense (pas d'appels en défense) : au premier pli, un As hors atout ; contre 140 ou
        plus, les cartes maîtresses ;
        sinon faire couper le preneur : la couleur qu'il n'a plus (la plus longue si plusieurs), sinon
        la couleur du pli que je viens de gagner en l'entamant, sinon notre couleur la plus longue ;
        atout seulement s'il ne reste que ça."""
        trump = game.trump
        side = [c for c in legal if c.suit != trump]
        gone = {c for cards in game.played for c in cards}
        hand = game.hands[seat]
        masters = sorted((c for c in side if self._is_master(c, trump, gone, hand)), key=lambda c: -c.points(trump))
        aces = [c for c in side if c.rank == Rank.ACE]
        if not game.tricks and aces:
            # première entame de la défense : un As (hors atout), dans la couleur la plus longue
            return max(aces, key=lambda c: (sum(d.suit == c.suit for d in side), c.suit.value))
        if game.contract["value"] >= 140 and masters:
            return masters[0]
        ruff = self._ruff_lead(game, side)
        if ruff is not None:
            return ruff
        if game.tricks:
            last, winner = game.tricks[-1]
            again = [c for c in side if c.suit == last[0][1].suit]
            if last[0][0] == seat and winner == seat and last[0][1].suit != trump and again:
                # j'ai gagné le pli que j'avais entamé : je rejoue la couleur (faire couper le preneur, ou
                # mieux, faire couper mon partenaire), avec ma plus grosse carte : le joueur suivant ne
                # passe pas au-dessus, et son partenaire doit couper au lieu de le laisser maître
                return max(again, key=lambda c: c.strength(trump))
        if side:
            return self._from_longest(side, trump, gone, hand)
        return min(legal, key=lambda c: c.strength(trump))

    @staticmethod
    def _partner_announced(game, seat):
        """Mon partenaire a annoncé l'atout le premier dans l'équipe, à 100 ou plus, et l'équipe a pris."""
        trump, contract = game.trump, game.contract
        if team_of(contract["seat"]) != team_of(seat):
            return False
        first = next(((s, a) for s, a in game.bids if a[0] == "bid" and a[2] == trump and team_of(s) == team_of(seat)), None)
        return first is not None and first[0] == partner_of(seat) and first[1][1] >= 100

    def _last_opponent_trump(self, game, seat):
        """Il ne reste qu'un atout dehors, et il peut être chez un adversaire."""
        from .papi_robert import PapiRobertBot
        trump, hand = game.trump, game.hands[seat]
        gone = {c for cards in game.played for c in cards} | {c for _, c in game.trick}
        unseen = [c for c in self._all_trumps(trump) if c not in gone and c not in hand]
        if len(unseen) != 1:
            return False
        voids = PapiRobertBot._shown_voids(game)
        return any(trump not in voids[s] for s in range(4) if team_of(s) != team_of(seat))

    def _force_ruff(self, game, seat, side):
        """Faire couper le dernier atout adverse : petite carte d'une couleur que l'adversaire qui peut
        encore avoir de l'atout n'a plus."""
        from .papi_robert import PapiRobertBot
        trump = game.trump
        voids = PapiRobertBot._shown_voids(game)
        target = {s for o in range(4) if team_of(o) != team_of(seat) and trump not in voids[o] for s in voids[o]}
        cards = [c for c in side if c.suit in target]
        if not cards:
            return None
        gone = {c for cards_ in game.played for c in cards_}
        masters = [c for c in cards if self._is_master(c, trump, gone, game.hands[seat])]
        if masters:
            # une carte maîtresse (la plus faible) : le partenaire de l'adversaire ne peut pas prendre le pli,
            # l'adversaire doit couper
            return min(masters, key=lambda c: c.strength(trump))
        return min(cards, key=lambda c: (c.points(trump), c.strength(trump)))

    def _weak_alone(self, game, seat):
        """Preneur très faible à l'atout (au plus 2 atouts, ou 3 sans le Valet, au départ) dont le
        partenaire n'a pas surenchéri dans l'atout (il n'a pas le Valet ou le 9 qui manque)."""
        trump, contract = game.trump, game.contract
        if contract["seat"] != seat:
            return False
        if any(s == partner_of(seat) and a[0] == "bid" and a[2] == trump for s, a in game.bids):
            return False
        r = ranks_in(list(game.hands[seat]) + list(game.played[seat]), trump)
        return len(r) <= 2 or (len(r) == 3 and Rank.JACK not in r)

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
        # garder son dernier atout s'il n'en reste qu'un dehors, quelle que soit sa force .
        if len(trumps) == 1 and len(outstanding) == 1:
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
        suit_cards = [c for c in cards if c.suit == longest]
        gone = {c for cards_ in game.played for c in cards_}
        masters = [c for c in suit_cards if AsRBot._is_master(c, game.trump, gone, game.hands[game.current])]
        if masters:  # la plus faible carte maîtresse : le preneur doit couper
            return min(masters, key=lambda c: c.strength(game.trump))
        return min(suit_cards, key=lambda c: (c.points(game.trump), c.strength(game.trump)))

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
