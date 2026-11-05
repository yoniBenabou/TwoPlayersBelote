"""Comment l'IA de la Coinche à 4 (réseau PPO, models/coinche_4p.pt) annonce.

Le réseau n'a pas de règles écrites : on le fait annoncer sur des milliers de donnes tirées au hasard
et on regarde ce qu'il a en main quand il choisit chaque annonce. Les annonces de l'IA sont les mêmes
pour "IA" et "IA + recherche" (la recherche ne sert qu'au jeu de la carte) : son annonce est la plus
probable pour le réseau.

Trois parties :
- ouvertures : l'IA parle la première ; ce qu'elle a en main pour chaque annonce, puis, à l'inverse,
  ce qu'elle ouvre selon sa main (catégorie d'atout x As hors atout) ;
- réponses : son partenaire a ouvert (80 à 120), l'adversaire suivant a passé ; ce qu'elle répond selon
  ce qu'elle a dans l'atout du partenaire et ses As hors atout ;
- --main : les probabilités du réseau pour une main précise (ouverture, ou réponse avec --apres).

    python -m analyse_ia.echantillon                          # rapport complet (≈ 1 minute)
    python -m analyse_ia.echantillon --donnes 5000 --out analyse_ia/rapports/echantillon.md
    python -m analyse_ia.echantillon --main "VP 9P AP 7P AC 10C RK 8T"
    python -m analyse_ia.echantillon --main "9P 8P AC AK 10K RT DT 7T" --apres 90P

Cartes : valeur (7 8 9 10 V D R A) puis couleur (P pique, C cœur, K carreau, T trèfle), ou les
symboles ♠ ♥ ♦ ♣. Annonce du partenaire pour --apres : valeur puis couleur (90P, 100C, capotT...).
"""
import argparse
import random
import sys
from collections import Counter, defaultdict

import torch

from belote.coinche.engine import CAPOT, SUITS, CoincheGame
from belote.coinche.rl_env import CoincheEnv, action_to_bid
from belote.core.cards import Card, Rank, Suit
from coinche4.game import load_network
from coinche4.server import DEFAULT_MODEL

SYMBOL = {Suit.PIQUE: "♠", Suit.COEUR: "♥", Suit.CARREAU: "♦", Suit.TREFLE: "♣"}
SUIT_BY_LETTER = {"P": Suit.PIQUE, "C": Suit.COEUR, "K": Suit.CARREAU, "T": Suit.TREFLE,
                  "♠": Suit.PIQUE, "♥": Suit.COEUR, "♦": Suit.CARREAU, "♣": Suit.TREFLE}
RANK_BY_LABEL = {"7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE, "10": Rank.TEN,
                 "V": Rank.JACK, "D": Rank.QUEEN, "R": Rank.KING, "A": Rank.ACE}
RANK_LABEL = {r: k for k, r in RANK_BY_LABEL.items()}
OPENING_LEVELS = (80, 90, 100, 110, 120)

# catégories d'atout, de la plus forte à la plus faible (lues dans une couleur donnée)
CATEGORIES = ("V+9, 4 atouts ou +", "V+9, 3 atouts", "V+9 seuls", "V sans 9, 3 atouts ou +",
              "9 sans V, 3 atouts ou +", "V ou 9, 2 atouts", "V ou 9 sec", "ni V ni 9")


# ---------- le réseau ----------
def policy(network, game):
    """{annonce: probabilité} du réseau pour la place qui doit parler (comme coinche4.game.AIPlayer)."""
    env = CoincheEnv(bidding=True)
    env.game = game
    env.voids = [set() for _ in range(4)]
    env.trump_cap = [None] * 4
    env.belote_seen = None
    env.done = False
    env.bid_seats = set(range(4))
    mask = torch.as_tensor(env.legal_mask())
    with torch.no_grad():
        logits, _value = network(torch.as_tensor(env._observe()))
        probs = torch.softmax(logits.masked_fill(~mask, float("-inf")), dim=-1)
    return {action_to_bid(i): p for i, p in enumerate(probs.tolist()) if mask[i]}


def best(probs):
    return max(probs, key=probs.get)


# ---------- description d'une main ----------
def features(hand, suit):
    ranks = {c.rank for c in hand if c.suit == suit}
    return {
        "V": Rank.JACK in ranks, "9": Rank.NINE in ranks, "A_atout": Rank.ACE in ranks,
        "atouts": len(ranks),
        "As": sum(c.rank == Rank.ACE and c.suit != suit for c in hand),
        "10": sum(c.rank == Rank.TEN and c.suit != suit for c in hand),
        "couleurs": len({c.suit for c in hand}),
        "belote": Rank.KING in ranks and Rank.QUEEN in ranks,
    }


