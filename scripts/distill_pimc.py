"""Coinche à 4 : le réseau apprend à jouer les cartes comme la recherche (expert iteration).

Toujours du self-play, en deux étapes :
1. --generate : l'IA joue contre elle-même (le réseau aux 4 places pour les annonces) ; à chaque carte où
   il y a le choix, la recherche (PIMC, 20 mains imaginées, le réseau finit chaque donne) note chaque
   carte jouable (écart de score moyen à la fin de la donne) et joue la meilleure. On garde
   l'observation, les cartes jouables, ces notes, et ce que le réseau aurait joué (ses probabilités).
   Les annonces restent celles du réseau (la recherche aux annonces faisait perdre) : pour elles, on
   garde les probabilités du réseau, pour qu'il ne les oublie pas en apprenant les cartes.
   Chaque processus écrit un fichier toutes les --save-every donnes : on peut arrêter quand on veut.
2. --train : on repart du modèle actuel ; aux cartes, la cible est softmax(notes / --tau) (une carte
   notée 20 points de mieux est préférée e fois plus pour tau = 20 : les notes sont bruitées, une cible
   adoucie évite de copier le bruit) ; aux annonces, les probabilités du réseau de départ ; la tête de
   valeur apprend le résultat de la donne.

    python -m scripts.distill_pimc --generate --data-dir runs/distill1 --hours 8
    python -m scripts.distill_pimc --train --data-dir runs/distill1 --out runs/distill1/coinche_4p_d1.pt
    python -m scripts.coinche_eval --a runs/distill1/coinche_4p_d1.pt --b models/coinche_4p.pt --deals 3000

On peut recommencer avec le nouveau modèle (--model) : la recherche s'appuie alors sur un meilleur
réseau, donc donne de meilleures cibles.
"""
import argparse
import glob
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import torch
import torch.nn.functional as F

from belote.coinche.pimc import CoinchePIMC
from belote.coinche.rl_env import CoincheEnv
from belote.rl.networks import ActorCriticNetwork

DEFAULT_MODEL = "models/coinche_4p.pt"


# ---------- 1. données ----------
def generate(job):
    worker, model, data_dir, until, max_deals, save_every, samples = job
    torch.set_num_threads(1)
    network = ActorCriticNetwork.from_checkpoint(model)
    network.eval()
    # self-play entre IA : pas besoin des conventions des robots pour lire les annonces
    search = CoinchePIMC(network, n_samples=samples, seed=1000 + worker, conventions=())
    env = CoincheEnv(bidding=True, seed=worker * 7919 + int(time.time()) % 100_000)
    buf = {k: [] for k in ("obs", "mask", "values", "net_probs", "card", "value")}
    part, deals = 0, 0

    def flush():
        nonlocal part
        if not buf["obs"]:
            return
        np.savez_compressed(os.path.join(data_dir, f"w{worker:02d}_{part:04d}.npz"),
                            obs=np.stack(buf["obs"]), mask=np.stack(buf["mask"]),
                            values=np.stack(buf["values"]), net_probs=np.stack(buf["net_probs"]),
                            card=np.array(buf["card"]), value=np.array(buf["value"], dtype=np.float32))
        part += 1
        for v in buf.values():
            v.clear()

    while time.time() < until and deals < max_deals:
        env.reset()
        deals += 1
        start, seats = len(buf["obs"]), []
        rewards = [0.0] * 4
        while not env.done:
            seat = env.game.current
            obs = env._observe()
            mask = env.legal_mask()
            action, probs = search.network_choice(env)
            values = np.full(mask.shape, np.nan, dtype=np.float32)
            card = env.game.phase == "play"
            if card and mask.sum() > 1:
                action = search.act(env)
                for a, v in search.last_values.items():
                    values[a] = v
            buf["obs"].append(obs.astype(np.float16))
            buf["mask"].append(mask)
            buf["values"].append(values)
            buf["net_probs"].append(probs.numpy().astype(np.float16))
            buf["card"].append(card)
            seats.append(seat)
            _, rewards, _ = env.step(action)
        buf["value"].extend(rewards[s] for s in seats)
        assert len(buf["value"]) == len(buf["obs"]) and len(seats) == len(buf["obs"]) - start
        if deals % save_every == 0:
            flush()
    flush()
    return deals


# ---------- 2. apprentissage ----------
def load(data_dir):
    files = sorted(glob.glob(os.path.join(data_dir, "w*.npz")))
    parts = [np.load(f) for f in files]
    data = {k: np.concatenate([p[k] for p in parts]) for k in ("obs", "mask", "values", "net_probs", "card", "value")}
    return data, len(files)


def targets(data, tau):
    """Cible de la politique pour chaque décision : notes adoucies de la recherche quand elle a noté
    les cartes (au moins 2 jouables), sinon les probabilités du réseau de départ."""
    values = data["values"].astype(np.float64)
    searched = ~np.isnan(values).all(axis=1)
    target = data["net_probs"].astype(np.float32)
    v = values[searched]
    z = np.where(np.isnan(v), -np.inf, v / tau)
    z -= z.max(axis=1, keepdims=True)
    p = np.exp(z)
    target[searched] = (p / p.sum(axis=1, keepdims=True)).astype(np.float32)
    return target, searched


