"""Robot "Papi Robert" (Coinche à 4) : le jeu aux As de la fiche "Belote au miel"."""
import random
import sys

from belote.coinche.bots import volley
from belote.coinche.engine import CAPOT, CoincheGame
from belote.coinche.inference import may_hold, trump_ceilings
from belote.coinche.papi_robert import PapiRobertBot, best_opening, opening_value, response
from belote.core.cards import Card, Rank, Suit
from tests.test_petit_jeu import hand, table

S, H, D, C = Suit.PIQUE, Suit.COEUR, Suit.CARREAU, Suit.TREFLE


def check_openings():
    assert opening_value(hand(S="J 7", H="A 8", D="A 8", C="7 8"), S) == 80          # 2 As hors atout
    assert opening_value(hand(S="9 8 7", H="A", D="A", C="7 8 10"), S) == 80         # 3 atouts + 2 As
    assert opening_value(hand(S="J 9 7", H="A 8", D="A 8", C="7"), S) == 80          # 80 même avec Valet-9
    assert opening_value(hand(S="J 8 7", H="A 8", D="7 8", C="7"), S) == 90          # 3 atouts + 1 As
    assert opening_value(hand(S="9 8 7", H="A 8", D="7 8", C="K"), S) == 90          # 9 troisième + 1 As
    assert opening_value(hand(S="J 8 7", H="K 8", D="7 8", C="7"), S) is None        # pas d'As
    assert opening_value(hand(S="J A 7", H="K 8", D="7 8", C="K"), S) is None        # l'As d'atout ne compte pas
    assert opening_value(hand(S="J 9 7", H="A 10", D="7 8", C="7"), S) == 90         # J 9 troisièmes sans l'As
    assert opening_value(hand(S="J 9 A", H="A 8", D="7 8", C="7"), S) == 80          # J 9 A + un As : 2 As, 80
    assert opening_value(hand(S="J 9 7 8", H="A", D="7 8", C="7"), S) == 100         # J 9 quatrièmes
    assert opening_value(hand(S="J 9 A", H="8 10", D="7 8", C="7"), S) == 90         # jeu nul à côté : timide
    assert opening_value(hand(S="J 9 7 8", H="8 7", D="7", C="7"), S) == 90          # jeu nul à côté : timide
    assert opening_value(hand(S="J 9 7 8", H="A 8", D="7 8"), S) == 110              # tricolore
    assert opening_value(hand(S="J 9 A", H="A 8 7", D="7 8"), S) == 110              # tricolore, J 9 A
    assert opening_value(hand(S="J 9 7 8", H="A 8", D="A 8"), S) == 110              # 110 direct malgré 2 As
    assert opening_value(hand(S="J 9 7 8", H="A 8 7 K"), S) == 120                   # bicolore
    assert opening_value(hand(S="J 9 7 8", H="A", D="A", C="7 8"), S) == 80          # jeu de 100 et 2 As : 80
    assert opening_value(hand(S="J A K Q 8", H="A 7 8"), S) == 80                    # 2 As (dont l'As d'atout) : 80
    assert opening_value(hand(S="J 10 K Q 8", H="A 7 8"), S) == 90                   # jamais 100 sans les 2 majeures
    # 80 : l'As d'atout compte ; il faut le Valet ou le 9 (Roi-Dame secs ne suffisent pas)
    assert best_opening(hand(C="9 A", H="A 7", D="K Q", S="7 8")) == (80, C)
    assert opening_value(hand(S="K Q 7", H="A 8", D="A 8", C="7"), S) is None        # sans Valet ni 9
    assert opening_value(hand(S="K Q 8 7", H="A 8", D="A", C="7"), S) == 80          # 4 atouts avec la belote
    assert opening_value(hand(S="10 K 8 7 Q", H="A", D="A", C="7"), S) == 80         # 5 atouts sans majeure
    assert opening_value(hand(S="10 K 8 7", H="A", D="A", C="7 8"), S) is None       # 4 atouts sans belote
    # le plus de majeures d'abord : 90 à cœur plutôt que 90 à pique
    assert best_opening(hand(S="J 8 7 K", H="J 9 7", D="A")) == (90, H)