def category(f):
    v, n9, n = f["V"], f["9"], f["atouts"]
    if v and n9:
        return CATEGORIES[0] if n >= 4 else CATEGORIES[1] if n == 3 else CATEGORIES[2]
    if v and n >= 3:
        return CATEGORIES[3]
    if n9 and n >= 3:
        return CATEGORIES[4]
    if (v or n9) and n == 2:
        return CATEGORIES[5]
    if v or n9:
        return CATEGORIES[6]
    return CATEGORIES[7]


def best_suit(hand):
    """La couleur d'atout la plus naturelle de la main (majeures, longueur, force)."""
    def key(suit):
        f = features(hand, suit)
        return (f["V"] + f["9"], f["atouts"], sum(c.strength(suit) for c in hand if c.suit == suit))
    return max(SUITS, key=key)


def bid_label(bid):
    if bid[0] != "bid":
        return {"pass": "Passe", "coinche": "Coinche", "surcoinche": "Surcoinche"}[bid[0]]
    return f"{'Capot' if bid[1] == CAPOT else bid[1]} {SYMBOL[bid[2]]}"


def hand_label(hand):
    return " ".join(f"{RANK_LABEL[c.rank]}{SYMBOL[c.suit]}" for c in sorted(hand, key=lambda c: (SUITS.index(c.suit), -c.strength(None))))


# ---------- donnes ----------
def deal(rng, fixed=None):
    """Une donne : (partie, place qui parle). fixed : main imposée à cette place."""
    game = CoincheGame(rng=random.Random(rng.random()))
    seat = game.current
    if fixed is not None:
        rest = [c for h in game.hands for c in h if c not in fixed]
        rng.shuffle(rest)
        others = [s for s in range(4) if s != seat]
        game.hands[seat] = list(fixed)
        for i, s in enumerate(others):
            game.hands[s] = rest[8 * i: 8 * i + 8]
    return game, seat


def after_partner(game, opener_bid):
    """Le partenaire de la place qui parle ouvre opener_bid, l'adversaire suivant passe : c'est à
    la place d'en face (l'IA étudiée) de parler. Renvoie cette place."""
    opener = game.current
    game.bid(opener, opener_bid)
    game.bid(game.current, ("pass",))
    return game.current


# ---------- rapport ----------
def pct(x, n):
    return f"{100 * x / n:.0f} %" if n else "–"


def openings(network, n, rng, out):
    choices = Counter()
    profile = defaultdict(list)  # niveau -> features (dans la couleur annoncée ; meilleure couleur si passe)
    grid = defaultdict(Counter)  # (catégorie, As) -> niveau
    for _ in range(n):
        game, seat = deal(rng)
        hand = game.hands[seat]
        bid = best(policy(network, game))
        level = bid[1] if bid[0] == "bid" else "Passe"
        choices[level] += 1
        suit = bid[2] if bid[0] == "bid" else best_suit(hand)
        f = features(hand, suit)
        profile[level].append(f)
        natural = features(hand, best_suit(hand))
        grid[(category(natural), min(natural["As"], 3))][level] += 1

    out(f"## Ouvertures (l'IA parle la première, {n} donnes)\n")
    out("| Annonce | Fréquence | Valet | 9 | Valet + 9 | As d'atout | Atouts (moy.) | As hors atout (moy.) | 10 hors atout (moy.) | Belote | Couleurs (moy.) |")
    out("|---|---|---|---|---|---|---|---|---|---|---|")
    order = ["Passe"] + sorted(k for k in choices if k != "Passe")
    for level in order:
        fs = profile[level]
        k = len(fs)
        mean = lambda key: sum(f[key] for f in fs) / k
        share = lambda key: pct(sum(f[key] for f in fs), k)
        name = "Passe (meilleure couleur)" if level == "Passe" else ("Capot" if level == CAPOT else level)
        out(f"| {name} | {pct(k, n)} | {share('V')} | {share('9')} | {pct(sum(f['V'] and f['9'] for f in fs), k)} "
            f"| {share('A_atout')} | {mean('atouts'):.1f} | {mean('As'):.1f} | {mean('10'):.1f} | {share('belote')} | {mean('couleurs'):.1f} |")
    out("")
    out("### Ce qu'elle ouvre selon sa main (meilleure couleur d'atout × As hors atout)\n")
    out("Chaque case : l'annonce la plus fréquente, sa part, et le nombre de donnes.\n")
    out("| Atout | 0 As | 1 As | 2 As | 3 As |")
    out("|---|---|---|---|---|")
    for cat in CATEGORIES:
        cells = []
        for aces in range(4):
            c = grid[(cat, aces)]
            total = sum(c.values())
            if total < 15:
                cells.append(f"(peu de donnes : {total})" if total else "–")
                continue
            top, count = c.most_common(1)[0]
            top = "Passe" if top == "Passe" else ("Capot" if top == CAPOT else top)
            cells.append(f"**{top}** {pct(count, total)} ({total})")
        out(f"| {cat} | " + " | ".join(cells) + " |")
    out("")


