"""Entraînement PPO pour la Coinche à 4 (belote/coinche/rl_env.py).

Self-play : un seul réseau joue les 4 places (chacune vue de sa position).
Étape 1 (par défaut) : les annonces sont faites par les robots CoincheBot,
le réseau apprend à jouer les cartes. --bidding : le réseau fait aussi les
annonces. Évaluation régulière contre une équipe de robots, en donnes
dupliquées (chaque donne jouée deux fois, l'IA d'un côté puis de l'autre)
et en parties complètes en 1 500 points.

    python -m scripts.train_coinche --out-dir /chemin/run --total-deals 5000000
    python -m scripts.train_coinche --out-dir /chemin/run --resume
"""
import argparse
import json
import math
import os
import random
import sys
import time

import numpy as np
import torch
from torch.utils.tensorboard import SummaryWriter

from belote.coinche.engine import DEFAULT_TARGET, team_of
from belote.coinche.rl_env import CoincheEnv
from belote.rl.gae import compute_gae
from belote.rl.networks import ActorCriticNetwork
from belote.rl.ppo_agent import PPOAgent
from belote.rl.ppo_update import ppo_update
from belote.rl.self_play import Transition

CHECKPOINT_DIR = "checkpoints"
RESUME_FILE = os.path.join(CHECKPOINT_DIR, "resume_state.pt")
FINISHED_MARKER = "=== Entraînement terminé ==="
N_ENVS = 32  # donnes jouées en parallèle pendant la collecte
CONFIG_KEYS = ("total_deals", "rollout_deals", "eval_every", "lr", "entropy_coef", "seed", "bidding",
               "hidden_size", "vs_bots_share", "init_from")


# ---------- collecte ----------
def collect_deal(env, agent, learner_seats):
    """Une donne ; seules les places learner_seats sont jouées par le réseau
    (les autres par CoincheBot). Retourne les transitions, GAE calculé."""
    bid_seats = learner_seats if env.bidding else None
    obs = env.reset(bid_seats=bid_seats)
    buffer, last = [], {}
    done = env.done
    while not done:
        seat = env.current
        mask = env.legal_mask()
        if seat in learner_seats:
            with torch.no_grad():
                action, log_prob, value, _ = agent.act_and_evaluate(obs, mask)
            buffer.append(Transition(obs=obs, legal_mask=mask, action=action, log_prob=log_prob.item(),
                                     value=value.item(), player=seat))
            last[seat] = len(buffer) - 1
        else:
            action = env.play_bot()
        obs, rewards, done = env.step(action)
    for seat, idx in last.items():
        buffer[idx].reward += rewards[seat]
    compute_gae(buffer)
    return buffer


def collect_rollout(envs, agent, n_deals, vs_bots_share):
    """n_deals donnes jouées en parallèle sur les environnements envs : à
    chaque pas, un seul passage du réseau pour toutes les places qui attendent
    une décision (beaucoup plus rapide que donne par donne). Même résultat
    que collect_deal appelé n_deals fois."""
    buffer = []
    started = 0
    slots = []  # par environnement : (transitions, dernière transition par place, places du réseau)

    def start(env):
        nonlocal started
        if started >= n_deals:
            return None
        if vs_bots_share and random.random() < vs_bots_share:
            team = started % 2
            seats = {team, team + 2}
        else:
            seats = {0, 1, 2, 3}
        started += 1
        obs = env.reset(bid_seats=seats if env.bidding else None)
        return {"trans": [], "last": {}, "seats": seats, "obs": obs}

    def advance_bots(env, slot):
        """Joue les robots jusqu'au tour du réseau ; True si la donne est finie."""
        while not env.done and env.current not in slot["seats"]:
            slot["obs"], slot["rewards"], _ = env.step(env.play_bot())
        return env.done

    def finish(env, slot):
        if env.game.phase == "done":
            for seat, idx in slot["last"].items():
                slot["trans"][idx].reward += slot["rewards"][seat]
        compute_gae(slot["trans"])
        buffer.extend(slot["trans"])

    for env in envs:
        slots.append(start(env))
    while True:
        waiting = []
        for i, env in enumerate(envs):
            slot = slots[i]
            while slot is not None and advance_bots(env, slot):
                finish(env, slot)
                slot = slots[i] = start(env)
            if slot is not None:
                waiting.append(i)
        if not waiting:
            return buffer
        obs = np.stack([slots[i]["obs"] for i in waiting])
        masks = np.stack([envs[i].legal_mask() for i in waiting])
        with torch.no_grad():
            actions, log_probs, values, _ = agent.act_and_evaluate(obs, masks, batch=True)
        for k, i in enumerate(waiting):
            env, slot = envs[i], slots[i]
            seat = env.current
            slot["trans"].append(Transition(obs=slot["obs"], legal_mask=masks[k], action=int(actions[k]),
                                            log_prob=float(log_probs[k]), value=float(values[k]), player=seat))
            slot["last"][seat] = len(slot["trans"]) - 1
            slot["obs"], slot["rewards"], _ = env.step(int(actions[k]))


