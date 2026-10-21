import argparse
import random
import sys

import torch

from belote.core.cards import SUIT_SYMBOLS, sort_hand
from belote.rl.agents import HeuristicAgent, RandomAgent, TrumpCountAgent, VoidExploitAgent
from belote.rl.env import BeloteEnv, INDEX_CARD
from belote.rl.networks import ActorCriticNetwork
from belote.rl.ppo_agent import PPOAgent

OPPONENTS = {
    "random": RandomAgent,
    "heuristic": HeuristicAgent,
    "voidexploit": VoidExploitAgent,
    "trumpcount": TrumpCountAgent,
}


def format_hand(hand, trump_suit):
    return "  ".join(str(card) for card in sort_hand(hand, trump_suit))


def ppo_choice_details(agent, obs, legal_mask, action):
    """Probabilité de la carte jouée et meilleure alternative, pour un PPOAgent."""
    with torch.no_grad():
        masked_logits, value = agent._masked_logits_and_value(obs, legal_mask)
        probs = torch.softmax(masked_logits, dim=-1)
    chosen = probs[action].item()
    others = [(probs[i].item(), i) for i in range(len(probs)) if legal_mask[i] and i != action]
    text = f"[confiance {chosen * 100:3.0f} %"
    if others:
        p_alt, alt = max(others)
        text += f", sinon {INDEX_CARD[alt]} {p_alt * 100:.0f} %"
    return text + "]"


def play_and_show(env, agents, labels, deal=None):
    """Joue une manche (siège 0 meneur du premier pli) et l'affiche pli par pli.
    agents/labels : {siège: agent}, {siège: nom}. Retourne les points réels."""
    obs, info = env.reset(options={"starting_player": 0, "deal": deal})
    trump_suit = env.trump_suit
    print(f"Atout : {SUIT_SYMBOLS[trump_suit]}")
    for seat in (0, 1):
        print(f"Main {labels[seat]:<12}: {format_hand(env.players[seat].dealt_hand, trump_suit)}")

    trick_no = 1
    trick_cards = []
    while True:
        player_idx = env.current_idx
        agent = agents[player_idx]
        legal_mask = info["legal_actions"]
        action = agent.act(obs, legal_mask, info)
        details = ppo_choice_details(agent, obs, legal_mask, action) if isinstance(agent, PPOAgent) else ""

        obs, _rewards, done, info = env.step(action)
        trick_cards.append((player_idx, INDEX_CARD[action], details))

        if len(trick_cards) == 2:
            winner = env.trick_winners[trick_no - 1]
            points = sum(card.points(trump_suit) for _, card, _ in trick_cards) + (10 if trick_no == 8 else 0)
            print(f"\nPli {trick_no} -> {labels[winner]} ({points} pts)")
            for seat, card, details in trick_cards:
                print(f"   {labels[seat]:<12} joue {str(card):<5} {details}")
            trick_cards = []
            trick_no += 1

        if done:
            p0, p1 = info["final_points"]
            print(f"\nScore : {labels[0]} = {p0} | {labels[1]} = {p1} (belote-rebelote et dix de der inclus)")
            return p0, p1


def load_ppo(checkpoint):
    network = ActorCriticNetwork()
    if checkpoint:
        network.load_state_dict(torch.load(checkpoint, map_location="cpu"))
    network.eval()
    return PPOAgent(network, deterministic=True)


def main(args):
    if args.seed is not None:
        random.seed(args.seed)
    env = BeloteEnv()
    ppo = load_ppo(args.checkpoint)
    if not args.checkpoint:
        print("Réseau à poids aléatoires (pas encore entraîné).")
    opponent = ppo if args.opponent == "self" else OPPONENTS[args.opponent]()
    opp_label = "PPO bis" if args.opponent == "self" else OPPONENTS[args.opponent].__name__.replace("Agent", "")

    for i in range(1, args.games + 1):
        print(f"\n{'=' * 20} Donne {i}/{args.games} {'=' * 20}")
        print("\n--- Partie A : PPO a la main 1 (meneur) ---")
        ppo_a, opp_b = play_and_show(env, {0: ppo, 1: opponent}, {0: "PPO", 1: opp_label})
        if args.duplicate:
            deal = env.deal
            print(f"\n--- Partie B : même donne, mains échangées : {opp_label} a la main 1 (meneur) ---")
            opp_a, ppo_b = play_and_show(env, {0: opponent, 1: ppo}, {0: opp_label, 1: "PPO"}, deal=deal)
            print(
                f"\nBilan de la donne : avec la main 1, PPO {ppo_a} vs {opp_label} {opp_a} ; "
                f"avec la main 2, PPO {ppo_b} vs {opp_label} {opp_b} "
                f"=> écart PPO {((ppo_a - opp_b) + (ppo_b - opp_a)) / 2:+.1f} pts/partie"
            )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(
        description="Affiche le détail de parties jouées par l'agent PPO (self-play ou contre une heuristique)."
    )
    parser.add_argument("--games", type=int, default=1, help="Nombre de donnes à afficher.")
    parser.add_argument("--checkpoint", help="Poids entraînés (.pt) ; sans ça, réseau à poids aléatoires.")
    parser.add_argument("--opponent", default="self", choices=["self", *OPPONENTS],
                        help="Adversaire de l'agent PPO (self = lui-même).")
    parser.add_argument("--duplicate", action="store_true",
                        help="Rejoue chaque donne en échangeant les mains (comme l'évaluation dupliquée).")
    parser.add_argument("--seed", type=int, help="Graine pour choisir les donnes (reproductible).")
    main(parser.parse_args())
