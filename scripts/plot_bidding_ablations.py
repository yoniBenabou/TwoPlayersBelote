"""Figure des expériences de contrôle des annonces :
  - à gauche, courbes d'apprentissage (écart de points contre TrumpCount) :
    démarrage à chaud (2 graines), depuis zéro, sans la règle du dedans ;
  - à droite, probabilité de prendre au tour 1 selon la force de la main,
    avec et sans la règle du dedans pendant l'entraînement.

    python -m scripts.plot_bidding_ablations
"""
import argparse
import os
import random
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from belote.rl.agents import TrumpCountAgent, trump_strength  # noqa: E402
from belote.rl.env import TAKE, BeloteEnv  # noqa: E402
from scripts.compare_checkpoints import load_agent  # noqa: E402

EXP = "/ugproj/crml-prj10880/experiments"
RUNS = [  # (dossier, légende, couleur, style)
    ("bidding_CA_seed1", "Warm start from the agent without bidding (seed 1)", "#2a78d6", "-"),
    ("bidding_CA_seed2", "Warm start (seed 2)", "#2a78d6", ":"),
    ("bidding_scratch_seed1", "From scratch", "#eb6834", "-"),
    ("bidding_nodedans_seed1", "Warm start, trained without the “dedans” rule", "#8c99a8", "-"),
]


def curve(run_dir):
    """[(parties, écart de points, IC95)] contre TrumpCount, lus dans train.log."""
    out, games = [], None
    with open(os.path.join(run_dir, "train.log"), encoding="utf-8") as f:
        for line in f:
            m = re.search(r"Évaluation à (\d+)", line)
            if m:
                games = int(m.group(1))
            m = re.search(r"TrumpCountAgent .*écart points\s+([+-][\d.]+) \(±([\d.]+)\)", line)
            if m and games is not None:
                out.append((games, float(m.group(1)), float(m.group(2))))
    return out


def take_curve(path, n_rounds=6000, seed=0):
    """% de prise au tour 1 (premier à parler) par tranche de force de la couleur retournée."""
    agent, opponent, env = load_agent(path), TrumpCountAgent(), BeloteEnv(bidding=True)
    random.seed(seed)
    bins = {}
    for k in range(n_rounds):
        me = k % 2
        obs, info = env.reset(options={"starting_player": me})
        action = agent.act(obs, info["legal_actions"], info)
        b = min(trump_strength(env.players[me].hand, env.turned_card.suit) // 10 * 10, 60)
        n, t = bins.get(b, (0, 0))
        bins[b] = (n + 1, t + (action == TAKE))
    return {b: 100 * t / n for b, (n, t) in sorted(bins.items())}


def main():
    parser = argparse.ArgumentParser(description="Figure des contrôles des annonces.")
    parser.add_argument("--out", default="figures/bidding_ablations_en.png")
    args = parser.parse_args()
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})
    for run, label, color, ls in RUNS:
        pts = curve(os.path.join(EXP, run))
        xs = [g / 1e6 for g, _, _ in pts]
        ys = [d for _, d, _ in pts]
        ax.plot(xs, ys, ls, color=color, label=label, lw=1.6)
    ax.axhline(0, color="#52514e", lw=0.8, ls="--")
    ax.set_xlabel("Training games with bidding (millions)")
    ax.set_ylabel("Point margin per round vs TrumpCount")
    ax.set_title("Learning to bid: warm start, from scratch, no “dedans” rule")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")

    for run, label, color in (("bidding_CA_seed1", "Trained with the “dedans” rule", "#2a78d6"),
                              ("bidding_nodedans_seed1", "Trained without it", "#8c99a8")):
        c = take_curve(os.path.join(EXP, run, "checkpoints", "ppo_2000000.pt"))
        bx.plot([b + 5 for b in c], list(c.values()), "-o", color=color, label=label)
    bx.set_xlabel("Strength of the turned suit in hand")
    bx.set_ylabel("Takes in round 1, first to speak (%)")
    bx.set_title("Without the rule, the agent takes almost anything")
    bx.legend(frameon=False, fontsize=9)
    for a in (ax, bx):
        a.spines[["top", "right"]].set_visible(False)
        a.grid(axis="y", color="#e4e3df")
        a.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(args.out, dpi=160)
    print(f"Figure : {args.out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
