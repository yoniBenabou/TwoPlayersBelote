import random
import sys

from belote.coinche.bots import CoincheBot
from belote.coinche.engine import (
    CAPOT, CoincheGame, legal_cards, score_deal, team_of, trick_winner,
)
from belote.core.cards import Card, Rank, Suit

S, H, D, C = Suit.PIQUE, Suit.COEUR, Suit.CARREAU, Suit.TREFLE
R = {"7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE, "10": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN,
     "K": Rank.KING, "A": Rank.ACE}


def cards(text, suit):
    return [Card(suit, R[r]) for r in text.split()]


def check_trick_winner():
    # couleur demandée sans atout : la plus forte de la couleur ; défausse ignorée
    assert trick_winner([(0, Card(H, Rank.KING)), (1, Card(H, Rank.ACE)), (2, Card(S, Rank.ACE)), (3, Card(H, Rank.TEN))], C) == 1
    # un atout bat tout ; le plus fort atout gagne (Valet > 9 > As)
    assert trick_winner([(0, Card(H, Rank.ACE)), (1, Card(C, Rank.SEVEN)), (2, Card(C, Rank.NINE)), (3, Card(H, Rank.TEN))], C) == 2
    assert trick_winner([(0, Card(C, Rank.ACE)), (1, Card(C, Rank.NINE)), (2, Card(C, Rank.JACK)), (3, Card(C, Rank.TEN))], C) == 2


def check_legal_cards():
    trump = C
    hand = cards("7 A", H) + cards("8 J", C) + cards("K", S)
    # 1. fournir
    assert set(legal_cards(hand, [(1, Card(H, Rank.KING))], trump, 2)) == set(cards("7 A", H))
    # 2. atout demandé : monter si possible, même sur le partenaire (place 0 = partenaire de 2)
    assert legal_cards(hand, [(0, Card(C, Rank.NINE))], trump, 2) == [Card(C, Rank.JACK)]
    # ... et si on ne peut pas monter, n'importe quel atout
    assert set(legal_cards(cards("8 10", C), [(1, Card(C, Rank.JACK))], trump, 2)) == set(cards("8 10", C))
    # 3. partenaire maître et pas la couleur : carte libre
    trick = [(0, Card(D, Rank.ACE)), (1, Card(D, Rank.SEVEN))]
    assert set(legal_cards(hand, trick, trump, 2)) == set(hand)
    # 4. adversaire maître et pas la couleur : couper
    trick = [(1, Card(D, Rank.ACE))]
    assert set(legal_cards(hand, trick, trump, 2)) == set(cards("8 J", C))
    # 5. un adversaire a coupé : monter sur son atout si possible...
    trick = [(1, Card(D, Rank.ACE)), (2, Card(D, Rank.SEVEN)), (3, Card(C, Rank.TEN))]
    assert legal_cards(hand, trick, trump, 0) == [Card(C, Rank.JACK)]
    # ... sinon sous-couper (un atout plus petit reste obligatoire)
    low = cards("7 A", H) + cards("8 10", C) + cards("K", S)
    trick = [(1, Card(D, Rank.ACE)), (2, Card(D, Rank.SEVEN)), (3, Card(C, Rank.JACK))]
    assert set(legal_cards(low, trick, trump, 0)) == set(cards("8 10", C))
    # 6. le partenaire a coupé et il est maître : carte libre
    trick = [(1, Card(D, Rank.ACE)), (2, Card(C, Rank.SEVEN)), (3, Card(D, Rank.KING))]
    assert set(legal_cards(hand, trick, trump, 0)) == set(hand)
    # 7. pas la couleur, pas d'atout, adversaire maître : carte libre
    assert set(legal_cards(cards("7 A", H), [(1, Card(D, Rank.ACE))], trump, 2)) == set(cards("7 A", H))