def check_responses():
    # sur 80 : +10 avec le Valet ou le 9, puis +10 par As ; rien sans Valet ni 9
    assert response(hand(S="J 8", H="A 7", D="7 8", C="7 8"), 80, S) == (100, S)
    assert response(hand(S="9", H="K 7", D="7 8", C="7 8 Q"), 80, S) == (90, S)
    assert response(hand(S="J 9", H="K 7", D="7 8", C="7 8 Q"), 80, S) == (100, S)  # Valet et 9 : +20
    assert response(hand(S="8 7", H="A 7", D="A 8", C="7 8"), 80, S) is None
    # sans complément, je change d'atout avec une ouverture ailleurs
    assert response(hand(S="8", H="J 8 7", D="A 8", C="7 8 Q"), 80, S) == (90, H)
    # un jeu de 100 chez moi passe avant le complément
    assert response(hand(S="9", H="J 9 A", D="A 8", C="7 8"), 80, S) == (100, H)
    # sur 90 : la deuxième majeure, +10, puis +10 par As ; pas de réponse sans elle, même avec des As
    assert response(hand(S="9 8", H="A 7", D="7 8", C="7 8"), 90, S) == (110, S)
    assert response(hand(S="8 7", H="A 7", D="A 8", C="7 8"), 90, S) is None
    # sur 100 : +10 par As
    assert response(hand(S="8", H="A 7", D="A 8", C="7 8 K"), 100, S) == (120, S)
    assert response(hand(S="8", H="K 7", D="Q 8", C="7 8 K"), 100, S) is None
    # sur 110 : rien avec un As, +10 avec deux, +20 avec trois
    assert response(hand(S="8", H="A 7", D="A 8", C="7 8 K"), 110, S) == (120, S)
    assert response(hand(S="8", H="A 7", D="K 8", C="7 8 K"), 110, S) is None
    assert response(hand(S="8", H="A 7", D="A 8", C="A 8 K"), 110, S) == (130, S)
    # sur 120 : +10 seulement avec les trois As ; l'As d'atout ne compte pas
    assert response(hand(S="8", H="A 7", D="K 8", C="7 8 K"), 120, S) is None
    assert response(hand(S="A", H="A 7", D="K 8", C="7 8 K"), 120, S) is None
    assert response(hand(S="8", H="A 7", D="A 8", C="A 8 K"), 120, S) == (130, S)
    # sur 110 ou 120 : les trois As et un 10 derrière un As : capot
    assert response(hand(S="8", H="A 10", D="A 8", C="A 8 K"), 110, S) == (CAPOT, S)
    assert response(hand(S="8", H="A 10", D="A 8", C="A 8 K"), 120, S) == (CAPOT, S)


def bid_round(game, bot, n):
    for _ in range(n):
        game.bid(game.current, bot.bid(game, game.current))


def check_auctions():
    bot = PapiRobertBot()
    # 110 avec 5 atouts (tricolore) ; le partenaire a les trois As sans 10 (+20) : capot
    game = table([hand(S="J 9 A 8 7", H="Q K", D="7"), hand(H="7 8", D="8", C="8 9"),
                  hand(H="A 9", D="A 9", C="A 7"), None])
    bid_round(game, bot, 4)
    assert [a for _, a in game.bids] == [("bid", 110, S), ("pass",), ("bid", 130, S), ("pass",)], game.bids
    assert bot.bid(game, 0) == ("bid", CAPOT, S)
    # 90 avec 5 atouts et une majeure ; le partenaire montre la 2e majeure (100) ; relance avec mon As : 110
    game = table([hand(S="J 7 8 K Q", H="A", D="7", C="7"), hand(H="8 Q", D="8", C="8"),
                  hand(S="9", H="7 10", D="Q K", C="K Q"), None])
    game.bid(0, bot.bid(game, 0)); game.bid(1, ("pass",))
    game.bid(2, bot.bid(game, 2)); game.bid(3, ("pass",))
    assert game.bids[0][1] == ("bid", 90, S) and game.bids[2][1] == ("bid", 100, S), game.bids
    assert bot.bid(game, 0) == ("bid", 110, S)
    # sur 80, le partenaire soutient dans la couleur : 9 d'atout et un As -> 100
    game = table([hand(S="J 7", H="A 8", D="A 8", C="7 8"), hand(H="Q K", D="Q K", C="Q 10"),
                  hand(S="9 10", H="7 9", D="7 9", C="A K")])
    bid_round(game, bot, 3)
    assert game.bids[0][1] == ("bid", 80, S) and game.bids[2][1] == ("bid", 100, S), game.bids
    # ouvert à 80 avec un jeu de 100 : je remonte à 100 quand un adversaire a parlé
    game = table([hand(S="J 9 7 8", H="A", D="A", C="7 8"), None, hand(H="7 8", D="7 8", C="Q K")])
    game.bid(0, bot.bid(game, 0))
    game.bid(1, ("bid", 90, H))
    game.bid(2, bot.bid(game, 2)); game.bid(3, ("pass",))
    assert game.bids[0][1] == ("bid", 80, S) and game.bids[2][1] == ("pass",), game.bids
    assert bot.bid(game, 0) == ("bid", 100, S)


