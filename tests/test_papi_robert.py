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
    assert opening_value(hand(S="9 8 7 K", H="K 8", D="7 8"), S) == 90               # 4 atouts dont une majeure
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
    assert opening_value(hand(S="J 9 7 8", H="8 7", D="7 K"), S) == 90               # 4 atouts sans As : pas maître
    assert opening_value(hand(S="J A K Q 8", H="A 7 8"), S) == 90                    # jamais 100 sans les 2 majeures
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
    # sur 100 et 110 : +10 par As
    assert response(hand(S="8", H="A 7", D="A 8", C="7 8 K"), 100, S) == (120, S)
    assert response(hand(S="8", H="A 7", D="A 8", C="7 8 K"), 110, S) == (130, S)
    assert response(hand(S="8", H="K 7", D="Q 8", C="7 8 K"), 100, S) is None
    # sur 120 : rien avec un As, +10 avec deux, +20 avec les trois ; l'As d'atout ne compte pas
    assert response(hand(S="8", H="A 7", D="K 8", C="7 8 K"), 120, S) is None
    assert response(hand(S="A", H="A 7", D="K 8", C="7 8 K"), 120, S) is None
    assert response(hand(S="8", H="A 7", D="A 8", C="7 8 K"), 120, S) == (130, S)
    assert response(hand(S="8", H="A 7", D="A 8", C="A 8 K"), 120, S) == (140, S)


def bid_round(game, bot, n):
    for _ in range(n):
        game.bid(game.current, bot.bid(game, game.current))


def check_auctions():
    bot = PapiRobertBot()
    # 110 avec 5 atouts ; le partenaire a deux As (+20) : capot
    game = table([hand(S="J 9 7 8 K", H="A", D="7", C="Q"), hand(H="7 8", D="8", C="8 9"),
                  hand(H="10", D="A 9", C="A 10"), None])
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
    check_full_games()
    print("OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
