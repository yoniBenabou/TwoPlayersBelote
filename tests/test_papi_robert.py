"""Robot "Papi Robert" (Coinche à 4) : le jeu aux As de la fiche "Belote au miel"."""
import random
import sys

from belote.coinche.engine import CAPOT, CoincheGame
from belote.coinche.papi_robert import PapiRobertBot, best_opening, opening_value, response
from belote.core.cards import Card, Rank, Suit
from tests.test_petit_jeu import hand, table

S, H, D, C = Suit.PIQUE, Suit.COEUR, Suit.CARREAU, Suit.TREFLE


def check_openings():
    assert opening_value(hand(S="J 7", H="A 8", D="A 8", C="7 8"), S) == 80          # jeu aux As, 2 atouts
    assert opening_value(hand(S="9 8 7", H="A", D="A", C="7 8 10"), S) == 80         # 3 atouts + 2 As
    assert opening_value(hand(S="J 8 7", H="A 8", D="7 8", C="7"), S) == 90          # 3 atouts + 1 As
    assert opening_value(hand(S="J 8 7", H="K 8", D="7 8", C="7"), S) is None        # pas d'As
    assert opening_value(hand(S="9 8 7 K", H="A 8", D="7 8"), S) == 90               # 9 quatrième et un As
    assert opening_value(hand(S="9 8 7 K", H="K 8", D="7 8"), S) is None             # 90 oblige d'avoir un As
    assert opening_value(hand(S="9 8 7", H="A 8", D="7 8", C="K"), S) is None        # 9 troisième : pas 90
    assert opening_value(hand(S="J A 7", H="K 8", D="7 8", C="K"), S) == 90          # Valet troisième, As d'atout
    assert opening_value(hand(S="9 A 7 8", H="K 8", D="7 8"), S) == 90               # 9 quatrième, As d'atout
    assert opening_value(hand(S="J 9 7", H="A 10", D="7 8", C="7"), S) == 100        # les deux majeures + As
    assert opening_value(hand(S="J 9 7", H="A 8", D="7 8", C="7"), S) == 90          # jeu light à côté
    assert opening_value(hand(S="J 9 7 8", H="A", D="7 8", C="7"), S) == 100         # 4 atouts, 4 couleurs
    assert opening_value(hand(S="J 9 7 8", H="A 8", D="7 8"), S) == 110              # tricolore
    assert opening_value(hand(S="J 9 7 8 K", H="A", D="7", C="7"), S) == 110         # 5 atouts
    assert opening_value(hand(S="J 9 7 8", H="A 8 7 K"), S) == 120                   # bicolore
    assert opening_value(hand(C="J 9 10 K Q", H="8 7", D="7"), C) == 110             # maître sans As (exemple de Noa)
    assert opening_value(hand(S="J 9 A 8", H="8 7", D="7", C="7"), S) == 100         # maître avec l'As d'atout
    assert opening_value(hand(S="J 9 A", H="8 10", D="7 8", C="7"), S) == 100        # J 9 A + un 10 à côté
    assert opening_value(hand(S="J 9 A", H="8 7", D="7 8", C="7"), S) == 90          # J 9 A, rien à côté : light
    assert opening_value(hand(S="J 9 7 8", H="8 7", D="7 K"), S) is None             # sans As : ni maître ni 90
    assert opening_value(hand(S="J A K Q 8", H="A 7 8"), S) == 90                    # jamais 100 sans les 2 majeures
    # exemple de Noa : 9 et As de trèfle, As de cœur, Roi-Dame de carreau, 7 de pique : 80 carreau
    # (belote et 2 As à côté) plutôt que trèfle
    assert best_opening(hand(C="9 A", H="A 7", D="K Q", S="7 8")) == (80, D)
    # le plus de majeures d'abord : 90 à cœur (2 majeures, light) plutôt que 90 à pique (une majeure, 4 atouts)
    assert best_opening(hand(S="J 8 7 K", H="J 9 7", D="A")) == (90, H)