# ---------- évaluation ----------
def mean_ci(values):
    n = len(values)
    m = sum(values) / n
    if n < 2:
        return m, 0.0
    var = sum((v - m) ** 2 for v in values) / (n - 1)
    return m, 1.96 * math.sqrt(var / n)


def play_deal(env, agent, ai_team, deal=None):
    """Une donne : l'IA (réseau, coup le plus probable) joue l'équipe ai_team,
    CoincheBot l'autre. Retourne (scores [équipe 0, équipe 1], résultat) ou None si redistribution."""
    ai_seats = {ai_team, ai_team + 2}
    env.reset(deal=deal, bid_seats=ai_seats if env.bidding else None)
    obs = env._observe() if not env.done else None
    done = env.done
    while not done:
        seat = env.current
        if seat in ai_seats:
            action = agent.act(obs, env.legal_mask())
        else:
            action = env.play_bot()
        obs, _rewards, done = env.step(action)
    if env.game.phase == "redeal":
        return None
    return env.game.result["scores"], env.game.result


def evaluate(agent, bidding, n_deals=1000, n_games=100, seed=12345):
    """Donnes dupliquées : la même donne (mains, donneur) jouée avec l'IA en
    Sud-Nord puis en Est-Ouest ; écart moyen par donne (IA - robots). Puis
    parties complètes en 1 500 points (IA en Sud-Nord une partie sur deux)."""
    env = CoincheEnv(bidding=bidding, seed=seed)
    diffs, ai_taken, ai_made = [], 0, 0
    played = 0
    while played < n_deals:
        deal = env.random_deal()
        if not bidding:
            # donne utilisable seulement si les robots ne passent pas tous
            probe = CoincheEnv(bidding=False)
            try:
                probe.reset(deal=deal)
            except ValueError:
                continue
        pair = []
        for ai_team in (0, 1):
            out = play_deal(env, agent, ai_team, deal)
            if out is None:
                pair.append(0.0)
                continue
            scores, result = out
            pair.append(scores[ai_team] - scores[1 - ai_team])
            if team_of(result["contract"]["seat"]) == ai_team:
                ai_taken += 1
                ai_made += result["made"]
        diffs.append(sum(pair) / 2)
        played += 1
    diff, diff_ci = mean_ci(diffs)

    wins = []
    game_env = CoincheEnv(bidding=bidding, seed=seed + 1)
    for g in range(n_games):
        ai_team = g % 2
        totals = [0, 0]
        while max(totals) < DEFAULT_TARGET or totals[0] == totals[1]:
            out = play_deal(game_env, agent, ai_team)
            if out is not None:
                totals = [totals[t] + out[0][t] for t in (0, 1)]
        wins.append(1.0 if totals[ai_team] > totals[1 - ai_team] else 0.0)
    win, win_ci = mean_ci(wins)
    return {"deal_diff": diff, "deal_diff_ci95": diff_ci, "game_win_rate": win, "game_win_rate_ci95": win_ci,
            "ai_takes": ai_taken / (2 * n_deals), "ai_made": ai_made / max(1, ai_taken)}


# ---------- boucle ----------
def save_resume(network, optimizer, deals, next_eval):
    state = {"network": network.state_dict(), "optimizer": optimizer.state_dict(), "deals": deals,
             "next_eval": next_eval,
             "rng": {"python": random.getstate(), "numpy": np.random.get_state(), "torch": torch.get_rng_state()}}
    torch.save(state, RESUME_FILE + ".tmp")
    os.replace(RESUME_FILE + ".tmp", RESUME_FILE)


