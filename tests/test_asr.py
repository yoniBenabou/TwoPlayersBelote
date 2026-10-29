"""Robot "AsR" (Coinche à 4) : exemples du document de conventions."""
import random
import sys

from belote.coinche.asr import AsRBot, natural_opening
from belote.coinche.engine import CAPOT, CoincheGame
from belote.core.cards import Card, Rank, Suit
from tests.test_petit_jeu import hand, table

S, H, D, C = Suit.PIQUE, Suit.COEUR, Suit.CARREAU, Suit.TREFLE
bot = AsRBot()


def opening(**suits):
    o = natural_opening(hand(**suits))
    return o and o[:2]


def check_openings():
    assert opening(H="J 9 A 10", S="A", D="7 8", C="7") == (110, H)       # main exceptionnelle : directement
    assert opening(H="J 9 A K", S="10 K Q", C="10") == (110, H)            # exemple du 110 cœur
    assert opening(S="A 7", D="A 8", H="7 8", C="8 Q")[0] == 80               # deux As, sans atout
    assert opening(H="J 7 8", S="A", D="7 8", C="7 Q") == (90, H)          # Valet troisième + As
    assert opening(H="J 7 8", S="K", D="7 8", C="7 Q") is None             # jamais 90 sans As
    assert opening(H="9 A 7 8", S="K", D="7 8", C="7") == (90, H)          # 9 quatrième, As d'atout
    assert opening(H="J 9 A", S="K", D="7 8", C="7 Q") == (100, H)         # maîtrise
    assert opening(H="J 9 7 8", S="K", D="7 8", C="7") == (100, H)         # Valet + 9 quatrièmes
    assert opening(H="J 9 A", S="A", D="7 8", C="7 Q") == (80, H)          # deux As : 80 d'abord


def deal(hands, bids):
    """Table avec des mains imposées et des annonces jouées dans l'ordre (à partir de Sud)."""
    game = table(hands)
    for b in bids:
        game.bid(game.current, b)
    return game


P = ("pass",)


def check_answers_to_90():
    # Valet complémentaire, aucun As : 100 ; Valet + 2 As : 120 ; 9 second + 1 As : 110 ; 9 sec : rien
    opener = hand(H="9 7 8 K", S="A", D="7", C="7 Q")
    for north, want in [(hand(H="J", S="Q", D="9 Q", C="9 K"), ("bid", 100, H)),
                        (hand(H="J", S="Q", D="A Q", C="A K"), ("bid", 120, H))]:
        g = deal([opener, hand(S="7 8", D="K", C="8"), north], [("bid", 90, H), P])
        assert bot.bid(g, 2) == want, (north, bot.bid(g, 2))
    opener = hand(H="J 7 8", S="A", D="7", C="7 Q 8")
    for north, want in [(hand(H="9 10", S="Q", D="A Q", C="9 K"), ("bid", 110, H)),
                        (hand(H="9", S="Q K", D="A Q", C="9 K 10"), P)]:
        g = deal([opener, hand(S="7 8", D="K", C="J"), north], [("bid", 90, H), P])
        assert bot.bid(g, 2) == want, (north, bot.bid(g, 2))


def check_answers_to_80():
    # 80 cœur, partenaire 90 (Valet ou 9) ; j'ai le complément et deux As hors cœur : 110 (les deux As
    # sont déjà annoncés par le 80 : +10 pour le complément, +10 parce qu'ils sont hors atout)
    south = hand(H="9 7", S="A", D="A", C="7 8 Q 10")
    north = hand(H="J 8 10", S="7 8", D="7 8", C="A")
    g = deal([south, hand(S="9 10", D="9 10", C="9"), north], [])
    g.bid(0, bot.bid(g, 0))
    assert g.bids[-1][1] == ("bid", 80, H), g.bids
    g.bid(1, P)
    assert bot.bid(g, 2) == ("bid", 90, H)
    g.bid(2, ("bid", 90, H)); g.bid(3, P)
    assert bot.bid(g, 0) == ("bid", 110, H)
    g.hands[0] = hand(H="9 7", S="A", D="A", C="A 8 Q 10")              # trois As hors atout : 120
    assert bot.bid(g, 0) == ("bid", 120, H)
    # partenaire 100 dans une autre couleur : +10 avec deux As hors de son atout, +20 avec trois
    for mine, want in [(hand(S="A", D="A", C="8 7", H="7 8 Q K"), ("bid", 110, C)),
                       (hand(S="A", D="A", H="A 7", C="8 7"), ("bid", 120, C)),
                       (hand(S="A 7", D="Q", H="K Q 7", C="8 7"), P)]:
        g = deal([mine, hand(S="9", D="9", H="9")], [("bid", 80, S), P, ("bid", 100, C), P])
        assert bot.bid(g, 0) == want, (mine, bot.bid(g, 0))
    # partenaire 110 dans une autre couleur : +10 par As
    g = deal([hand(S="A 7", D="Q 7", H="K Q 7", C="8"), hand(S="9", D="9", H="9")], [("bid", 80, S), P, ("bid", 110, C), P])
    assert bot.bid(g, 0) == ("bid", 120, C)


