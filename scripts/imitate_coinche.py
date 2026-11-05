"""Coinche à 4 : réseau de départ qui imite les robots (Petit jeu, Papi Robert, AsR).

Sert à comparer, pour le compte rendu, une IA qui part des règles des robots avec
l'IA qui apprend depuis zéro. Deux étapes :
1. les robots jouent des donnes entre eux (à chaque donne, chaque équipe tire une
   convention au hasard parmi --bots ; les deux joueurs d'une équipe ont la même) ;
   on garde, pour chaque décision (annonce ou carte), l'observation vue par le
   joueur, les coups légaux et le coup du robot, et le résultat final de la donne
   pour ce joueur ;
2. le réseau (même forme que scripts.train_coinche --bidding) apprend à reproduire
   le coup du robot (entropie croisée sur les coups légaux) et à prédire le
   résultat de la donne (tête de valeur, pour que PPO démarre avec un bon critique).

Le modèle obtenu se donne ensuite à scripts.train_coinche --bidding --init-from.

    python -m scripts.imitate_coinche --out /chemin/imitation.pt --deals 200000
"""
import argparse
import json
import os
import random
import sys
import tempfile
import time
from multiprocessing import Pool

import numpy as np
import torch
import torch.nn.functional as F

from belote.coinche.engine import team_of
from belote.coinche.rl_env import CARD_INDEX, CoincheEnv, bid_to_action
from belote.rl.networks import ActorCriticNetwork
from scripts.train_coinche import BOT_KINDS


def generate(job):
    """Un processus : n donnes de robots, écrites dans un fichier .npz. Retourne son chemin."""
    seed, n_deals, bot_names, path = job
    rng = random.Random(seed)
    bots = [BOT_KINDS[name]() for name in bot_names]
    env = CoincheEnv(bidding=True, seed=seed)
    obs_l, mask_l, act_l, val_l, bid_l = [], [], [], [], []
    for _ in range(n_deals):
        obs = env.reset(bid_seats={0, 1, 2, 3})
        team_bots = [rng.choice(bots), rng.choice(bots)]
        start, seats = len(act_l), []
        rewards = [0.0] * 4
        while not env.done:
            game = env.game
            seat = game.current
            bot = team_bots[team_of(seat)]
            bidding = game.phase == "bidding"
            action = bid_to_action(bot.bid(game, seat)) if bidding else CARD_INDEX[bot.play(game, seat)]
            obs_l.append(obs.astype(np.float16))
            mask_l.append(env.legal_mask())
            act_l.append(action)
            bid_l.append(bidding)
            seats.append(seat)
            obs, rewards, _ = env.step(action)
        val_l.extend(rewards[s] for s in seats)  # redistribution : résultat 0 pour tout le monde
        assert len(val_l) == len(act_l) and len(seats) == len(act_l) - start
    np.savez(path, obs=np.stack(obs_l), mask=np.stack(mask_l), action=np.array(act_l, dtype=np.int64),
             value=np.array(val_l, dtype=np.float32), bidding=np.array(bid_l, dtype=bool))
    return path


def main():
    parser = argparse.ArgumentParser(description="Réseau de départ par imitation des robots (Coinche à 4).")
    parser.add_argument("--out", required=True, help="modèle .pt écrit (poids, comme les checkpoints PPO)")
    parser.add_argument("--deals", type=int, default=200_000)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--bots", default="petitjeu,papirobert,asr")
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--value-coef", type=float, default=0.5)
    parser.add_argument("--hidden-size", type=int, default=256)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    torch.manual_seed(args.seed)
    bot_names = args.bots.split(",")
    t0 = time.time()

    # 1. exemples
    tmp = tempfile.mkdtemp(prefix="imitation_", dir=os.path.dirname(os.path.abspath(args.out)))
    per = -(-args.deals // args.workers)
    jobs = [(args.seed * 1000 + i, per, bot_names, os.path.join(tmp, f"part{i}.npz")) for i in range(args.workers)]
    with Pool(args.workers) as pool:
        paths = pool.map(generate, jobs)
    parts = [np.load(p) for p in paths]
    data = {k: np.concatenate([p[k] for p in parts]) for k in ("obs", "mask", "action", "value", "bidding")}
    for p in paths:
        os.remove(p)
    os.rmdir(tmp)
    n = len(data["action"])
    print(f"{args.workers * per} donnes de robots, {n} décisions ({data['bidding'].mean():.0%} d'annonces) "
          f"en {(time.time() - t0) / 60:.1f} min", flush=True)

    # 2. apprentissage
    device = "cuda" if torch.cuda.is_available() else "cpu"
    obs = torch.from_numpy(data["obs"])
    mask = torch.from_numpy(data["mask"])
    action = torch.from_numpy(data["action"])
    value = torch.from_numpy(data["value"])
    bidding = torch.from_numpy(data["bidding"])
    perm = torch.randperm(n)
    n_test = max(1, n // 50)
    test, train = perm[:n_test], perm[n_test:]
    network = ActorCriticNetwork(obs_size=obs.shape[1], num_actions=mask.shape[1], hidden_size=args.hidden_size).to(device)
    optimizer = torch.optim.Adam(network.parameters(), lr=args.lr)
    steps = args.epochs * (len(train) // args.batch + 1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, steps)

    def batch_loss(idx):
        o = obs[idx].to(device).float()
        m = mask[idx].to(device)
        logits, v = network(o)
        logits = logits.masked_fill(~m, -1e9)
        a = action[idx].to(device)
        policy = F.cross_entropy(logits, a)
        value_loss = F.mse_loss(v.squeeze(-1), value[idx].to(device))
        correct = logits.argmax(-1) == a
        return policy, value_loss, correct

    history = []
    for epoch in range(args.epochs):
        network.train()
        order = train[torch.randperm(len(train))]
        for i in range(0, len(order), args.batch):
            policy, value_loss, _ = batch_loss(order[i:i + args.batch])
            loss = policy + args.value_coef * value_loss
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(network.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
        network.eval()
        with torch.no_grad():
            pols, vals, corr = [], [], []
            for i in range(0, len(test), args.batch):
                p, v, c = batch_loss(test[i:i + args.batch])
                pols.append(p.item()); vals.append(v.item()); corr.append(c.cpu())
            corr = torch.cat(corr)
            tb = bidding[test]
            row = {"epoch": epoch + 1, "policy_loss": float(np.mean(pols)), "value_loss": float(np.mean(vals)),
                   "accuracy": corr.float().mean().item(), "bid_accuracy": corr[tb].float().mean().item(),
                   "card_accuracy": corr[~tb].float().mean().item()}
        history.append(row)
        print(f"époque {epoch + 1} : même coup que le robot {row['accuracy']:.1%} (annonces {row['bid_accuracy']:.1%}, "
              f"cartes {row['card_accuracy']:.1%}), erreur de valeur {row['value_loss']:.4f} "
              f"({(time.time() - t0) / 60:.1f} min)", flush=True)

    torch.save({k: v.cpu() for k, v in network.state_dict().items()}, args.out)
    with open(os.path.splitext(args.out)[0] + ".json", "w") as f:
        json.dump({"args": vars(args), "decisions": n, "history": history}, f, indent=1)
    print(f"Modèle écrit : {args.out}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