def train(total_deals=5_000_000, rollout_deals=128, eval_every=50_000, lr=3e-4, entropy_coef=0.01, seed=None,
          bidding=False, hidden_size=256, vs_bots_share=0.0, init_from=None, resume=False):
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    config = {k: v for k, v in locals().items() if k in CONFIG_KEYS}
    if not resume:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)
    envs = [CoincheEnv(bidding=bidding, seed=None if seed is None else seed * 1000 + i) for i in range(N_ENVS)]
    env = envs[0]
    network = ActorCriticNetwork(obs_size=env.obs_size, num_actions=env.num_actions, hidden_size=hidden_size)
    if init_from and not resume:
        # démarrage à chaud (ex. étape 2 depuis le réseau de l'étape 1) : mêmes entrées, actions ajoutées à zéro
        old = torch.load(init_from, map_location="cpu")
        with torch.no_grad():
            for name, p in network.named_parameters():
                q = old[name]
                if q.shape == p.shape:
                    p.copy_(q)
                else:
                    p.zero_()
                    p[: q.shape[0]] = q
    agent = PPOAgent(network)
    eval_agent = PPOAgent(network, deterministic=True)
    optimizer = torch.optim.Adam(network.parameters(), lr=lr)
    writer = SummaryWriter("runs")
    deals, next_eval = 0, 0
    if resume:
        state = torch.load(RESUME_FILE, map_location="cpu", weights_only=False)
        network.load_state_dict(state["network"])
        optimizer.load_state_dict(state["optimizer"])
        random.setstate(state["rng"]["python"])
        np.random.set_state(state["rng"]["numpy"])
        torch.set_rng_state(state["rng"]["torch"])
        deals, next_eval = state["deals"], state["next_eval"]
        print(f"=== Reprise à {deals} donnes ===")
    print(f"=== Coinche à 4 : {total_deals} donnes, éval toutes les {eval_every} ===\nConfig : {config}", flush=True)
    t0 = time.time()
    while True:
        if deals >= next_eval:
            r = evaluate(eval_agent, bidding)
            print(f"\n--- Évaluation à {deals} donnes ({(time.time() - t0) / 60:.0f} min) ---\n"
                  f"  Contre les robots : écart {r['deal_diff']:+6.1f} pts/donne (±{r['deal_diff_ci95']:.1f}) | "
                  f"parties gagnées {100 * r['game_win_rate']:5.1f}% (±{100 * r['game_win_rate_ci95']:.1f}) | "
                  f"l'IA prend {100 * r['ai_takes']:.0f}% des donnes, réussit {100 * r['ai_made']:.0f}%", flush=True)
            for k, v in r.items():
                writer.add_scalar(f"eval/{k}", v, deals)
            torch.save(network.state_dict(), os.path.join(CHECKPOINT_DIR, f"ppo_{deals:08d}.pt"))
            next_eval += eval_every
            save_resume(network, optimizer, deals, next_eval)
        if deals >= total_deals:
            break
        buffer = collect_rollout(envs, agent, rollout_deals, vs_bots_share)
        if not buffer:
            continue
        metrics = ppo_update(agent, optimizer, buffer, entropy_coef=entropy_coef)
        if not all(torch.isfinite(p).all() for p in network.parameters()):
            raise RuntimeError(f"Poids non finis à {deals} donnes")
        deals += rollout_deals
        for k, v in metrics.items():
            writer.add_scalar(f"train/{k}", v, deals)
    writer.close()
    print(f"\n{FINISHED_MARKER}")


def main():
    parser = argparse.ArgumentParser(description="Entraînement PPO Coinche à 4.")
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--total-deals", type=int, default=5_000_000)
    parser.add_argument("--rollout-deals", type=int, default=128)
    parser.add_argument("--eval-every", type=int, default=50_000)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--entropy-coef", type=float, default=0.01)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--bidding", action="store_true", help="le réseau fait aussi les annonces")
    parser.add_argument("--hidden-size", type=int, default=256)
    parser.add_argument("--vs-bots-share", type=float, default=0.0,
                        help="part des donnes jouées contre une équipe de robots (le reste en self-play)")
    parser.add_argument("--init-from", help="modèle .pt de départ (ex. étape 1 pour l'étape 2)")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    init_from = os.path.abspath(args.init_from) if args.init_from else None
    os.makedirs(args.out_dir, exist_ok=True)
    os.chdir(args.out_dir)
    if args.resume:
        with open("config.json") as f:
            saved = json.load(f)
        train(**{k: saved[k] for k in CONFIG_KEYS if k in saved}, resume=True)
        return
    train(total_deals=args.total_deals, rollout_deals=args.rollout_deals, eval_every=args.eval_every, lr=args.lr,
          entropy_coef=args.entropy_coef, seed=args.seed, bidding=args.bidding, hidden_size=args.hidden_size,
          vs_bots_share=args.vs_bots_share, init_from=init_from)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
