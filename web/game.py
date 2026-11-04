"""Table du site web : la table de coinche4 (moteur, robots, IA entraînée), avec en plus
l'IA comme partenaire possible en Nord.

L'IA est indépendante de la place (son observation est construite depuis game.current) :
le même AIPlayer joue donc Est, Ouest et, si on le choisit, Nord. L'interface (web/index.html)
construit tous ses textes en français à partir des données des événements.
"""
from coinche4.game import PARTNER, AIPlayer, IllegalMove, SEARCH_SAMPLES, STYLES, Table

AI_PARTNER = "ai"
PARTNERS = (AI_PARTNER,) + STYLES


class WebTable(Table):
    def configure(self, name, partner, opponents, start=True):
        if partner not in PARTNERS:
            raise IllegalMove(f"Unknown partner: {partner}")
        ai_partner = partner == AI_PARTNER
        if ai_partner and self.network is None:
            raise IllegalMove("The AI model is not available on this server.")
        if start and self.game_id is not None and not self.game.game_over and self.human_actions > 0:
            self._record_game("abandoned")  # avec les anciens réglages
            self.game_id = None
        # la table de base ne connaît que les conventions : on la règle avec une convention, puis on met l'IA en Nord
        super().configure(name, STYLES[0] if ai_partner else partner, opponents, start=False)
        if ai_partner:
            self.partner = AI_PARTNER
            if self.ai is None:  # adversaires robots : une IA pour Nord seulement
                self.ai = AIPlayer(self.network, 0)
            self.players[PARTNER] = self.ai
        if start:
            return self.new_game()
        return None

    def state(self, events, viewer=None, since=None):
        data = super().state(events, viewer=viewer, since=since)
        data["aiAvailable"] = self.network is not None
        data["searchSamples"] = SEARCH_SAMPLES
        return data