def check_opener_capot():
    # 110 : le partenaire montre les 3 As (+20) ; un 10 second hors atout -> capot, sinon rien
    assert PapiRobertBot._relaunch(hand(S="J 9 A 8", H="10 7", D="7 8"), ("bid", 110, S), ("bid", 130, S)) \
        == ("bid", CAPOT, S)
    assert PapiRobertBot._relaunch(hand(S="J 9 A 8", H="10 7 8", D="7"), ("bid", 110, S), ("bid", 130, S)) is None
    # 120 : +10 = les 3 As ; 5 atouts -> capot
    assert PapiRobertBot._relaunch(hand(S="J 9 A 8 7", H="8 7 Q"), ("bid", 120, S), ("bid", 130, S)) \
        == ("bid", CAPOT, S)


def check_after_opponent():
    bot = PapiRobertBot()
    # sur 80 adverse : valeur exacte ; un jeu aux As seul ne parle plus
    game = table([None, None, hand(S="J 8 7", H="A 8", D="7 8", C="7")])
    game.bid(0, ("pass",)); game.bid(1, ("bid", 80, H))
    assert bot.bid(game, 2) == ("bid", 90, S)
    game = table([None, None, hand(S="8 7", C="A 8", D="A 8", H="7 9")])
    game.bid(0, ("pass",)); game.bid(1, ("bid", 80, H))
    assert bot.bid(game, 2) == ("pass",)
    # sur 90 adverse : un 90 colle (100), un 100 saute (110), rien sous 90
    game = table([None, None, hand(S="J 8 7", C="A 8", D="7 8", H="7")])
    game.bid(0, ("pass",)); game.bid(1, ("bid", 90, H))
    assert bot.bid(game, 2) == ("bid", 100, S)
    game = table([None, None, hand(S="J 9 7 8", C="A", D="7 8", H="7")])
    game.bid(0, ("pass",)); game.bid(1, ("bid", 90, H))
    assert bot.bid(game, 2) == ("bid", 110, S)
    # le partenaire lit 100 sur 90 comme un 90 : 2e majeure et un As (+20) -> 120
    game = table([hand(S="9", H="A 8", C="7 9 Q", D="7 8"), None, hand(S="J 8 7", C="A 8", D="Q K", H="7")])
    game.bid(0, ("pass",)); game.bid(1, ("bid", 90, H))
    game.bid(2, bot.bid(game, 2)); game.bid(3, ("pass",))
    assert game.bids[2][1] == ("bid", 100, S), game.bids
    assert bot.bid(game, 0) == ("bid", 120, S)


