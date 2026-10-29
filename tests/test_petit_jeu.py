"""Robot "petit jeu" (Coinche à 4) : annonces et entames selon les règles de la table."""
import random
import sys

from belote.coinche.engine import CoincheGame
from belote.coinche.petit_jeu import PetitJeuBot, best_opening, opening_value
from belote.core.cards import Card, Rank, Suit

S, H, D, C = Suit.PIQUE, Suit.COEUR, Suit.CARREAU, Suit.TREFLE
R = {"7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE, "10": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN,
     "K": Rank.KING, "A": Rank.ACE}


def hand(**suits):
    """hand(S="J 8 7", H="A") -> liste de cartes."""
    out = []
    for name, ranks in suits.items():
        suit = {"S": S, "H": H, "D": D, "C": C}[name]
        out += [Card(suit, R[r]) for r in ranks.split()]
    return out


def table(hands, dealer=3):
    """Partie avec des mains imposées ; le donneur 3 (Est) fait parler Sud (0) en premier."""
    game = CoincheGame(rng=random.Random(0))
    # cartes de complément les plus faibles d'abord (7, 8, Dame...), Valets et 9 en dernier, distribuées
    # à tour de rôle : elles ne doivent pas donner d'annonce à une main qu'on n'a pas écrite
    order = [Rank.SEVEN, Rank.EIGHT, Rank.QUEEN, Rank.KING, Rank.TEN, Rank.ACE, Rank.NINE, Rank.JACK]
    rest = [c for r in order for c in (Card(s, r) for s in Suit) if all(c not in h for h in hands if h)]
    full = [list(h or []) for h in hands] + [[] for _ in range(4 - len(hands))]
    while any(len(h) < 8 for h in full):
        for h in full:
            if len(h) < 8:
                h.append(rest.pop(0))
    game.hands = full
    game.dealer = dealer
    game.current = (dealer + 1) % 4
    return game


def check_openings():
    assert opening_value(hand(S="J 8 7", H="A 10", D="K Q", C="7"), S) == 80
    assert opening_value(hand(S="9 8 7"), S) == 80
    assert opening_value(hand(S="J 8"), S) is None                       # deux atouts seulement
    assert opening_value(hand(S="J 9 7"), S) == 90
    assert opening_value(hand(S="J 9 A 8", H="7", D="7", C="7 8"), S) == 100   # maître, 4 couleurs
    assert opening_value(hand(S="J 9 K 8 7", H="7", D="7", C="8"), S) == 100   # maître sans l'As
    assert opening_value(hand(S="J 9 A 8", H="7 8", D="7 8"), S) == 110        # tricolore
    assert opening_value(hand(S="J 9 A 8 7", H="7 8 9"), S) == 120             # bicolore
    assert opening_value(hand(S="J 9 A"), S) == 90                             # l'As sans 4e atout : 90
    assert best_opening(hand(S="J 8 7", H="J 9 7", D="A", C="A")) == (90, H)


def check_responses():
    bot = PetitJeuBot()
    # exemple des règles : 80 piques avec le Valet ; le partenaire a le 9 de pique (+10) et l'As de cœur (+10)
    north = hand(S="9 8", H="A 7", D="7 8", C="7 8")
    game = table([hand(S="J 10 7", H="K Q", D="K Q", C="K"), hand(H="8 9", D="9", C="9"), north, None])
    for _ in range(2):
        game.bid(game.current, bot.bid(game, game.current))
    assert game.bids[0][1] == ("bid", 80, S), game.bids
    assert bot.bid(game, 2) == ("bid", 100, S)
    # le 9 sec ne répond pas
    game = table([hand(S="J 10 7", H="K Q", D="K Q", C="K"), hand(H="8 9", D="9", C="9"),
                  hand(S="9", H="A 7", D="7 8", C="7 8 10"), None])
    for _ in range(2):
        game.bid(game.current, bot.bid(game, game.current))
    assert bot.bid(game, 2) == ("pass",)
    # sur 90 : +10 par As hors atout, même sans majeure
    game = table([hand(S="J 9 7", H="K Q", D="K Q", C="K"), hand(H="8 9", D="9", C="9"),
                  hand(S="8", H="A 7", D="A 8", C="7 8 10"), None])
    for _ in range(2):
        game.bid(game.current, bot.bid(game, game.current))
    assert game.bids[0][1] == ("bid", 90, S) and bot.bid(game, 2) == ("bid", 110, S)


def check_opponent_spoke_first():
    bot = PetitJeuBot()
    # exemple des règles : 80 cœurs, un adversaire dit 90 piques, le partenaire (Valet de cœur) dit 100 cœurs
    game = table([hand(H="9 8 7", S="7 8", D="7 8", C="7"),
                  hand(S="J 9 10", H="10", D="9", C="9 10 J"),
                  hand(H="J 10", S="Q", D="Q K", C="Q K 8"), None])
    game.bid(0, bot.bid(game, 0))
    assert game.bids[-1][1] == ("bid", 80, H)
    game.bid(1, bot.bid(game, 1))
    assert game.bids[-1][1] == ("bid", 90, S), game.bids
    assert bot.bid(game, 2) == ("bid", 100, H)
    # j'ouvrirais à 80 mais un adversaire a dit 80 : je dis 90
    game = table([hand(S="J 9 10", H="10", D="9", C="9 10 J"), hand(H="9 8 7", S="7 8", D="7 8", C="7")])
    game.bid(0, ("bid", 80, S))
    assert bot.bid(game, 1) == ("bid", 90, H)
    # un 100 ne monte pas à 110 parce qu'un adversaire a parlé
    game = table([hand(S="J 9 10", H="10", D="9", C="9 10 J"), hand(H="J 9 A 8", S="7", D="7", C="7 8")])
    game.bid(0, ("bid", 100, S))
    assert bot.bid(game, 1) == ("pass",)


def check_leads():
    bot = PetitJeuBot()
    game = table([hand(S="J 9 7", H="A 10", D="K", C="8 7"), None, None, None])
    game.bid(0, ("bid", 90, S))
    for seat in (1, 2, 3):
        game.bid(seat, ("pass",))
    assert game.current == 0
    assert bot.play(game, 0) == Card(S, Rank.JACK)            # attaque : atout maître d'abord
    # défense : As, puis singleton, puis couleur longue
    game = table([None, hand(S="J 9 7", H="A 10")])
    game.bid(0, ("pass",))
    game.bid(1, ("bid", 90, S))
    game.bid(2, ("pass",)); game.bid(3, ("pass",)); game.bid(0, ("pass",))
    game.hands[0] = hand(H="7", D="A 8 9 10", C="8 9 K")
    assert bot.play(game, 0) == Card(D, Rank.ACE)
    game.hands[0] = hand(H="7", D="8 9 10", C="8 9 K Q")
    assert bot.play(game, 0) == Card(H, Rank.SEVEN)           # singleton
    game.hands[0] = hand(H="7 8", D="8 9 10", C="8 9 K")
    assert bot.play(game, 0).suit in (D, C) and bot.play(game, 0).rank in (Rank.EIGHT,)


def check_full_games(n=100):
    bot = PetitJeuBot()
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
    check_opponent_spoke_first()
    check_leads()
    check_full_games()
    print("Robot petit jeu (ouvertures, réponses, adversaire qui parle avant, entames, parties complètes) : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