def check_110_dialogue():
    # 110 cœur ; Nord a un As noir : 120 ; Sud a l'autre : 130 ; Nord compte ses plis noirs en plus : 160
    south = hand(H="J 9 A K", S="7 8", C="A", D="7")
    north = hand(S="A 10 K", C="10", H="7", D="8 9 Q")
    g = deal([south, hand(S="Q J", D="10 J", C="7 8"), north], [])
    g.bid(0, bot.bid(g, 0))
    assert g.bids[-1][1] == ("bid", 110, H), g.bids
    g.bid(1, P)
    g.bid(2, bot.bid(g, 2))
    assert g.bids[-1][1] == ("bid", 120, H), g.bids
    g.bid(3, P)
    g.bid(0, bot.bid(g, 0))
    assert g.bids[-1][1] == ("bid", 130, H), g.bids
    g.bid(1, P)
    assert bot.bid(g, 2) == ("bid", 160, H)
    g.bid(2, ("bid", 160, H)); g.bid(3, P)
    assert bot.bid(g, 0) == ("bid", CAPOT, H)


def check_100_dialogue():
    # 100 cœur (Sud a l'As de pique) ; Nord a deux As : 120 ; Sud a le dernier : 130 (« annonce tes autres
    # plis maîtres ») ; Nord : le 10 de carreau derrière son As, le 10 de pique derrière l'As de Sud : 150
    south = hand(H="J 9 7 8", S="A", D="7 8", C="7")
    north = hand(D="A 10 Q", C="A 8", S="10", H="Q K")
    g = deal([south, hand(S="9 J", D="9 J", C="9 J"), north], [])
    g.bid(0, bot.bid(g, 0))
    assert g.bids[-1][1] == ("bid", 100, H), g.bids
    g.bid(1, P)
    g.bid(2, bot.bid(g, 2))
    assert g.bids[-1][1] == ("bid", 120, H), g.bids
    g.bid(3, P)
    g.bid(0, bot.bid(g, 0))
    assert g.bids[-1][1] == ("bid", 130, H), g.bids
    g.bid(1, P)
    g.bid(2, bot.bid(g, 2))
    assert g.bids[-1][1] == ("bid", 150, H), g.bids
    g.bid(3, P)
    assert bot.bid(g, 0) == ("bid", CAPOT, H)
    # sans le troisième As, Sud ne remonte pas
    g = deal([hand(H="J 9 A 8", S="K", D="7 8", C="7"), hand(S="9 J", D="9 J", C="9 J"), north],
             [("bid", 100, H), P, ("bid", 120, H), P])
    assert bot.bid(g, 0) == P
    # Nord a les trois As (130) : Sud remonte à 140 ; Nord n'a pas d'autre pli maître : il passe
    north3 = hand(D="A Q", C="A 8", S="A 8", H="Q K")
    g = deal([hand(H="J 9 A 8", S="K", D="7 8", C="7"), hand(S="9 J", D="9 J", C="9 J"), north3],
             [("bid", 100, H), P, ("bid", 130, H), P])
    assert bot.bid(g, 0) == ("bid", 140, H)
    g.bid(0, ("bid", 140, H)); g.bid(1, P)
    assert bot.bid(g, 2) == P


def check_capot_on_100():
    # Nord a quatre plis maîtres sur le 100 de Sud ; la réponse dépend de qui a la partance
    # (donneur 3 : Sud entame ; donneur 1 : Nord entame ; donneur 0 : Ouest, un adversaire, entame)
    with_trump = hand(D="A 10 K", C="A", S="Q 8", H="7 8")           # deux As hors atout, un atout
    no_trump = hand(D="A 10 K", C="A 8", S="Q 8 7")                   # deux As hors atout, sans atout
    three_aces = hand(D="A 10", C="A", S="A 8", H="7 8 Q")           # trois As hors atout, un atout
    for dealer, nh, want in [(3, no_trump, ("bid", CAPOT, H)),        # le partenaire a la partance
                             (1, with_trump, ("bid", CAPOT, H)),      # j'ai la partance, avec un atout
                             (1, no_trump, ("bid", 120, H)),          # j'ai la partance, sans atout : +10 par As
                             (0, no_trump, ("bid", 120, H)),          # adversaire, sans atout : +10 par As
                             (0, with_trump, ("bid", 120, H)),        # adversaire, un atout, deux As : +10 par As
                             (0, three_aces, ("bid", CAPOT, H))]:     # adversaire, un atout, trois As : capot
        g = table([hand(H="J 9 A K"), hand(S="9 J"), nh], dealer=dealer)
        while g.current != 0:
            g.bid(g.current, P)
        g.bid(0, ("bid", 100, H))
        while g.current != 2:
            g.bid(g.current, P)
        assert bot.bid(g, 2) == want, (dealer, nh, bot.bid(g, 2))