def check_second_turn():
    bot = PapiRobertBot()
    # belote : mon partenaire a dit 100, je n'ai rien répondu, un adversaire parle : 20 de plus (120)
    game = table([hand(S="J 9 7 8", H="A", D="7 8", C="7"), None, hand(S="K Q", H="8 9", D="9 10", C="8 9")])
    game.bid(0, bot.bid(game, 0)); game.bid(1, ("pass",))
    game.bid(2, bot.bid(game, 2)); game.bid(3, ("bid", 110, H))
    assert game.bids[0][1] == ("bid", 100, S) and game.bids[2][1] == ("pass",), game.bids
    game.bid(0, bot.bid(game, 0)); game.bid(1, ("pass",))
    assert bot.bid(game, 2) == ("bid", 120, S)
    # jamais plus de 20 : sur 150, la belote ne se dit pas (170 n'existe pas)
    game = table([hand(S="J 9 7 8", H="A", D="7 8", C="7"), None, hand(S="K Q", H="8 9", D="9 10", C="8 9")])
    game.bids = [(0, ("bid", 150, S)), (1, ("pass",)), (2, ("pass",)), (3, ("bid", 160, H))]
    assert bot._second_turn(game, 2, 0, 150, 150, S) is None
    # sur 90, sans la deuxième majeure, mes deux As au second tour : 110
    game = table([hand(S="J 8 7", H="A 8", D="7 8", C="7"), None, hand(S="Q K", H="7", D="A K", C="A K 10")])
    game.bid(0, bot.bid(game, 0)); game.bid(1, ("pass",))
    game.bid(2, bot.bid(game, 2)); game.bid(3, ("bid", 100, H))
    assert game.bids[0][1] == ("bid", 90, S) and game.bids[2][1] == ("pass",), game.bids
    game.bid(0, bot.bid(game, 0)); game.bid(1, ("pass",))
    assert bot.bid(game, 2) == ("bid", 110, S)


def check_exit():
    bot = PapiRobertBot()
    # l'adversaire sort avec son 100 : je monte au-dessus dans une vraie couleur, sinon je contre
    game = table([None, None, hand(S="J 8 7", H="A 8", D="7 8", C="7")])
    game.totals = [0, 1400]
    game.bid(0, ("pass",)); game.bid(1, ("bid", 100, H))
    assert bot.bid(game, 2) == ("bid", 110, S)
    game = table([None, None, hand(S="8 7", H="7 8", D="7 8", C="Q K")])
    game.totals = [0, 1400]
    game.bid(0, ("pass",)); game.bid(1, ("bid", 100, H))
    assert bot.bid(game, 2) == ("coinche",)


def check_attack_leads():
    bot = PapiRobertBot()
    # mon partenaire a annoncé l'atout : je lui rends la main avec mon plus petit atout
    game = table([hand(S="8 7 K", H="A 10", D="K", C="8 7"), None, hand(S="J 9 A")])
    game.bid(0, ("pass",)); game.bid(1, ("pass",)); game.bid(2, ("bid", 100, S))
    for seat in (3, 0, 1):
        game.bid(seat, ("pass",))
    assert bot.play(game, 0) == Card(S, Rank.SEVEN)
    # dernier atout, main faible, partenaire à 90 : je le garde et je joue une petite carte
    game = table([hand(S="7", H="K 10 8", D="K Q", C="8 7"), None, hand(S="J 8 A")])
    game.bid(0, ("pass",)); game.bid(1, ("pass",)); game.bid(2, ("bid", 90, S))
    for seat in (3, 0, 1):
        game.bid(seat, ("pass",))
    card = bot.play(game, 0)
    assert card.suit != S and card.points(S) == 0, card
    # avec une carte maîtresse (l'As de cœur), la main n'est pas faible : je rends la main en atout
    game.hands[0] = hand(S="7", H="A 10 8", D="K Q", C="8 7")
    assert bot.play(game, 0) == Card(S, Rank.SEVEN)
    # sans atout, les adversaires en ont encore : petite carte plutôt que l'As
    game = table([hand(H="A 10 8", D="K Q 7", C="8 7"), None, hand(S="J 9 A 8")])
    game.bid(0, ("pass",)); game.bid(1, ("pass",)); game.bid(2, ("bid", 100, S))
    for seat in (3, 0, 1):
        game.bid(seat, ("pass",))
    assert bot.play(game, 0) in (Card(D, Rank.SEVEN), Card(C, Rank.SEVEN), Card(C, Rank.EIGHT), Card(H, Rank.EIGHT))


