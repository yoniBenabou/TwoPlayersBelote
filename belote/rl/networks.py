import torch
import torch.nn as nn

from .env import BELIEF_SIZE, NUM_CARDS, OBS_SIZE


class ActorCriticNetwork(nn.Module):
    """Réseau acteur-critique partagé pour les deux sièges en self-play.

    BeloteEnv._observe() retourne toujours l'observation du point de vue du
    joueur actif (jamais "siège 0"/"siège 1"), donc une seule instance de ce
    réseau peut jouer indifféremment les deux mains : il ne voit jamais le
    siège physique, seulement sa propre main / les cartes jouées / les
    scores, déjà depuis sa perspective.

    Activation ReLU et initialisation par défaut de PyTorch (le plan initial
    prévoyait Tanh + initialisation orthogonale) : cette version converge
    bien, et tous les checkpoints entraînés en dépendent ; changer
    l'activation les rendrait inutilisables au rechargement.
    """

    def __init__(self, obs_size: int = OBS_SIZE, num_actions: int = NUM_CARDS, hidden_size: int = 128):
        super().__init__()
        self.obs_size = obs_size
        self.trunk = nn.Sequential(
            nn.Linear(obs_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
        )
        self.policy_head = nn.Linear(hidden_size, num_actions)
        self.value_head = nn.Linear(hidden_size, 1)

    @property
    def uses_belief(self) -> bool:
        """True si le réseau attend l'observation avec le tableau des cartes
        possibles chez l'adversaire (BeloteEnv(belief=True))."""
        return self.obs_size == OBS_SIZE + BELIEF_SIZE

    @classmethod
    def from_checkpoint(cls, path):
        """Recharge des poids sauvegardés, en déduisant la taille d'entrée
        (avec ou sans tableau des cartes possibles) et la taille cachée."""
        state = torch.load(path, map_location="cpu")
        hidden_size, obs_size = state["trunk.0.weight"].shape
        network = cls(obs_size=obs_size, hidden_size=hidden_size)
        network.load_state_dict(state)
        return network

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """obs: (..., obs_size) -> logits: (..., num_actions), value: (...)"""
        features = self.trunk(obs)
        logits = self.policy_head(features)
        value = self.value_head(features).squeeze(-1)
        return logits, value
