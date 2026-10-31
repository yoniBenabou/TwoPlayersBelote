"""Réflexion de fin de donne (Coinche à 4) : sur les derniers plis, chaque carte jouable est essayée.

Le robot imagine les répartitions possibles des cartes qu'il ne voit pas (en respectant le nombre de
cartes de chacun et les couleurs qu'un joueur a montré ne plus avoir), joue la fin de la donne à cartes
ouvertes (chaque équipe joue au mieux) et compte les points des plis, der comprise. Il ne regarde jamais
les vraies mains des autres joueurs."""
import random

from ..core.cards import Card, Rank
from .engine import CAPOT, SUITS, legal_cards, team_of, trick_winner

DER = 10


def _voids(game):
    """Couleurs que chaque joueur a montré ne plus avoir (il n'a pas fourni)."""
    voids = [set() for _ in range(4)]
    for trick in [t for t, _w in game.tricks] + ([game.trick] if game.trick else []):
        led = trick[0][1].suit
        for s, c in trick[1:]:
            if c.suit != led:
                voids[s].add(led)
    return voids


def _worlds(game, seat, max_worlds, rng):
    """Répartitions possibles des cartes cachées entre les trois autres joueurs."""
    seen = {c for cards in game.played for c in cards} | {c for _s, c in game.trick} | set(game.hands[seat])
    unseen = [Card(s, r) for s in SUITS for r in Rank if Card(s, r) not in seen]
    others = [s for s in range(4) if s != seat]
    need = {s: len(game.hands[s]) for s in others}  # nombre de cartes : public
    voids = _voids(game)
    found = []

    def place(i, hands):
        if len(found) > 4 * max_worlds:
            return
        if i == len(unseen):
            found.append({s: list(h) for s, h in hands.items()})
            return
        card = unseen[i]
        for s in others:
            if len(hands[s]) < need[s] and card.suit not in voids[s]:
                hands[s].append(card)
                place(i + 1, hands)
                hands[s].pop()

    rng.shuffle(unseen)
    place(0, {s: [] for s in others})
    if len(found) > max_worlds:
        found = rng.sample(found, max_worlds)
    return found


def _search(hands, trick, cur, trump, done, team, alpha, beta):
    """Points que l'équipe team marque d'ici la fin, chaque équipe jouant au mieux (alpha-bêta)."""
    if not hands[cur]:
        return 0
    maximize = team_of(cur) == team
    best = -1 if maximize else 10 ** 6
    for card in legal_cards(hands[cur], trick, trump, cur):
        hand = hands[cur]
        hands[cur] = [c for c in hand if c != card]
        t2 = trick + [(cur, card)]
        if len(t2) == 4:
            winner = t2[trick_winner(t2, trump)][0]
            points = sum(c.points(trump) for _s, c in t2) + (DER if done + 1 == 8 else 0)
            gain = points if team_of(winner) == team else 0
            value = gain + _search(hands, [], winner, trump, done + 1, team, alpha - gain, beta - gain)
        else:
            value = _search(hands, t2, (cur + 1) % 4, trump, done, team, alpha, beta)
        hands[cur] = hand
        if maximize:
            best = max(best, value)
            alpha = max(alpha, value)
        else:
            best = min(best, value)
            beta = min(beta, value)
        if alpha >= beta:
            break
    return best


def endgame_card(game, seat, legal, rule_card, margin=1.0, max_worlds=30, last_tricks=3):
    """Sur les last_tricks derniers plis : la carte qui rapporte le plus en moyenne si elle fait gagner au
    moins margin points de plus que rule_card (la carte des règles) ; sinon rule_card."""
    if len(game.hands[seat]) > last_tricks or len(legal) < 2 or game.contract["value"] == CAPOT:
        return rule_card  # au capot, c'est le nombre de plis qui compte, pas les points : on garde les règles
    rng = random.Random(" ".join(sorted(str(c) for c in game.hands[seat])) + str(game.trick))
    worlds = _worlds(game, seat, max_worlds, rng)
    if not worlds:
        return rule_card
    team, trump, done = team_of(seat), game.trump, len(game.tricks)
    scores = {}
    for card in legal:
        total = 0
        for world in worlds:
            hands = [None] * 4
            for s, h in world.items():
                hands[s] = list(h)
            hands[seat] = [c for c in game.hands[seat] if c != card]
            t2 = list(game.trick) + [(seat, card)]
            if len(t2) == 4:
                winner = t2[trick_winner(t2, trump)][0]
                points = sum(c.points(trump) for _s, c in t2) + (DER if done + 1 == 8 else 0)
                gain = points if team_of(winner) == team else 0
                total += gain + _search(hands, [], winner, trump, done + 1, team, -1, 10 ** 6)
            else:
                total += _search(hands, t2, (seat + 1) % 4, trump, done, team, -1, 10 ** 6)
        scores[card] = total / len(worlds)
    best = max(legal, key=lambda c: scores[c])
    return best if scores[best] >= scores[rule_card] + margin else rule_card