def check_collage():
    # un adversaire dit 90 ; j'ai une main de 90 : je colle à 100 ; mon partenaire ne répond que le complément
    g = deal([hand(S="J 9 7", D="A"), hand(H="J 7 8", C="A", D="7", S="Q")], [("bid", 90, S)])
    assert bot.bid(g, 1) == ("bid", 100, H)
    g.bid(1, ("bid", 100, H)); g.bid(2, P)
    g.hands[3] = hand(H="9 10", C="A 10", D="A 10", S="K 8")
    assert bot.bid(g, 3) == ("bid", 110, H)      # complément seulement, pas les As


def check_play():
    # appels : atout carreau, je veux pique (famille opposée) -> je défausse trèfle ; je veux cœur -> cœur
    assert AsRBot._call_discard(hand(S="A 7", C="8 9"), hand(S="A 7", C="8 9"), D).suit == C
    assert AsRBot._call_discard(hand(H="A 7", C="8 9"), hand(H="A 7", C="8 9"), D).suit == H
    # exemples de Noa : atout cœur, appel à carreau -> carreau (direct), appel à pique -> trèfle (indirect)
    assert AsRBot._call_discard(hand(D="A 7", C="8 9"), hand(D="A 7", C="8 9"), H).suit == D
    assert AsRBot._call_discard(hand(S="A 7", C="8 9", D="8"), hand(S="A 7", C="8 9", D="8"), H).suit == C
    # atout pique, appel à trèfle -> trèfle ; appel à carreau -> cœur
    assert AsRBot._call_discard(hand(C="A 7", H="8 9"), hand(C="A 7", H="8 9"), S).suit == C
    assert AsRBot._call_discard(hand(D="A 7", H="8 9"), hand(D="A 7", H="8 9"), S).suit == H
    # jeter l'As = la longue maîtresse : seulement avec As-10-Roi
    assert AsRBot._call_discard(hand(D="A 10 K 7", H="8 9"), hand(D="A 10 K 7", H="8 9"), S) == Card(D, Rank.ACE)
    assert AsRBot._call_discard(hand(D="A 10 7", H="8 9"), hand(D="A 10 7", H="8 9"), S) != Card(D, Rank.ACE)
    # 9 sans le Valet : petit atout d'abord
    g = deal([hand(S="9 7 8", H="A 10", D="K", C="8")], [("bid", 90, S), P, P, P])
    assert bot.play(g, 0) == Card(S, Rank.SEVEN)
    # contrés : on n'entame pas atout (Sud a pris 100 pique, Ouest a coinché)
    g = deal([hand(S="J 9 A 8", H="A 10", D="K", C="8")], [("bid", 100, S), ("coinche",), P, P, P])
    assert g.phase == "play" and g.contract["mult"] == 2 and g.current == 0, (g.phase, g.bids)
    assert bot.play(g, 0).suit != S
    # on ne défausse pas un As sans le 10 et le Roi derrière : As-Valet de cœur
    g = deal([None, None, hand(S="J 9 A 8")], [P, P, ("bid", 100, S), P, P, P])
    g.trick = [(1, Card(D, Rank.ACE)), (2, Card(D, Rank.SEVEN))]      # Ouest, partenaire d'Est, est maître
    g.current = 3
    g.hands[3] = hand(H="A J", C="7 8 K Q 10")
    from belote.coinche.bots import CoincheBot
    assert CoincheBot().play(g, 3) == Card(H, Rank.ACE)               # l'ancien comportement donnait l'As
    assert bot.play(g, 3) != Card(H, Rank.ACE)
    g.hands[3] = hand(H="A 10", C="7 8 K Q J 9")                     # As-10 seulement : il le garde
    assert Card(H, Rank.ACE) not in bot._keep_aces(g, 3, g.legal_cards(3))
    g.hands[3] = hand(H="A 10 K", C="7 8 Q J 9")                     # As-10-Roi : il peut le donner
    assert Card(H, Rank.ACE) in bot._keep_aces(g, 3, g.legal_cards(3))
    g.hands[3] = hand(H="A", C="A")                                   # que des As : pas le choix
    assert bot._keep_aces(g, 3, g.legal_cards(3)) == g.legal_cards(3)
    # signal de belote : Roi en premier avec un nombre pair d'atouts, Dame avec un nombre impair
    g = deal([hand(S="K Q 7 8", H="A 10", D="K", C="8")], [("bid", 90, S), P, P, P])
    assert bot._belote_signal(g, 0, g.legal_cards(0), Card(S, Rank.QUEEN)) == Card(S, Rank.KING)
    g = deal([hand(S="K Q 7", H="A 10", D="K Q", C="8")], [("bid", 90, S), P, P, P])
    assert bot._belote_signal(g, 0, g.legal_cards(0), Card(S, Rank.KING)) == Card(S, Rank.QUEEN)
    # défense : faire couper le preneur (Ouest a pris, il n'a plus de carreau)
    g = deal([None, hand(S="J 9 A 8")], [P, ("bid", 100, S), P, P, P])
    g.tricks = [([(0, Card(D, Rank.SEVEN)), (1, Card(S, Rank.EIGHT)), (2, Card(D, Rank.EIGHT)),
                  (3, Card(D, Rank.NINE))], 1)]
    g.current = 0
    g.hands[0] = hand(D="Q 10", H="K Q", C="A K 7")
    assert bot.play(g, 0) == Card(D, Rank.QUEEN)
    # exemple de Noa : contrat 90 carreau ; Ouest (défense) entame l'As de trèfle et gagne le pli : il rejoue trèfle
    g2 = deal([hand(D="J 9 7 8")], [("bid", 90, D), P, P, P])
    g2.tricks = [([(1, Card(C, Rank.ACE)), (2, Card(C, Rank.EIGHT)), (3, Card(C, Rank.NINE)),
                   (0, Card(C, Rank.KING))], 1)]
    g2.played[1].append(Card(C, Rank.ACE))
    g2.current = 1
    g2.hands[1] = hand(C="10 7", S="7 8 9 K Q")                         # pique plus long, mais il rejoue trèfle,
    assert bot.play(g2, 1) == Card(C, Rank.TEN), bot.play(g2, 1)       # avec sa plus grosse carte
    # premier pli, la défense entame : un As hors atout d'abord
    g3 = deal([hand(D="J 9 7 8")], [("bid", 90, D), P, P, P])
    g3.current = 1
    g3.hands[1] = hand(C="A 7", S="7 8 9 K Q", H="8")
    assert bot.play(g3, 1) == Card(C, Rank.ACE)
    g.hands[0] = hand(D="A", H="K Q", C="7 8 9")                       # seul carreau : l'As, sacrifié pour le faire couper
    assert bot.play(g, 0) == Card(D, Rank.ACE)


