import argparse
import copy
import glob
import json
import os
import random
import sys

import numpy as np
import torch
from torch.utils.tensorboard import SummaryWriter

from belote.rl.agents import HeuristicAgent, TrumpCountAgent, VoidExploitAgent
from belote.rl.env import BeloteEnv
from belote.rl.evaluation import evaluate_against, run_evaluation_suite
from belote.rl.networks import ActorCriticNetwork
from belote.rl.ppo_agent import PPOAgent
from belote.rl.ppo_update import ppo_update
from belote.rl.self_play import DEFAULT_ROLLOUT_EPISODES, collect_rollout

# Valeurs par défaut = meilleure configuration trouvée (C + A : reward sans
# bonus de victoire, lr 3e-4). L'apprentissage plafonne vers 1,5-2 millions
# de parties avec cette configuration (cf. scripts/compare_checkpoints.py).
TOTAL_GAMES = 2_000_000
ROLLOUT_EPISODES = DEFAULT_ROLLOUT_EPISODES
EVAL_EVERY_N_GAMES = 50_000
LR = 3e-4
ENTROPY_COEF = 0.01
WIN_BONUS = False
CHECKPOINT_DIR = "checkpoints"
LOG_DIR = "runs"
# État complet pour reprendre un entraînement interrompu (--resume), écrasé à
# chaque évaluation : poids, optimiseur Adam, compteurs, générateurs aléatoires.
RESUME_FILE = os.path.join(CHECKPOINT_DIR, "resume_state.pt")
# Écrit si une mise à jour PPO rend les poids non finis : état juste avant la
# mise à jour fautive + les coups du rollout, pour la rejouer et diagnostiquer.
NAN_DUMP_FILE = "nan_dump.pt"
# Paramètres de train() enregistrés dans config.json (et relus par --resume).
CONFIG_KEYS = ("total_games", "rollout_episodes", "eval_every_n_games", "lr", "entropy_coef", "win_bonus",
               "vs_heuristics", "seed", "belief", "bidding", "init_from", "dedans",
               "league", "league_init", "self_play_share", "league_max", "exploit")


class NonFiniteTrainingError(RuntimeError):
    """Une mise à jour PPO a produit des poids ou une loss non finis (NaN/inf)."""


def log_optimization_metrics(writer, metrics, games_trained):
    for key, value in metrics.items():
        writer.add_scalar(f"train/{key}", value, games_trained)


def log_eval_results(writer, results, games_trained):
    for opponent_name, result in results.items():
        for key in ("win_rate", "win_rate_ci95", "avg_point_diff", "avg_point_diff_ci95"):
            writer.add_scalar(f"eval/{opponent_name}/{key}", result[key], games_trained)


def save_checkpoint(network, games_trained):
    path = os.path.join(CHECKPOINT_DIR, f"ppo_{games_trained:07d}.pt")
    torch.save(network.state_dict(), path)
    print(f"Checkpoint sauvegardé : {path}")


def save_resume_state(network, optimizer, games_trained, next_eval_at):
    state = {
        "network": network.state_dict(),
        "optimizer": optimizer.state_dict(),
        "games_trained": games_trained,
        "next_eval_at": next_eval_at,
        "rng": {"python": random.getstate(), "numpy": np.random.get_state(), "torch": torch.get_rng_state()},
    }
    tmp = RESUME_FILE + ".tmp"
    torch.save(state, tmp)
    os.replace(tmp, RESUME_FILE)  # jamais de fichier à moitié écrit si on est interrompu ici


def load_resume_state(network, optimizer):
    state = torch.load(RESUME_FILE, map_location="cpu", weights_only=False)
    network.load_state_dict(state["network"])
    optimizer.load_state_dict(state["optimizer"])
    random.setstate(state["rng"]["python"])
    np.random.set_state(state["rng"]["numpy"])
    torch.set_rng_state(state["rng"]["torch"])
    return state["games_trained"], state["next_eval_at"]


def frozen_agent(source):
    """Version figée pour la ligue : copie d'un réseau, ou modèle .pt ; joue en tirant ses coups."""
    if isinstance(source, str):
        network = ActorCriticNetwork.from_checkpoint(source)
    else:
        network = copy.deepcopy(source)
    network.eval()
    for parameter in network.parameters():
        parameter.requires_grad_(False)
    return PPOAgent(network, deterministic=False)


def all_finite(network, metrics):
    return all(torch.isfinite(p).all() for p in network.parameters()) and all(np.isfinite(v) for v in metrics.values())