def check_defence_two_aces():
    bot = PapiRobertBot()
    # Ouest a pris ; Sud a deux As : il les joue d'abord, puis rejoue une de ces couleurs (petite carte)
    game = table([hand(H="A 7 8", D="A 9 Q", C="K Q"), hand(S="J 9 A 8")])
    game.bid(0, ("pass",)); game.bid(1, ("bid", 100, S))
    game.bid(2, ("pass",)); game.bid(3, ("pass",)); game.bid(0, ("pass",))
    assert bot.play(game, 0).rank == Rank.ACE
    # les deux As sont passés (Ouest a coupé le carreau) : Sud rejoue carreau pour le faire couper
    game.hands[0] = hand(H="7 8", D="9 Q", C="K Q")
    game.tricks = [([(0, Card(H, Rank.ACE)), (1, Card(H, Rank.NINE)), (2, Card(H, Rank.KING)),
                     (3, Card(H, Rank.QUEEN))], 0),
                   ([(0, Card(D, Rank.ACE)), (1, Card(S, Rank.SEVEN)), (2, Card(D, Rank.SEVEN)),
                     (3, Card(D, Rank.EIGHT))], 1)]
    game.current = 0
    assert bot.play(game, 0) == Card(D, Rank.NINE)


def check_voids():
    # Sud prend à pique
    game = table([hand(S="J 9 7 8"), None, None, None])
    game.bid(0, ("bid", 100, S))
    for seat in (1, 2, 3):
        game.bid(seat, ("pass",))
    # Ouest entame cœur, Nord défausse un carreau alors qu'il devait couper : il n'a plus d'atout
    game.trick = [(1, Card(H, Rank.SEVEN)), (2, Card(D, Rank.EIGHT))]
    assert S in PapiRobertBot._shown_voids(game)[2]
    # Sud est maître (As de cœur) : Nord, son partenaire, pouvait défausser ; on ne sait rien de ses atouts
    game.trick = [(0, Card(H, Rank.ACE)), (1, Card(H, Rank.SEVEN)), (2, Card(D, Rank.EIGHT))]
    assert S not in PapiRobertBot._shown_voids(game)[2] and H in PapiRobertBot._shown_voids(game)[2]
    # Nord a déjà coupé : Est défausse, il n'a peut-être qu'un atout plus petit ; on ne conclut rien
    game.trick = [(1, Card(H, Rank.SEVEN)), (2, Card(S, Rank.ACE)), (3, Card(D, Rank.NINE))]
    assert S not in PapiRobertBot._shown_voids(game)[3]
    # plafond d'atout : Sud joue la Dame, Ouest met le 7 : ni Roi, ni 10, ni As, ni 9, ni Valet
    game.trick = [(0, Card(S, Rank.QUEEN)), (1, Card(S, Rank.SEVEN))]
    assert not may_hold(game, 1, Card(S, Rank.KING)) and not may_hold(game, 1, Card(S, Rank.JACK))
    assert may_hold(game, 1, Card(S, Rank.EIGHT))
    game.played[0].append(Card(S, Rank.QUEEN)); game.played[1].append(Card(S, Rank.SEVEN))
    game.played[3].append(Card(S, Rank.EIGHT))  # le 8 est tombé aussi : Ouest n'a plus d'atout
    assert S in PapiRobertBot._shown_voids(game)[1]
    game.played = [[] for _ in range(4)]
    # pli coupé : Nord coupe du 10, Est (partenaire d'Ouest qui n'est pas maître) met le 7 : rien au-dessus du 10
    game.trick = [(1, Card(H, Rank.SEVEN)), (2, Card(S, Rank.TEN)), (3, Card(S, Rank.SEVEN))]
    assert not may_hold(game, 3, Card(S, Rank.ACE)) and may_hold(game, 3, Card(S, Rank.KING))
    # partenaire maître : Nord a coupé, Sud défausse ; on ne conclut rien sur ses atouts
    game.trick = [(1, Card(H, Rank.SEVEN)), (2, Card(S, Rank.TEN)), (3, Card(H, Rank.EIGHT)), (0, Card(D, Rank.SEVEN))]
    assert trump_ceilings(game)[0] is None
    # Est et Ouest ont montré qu'ils n'ont plus d'atout : Sud ne joue plus atout
    game.trick = []
    game.tricks = [([(0, Card(H, Rank.ACE)), (1, Card(C, Rank.SEVEN)), (2, Card(H, Rank.SEVEN)),
                     (3, Card(H, Rank.EIGHT))], 0),
                   ([(0, Card(D, Rank.ACE)), (1, Card(D, Rank.SEVEN)), (2, Card(D, Rank.EIGHT)),
                     (3, Card(C, Rank.EIGHT))], 0)]
    assert not PapiRobertBot._opponents_may_have_trumps(game, 0)