def check_responses():
    # sur 80 (jeu aux As) : on change d'atout, +10, +20 avec un As, +30 avec deux
    assert response(hand(H="J 8 7", D="K", C="7 8 Q K"), 80, S) == (90, H)
    assert response(hand(H="9 8 7", D="A", C="7 8 Q K"), 80, S) == (100, H)
    assert response(hand(H="9 8 7", D="A", C="A 8 Q K"), 80, S) == (110, H)
    assert response(hand(H="9 8", D="A", C="A 8 Q K 7"), 80, S) is None              # 2 cartes seulement
    # sur 90 : la deuxième majeure, +10, puis +10 par As ; pas de réponse sans elle, même avec des As
    assert response(hand(S="9 8", H="A 7", D="7 8", C="7 8"), 90, S) == (110, S)
    assert response(hand(S="8 7", H="A 7", D="A 8", C="7 8"), 90, S) is None
    # sur 100 : +10 par As
    assert response(hand(S="8", H="A 7", D="A 8", C="7 8 K"), 100, S) == (120, S)
    # sur 110 : rien avec un As, +10 avec deux, +20 avec trois (exemple de Noa : 2 As -> 120)
    assert response(hand(S="8", H="A 7", D="A 8", C="7 8 K"), 110, S) == (120, S)
    assert response(hand(S="8", H="A 7", D="K 8", C="7 8 K"), 110, S) is None
    assert response(hand(S="8", H="A 7", D="A 8", C="A 8 K"), 110, S) == (130, S)
    assert response(hand(S="8", H="K 7", D="Q 8", C="7 8 K"), 100, S) is None
    # sur 120 : +10 seulement avec les trois As ; l'As d'atout ne compte pas
    assert response(hand(S="8", H="A 7", D="K 8", C="7 8 K"), 120, S) is None
    assert response(hand(S="A", H="A 7", D="K 8", C="7 8 K"), 120, S) is None
    assert response(hand(S="8", H="A 7", D="A 8", C="7 8 K"), 120, S) is None
    assert response(hand(S="8", H="A 7", D="A 8", C="A 8 K"), 120, S) == (130, S)


def bid_round(game, bot, n):
    for _ in range(n):
        game.bid(game.current, bot.bid(game, game.current))


def check_auctions():
    bot = PapiRobertBot()
    # 110 avec 5 atouts (dont l'As) ; le partenaire a les trois As (+20) : capot
    game = table([hand(S="J 9 A 8 7", H="Q", D="7", C="Q"), hand(H="7 8", D="8", C="8 9"),
                  hand(H="A 10", D="A 9", C="A 10"), None])
    bid_round(game, bot, 4)
    assert [a for _, a in game.bids] == [("bid", 110, S), ("pass",), ("bid", 130, S), ("pass",)], game.bids
    assert bot.bid(game, 0) == ("bid", CAPOT, S)
    # 90 avec 5 atouts et une majeure ; le partenaire montre la 2e majeure (100) ; relance avec mon As : 110
    game = table([hand(S="J 7 8 K Q", H="A", D="7", C="7"), hand(H="8 9", D="8", C="8"),
                  hand(S="9", H="7 10", D="Q K", C="K Q"), None])
    bid_round(game, bot, 4)
    assert game.bids[0][1] == ("bid", 90, S) and game.bids[2][1] == ("bid", 100, S), game.bids
    assert bot.bid(game, 0) == ("bid", 110, S)
    # l'ouvreur au jeu aux As ne reparle pas quand le partenaire a changé d'atout
    game = table([hand(S="J 7", H="A 8", D="A 8", C="7 8"), hand(S="Q K", H="Q K", D="Q K", C="Q 10"),
                  hand(C="J 9 K A", H="7 9", D="7 9")])
    bid_round(game, bot, 4)
    assert game.bids[0][1] == ("bid", 80, S) and game.bids[2][1] == ("bid", 90, C), game.bids
    assert bot.bid(game, 0) == ("pass",)


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
    game.tricks = [([(3, Card(D, Rank.SEVEN)), (0, Card(H, Rank.SEVEN)), (1, Card(D, Rank.EIGHT)),
                     (2, Card(D, Rank.NINE))], 2)]
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


def check_full_games(n=100):
    bot = PapiRobertBot()
    rng = random.Random(0)
    for _ in range(n):
        game = CoincheGame(rng=random.Random(rng.random()))
        while not game.game_over:
            if game.phase in ("redeal", "done"):
                game.new_deal()
                continue
            seat = game.current
            if game.phase == "bidding":
                game.bid(seat, bot.bid(game, seat))
            else:
                game.play(seat, bot.play(game, seat))


def main():
    check_openings()
    check_responses()
    check_auctions()
    check_play()
    check_discards()
    check_trump_until_void()
    check_defence_no_trump_lead()
    check_coinched()
    check_full_games()
    print("OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
