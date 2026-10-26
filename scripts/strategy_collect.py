"""Collecte des décisions d'un agent pour étudier sa stratégie (point B).

L'agent étudié ("sujet") joue N manches contre un adversaire fixe, sur des
donnes tirées d'une graine fixe : tous les sujets voient donc exactement les
mêmes donnes, aux mêmes places (sujet au siège k % 2, premier à parler
k // 2 % 2). Chaque décision est enregistrée avec son contexte complet, y
compris la main cachée de l'adversaire (pour l'analyse seulement : les
agents, eux, ne la voient jamais).

    python -m scripts.strategy_collect --subject new --rounds 20000

Sujets : new (agent avec annonces), old (agent sans annonces + annonces
heuristiques), old_native (agent sans annonces, atout au hasard, sans
annonces), trumpcount, heuristic. Résultat : <out-dir>/<sujet>.pkl, lu par
scripts.strategy_analysis.
"""
import argparse
import os
import pickle
import random
import sys

import numpy as np

from belote.core.cards import build_deck
from belote.rl.agents import HeuristicAgent, HeuristicBiddingWrapper, TrumpCountAgent
from belote.rl.env import INDEX_CARD, SUITS, BeloteEnv
from belote.rl.pimc import PIMCAgent
from scripts.compare_checkpoints import load_agent

NEW_MODEL = "models/ppo_bidding_2M.pt"
OLD_MODEL = "models/ppo_CA_3M.pt"
DEFAULT_OUT = "/ugproj/crml-prj10880/experiments/strategy_analysis"


def make_subject(name):
    """(agent, bidding) pour un nom de sujet."""
    if name == "new":
        return load_agent(NEW_MODEL), True
    if name in ("old", "old_native"):
        agent = load_agent(OLD_MODEL)
        if name == "old_native":
            return agent, False
        return HeuristicBiddingWrapper(agent, agent.network.obs_size), True
    if name.startswith("pimc"):  # pimc ou pimc<K> : agent avec annonces + recherche PIMC
        return PIMCAgent(load_agent(NEW_MODEL), n_samples=int(name[4:] or 20)), True
    if name == "trumpcount":
        return TrumpCountAgent(), True
    if name == "heuristic":
        return HeuristicAgent(), True
    raise ValueError(name)


def deals(n, seed):
    """Mêmes donnes pour tous les sujets : (main0, main1, carte retournée, atout tiré au hasard)."""
    rng = random.Random(seed)
    deck = build_deck()
    for _ in range(n):
        rng.shuffle(deck)
        yield list(deck[:8]), list(deck[8:16]), deck[16], rng.choice(SUITS)


def collect(subject_name, n_rounds, seed=2026, shadow_name=None):
    """shadow_name : autre sujet interrogé sur chaque coup du sujet, sans jouer
    (même situation exacte) ; son choix est enregistré dans "shadow"."""
    subject, bidding = make_subject(subject_name)
    shadow = make_subject(shadow_name)[0] if shadow_name else None
    opponent = TrumpCountAgent()
    env = BeloteEnv(bidding=bidding, win_bonus=False)
    np.random.seed(seed)
    plays, bids, rounds = [], [], []
    for k, (h0, h1, turned, random_trump) in enumerate(deals(n_rounds, seed)):
        me = k % 2
        first = k // 2 % 2
        obs, info = env.reset(options={"starting_player": first,
                                       "deal": (h0, h1, turned if bidding else random_trump)})
        agents = {me: subject, 1 - me: opponent}
        if hasattr(subject, "attach_env"):
            subject.attach_env(env)
        log = {"k": k, "me": me, "first": first, "hands": (list(h0), list(h1)),
               "turned": turned if bidding else None, "bids": [], "plays": []}
        my_plays, my_bids = [], []
        done = False
        while not done:
            seat = env.current_idx
            action = agents[seat].act(obs, info["legal_actions"], info)
            phase = env.phase
            if phase != "play":
                log["bids"].append((seat, phase, action))
                if seat == me:
                    hand = list(env.players[me].hand)
                    my_bids.append({
                        "r": k, "phase": phase, "first": first == me, "hand": hand, "turned": turned,
                        "action": action, "opp_passed": (1 - me, "bid1") in env.passes,
                    })
            else:
                card = INDEX_CARD[action]
                log["plays"].append((seat, card))
                if seat == me:
                    if shadow is not None:
                        shadow_card = INDEX_CARD[shadow.act(obs, info["legal_actions"], info)]
                    my_plays.append({
                        "r": k, "t": env.trick_no, "lead": env.led_card is None, "led": env.led_card,
                        "trump": env.trump_suit, "hand": list(env.players[me].hand),
                        "opp": list(env.players[1 - me].hand), "card": card,
                        "played": {INDEX_CARD[i] for i, p in enumerate(env.played_public) if p},
                        "turned": env.turned_card,
                        "shadow": shadow_card if shadow is not None else None,
                    })
            obs, _, done, info = env.step(action)

        redeal = bool(info.get("redeal"))
        role = None if env.taker is None else ("taker" if env.taker == me else "defender")
        pts = info["final_points"]
        outcome = {"redeal": redeal, "role": role, "trump": env.trump_suit, "dedans": env.dedans,
                   "my_points": pts[me], "opp_points": pts[1 - me],
                   "tricks": [w == me for w in env.trick_winners] if not redeal else None}
        for p in my_plays:
            p["role"] = role
            p["won"] = outcome["tricks"][p["t"] - 1]
        for b in my_bids:
            b["outcome"] = outcome
        log.update(outcome)
        plays += my_plays
        bids += my_bids
        rounds.append(log)
    return {"subject": subject_name, "bidding": bidding, "plays": plays, "bids": bids, "rounds": rounds}


def main():
    parser = argparse.ArgumentParser(description="Collecte des décisions d'un agent (étude de stratégie).")
    parser.add_argument("--subject", required=True, help="new, old, old_native, trumpcount, heuristic ou pimc<K> (ex. pimc20)")
    parser.add_argument("--rounds", type=int, default=20000)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--out-dir", default=DEFAULT_OUT)
    parser.add_argument("--shadow", choices=["old"], help="sujet interrogé en parallèle sur chaque coup (sans jouer)")
    args = parser.parse_args()
    data = collect(args.subject, args.rounds, args.seed, args.shadow)
    os.makedirs(args.out_dir, exist_ok=True)
    path = os.path.join(args.out_dir, f"{args.subject}.pkl")
    with open(path, "wb") as f:
        pickle.dump(data, f)
    print(f"{args.subject} : {len(data['plays'])} coups, {len(data['bids'])} annonces -> {path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