def check_play():
    bot = PapiRobertBot()
    # attaque : commencer fort (le plus gros atout)
    game = table([hand(S="J 9 7", H="A 10", D="K", C="8 7"), None, None, None])
    game.bid(0, ("bid", 100, S))
    for seat in (1, 2, 3):
        game.bid(seat, ("pass",))
    assert bot.play(game, 0) == Card(S, Rank.JACK)
    # appel indirect : Nord n'a plus d'atout et a l'As de cœur : petite carte à carreau (couleur sœur)
    game.play(0, Card(S, Rank.JACK))
    game.play(1, bot.play(game, 1))
    game.hands[2] = hand(H="A 7", D="8 Q", C="9 K Q J")
    card = bot.play(game, 2)
    assert card == Card(D, Rank.EIGHT), card
    game.tricks.append(([(0, Card(S, Rank.JACK)), (1, game.trick[1][1]), (2, card)], 0))
    assert PapiRobertBot._called_suits(game, 0) == {H}


def check_discards():
    bot = PapiRobertBot()
    # Sud prend à pique ; Ouest entame carreau, Nord (partenaire de Sud) n'a plus de carreau ni d'atout :
    # il garde son As de cœur (sans 10 et Roi derrière) et défausse une autre carte
    game = table([hand(S="J 9 7 8"), None, None, None])
    game.bid(0, ("bid", 90, S))
    for seat in (1, 2, 3):
        game.bid(seat, ("pass",))
    game.trick = [(1, Card(D, Rank.SEVEN))]
    game.current = 2
    game.hands[2] = hand(H="A 7 8", C="A 8 9 Q K")
    legal = game.legal_cards(2)
    allowed = PapiRobertBot._allowed_discards(game, 2, legal)
    assert Card(H, Rank.ACE) not in allowed and Card(C, Rank.ACE) not in allowed
    assert bot.play(game, 2).rank != Rank.ACE
    # As protégé (10 et Roi derrière) : il peut le défausser
    game.hands[2] = hand(H="A 10 K", C="7 8 9 Q K")
    assert Card(H, Rank.ACE) in PapiRobertBot._allowed_discards(game, 2, game.legal_cards(2))
    # pas le choix : il ne reste que deux As
    game.hands[2] = hand(H="A", C="A")
    assert PapiRobertBot._allowed_discards(game, 2, game.legal_cards(2)) == game.legal_cards(2)


def check_defence_no_trump_lead():
    bot = PapiRobertBot()
    # Ouest a pris à pique ; Sud (défense) a la main avec le 7 de pique et des cartes à points : pas d'atout
    game = table([None, hand(S="J 9 A 8")])
    game.bid(0, ("pass",))
    game.bid(1, ("bid", 100, S))
    game.bid(2, ("pass",)); game.bid(3, ("pass",)); game.bid(0, ("pass",))
    game.hands[0] = hand(S="7", H="K Q", D="K 10", C="Q K 10")
    assert bot.play(game, 0).suit != S
    game.hands[0] = hand(S="7 8")                      # que des atouts : pas le choix
    assert bot.play(game, 0).suit == S