def train(
    total_games: int = TOTAL_GAMES,
    rollout_episodes: int = ROLLOUT_EPISODES,
    eval_every_n_games: int = EVAL_EVERY_N_GAMES,
    lr: float = LR,
    entropy_coef: float = ENTROPY_COEF,
    win_bonus: bool = WIN_BONUS,
    vs_heuristics: bool = False,
    seed: int | None = None,
    belief: bool = False,
    bidding: bool = False,
    init_from: str | None = None,
    resume: bool = False,
    dedans: bool = True,
    league: bool = False,
    league_init: list | None = None,
    self_play_share: float = 0.5,
    league_max: int = 20,
    exploit: str | None = None,
):
    """vs_heuristics : au lieu du self-play, chaque manche d'entraînement
    oppose l'agent à un adversaire tiré au hasard parmi les heuristiques
    (étape 1 du curriculum). win_bonus=True : ajoute le +1/-1 final au reward.
    seed : graine aléatoire (donnes, initialisation du réseau, échantillonnage)
    pour pouvoir refaire un entraînement avec une autre graine.
    belief : ajoute à l'observation le tableau des cartes possibles chez
    l'adversaire (BeloteEnv(belief=True)).
    bidding : phase d'annonce de l'atout avant le jeu (BeloteEnv(bidding=True)).
    init_from : démarrage à chaud depuis un modèle déjà entraîné (cf.
    ActorCriticNetwork.init_from), par exemple l'agent sans annonces.
    dedans=False : expérience de contrôle, entraînement sans la règle du
    preneur "dedans" (l'évaluation, elle, applique toujours les vraies règles).
    league : self-play contre un mélange d'anciennes versions (étape 3 du
    curriculum). Une part self_play_share des manches reste en self-play pur ;
    les autres opposent l'agent à une version figée tirée au hasard dans la
    ligue : les modèles league_init, puis chaque checkpoint sauvegardé (les
    league_max plus récents). Les versions de la ligue jouent en tirant leurs
    coups selon leurs probabilités, comme en self-play.
    exploit : modèle .pt de l'agent à exploiter (point D15). Toutes les manches
    d'entraînement l'opposent à cet agent figé, qui joue comme en partie
    réelle (son coup le plus probable) ; chaque évaluation mesure aussi
    l'écart contre lui.
    resume : reprend là où RESUME_FILE s'est arrêté (poids, optimiseur,
    compteurs, générateurs aléatoires) ; config.json n'est pas réécrit."""
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
    os.makedirs(CHECKPOINT_DIR, exist_ok=True)
    os.makedirs(LOG_DIR, exist_ok=True)

    config = {
        "total_games": total_games, "rollout_episodes": rollout_episodes,
        "eval_every_n_games": eval_every_n_games, "lr": lr, "entropy_coef": entropy_coef,
        "win_bonus": win_bonus, "vs_heuristics": vs_heuristics, "seed": seed, "belief": belief, "bidding": bidding, "init_from": init_from,
        "dedans": dedans, "league": league, "league_init": league_init,
        "self_play_share": self_play_share, "league_max": league_max, "exploit": exploit,
    }
    if not resume:
        with open("config.json", "w") as f:
            json.dump(config, f, indent=2)

    env = BeloteEnv(win_bonus=win_bonus, belief=belief, bidding=bidding, dedans=dedans)
    opponents = [HeuristicAgent(), VoidExploitAgent(), TrumpCountAgent()] if vs_heuristics else None
    league_fixed = [frozen_agent(path) for path in (league_init or [])] if league else []
    league_recent = []
    target = None
    if exploit:
        target_network = ActorCriticNetwork.from_checkpoint(exploit)
        target_network.eval()
        target = PPOAgent(target_network, deterministic=True)
        opponents = [target]
    network = ActorCriticNetwork(obs_size=env.obs_size, num_actions=env.num_actions)
    if init_from and not resume:
        network.init_from(init_from)
    agent = PPOAgent(network)
    eval_agent = PPOAgent(network, deterministic=True)
    optimizer = torch.optim.Adam(network.parameters(), lr=lr)
    writer = SummaryWriter(LOG_DIR)

    games_trained = 0
    next_eval_at = 0
    if resume:
        games_trained, next_eval_at = load_resume_state(network, optimizer)
        print(f"=== Reprise à {games_trained} parties d'entraînement ===")

    print(f"=== Entraînement PPO : {total_games} parties, éval toutes les {eval_every_n_games} parties ===")
    print(f"Config : {config}")

    while True:
        if league and not league_recent:
            # au départ ou à la reprise : les checkpoints déjà sauvegardés de ce run
            league_recent = [frozen_agent(path) for path in sorted(glob.glob(os.path.join(CHECKPOINT_DIR, "ppo_*.pt")))]
            league_recent = league_recent[-league_max:]
        if games_trained >= next_eval_at:
            print(f"\n--- Évaluation à {games_trained} parties d'entraînement ---")
            results = run_evaluation_suite(eval_agent)
            if target is not None:
                result = evaluate_against(eval_agent, target, 1000)
                results["Target"] = result
                print(f"  Cible (figée)    win_rate={result['win_rate'] * 100:5.1f}% "
                      f"(±{result['win_rate_ci95'] * 100:.1f}pp) | écart points {result['avg_point_diff']:+6.1f} "
                      f"(±{result['avg_point_diff_ci95']:.1f}) | n={result['n_games']} parties")
            log_eval_results(writer, results, games_trained)
            save_checkpoint(network, games_trained)
            if league:
                league_recent = (league_recent + [frozen_agent(network)])[-league_max:]
                print(f"Ligue : {len(league_fixed)} modèles de départ + {len(league_recent)} versions de ce run")
            next_eval_at += eval_every_n_games
            save_resume_state(network, optimizer, games_trained, next_eval_at)

        if games_trained >= total_games:
            break

        if league:
            buffer = collect_rollout(env, agent, n_episodes=rollout_episodes,
                                     opponents=league_fixed + league_recent, self_play_share=self_play_share)
        else:
            buffer = collect_rollout(env, agent, n_episodes=rollout_episodes, opponents=opponents)
        before = {"network": copy.deepcopy(network.state_dict()), "optimizer": copy.deepcopy(optimizer.state_dict())}
        metrics = ppo_update(agent, optimizer, buffer, entropy_coef=entropy_coef)
        if not all_finite(network, metrics):
            torch.save({"games_trained": games_trained, "network_before": before["network"],
                        "optimizer_before": before["optimizer"], "buffer": buffer, "metrics": metrics,
                        "config": config}, NAN_DUMP_FILE)
            writer.close()
            raise NonFiniteTrainingError(
                f"Poids ou loss non finis après la mise à jour à {games_trained} parties (métriques : {metrics}). "
                f"État d'avant et rollout fautif sauvegardés dans {os.path.abspath(NAN_DUMP_FILE)}.")
        games_trained += rollout_episodes
        log_optimization_metrics(writer, metrics, games_trained)

    writer.close()
    print("\n=== Entraînement terminé ===")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Entraînement PPO belote 2 joueurs.")
    parser.add_argument("--total-games", type=int, default=TOTAL_GAMES)
    parser.add_argument("--eval-every", type=int, default=EVAL_EVERY_N_GAMES)
    parser.add_argument("--lr", type=float, default=LR)
    parser.add_argument("--entropy-coef", type=float, default=ENTROPY_COEF)
    parser.add_argument("--win-bonus", action=argparse.BooleanOptionalAction, default=WIN_BONUS,
                        help="ajoute le +1/-1 de victoire au reward (désactivé par défaut)")
    parser.add_argument("--vs-heuristics", action="store_true", help="adversaires heuristiques au lieu du self-play")
    parser.add_argument("--seed", type=int, help="graine aléatoire (reproductibilité)")
    parser.add_argument("--belief", action="store_true", help="ajoute le tableau des cartes possibles chez l'adversaire")
    parser.add_argument("--bidding", action="store_true", help="phase d'annonce de l'atout avant le jeu")
    parser.add_argument("--no-dedans", dest="dedans", action="store_false",
                        help="contrôle : entraîner sans la règle du preneur dedans (évaluation avec)")
    parser.add_argument("--league", action="store_true",
                        help="self-play contre un mélange d'anciennes versions (ligue)")
    parser.add_argument("--league-init", nargs="*", default=[],
                        help="modèles .pt placés dans la ligue dès le départ")
    parser.add_argument("--self-play-share", type=float, default=0.5,
                        help="avec --league : part des manches en self-play pur (0.5 par défaut)")
    parser.add_argument("--league-max", type=int, default=20,
                        help="avec --league : nombre de versions récentes de ce run gardées dans la ligue")
    parser.add_argument("--exploit", metavar="MODELE",
                        help="entraîner uniquement contre ce modèle figé, pour trouver ses failles (exploitabilité)")
    parser.add_argument("--init-from", help="modèle .pt de départ (démarrage à chaud)")
    parser.add_argument("--out-dir", default=".", help="dossier où écrire checkpoints/, runs/ et config.json")
    parser.add_argument("--resume", action="store_true",
                        help="reprend l'entraînement de --out-dir (config.json + checkpoints/resume_state.pt) ; "
                             "les autres options sont ignorées")
    args = parser.parse_args()

    if args.resume:
        os.chdir(args.out_dir)
        if not os.path.exists(RESUME_FILE):
            sys.exit(f"Rien à reprendre : {os.path.abspath(RESUME_FILE)} n'existe pas.")
        with open("config.json") as f:
            saved = json.load(f)
        train(**{k: saved[k] for k in CONFIG_KEYS if k in saved}, resume=True)
        sys.exit(0)

    # Chemins d'entrée rendus absolus avant de se placer dans le dossier de sortie.
    init_from = os.path.abspath(args.init_from) if args.init_from else None
    exploit = os.path.abspath(args.exploit) if args.exploit else None
    league_init = [os.path.abspath(p) for p in args.league_init]
    os.makedirs(args.out_dir, exist_ok=True)
    os.chdir(args.out_dir)
    train(
        total_games=args.total_games,
        eval_every_n_games=args.eval_every,
        lr=args.lr,
        entropy_coef=args.entropy_coef,
        win_bonus=args.win_bonus,
        vs_heuristics=args.vs_heuristics,
        seed=args.seed,
        belief=args.belief,
        bidding=args.bidding,
        init_from=init_from,
        dedans=args.dedans,
        league=args.league,
        league_init=league_init,
        self_play_share=args.self_play_share,
        league_max=args.league_max,
        exploit=exploit,
    )
