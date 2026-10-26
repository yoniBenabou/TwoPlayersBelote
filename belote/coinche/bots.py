"""Robots simples pour la Coinche à 4 (partenaire et adversaires du joueur
humain dans la page web, en attendant une IA entraînée). Règles à la main,
sans apprentissage : de quoi faire des parties crédibles pour vérifier les
règles, pas pour bien jouer."""
from ..core.cards import Card, Rank
from .engine import SUITS, partner_of, team_of, trick_winner

TRUMP_WEIGHT = {Rank.JACK: 25, Rank.NINE: 18, Rank.ACE: 11, Rank.TEN: 9, Rank.KING: 6, Rank.QUEEN: 6,
                Rank.EIGHT: 4, Rank.SEVEN: 4}


def hand_estimate(hand, trump):
    """Points qu'une main peut espérer avec cet atout : atouts pondérés + As et 10 secs ailleurs."""
    estimate = sum(TRUMP_WEIGHT[c.rank] for c in hand if c.suit == trump)
    for suit in SUITS:
        if suit == trump:
            continue
        ranks = {c.rank for c in hand if c.suit == suit}
        estimate += 10 * (Rank.ACE in ranks) + 5 * (Rank.ACE in ranks and Rank.TEN in ranks)
    return estimate


class CoincheBot:
    def bid(self, game, seat):
        legal = game.legal_bids(seat)
        hand = game.hands[seat]
        contract = game.contract
        if ("surcoinche",) in legal:
            return ("pass",)
        if ("coinche",) in legal:
            trump = contract["suit"]
            mine = {c.rank for c in hand if c.suit == trump}
            aces = sum(c.rank == Rank.ACE and c.suit != trump for c in hand)
            # coinche : des atouts forts dans leur couleur + un As, contre un contrat déjà haut
            if contract["value"] >= 90 and (Rank.JACK in mine or Rank.NINE in mine) and len(mine) >= 2 and aces >= 1:
                return ("coinche",)
        best = max(SUITS, key=lambda s: hand_estimate(hand, s))
        estimate = hand_estimate(hand, best)
        # estimation -> contrat : 55 -> 80, puis +10 par tranche de 10
        value = 80 + 10 * ((estimate - 55) // 10) if estimate >= 55 else None
        if contract is not None and team_of(contract["seat"]) == team_of(seat):
            # partenaire au contrat : une seule montée de 10, avec le Valet ou le 9 de son atout
            already = any(s == seat and a[0] == "bid" for s, a in game.bids)
            strong = any(c.suit == contract["suit"] and c.rank in (Rank.JACK, Rank.NINE) for c in hand)
            action = ("bid", contract["value"] + 10, contract["suit"])
            return action if strong and not already and action in legal else ("pass",)
        if value is None:
            return ("pass",)
        value = min(value, 160)
        action = ("bid", value, best)
        return action if action in legal else ("pass",)

    def play(self, game, seat):
        legal = game.legal_cards(seat)
        trump, trick = game.trump, game.trick
        strength = lambda c: (c.suit == trump, c.strength(trump))
        if not trick:
            attacking = team_of(game.contract["seat"]) == team_of(seat)
            trumps = [c for c in legal if c.suit == trump]
            gone = {c for cards in game.played for c in cards}
            outstanding = [c for c in self._all_trumps(trump) if c not in gone and c not in game.hands[seat]]
            if attacking and trumps and outstanding:
                top = max(trumps, key=strength)
                if all(top.strength(trump) > c.strength(trump) for c in outstanding):
                    return top  # atout maître : on fait tomber les atouts
            aces = [c for c in legal if c.rank == Rank.ACE and c.suit != trump]
            if aces:
                return aces[0]
            return min(legal, key=lambda c: (c.points(trump), strength(c)))
        winning = trick[trick_winner(trick, trump)]
        if winning[0] == partner_of(seat):
            # partenaire maître : on lui donne des points si son pli semble sûr, sinon petite carte
            safe = winning[1].suit == trump or winning[1].rank == Rank.ACE or len(trick) == 3
            key = (lambda c: (-c.points(trump), strength(c))) if safe else (lambda c: (c.points(trump), strength(c)))
            non_trump = [c for c in legal if c.suit != trump]
            return min(non_trump or legal, key=key)
        winners = [c for c in legal if trick_winner(trick + [(seat, c)], trump) == len(trick)]
        if winners:
            return min(winners, key=strength)
        return min(legal, key=lambda c: (c.points(trump), strength(c)))

    @staticmethod
    def _all_trumps(trump):
        return [Card(trump, r) for r in Rank]