def check_keep_nine():
    """Sur le Valet d'atout : 9-As-10 tous maîtres -> le 9 au partenaire (le plus de points), le moins de
    points à un adversaire (le 10) ; 9 pas accompagné de maîtres -> on garde le 9."""
    from belote.coinche.bots import CoincheBot
    from belote.coinche.papi_robert import PapiRobertBot
    from belote.coinche.petit_jeu import PetitJeuBot
    for kind in (CoincheBot, PetitJeuBot, PapiRobertBot, AsRBot):
        for trick in ([(0, Card(S, Rank.JACK))], [(0, Card(S, Rank.EIGHT)), (1, Card(S, Rank.JACK))]):
            g = deal([hand(S="J 8"), hand(S="7 K"), hand(S="9 A 10", H="7 8")], [("bid", 90, S), P, P, P])
            g.trick, g.current = list(trick), 2
            want = Card(S, Rank.NINE) if len(trick) == 1 else Card(S, Rank.TEN)
            assert kind().play(g, 2) == want, (kind.__name__, trick)
        # l'As d'atout est dehors : mes atouts ne sont pas tous maîtres, je garde le 9 sur le Valet du partenaire
        g = deal([hand(S="J 8"), hand(S="A K"), hand(S="9 10 7", H="7 8")], [("bid", 90, S), P, P, P])
        g.trick, g.current = [(0, Card(S, Rank.JACK))], 2
        assert kind().play(g, 2) == Card(S, Rank.SEVEN), kind.__name__


def check_full_games(n=100):
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
    check_answers_to_90()
    check_answers_to_80()
    check_110_dialogue()
    check_100_dialogue()
    check_capot_on_100()
    check_collage()
    check_play()
    check_keep_nine()
    check_full_games()
    print("Robot AsR (ouvertures, réponses à 80 et 90, dialogue 110-120-130, dialogue 100, capot sur 100, collage, jeu, parties) : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