def check_coinched():
    bot = PapiRobertBot()
    # Sud prend 100 à pique, Ouest coinche : Sud garde ses atouts et joue son As
    game = table([hand(S="J 9 7 8", H="A 10", D="K", C="8"), None, None, None])
    game.bid(0, ("bid", 100, S))
    game.bid(1, ("coinche",))
    while game.phase == "bidding":
        game.bid(game.current, ("pass",))
    assert game.phase == "play" and game.contract["mult"] == 2 and game.current == 0, (game.phase, game.current)
    assert bot.play(game, 0) == Card(H, Rank.ACE)
    # défense : Sud (le preneur) n'a plus de carreau : Ouest joue petit carreau pour le faire couper
    game.tricks = [([(3, Card(D, Rank.SEVEN)), (0, Card(S, Rank.SEVEN)), (1, Card(D, Rank.EIGHT)),
                     (2, Card(D, Rank.NINE))], 0)]
    game.current = 1
    game.hands[1] = hand(D="Q 10", H="K Q", C="A K 7")
    assert bot.play(game, 1) == Card(D, Rank.QUEEN)


def check_trump_until_void():
    bot = PapiRobertBot()
    # Sud a pris ; les adversaires n'ont plus d'atout (ils n'ont pas fourni) : il garde ses atouts et joue son As
    game = table([hand(S="J 9 7 8", H="A 10", D="K", C="8"), None, None, None])
    game.bid(0, ("bid", 90, S))
    for seat in (1, 2, 3):
        game.bid(seat, ("pass",))
    game.tricks = [([(0, Card(S, Rank.ACE)), (1, Card(H, Rank.SEVEN)), (2, Card(S, Rank.TEN)),
                     (3, Card(D, Rank.SEVEN))], 0)]
    for c in (Card(S, Rank.KING), Card(S, Rank.QUEEN)):
        game.played[2].append(c)
    assert bot.play(game, 0) == Card(H, Rank.ACE)


def check_volley():
    bot = PapiRobertBot()
    # Sud dit 150 cœur ; Ouest a la parole ; Est (Valet et As de cœur) est sûr de la chute : il coinche à la volée
    # (Valet 20 + As 11, plus 10 chacun = 51 > 162 - 150 + 20 de belote possible)
    game = table([hand(S="7 8"), None, None, hand(H="J A", S="A", D="8")])
    game.bid(0, ("bid", 150, H))
    assert game.volley_seats() == [3]
    assert volley(game, [bot] * 4) == 3
    assert game.contract["mult"] == 2 and game.coinche_seat == 3 and game.current == 0
    assert game.volley_seats() == [] and volley(game, [bot] * 4) is None
    # même main sur 100 : pas quasi sûr (51 <= 62 + 20 de belote), pas de coinche à la volée
    game = table([hand(S="7 8"), None, None, hand(H="J A", S="A", D="8")])
    game.bid(0, ("bid", 100, H))
    assert volley(game, [bot] * 4) is None and game.current == 1
    # Valet-9 d'atout et deux As sur 100 : 96 > 82, coinche
    game = table([hand(S="7 8"), None, None, hand(H="J 9", S="A", D="A")])
    game.bid(0, ("bid", 100, H))
    assert volley(game, [bot] * 4) == 3


def check_full_games(n=100):
    bot = PapiRobertBot()
    rng = random.Random(0)
    for _ in range(n):
        game = CoincheGame(rng=random.Random(rng.random()))
        while not game.game_over:
            if game.phase in ("redeal", "done"):
                game.new_deal()
                continue
            if game.phase == "bidding" and volley(game, [bot] * 4) is not None:
                continue  # coinche à la volée
            seat = game.current
            if game.phase == "bidding":
                game.bid(seat, bot.bid(game, seat))
            else:
                game.play(seat, bot.play(game, seat))


def main():
    check_openings()
    check_responses()
    check_auctions()
    check_opener_capot()
    check_after_opponent()
    check_second_turn()
    check_exit()
    check_attack_leads()
    check_defence_two_aces()
    check_voids()
    check_play()
    check_discards()
    check_trump_until_void()
    check_defence_no_trump_lead()
    check_coinched()
    check_volley()
    check_full_games()
    print("OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
