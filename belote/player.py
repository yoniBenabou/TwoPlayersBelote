class Player:
    def __init__(self, name):
        self.name = name
        self.hand = []
        self.dealt_hand = []
        self.pile = []
        self.score = 0

    def reset_for_manche(self, cards):
        self.hand = list(cards)
        self.dealt_hand = list(cards)
        self.pile = []

    def manche_points(self, trump_suit):
        return sum(card.points(trump_suit) for card in self.pile)