def train(args):
    t0 = time.time()
    data, n_files = load(args.data_dir)
    target, searched = targets(data, args.tau)
    n = len(target)
    print(f"{n_files} fichiers, {n} décisions dont {searched.sum()} cartes notées par la recherche", flush=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    obs = torch.from_numpy(data["obs"])
    mask = torch.from_numpy(data["mask"])
    tgt = torch.from_numpy(target)
    val = torch.from_numpy(data["value"])
    srch = torch.from_numpy(searched)
    best = torch.from_numpy(np.nan_to_num(data["values"], nan=-np.inf).argmax(axis=1))
    net_best = torch.from_numpy(data["net_probs"].astype(np.float32).argmax(axis=1))
    gen = torch.Generator().manual_seed(args.seed)
    perm = torch.randperm(n, generator=gen)
    n_test = max(1, n // 50)
    test, tr = perm[:n_test], perm[n_test:]

    network = ActorCriticNetwork.from_checkpoint(args.model).to(device)
    optimizer = torch.optim.Adam(network.parameters(), lr=args.lr)
    steps = args.epochs * (len(tr) // args.batch + 1)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, steps)

    def batch(idx):
        o = obs[idx].to(device).float()
        m = mask[idx].to(device)
        logits, v = network(o)
        logp = torch.log_softmax(logits.masked_fill(~m, -1e9), dim=-1)
        t = tgt[idx].to(device)
        per = -(t * logp).sum(-1)
        s = srch[idx].to(device)
        weight = torch.where(s, torch.tensor(1.0, device=device), torch.tensor(args.bid_weight, device=device))
        policy = (per * weight).sum() / weight.sum()
        value_loss = F.mse_loss(v, val[idx].to(device))
        pick = logp.argmax(-1).cpu()
        return policy, value_loss, pick

    def evaluate():
        network.eval()
        picks, pols = [], []
        with torch.no_grad():
            for i in range(0, len(test), args.batch):
                p, _, k = batch(test[i:i + args.batch])
                pols.append(p.item()); picks.append(k)
        k = torch.cat(picks)
        s = srch[test]
        return {"policy_loss": float(np.mean(pols)),
                "cards_like_search": (k[s] == best[test][s]).float().mean().item(),
                "bids_like_before": (k[~s] == net_best[test][~s]).float().mean().item()}

    start = evaluate()
    print(f"départ : même carte que la recherche {start['cards_like_search']:.1%}, "
          f"mêmes annonces qu'avant {start['bids_like_before']:.1%}", flush=True)
    history = [dict(start, epoch=0)]
    for epoch in range(args.epochs):
        network.train()
        order = tr[torch.randperm(len(tr), generator=gen)]
        for i in range(0, len(order), args.batch):
            policy, value_loss, _ = batch(order[i:i + args.batch])
            loss = policy + args.value_coef * value_loss
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(network.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
        row = dict(evaluate(), epoch=epoch + 1)
        history.append(row)
        print(f"époque {epoch + 1} : même carte que la recherche {row['cards_like_search']:.1%}, "
              f"mêmes annonces qu'avant {row['bids_like_before']:.1%} ({(time.time() - t0) / 60:.1f} min)", flush=True)
    torch.save({k: v.cpu() for k, v in network.state_dict().items()}, args.out)
    with open(os.path.splitext(args.out)[0] + ".json", "w") as f:
        json.dump({"args": vars(args), "decisions": int(n), "searched": int(searched.sum()), "history": history},
                  f, indent=1)
    print(f"Modèle écrit : {args.out}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Le réseau apprend les cartes de la recherche (Coinche à 4).")
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--train", action="store_true")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--model", default=DEFAULT_MODEL, help="réseau de départ (et de la recherche)")
    parser.add_argument("--hours", type=float, default=8.0, help="--generate : durée")
    parser.add_argument("--max-deals", type=int, default=10**9, help="--generate : donnes par processus au plus")
    parser.add_argument("--workers", type=int, default=15)
    parser.add_argument("--samples", type=int, default=20, help="mains imaginées par la recherche")
    parser.add_argument("--save-every", type=int, default=200)
    parser.add_argument("--out", help="--train : modèle écrit")
    parser.add_argument("--tau", type=float, default=20.0, help="--train : adoucissement des notes (points)")
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--batch", type=int, default=4096)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--value-coef", type=float, default=0.5)
    parser.add_argument("--bid-weight", type=float, default=1.0, help="--train : poids des annonces (garder les mêmes)")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()
    if args.generate:
        os.makedirs(args.data_dir, exist_ok=True)
        until = time.time() + 3600 * args.hours
        jobs = [(w, args.model, args.data_dir, until, args.max_deals, args.save_every, args.samples)
                for w in range(args.workers)]
        with Pool(args.workers) as pool:
            deals = pool.map(generate, jobs)
        print(f"{sum(deals)} donnes jouées", flush=True)
    if args.train:
        train(args)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
