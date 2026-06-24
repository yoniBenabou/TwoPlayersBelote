import sys

import numpy as np
import torch

from belote.env import BeloteEnv, NUM_CARDS
from belote.networks import ActorCriticNetwork


def main():
    env = BeloteEnv()
    obs, info = env.reset(seed=1)

    net = ActorCriticNetwork()
    obs_tensor = torch.as_tensor(obs, dtype=torch.float32)

    logits, value = net(obs_tensor)
    assert logits.shape == (NUM_CARDS,), logits.shape
    assert value.shape == (), value.shape
    print("Forward pass sur une observation réelle de BeloteEnv (siège 0) : OK")
    print(f"  logits.shape = {tuple(logits.shape)} | value = {value.item():.4f}")

    # Même réseau, appelé sur l'observation du siège 1 après un coup : doit
    # fonctionner de façon identique, puisque l'observation est déjà relative
    # au joueur actif (pas de notion de "siège" dans l'entrée du réseau).
    action = int(np.flatnonzero(info["legal_actions"])[0])
    obs2, _, _, info2 = env.step(action)
    obs2_tensor = torch.as_tensor(obs2, dtype=torch.float32)
    logits2, value2 = net(obs2_tensor)
    assert logits2.shape == (NUM_CARDS,), logits2.shape
    print("Forward pass sur l'observation du joueur suivant (siège 1) : OK")
    print(f"  logits.shape = {tuple(logits2.shape)} | value = {value2.item():.4f}")

    batch = torch.as_tensor(np.stack([obs, obs2, obs]), dtype=torch.float32)
    logits_batch, value_batch = net(batch)
    assert logits_batch.shape == (3, NUM_CARDS), logits_batch.shape
    assert value_batch.shape == (3,), value_batch.shape
    print("Forward pass en batch (3 observations) : OK")

    n_params = sum(p.numel() for p in net.parameters())
    print(f"Nombre de paramètres du réseau : {n_params}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
