import argparse
import random
import sys

from belote.core.cards import SUIT_SYMBOLS, sort_hand
from belote.core.engine import has_belote, legal_moves
from belote.rl.env import CARD_INDEX, INDEX_CARD, BeloteEnv
from scripts.compare_checkpoints import load_agent

DEFAULT_CHECKPOINT = "models/ppo_CA_3M.pt"
DEFAULT_TARGET_SCORE = 501
HUMAN, AGENT = 0, 1  # sièges dans BeloteEnv


class Quit(Exception):
    pass


def format_hand(sorted_hand, legal_choices):
    parts = []
    for i, card in enumerate(sorted_hand):
        marker = "" if card in legal_choices else " (interdit)"
        parts.append(f"[{i}] {card}{marker}")
    return "  ".join(parts)


def ask_card(env, ask):
    """Demande au joueur humain une carte légale ; retourne l'action (index BeloteEnv)."""
    hand = env.players[HUMAN].hand
    choices = legal_moves(hand, env.led_card, env.trump_suit)
    sorted_hand = sort_hand(hand, env.trump_suit)
    print(f"Ta main : {format_hand(sorted_hand, choices)}")
    while True:
        raw = ask("Ta carte (numéro, q pour quitter) : ").strip().lower()
        if raw == "q":
            raise Quit()
        if not raw.isdigit() or int(raw) >= len(sorted_hand):
            print("Numéro invalide.")
            continue
        card = sorted_hand[int(raw)]
        if card not in choices:
            print("Coup non autorisé : il faut suivre la couleur, couper à l'atout, ou monter à l'atout si possible.")
            continue
        return CARD_INDEX[card]


def play_manche(env, agent, leader, manche_no, name, ask, reveal):
    """Joue une manche humain (siège 0) contre agent (siège 1). Retourne (points humain, points agent)."""
    obs, info = env.reset(options={"starting_player": leader})
    trump = env.trump_suit
    print(f"\n{'=' * 18} Manche {manche_no} · atout {SUIT_SYMBOLS[trump]} {'=' * 18}")
    if reveal:
        print(f"(Main de l'agent : {'  '.join(str(c) for c in sort_hand(env.players[AGENT].hand, trump))})")

    trick_no, trick = 1, []
    while True:
        seat = env.current_idx
        if not trick:
            opener = "à toi de commencer" if seat == HUMAN else "l'agent commence"
            print(f"\n--- Pli {trick_no}/8 · {opener} ---")
        if seat == HUMAN:
            action = ask_card(env, ask)
            print(f"Tu joues {INDEX_CARD[action]}")
        else:
            action = agent.act(obs, info["legal_actions"], info)
            print(f"L'agent joue {INDEX_CARD[action]}")
        trick.append((seat, INDEX_CARD[action]))
        obs, _rewards, done, info = env.step(action)

        if len(trick) == 2:
            winner = env.trick_winners[trick_no - 1]
            points = sum(card.points(trump) for _, card in trick) + (10 if trick_no == 8 else 0)
            who = name if winner == HUMAN else "L'agent"
            print(f"=> {who} remporte le pli ({points} pts)")
            trick, trick_no = [], trick_no + 1

        if done:
            human_points, agent_points = info["final_points"]
            print(f"\nRésultat de la manche : {name} = {human_points} | Agent = {agent_points}")
            for seat, who in ((HUMAN, name), (AGENT, "L'agent")):
                if has_belote(env.players[seat].dealt_hand, trump):
                    print(f"{who} avait Roi + Dame d'atout (+20, belote-rebelote).")
            return human_points, agent_points


def play(checkpoint=DEFAULT_CHECKPOINT, target=DEFAULT_TARGET_SCORE, name="Toi", reveal=False, ask=input):
    agent = load_agent(checkpoint)
    env = BeloteEnv()
    scores = {HUMAN: 0, AGENT: 0}
    leader = random.choice([HUMAN, AGENT])
    manche_no = 1
    print(f"=== Belote à deux : {name} contre l'agent PPO ({checkpoint}) ===")
    print(f"Premier à {target} points. Les cartes sont triées : atout d'abord, de la plus faible à la plus forte.")

    try:
        while scores[HUMAN] < target and scores[AGENT] < target:
            human_points, agent_points = play_manche(env, agent, leader, manche_no, name, ask, reveal)
            scores[HUMAN] += human_points
            scores[AGENT] += agent_points
            print(f"Scores cumulés : {name} = {scores[HUMAN]} | Agent = {scores[AGENT]} (objectif {target})")
            leader = AGENT if leader == HUMAN else HUMAN
            manche_no += 1
    except Quit:
        print(f"\nPartie interrompue. Scores : {name} = {scores[HUMAN]} | Agent = {scores[AGENT]}")
        return scores

    if scores[HUMAN] == scores[AGENT]:
        print(f"\n*** Égalité parfaite ({scores[HUMAN]} à {scores[AGENT]}) ! ***")
    else:
        winner = name if scores[HUMAN] > scores[AGENT] else "L'agent"
        print(f"\n*** {winner} remporte la partie ({scores[HUMAN]} à {scores[AGENT]}) ! ***")
    return scores


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Jouer à la belote à deux contre l'agent PPO entraîné.")
    parser.add_argument("--checkpoint", default=DEFAULT_CHECKPOINT, help="poids de l'agent (.pt)")
    parser.add_argument("--target", type=int, default=DEFAULT_TARGET_SCORE, help="score à atteindre pour gagner")
    parser.add_argument("--name", default="Toi")
    parser.add_argument("--reveal", action="store_true", help="affiche la main de l'agent (pour les démos)")
    args = parser.parse_args()
    play(args.checkpoint, args.target, args.name, args.reveal)
