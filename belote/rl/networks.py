import torch
import torch.nn as nn

from .env import NUM_ACTIONS_BIDDING, NUM_CARDS, OBS_SIZE, obs_size as env_obs_size


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
        self.num_actions = num_actions
        self.trunk = nn.Sequential(
            nn.Linear(obs_size, hidden_size),
            nn.ReLU(),
            nn.Linear(hidden_size, hidden_size),
            nn.ReLU(),
        )
        self.policy_head = nn.Linear(hidden_size, num_actions)
        self.value_head = nn.Linear(hidden_size, 1)

    @property
    def uses_bidding(self) -> bool:
        """True si le réseau a les 6 actions d'annonce (BeloteEnv(bidding=True))."""
        return self.num_actions == NUM_ACTIONS_BIDDING

    @property
    def uses_belief(self) -> bool:
        """True si le réseau attend le tableau des cartes possibles chez
        l'adversaire (BeloteEnv(belief=True))."""
        return self.obs_size == env_obs_size(belief=True, bidding=self.uses_bidding)

    def env_kwargs(self) -> dict:
        """Options de BeloteEnv compatibles avec ce réseau : BeloteEnv(**network.env_kwargs())."""
        kwargs = {"belief": self.uses_belief, "bidding": self.uses_bidding}
        if self.obs_size != env_obs_size(**kwargs):
            raise ValueError(f"Taille d'entrée {self.obs_size} incompatible avec BeloteEnv")
        return kwargs

    @classmethod
    def from_checkpoint(cls, path):
        """Recharge des poids sauvegardés, en déduisant la taille d'entrée
        (tableau des cartes possibles, annonces), le nombre d'actions et la
        taille cachée."""
        state = torch.load(path, map_location="cpu")
        hidden_size, obs_size = state["trunk.0.weight"].shape
        num_actions = state["policy_head.weight"].shape[0]
        network = cls(obs_size=obs_size, num_actions=num_actions, hidden_size=hidden_size)
        network.load_state_dict(state)
        return network

    def init_from(self, path):
        """Démarrage à chaud depuis un modèle déjà entraîné, éventuellement
        plus petit (ex. sans annonces) : les poids communs sont copiés ; les
        nouvelles entrées (blocs ajoutés à la fin de l'observation) et les
        nouvelles sorties (actions d'annonce) partent de zéro. Au départ, le
        réseau joue donc les cartes exactement comme l'ancien modèle."""
        old = torch.load(path, map_location="cpu")
        old_hidden, old_in = old["trunk.0.weight"].shape
        old_out = old["policy_head.weight"].shape[0]
        hidden = self.trunk[0].out_features
        if old_hidden != hidden or old_in > self.obs_size or old_out > self.num_actions:
            raise ValueError("Modèle de départ incompatible (taille cachée, entrée ou sorties)")
        old_bidding = old_out == NUM_ACTIONS_BIDDING
        if old_in not in (env_obs_size(False, old_bidding), env_obs_size(True, old_bidding)) or \
                (old_in == env_obs_size(True, old_bidding)) != self.uses_belief:
            raise ValueError("Le modèle de départ doit avoir la même option belief que le nouveau")
        with torch.no_grad():
            self.trunk[0].weight.zero_()
            self.trunk[0].weight[:, :old_in] = old["trunk.0.weight"]
            self.trunk[0].bias.copy_(old["trunk.0.bias"])
            self.trunk[2].weight.copy_(old["trunk.2.weight"])
            self.trunk[2].bias.copy_(old["trunk.2.bias"])
            self.policy_head.weight.zero_()
            self.policy_head.bias.zero_()
            self.policy_head.weight[:old_out] = old["policy_head.weight"]
            self.policy_head.bias[:old_out] = old["policy_head.bias"]
            self.value_head.weight.copy_(old["value_head.weight"])
            self.value_head.bias.copy_(old["value_head.bias"])

    def forward(self, obs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """obs: (..., obs_size) -> logits: (..., num_actions), value: (...)"""
        features = self.trunk(obs)
        logits = self.policy_head(features)
        value = self.value_head(features).squeeze(-1)
        return logits, value
