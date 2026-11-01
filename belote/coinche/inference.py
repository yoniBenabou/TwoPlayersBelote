"""Ce que les robots déduisent des cartes jouées (Coinche à 4), sans regarder les mains des autres.

- Chicane : un joueur qui ne fournit pas n'a plus la couleur demandée ; il n'a plus d'atout non plus s'il
  a défaussé alors qu'il devait couper (pas encore d'atout dans le pli, son partenaire pas maître).
- Plafond d'atout : un joueur obligé de monter qui ne monte pas n'a aucun atout plus fort que le meilleur
  atout du pli. À l'atout, on doit toujours monter si on peut (je joue la Dame, l'adversaire met le 7 :
  il n'a ni Roi, ni 10, ni As, ni 9, ni Valet) ; sur un pli coupé, quand son partenaire n'est pas maître,
  il doit surcouper s'il peut.
"""
from ..core.cards import Card, Rank
from .engine import partner_of, trick_winner


def _all_tricks(game):
    return [t for t, _w in game.tricks] + ([game.trick] if game.trick else [])


def trump_ceilings(game):
    """Pour chaque joueur, la force d'atout qu'il ne peut plus atteindre (None : pas de limite connue).
    Il peut seulement avoir des atouts strictement plus faibles."""
    trump = game.trump
    ceilings = [None] * 4
    for trick in _all_tricks(game):
        led = trick[0][1].suit
        for k, (s, c) in enumerate(trick[1:], start=1):
            before = trick[:k]
            trumps = [d for _t, d in before if d.suit == trump]
            if not trumps:
                continue
            best = max(d.strength(trump) for d in trumps)
            if c.suit == trump and c.strength(trump) > best:
                continue  # il est monté
            if led == trump:
                if c.suit != trump:
                    continue  # plus d'atout du tout : c'est une chicane
            elif c.suit == led or before[trick_winner(before, trump)][0] == partner_of(s):
                continue  # il a fourni, ou son partenaire était maître : pas d'obligation
            ceilings[s] = best if ceilings[s] is None else min(ceilings[s], best)
    return ceilings


def shown_voids(game):
    """Couleurs dont chaque joueur a montré qu'il n'en a plus (l'atout compris, voir plus haut ; et aussi
    l'atout quand tous les atouts sous son plafond sont déjà tombés)."""
    trump = game.trump
    voids = [set() for _ in range(4)]
    for trick in _all_tricks(game):
        led = trick[0][1].suit
        for k, (s, c) in enumerate(trick[1:], start=1):
            if c.suit == led:
                continue
            voids[s].add(led)
            before = trick[:k]
            if (c.suit != trump and not any(d.suit == trump for _t, d in before)
                    and before[trick_winner(before, trump)][0] != partner_of(s)):
                voids[s].add(trump)  # il devait couper : il n'a plus d'atout
    played = {c for cards in game.played for c in cards}
    for s, ceiling in enumerate(trump_ceilings(game)):
        if ceiling is not None and all(c in played for c in _trumps_below(trump, ceiling)):
            voids[s].add(trump)
    return voids


def _trumps_below(trump, ceiling):
    return [Card(trump, r) for r in Rank if Card(trump, r).strength(trump) < ceiling]


def may_hold(game, seat, card, voids=None, ceilings=None):
    """Le joueur seat peut-il encore avoir cette carte (d'après ce qu'il a montré) ?"""
    voids = shown_voids(game) if voids is None else voids
    if card.suit in voids[seat]:
        return False
    if card.suit == game.trump:
        ceilings = trump_ceilings(game) if ceilings is None else ceilings
        if ceilings[seat] is not None and card.strength(game.trump) >= ceilings[seat]:
            return False
    return True