def responses(network, n, rng, out):
    out(f"## Réponses (son partenaire ouvre, l'adversaire passe ; {n} donnes par niveau)\n")
    out("Ce qu'elle a dans l'atout du partenaire × ses As hors atout. Chaque case : la réponse la plus "
        "fréquente (+10, +20… dans la couleur du partenaire, « autre » = une autre couleur), sa part, "
        "et le nombre de donnes.\n")
    for level in OPENING_LEVELS:
        grid = defaultdict(Counter)
        for _ in range(n):
            game, _seat = deal(rng)
            suit = rng.choice(SUITS)
            me = after_partner(game, ("bid", level, suit))
            hand = game.hands[me]
            bid = best(policy(network, game))
            if bid[0] != "bid":
                answer = bid_label(bid)
            elif bid[2] == suit:
                answer = "Capot" if bid[1] == CAPOT else f"+{bid[1] - level}"
            else:
                answer = f"autre ({bid[1] if bid[1] != CAPOT else 'capot'})"
            f = features(hand, suit)
            grid[(category(f), min(f["As"], 3))][answer] += 1
        out(f"### Sur {level} du partenaire\n")
        out("| Dans son atout | 0 As | 1 As | 2 As | 3 As |")
        out("|---|---|---|---|---|")
        for cat in CATEGORIES:
            cells = []
            for aces in range(4):
                c = grid[(cat, aces)]
                total = sum(c.values())
                if total < 15:
                    cells.append(f"(peu : {total})" if total else "–")
                    continue
                top, count = c.most_common(1)[0]
                cells.append(f"**{top}** {pct(count, total)} ({total})")
            out(f"| {cat} | " + " | ".join(cells) + " |")
        out("")


# ---------- une main précise ----------
def parse_card(text):
    text = text.strip().upper().replace("♠", "P").replace("♥", "C").replace("♦", "K").replace("♣", "T")
    rank, suit = text[:-1], text[-1]
    if rank not in RANK_BY_LABEL or suit not in SUIT_BY_LETTER:
        raise ValueError(f"Carte inconnue : {text} (ex. VP, 10C, AK, 7T)")
    return Card(SUIT_BY_LETTER[suit], RANK_BY_LABEL[rank])


def parse_bid(text):
    text = text.strip().upper().replace("♠", "P").replace("♥", "C").replace("♦", "K").replace("♣", "T")
    value, suit = text[:-1], text[-1]
    value = CAPOT if value == "CAPOT" else int(value)
    return ("bid", value, SUIT_BY_LETTER[suit])


def one_hand(network, hand_text, after, rng, samples=200):
    hand = [parse_card(t) for t in hand_text.replace(",", " ").split()]
    if len(hand) != 8 or len(set(hand)) != 8:
        sys.exit("Il faut 8 cartes différentes.")
    # les autres mains ne changent rien à ce que voit l'IA, mais on moyenne quand même sur plusieurs donnes
    total = Counter()
    for _ in range(samples):
        if after:
            game = CoincheGame(rng=random.Random(rng.random()))
            me = (game.current + 2) % 4
            rest = [c for h in game.hands for c in h if c not in hand]
            rng.shuffle(rest)
            others = [s for s in range(4) if s != me]
            game.hands[me] = list(hand)
            for i, s in enumerate(others):
                game.hands[s] = rest[8 * i: 8 * i + 8]
            after_partner(game, parse_bid(after))
        else:
            game, _seat = deal(rng, fixed=hand)
        for bid, p in policy(network, game).items():
            total[bid] += p / samples
    print(f"Main : {hand_label(hand)}" + (f"  (le partenaire a ouvert {bid_label(parse_bid(after))})" if after else "  (l'IA parle la première)"))
    for bid, p in total.most_common(8):
        if p >= 0.005:
            print(f"  {bid_label(bid):12s} {100 * p:5.1f} %")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Comment l'IA de la Coinche à 4 annonce.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--donnes", type=int, default=20000, help="donnes pour les ouvertures")
    parser.add_argument("--reponses", type=int, default=6000, help="donnes par niveau pour les réponses")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--out", help="écrit le rapport (markdown) dans ce fichier")
    parser.add_argument("--main", help="une main précise : 8 cartes (ex. \"VP 9P AP 7P AC 10C RK 8T\")")
    parser.add_argument("--apres", help="avec --main : annonce d'ouverture du partenaire (ex. 90P)")
    args = parser.parse_args()
    torch.set_num_threads(1)
    network = load_network(args.model)
    if network is None:
        sys.exit(f"Modèle introuvable : {args.model}")
    rng = random.Random(args.seed)
    if args.main:
        return one_hand(network, args.main, args.apres, rng)
    lines = []

    def out(line=""):
        print(line)
        lines.append(line)

    out("# Comment l'IA annonce\n")
    out(f"Modèle : `{args.model}`. Annonce retenue : la plus probable pour le réseau (comme dans le site).\n")
    openings(network, args.donnes, rng, out)
    responses(network, args.reponses, rng, out)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
