"""Coinche à 4 : un réseau plus grand, qui voit aussi l'ordre des plis, recopie d'abord le modèle actuel.

Changer la taille du réseau ou ses entrées empêche de reprendre les poids. Plutôt que de repartir de
zéro (12 millions de donnes), le grand réseau apprend à jouer comme l'ancien, puis l'entraînement en
self-play (scripts.train_coinche --init-from) continue depuis là.
1. le modèle actuel joue contre lui-même (il tire ses coups selon ses probabilités, pour voir des
   situations variées ; 1 donne sur 4 contre les robots, comme à l'entraînement) ; on garde
   l'observation complète (avec l'ordre des plis, que l'ancien réseau ne lit pas), les coups légaux,
   ses probabilités et le résultat de la donne ;
2. le grand réseau apprend ces probabilités (entropie croisée sur la distribution complète) et le
   résultat de la donne (tête de valeur).

    python -m scripts.grow_coinche --out runs/grow/coinche_4p_512x3.pt --deals 300000 --hidden-size 512 --n-layers 3
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

DEFAULT_MODEL = "models/coinche_4p.pt"


def generate(job):
    seed, n_deals, teacher_path, bot_names, vs_bots, path = job
    torch.set_num_threads(1)
    rng = random.Random(seed)
    torch.manual_seed(seed)
    teacher = ActorCriticNetwork.from_checkpoint(teacher_path)
    teacher.eval()
    bots = [BOT_KINDS[name]() for name in bot_names]
    env = CoincheEnv(bidding=True, seed=seed)
    buf = {k: [] for k in ("obs", "mask", "probs", "value")}
    for _ in range(n_deals):
        bot, bot_team = (rng.choice(bots), rng.randrange(2)) if rng.random() < vs_bots else (None, None)
        obs = env.reset(bid_seats={0, 1, 2, 3})
        seats, rewards = [], [0.0] * 4
        while not env.done:
            game = env.game
            seat = game.current
            mask = env.legal_mask()
            if bot is not None and team_of(seat) == bot_team:
                bidding = game.phase == "bidding"
                action = bid_to_action(bot.bid(game, seat)) if bidding else CARD_INDEX[bot.play(game, seat)]
            else:
                with torch.no_grad():
                    logits, _ = teacher(torch.as_tensor(obs))
                probs = torch.softmax(logits.masked_fill(~torch.as_tensor(mask), float("-inf")), dim=-1)
                action = int(torch.multinomial(probs, 1))
                buf["obs"].append(obs.astype(np.float16))
                buf["mask"].append(mask)
                buf["probs"].append(probs.numpy().astype(np.float16))
                seats.append(seat)
            obs, rewards, _ = env.step(action)
        buf["value"].extend(rewards[s] for s in seats)
    np.savez(path, obs=np.stack(buf["obs"]), mask=np.stack(buf["mask"]), probs=np.stack(buf["probs"]),
             value=np.array(buf["value"], dtype=np.float32))
    return path


def main():
    parser = argparse.ArgumentParser(description="Un grand réseau recopie le modèle actuel (Coinche à 4).")
    parser.add_argument("--out", required=True)
    parser.add_argument("--teacher", default=DEFAULT_MODEL)
    parser.add_argument("--deals", type=int, default=300_000)
    parser.add_argument("--workers", type=int, default=15)
    parser.add_argument("--bots", default="petitjeu,papirobert,asr")
    parser.add_argument("--vs-bots", type=float, default=0.25)
    parser.add_argument("--hidden-size", type=int, default=512)
    parser.add_argument("--n-layers", type=int, default=3)
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--value-coef", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    torch.manual_seed(args.seed)
    t0 = time.time()

    tmp = tempfile.mkdtemp(prefix="grow_", dir=os.path.dirname(os.path.abspath(args.out)))
    per = -(-args.deals // args.workers)
    jobs = [(args.seed * 1000 + i, per, args.teacher, args.bots.split(","), args.vs_bots,
             os.path.join(tmp, f"part{i}.npz")) for i in range(args.workers)]
    with Pool(args.workers) as pool:
        paths = pool.map(generate, jobs)
    parts = [np.load(p) for p in paths]
    data = {k: np.concatenate([p[k] for p in parts]) for k in ("obs", "mask", "probs", "value")}
    for p in paths:
        os.remove(p)
    os.rmdir(tmp)
    n = len(data["value"])
    print(f"{args.workers * per} donnes, {n} décisions de l'ancien modèle en {(time.time() - t0) / 60:.1f} min",
          flush=True)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    obs = torch.from_numpy(data["obs"])
    mask = torch.from_numpy(data["mask"])
    probs = torch.from_numpy(data["probs"])
    value = torch.from_numpy(data["value"])
    perm = torch.randperm(n)
    n_test = max(1, n // 50)
    test, train = perm[:n_test], perm[n_test:]
    network = ActorCriticNetwork(obs_size=obs.shape[1], num_actions=mask.shape[1], hidden_size=args.hidden_size,
                                 n_layers=args.n_layers).to(device)
    optimizer = torch.optim.Adam(network.parameters(), lr=args.lr)
    steps = args.epochs * (len(train) // args.batch + 1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, steps)

    def batch_loss(idx):
        o = obs[idx].to(device).float()
        m = mask[idx].to(device)
        logits, v = network(o)
        logp = torch.log_softmax(logits.masked_fill(~m, -1e9), dim=-1)
        t = probs[idx].to(device).float()
        policy = -(t * logp).sum(-1).mean()
        value_loss = F.mse_loss(v, value[idx].to(device))
        same = logp.argmax(-1) == t.argmax(-1)
        return policy, value_loss, same

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
            pols, vals, same = [], [], []
            for i in range(0, len(test), args.batch):
                p, v, s = batch_loss(test[i:i + args.batch])
                pols.append(p.item()); vals.append(v.item()); same.append(s.cpu())
        row = {"epoch": epoch + 1, "policy_loss": float(np.mean(pols)), "value_loss": float(np.mean(vals)),
               "same_choice": torch.cat(same).float().mean().item()}
        history.append(row)
        print(f"époque {epoch + 1} : même coup préféré que l'ancien modèle {row['same_choice']:.1%}, "
              f"perte {row['policy_loss']:.4f}, erreur de valeur {row['value_loss']:.4f} "
              f"({(time.time() - t0) / 60:.1f} min)", flush=True)

    torch.save({k: v.cpu() for k, v in network.state_dict().items()}, args.out)
    with open(os.path.splitext(args.out)[0] + ".json", "w") as f:
        json.dump({"args": vars(args), "decisions": n, "history": history}, f, indent=1)
    print(f"Modèle écrit : {args.out}", flush=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