def check_scoring():
    """Barème de la table : cf. belote/coinche/engine.py (RULES)."""
    base = {"seat": 0, "value": 100, "suit": C, "mult": 1}
    case = lambda contract, tricks, belote, points: score_deal(contract, tricks, belote, points)[:2]
    # réussi : contrat + points arrondis + belote pour l'attaque ; points arrondis + belote pour la défense
    assert case(base, [5, 3], None, [110, 52]) == ([210, 50], True)
    assert case({**base, "value": 80}, [5, 3], None, [87, 75]) == ([170, 80], True)   # 87 -> 90, 75 -> 80
    assert case({**base, "value": 80}, [5, 3], None, [84, 78]) == ([160, 80], True)   # 84 -> 80, 78 -> 80
    assert case({**base, "value": 80}, [5, 3], None, [85, 77]) == ([170, 80], True)   # 85 -> 90
    assert case(base, [4, 4], 0, [90, 72]) == ([210, 70], True)                       # belote compte pour réussir
    assert case(base, [5, 3], 1, [110, 52]) == ([210, 70], True)                      # belote de la défense
    assert case({**base, "value": 80}, [4, 4], None, [81, 81]) == ([160, 80], True)   # pas besoin de faire plus
    # chuté : défense = contrat + 160 + 20 par belote, attaque 0
    assert case(base, [4, 4], 0, [70, 92]) == ([0, 280], False)
    assert case(base, [4, 4], 1, [70, 92]) == ([0, 280], False)
    assert case(base, [4, 4], None, [70, 92]) == ([0, 260], False)
    # coinché : contrat x 2 + 160 ; seule la belote de l'attaque compte (+20 si elle n'a pas servi à réussir)
    coinche = {**base, "mult": 2}
    assert case(coinche, [6, 2], 0, [120, 42]) == ([380, 0], True)
    assert case(coinche, [4, 4], 0, [90, 72]) == ([360, 0], True)                     # belote utile : +0
    assert case(coinche, [6, 2], 1, [120, 42]) == ([360, 0], True)                    # belote de la défense : 0
    assert case(coinche, [4, 4], 0, [70, 92]) == ([0, 380], False)                    # belote de l'attaque à la défense
    assert case(coinche, [4, 4], 1, [70, 92]) == ([0, 360], False)                    # belote de la défense : 0
    # surcoinché : contrat x 3 + 160
    surco = {**base, "mult": 3}
    assert case(surco, [6, 2], None, [120, 42]) == ([460, 0], True)
    assert case(surco, [3, 5], None, [60, 102]) == ([0, 460], False)
    # capot : 250 au lieu de 162 ; contrat capot réussi = 250 + 250 ; chuté = 250 + 160
    scores, made, detail = score_deal(base, [8, 0], None, [162, 0])
    assert (scores, made, detail["capot_team"]) == ([350, 0], True, 0)
    assert case({**base, "value": CAPOT}, [8, 0], None, [162, 0]) == ([500, 0], True)
    assert case({**base, "value": CAPOT}, [7, 1], None, [150, 12]) == ([0, 410], False)


def check_bidding_flow():
    game = CoincheGame(rng=random.Random(1))
    first = game.current
    for _ in range(4):
        game.bid(game.current, ("pass",))
    assert game.phase == "redeal", "4 passes sans annonce : redistribution"

    game = CoincheGame(rng=random.Random(2))
    a = game.current
    game.bid(a, ("bid", 80, H))
    try:
        game.bid(game.current, ("bid", 80, S))
        raise AssertionError("une annonce doit être plus haute que la précédente")
    except ValueError:
        pass
    assert ("coinche",) in game.legal_bids(game.current), "l'adversaire suivant peut coincher"
    game.bid(game.current, ("coinche",))
    nxt = game.current
    assert team_of(nxt) == team_of(a) and ("surcoinche",) in game.legal_bids(nxt)
    assert not any(b[0] == "bid" for b in game.legal_bids(nxt)), "après une coinche : plus d'enchères"
    game.bid(nxt, ("surcoinche",))
    assert game.phase == "play" and game.contract["mult"] == 3 and game.trump == H
    assert game.current == (game.dealer + 1) % 4, "le joueur après le donneur entame"

    game = CoincheGame(rng=random.Random(3))
    game.bid(game.current, ("bid", 90, S))
    for _ in range(2):
        game.bid(game.current, ("pass",))
    assert game.phase == "bidding"
    game.bid(game.current, ("pass",))
    assert game.phase == "play", "3 passes après une annonce : on joue"


def check_bot_games(n_games=200):
    """Parties complètes entre robots : coups toujours légaux, 162 (ou 250) points de plis par donne,
    totaux = somme des donnes, belote annoncée Belote puis Rebelote."""
    bot = CoincheBot()
    rng = random.Random(0)
    deals = made = coinched = capots = 0
    for _ in range(n_games):
        game = CoincheGame(rng=random.Random(rng.random()))
        while not game.game_over:
            if game.phase == "redeal":
                game.new_deal()
                continue
            if game.phase == "done":
                deals += 1
                r = game.result
                made += r["made"]
                coinched += r["contract"]["mult"] > 1
                assert sum(r["tricks_won"]) == 8
                if r["capot_team"] is None:
                    assert sum(game.trick_points) == 162, game.trick_points
                else:
                    capots += 1
                game.new_deal()
                continue
            seat = game.current
            if game.phase == "bidding":
                game.bid(seat, bot.bid(game, seat))
            else:
                card = bot.play(game, seat)
                call = game.belote_call(seat, card)
                if call:
                    assert call == ("Rebelote!" if any(c.suit == game.trump and c.rank in (Rank.KING, Rank.QUEEN)
                                                       for c in game.played[seat]) else "Belote!")
                game.play(seat, card)
        assert sum(sum(h["scores"]) for h in game.history if not h["redeal"]) == sum(game.totals)
        assert max(game.totals) >= game.target
    return deals, made, coinched, capots


def main():
    check_trick_winner()
    print("Gagnant du pli (couleur, atout, ordre des atouts) : OK")
    check_legal_cards()
    print("Cartes jouables (fournir, monter à l'atout, partenaire maître, couper, sous-couper) : OK")
    check_scoring()
    print("Barème (arrondi, chute, belote utile ou non, coinche x2, surcoinche x3, capot) : OK")
    check_bidding_flow()
    print("Annonces (redistribution, enchère plus haute, coinche, surcoinche, 3 passes) : OK")
    deals, made, coinched, capots = check_bot_games()
    print(f"200 parties entre robots : OK ({deals} donnes, contrats réussis {100 * made / deals:.0f}%, "
          f"coinchés {coinched}, capots {capots})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
