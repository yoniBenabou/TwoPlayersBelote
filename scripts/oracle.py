"""Plafond théorique contre RandomAgent : un joueur "tricheur" qui voit la main
de l'adversaire et joue le coup qui maximise l'espérance de son écart de
points, sachant que l'adversaire joue uniformément au hasard parmi ses coups
légaux (exactement RandomAgent). Aucun agent honnête ne peut faire mieux.

    python -m scripts.oracle --mode round --deals 600   # par manche (donnes dupliquées)
    python -m scripts.oracle --mode game --pairs 200    # parties complètes, premier à 501

Calcul exact par programmation dynamique sur (mes cartes restantes, ses
cartes restantes, qui mène, carte menée) : quelques secondes par manche.
"""
import argparse
import math
import random
import sys
from functools import lru_cache

from belote.core.cards import shuffled_deck
from belote.core.engine import deal_round, has_belote, legal_moves, random_trump, trick_winner

TARGET = 501


def play_deal(hand_me, hand_opp, trump, me_leads, rng):
    """Joue une manche tricheur (me) contre aléatoire. Retourne (mes points, ses points),
    dix de der et belote-rebelote compris."""
    me_cards, opp_cards = list(hand_me), list(hand_opp)

    def cards(mask, all_cards):
        return [(i, c) for i, c in enumerate(all_cards) if mask >> i & 1]

    def trick_value(lead_card, follow_card, me_leading, last):
        """(points du pli vus par moi, est-ce que je gagne le pli)."""
        pts = lead_card.points(trump) + follow_card.points(trump) + (10 if last else 0)
        me_wins = (trick_winner(lead_card, follow_card, trump) == "leader") == me_leading
        return (pts if me_wins else -pts), me_wins

    @lru_cache(maxsize=None)
    def value(mask_me, mask_opp, me_leading, led):
        """Espérance de (mes points futurs - ses points futurs) ; led = index de
        la carte menée dans la main du meneur, -1 si le pli est vide."""
        my_hand, opp_hand = cards(mask_me, me_cards), cards(mask_opp, opp_cards)
        if not my_hand and not opp_hand:
            return 0.0
        if led < 0:
            if me_leading:
                return max(value(mask_me & ~(1 << i), mask_opp, True, i) for i, _ in my_hand)
            return sum(value(mask_me, mask_opp & ~(1 << i), False, i) for i, _ in opp_hand) / len(opp_hand)
        last = len(my_hand) + len(opp_hand) == 1
        lead_card = me_cards[led] if me_leading else opp_cards[led]
        follower = opp_hand if me_leading else my_hand
        legal = set(legal_moves([c for _, c in follower], lead_card, trump))
        outcomes = []
        for i, c in follower:
            if c not in legal:
                continue
            pts, me_wins = trick_value(lead_card, c, me_leading, last)
            nm, no = (mask_me, mask_opp & ~(1 << i)) if me_leading else (mask_me & ~(1 << i), mask_opp)
            outcomes.append(pts + value(nm, no, me_wins, -1))
        return sum(outcomes) / len(outcomes) if me_leading else max(outcomes)

    mask_me = mask_opp = (1 << len(me_cards)) - 1
    me_leading, mine, theirs = me_leads, 0, 0
    for trick in range(8):
        my_hand, opp_hand = cards(mask_me, me_cards), cards(mask_opp, opp_cards)
        last = trick == 7
        if me_leading:
            li = max(my_hand, key=lambda ic: value(mask_me & ~(1 << ic[0]), mask_opp, True, ic[0]))[0]
            lead_card = me_cards[li]
            mask_me &= ~(1 << li)
            follow = rng.choice(legal_moves([c for _, c in opp_hand], lead_card, trump))
            mask_opp &= ~(1 << opp_cards.index(follow))
        else:
            lead_card = rng.choice([c for _, c in opp_hand])
            mask_opp &= ~(1 << opp_cards.index(lead_card))
            legal = set(legal_moves([c for _, c in my_hand], lead_card, trump))
            fi, follow = max(
                ((i, c) for i, c in my_hand if c in legal),
                key=lambda ic: (lambda pts, w: pts + value(mask_me & ~(1 << ic[0]), mask_opp, w, -1))(
                    *trick_value(lead_card, ic[1], False, last)),
            )
            mask_me &= ~(1 << fi)
        pts, me_wins = trick_value(lead_card, follow, me_leading, last)
        mine, theirs = (mine + pts, theirs) if me_wins else (mine, theirs - pts)
        me_leading = me_wins
    mine += 20 if has_belote(hand_me, trump) else 0
    theirs += 20 if has_belote(hand_opp, trump) else 0
    return mine, theirs


def random_deal():
    hand_a, hand_b = deal_round(shuffled_deck())
    return hand_a, hand_b, random_trump()


def ci95(scores):
    mean = sum(scores) / len(scores)
    sd = math.sqrt(sum((x - mean) ** 2 for x in scores) / (len(scores) - 1))
    return mean, 1.96 * sd / math.sqrt(len(scores))


def outcome(mine, theirs):
    return 1.0 if mine > theirs else 0.5 if mine == theirs else 0.0


def eval_rounds(n_deals, rng):
    """Donnes dupliquées : chaque donne jouée avec la main A puis la main B (la main A mène)."""
    deal_scores, margins = [], []
    for _ in range(n_deals):
        a, b, trump = random_deal()
        results = [play_deal(a, b, trump, True, rng), play_deal(b, a, trump, False, rng)]
        deal_scores.append(sum(outcome(m, t) for m, t in results) / 2)
        margins.append(sum(m - t for m, t in results) / 2)
    (win, win_ci), (margin, margin_ci) = ci95(deal_scores), ci95(margins)
    print(f"Par manche : {100 * win:.1f}% (±{100 * win_ci:.1f}pp) de manches gagnées, "
          f"écart {margin:+.1f} (±{margin_ci:.1f}) pts, {2 * n_deals} manches")


def eval_games(n_pairs, rng):
    """Parties complètes dupliquées : même suite de donnes, mains échangées, premier à 501."""
    pair_scores, rounds = [], 0
    for _ in range(n_pairs):
        deals = [random_deal() for _ in range(40)]
        pair = 0.0
        for has_a in (True, False):
            mine = theirs = 0
            for k, (a, b, trump) in enumerate(deals):
                a_leads = k % 2 == 0  # la main A mène une manche sur deux
                m, t = play_deal(a if has_a else b, b if has_a else a, trump, has_a == a_leads, rng)
                mine, theirs = mine + m, theirs + t
                if max(mine, theirs) >= TARGET:
                    break
            pair += outcome(mine, theirs) / 2
            rounds += k + 1
        pair_scores.append(pair)
    win, win_ci = ci95(pair_scores)
    print(f"Parties de {TARGET} : {100 * win:.1f}% (±{100 * win_ci:.1f}pp) de parties gagnées, "
          f"{2 * n_pairs} parties, {rounds / (2 * n_pairs):.1f} manches par partie")


def main():
    parser = argparse.ArgumentParser(description="Plafond théorique : joueur omniscient contre RandomAgent.")
    parser.add_argument("--mode", choices=["round", "game"], default="round")
    parser.add_argument("--deals", type=int, default=600, help="donnes dupliquées (mode round)")
    parser.add_argument("--pairs", type=int, default=200, help="parties dupliquées (mode game)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    random.seed(args.seed)
    rng = random.Random(args.seed + 1)
    if args.mode == "round":
        eval_rounds(args.deals, rng)
    else:
        eval_games(args.pairs, rng)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
