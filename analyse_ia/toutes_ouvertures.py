"""Toutes les ouvertures de l'IA de la Coinche à 4 : les 10 518 300 mains possibles.

Quand l'IA parle la première, son observation ne contient que ses 8 cartes (pas de score, pas de place
du donneur, aucune annonce) : son ouverture ne dépend que de sa main. On passe donc chaque main
possible (C(32, 8) = 10 518 300) dans le réseau, et on garde l'annonce la plus probable (celle que joue
le site), sa probabilité et la probabilité de passer.

    python -m analyse_ia.toutes_ouvertures --calcul   # ≈ 1 minute, écrit analyse_ia/donnees/ouvertures.npz
    python -m analyse_ia.toutes_ouvertures            # rapport à partir du fichier (analyse_ia/rapports/ouvertures.md)

Fichier (numpy) : mains (uint32, bit i = carte d'index i de belote.rl.env.INDEX_CARD : couleur * 8 +
rang 7 8 9 10 V D R A), annonce (uint8 : 0 = passe, 1 + 4 * k + c = CONTRACTS[k] dans SUITS[c]),
proba (float16, probabilité de l'annonce retenue), passe (float16, probabilité de passer).
"""
import argparse
import os
import sys
import time
from itertools import combinations, islice
from math import comb

import numpy as np
import torch

from belote.coinche.engine import CAPOT, CONTRACTS, SUITS
from belote.coinche.rl_env import BID0, COINCHE, OBS_SIZE, OFFSET, PASS
from coinche4.game import load_network
from coinche4.server import DEFAULT_MODEL

DATA = os.path.join("analyse_ia", "donnees", "ouvertures.npz")
REPORT = os.path.join("analyse_ia", "rapports", "ouvertures.md")
SYMBOL = ["♠", "♥", "♦", "♣"]  # même ordre que SUITS
N_HANDS = comb(32, 8)
# rangs dans l'index des cartes (couleur * 8 + rang)
SEVEN, EIGHT, NINE, TEN, JACK, QUEEN, KING, ACE = range(8)


# ---------- calcul ----------
def compute(model, batch, out_path):
    network = load_network(model)
    if network is None:
        sys.exit(f"Modèle introuvable : {model}")
    torch.set_num_threads(os.cpu_count() or 1)
    legal = torch.zeros(COINCHE + 2, dtype=torch.bool)
    legal[PASS:COINCHE] = True  # premier à parler : passer ou n'importe quelle annonce
    masks = np.empty(N_HANDS, dtype=np.uint32)
    choice = np.empty(N_HANDS, dtype=np.uint8)
    prob = np.empty(N_HANDS, dtype=np.float16)
    ppass = np.empty(N_HANDS, dtype=np.float16)
    weights = (1 << np.arange(32, dtype=np.uint64))
    it = combinations(range(32), 8)
    done, start = 0, time.time()
    with torch.no_grad():
        while True:
            chunk = np.array(list(islice(it, batch)), dtype=np.int64)
            if not len(chunk):
                break
            n = len(chunk)
            obs = np.zeros((n, OBS_SIZE), dtype=np.float32)
            obs[np.arange(n)[:, None], OFFSET["hand"] + chunk] = 1
            obs[:, OFFSET["phase"]] = 1
            logits, _ = network(torch.from_numpy(obs))
            probs = torch.softmax(logits.masked_fill(~legal, float("-inf")), dim=-1)
            best = probs.argmax(dim=-1)
            masks[done: done + n] = weights[chunk].sum(axis=1).astype(np.uint32)
            choice[done: done + n] = (best - PASS).numpy().astype(np.uint8)  # 0 = passe, 1.. = annonces
            prob[done: done + n] = probs.gather(1, best[:, None])[:, 0].numpy()
            ppass[done: done + n] = probs[:, PASS].numpy()
            done += n
            if done % (batch * 16) == 0 or done == N_HANDS:
                rate = done / (time.time() - start)
                print(f"  {done:>10,} / {N_HANDS:,} mains  ({rate:,.0f} mains/s, reste ≈ {(N_HANDS - done) / rate:.0f} s)",
                      flush=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.savez_compressed(out_path, mains=masks, annonce=choice, proba=prob, passe=ppass)
    print(f"Écrit : {out_path}")


# ---------- description vectorisée des mains ----------
def bit(masks, index):
    return (masks >> np.uint32(index)) & np.uint32(1)


def suit_features(masks, s):
    """Pour la couleur s : Valet, 9, As, nombre de cartes, belote (Roi + Dame)."""
    base = 8 * s
    count = sum(bit(masks, base + r) for r in range(8)).astype(np.int8)
    return {"V": bit(masks, base + JACK).astype(bool), "9": bit(masks, base + NINE).astype(bool),
            "A": bit(masks, base + ACE).astype(bool), "n": count,
            "belote": (bit(masks, base + KING) & bit(masks, base + QUEEN)).astype(bool),
            "10": bit(masks, base + TEN).astype(bool)}


def decode(choice):
    """(niveau, couleur) : niveau 0 = passe."""
    k = (choice.astype(np.int16) - 1) // 4
    level = np.where(choice == 0, 0, np.array(CONTRACTS)[np.clip(k, 0, len(CONTRACTS) - 1)])
    suit = np.where(choice == 0, -1, (choice.astype(np.int16) - 1) % 4)
    return level, suit


# ---------- rapport ----------
def report(path, out_path):
    data = np.load(path)
    masks, choice, prob = data["mains"], data["annonce"], data["proba"].astype(np.float32)
    n = len(masks)
    level, suit = decode(choice)
    per_suit = [suit_features(masks, s) for s in range(4)]
    # caractéristiques dans la couleur annoncée (ou, pour une passe, la meilleure couleur)
    strength = np.stack([2 * f["V"] + 2 * f["9"] + f["n"] for f in per_suit], axis=1)
    natural = strength.argmax(axis=1)
    ref = np.where(suit >= 0, suit, natural)
    pick = lambda key: np.choose(ref, [f[key] for f in per_suit])
    trumps, has_v, has_9, has_a, belote = pick("n"), pick("V"), pick("9"), pick("A"), pick("belote")
    aces = sum(bit(masks, 8 * s + ACE) for s in range(4)).astype(np.int8) - has_a.astype(np.int8)
    tens = sum(bit(masks, 8 * s + TEN) for s in range(4)).astype(np.int8) - pick("10").astype(np.int8)
    colours = sum((f["n"] > 0).astype(np.int8) for f in per_suit)

    lines = []
    out = lines.append
    out("# Toutes les ouvertures de l'IA\n")
    out(f"L'IA parle la première : son annonce ne dépend que de ses 8 cartes. Les {n:,} mains possibles "
        "ont été passées dans le réseau ; chaque main est aussi probable qu'une autre, donc les pourcentages "
        "sont exacts (aucun échantillonnage). Annonce retenue : la plus probable pour le réseau, comme sur le site.\n")

    out("## Combien de fois elle ouvre, et à quelle hauteur\n")
    out("| Annonce | Mains | Part | Confiance moy. | Valet | 9 | Valet + 9 | As d'atout | Atouts (moy.) | As hors atout (moy.) | 10 hors atout (moy.) | Belote | Couleurs (moy.) |")
    out("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
    for lv in [0] + [c for c in CONTRACTS if (level == c).any()]:
        sel = level == lv
        k = int(sel.sum())
        name = "Passe *(meilleure couleur)*" if lv == 0 else ("Capot" if lv == CAPOT else str(lv))
        mean = lambda a: f"{a[sel].mean():.1f}"
        share = lambda a: f"{100 * a[sel].mean():.0f} %"
        out(f"| {name} | {k:,} | {100 * k / n:.1f} % | {100 * prob[sel].mean():.0f} % | {share(has_v)} | {share(has_9)} "
            f"| {share(has_v & has_9)} | {share(has_a)} | {mean(trumps)} | {mean(aces)} | {mean(tens)} | {share(belote)} | {mean(colours)} |")
    out("")

    out("## Couleur choisie\n")
    out("| Couleur | Part des ouvertures |")
    out("|---|---|")
    opened = suit >= 0
    for s in range(4):
        out(f"| {SYMBOL[s]} | {100 * (suit[opened] == s).mean():.1f} % |")
    natural_ok = (suit[opened] == natural[opened]).mean()
    out(f"\nElle annonce sa « meilleure couleur » (le plus de majeures, puis le plus d'atouts) dans "
        f"{100 * natural_ok:.0f} % des ouvertures.\n")

    out("## Ce qu'elle fait selon son atout et ses As hors atout\n")
    out("Atout = la meilleure couleur de la main (le plus de majeures, puis le plus d'atouts), qu'elle ouvre "
        "ou non : chaque main est dans une seule case. Chaque case : part des mains où elle ouvre, puis "
        "l'ouverture la plus fréquente quand elle ouvre (et sa part).\n")
    # caractéristiques dans la meilleure couleur de la main (indépendantes de son choix)
    nat = lambda key: np.choose(natural, [f[key] for f in per_suit])
    trumps, has_v, has_9 = nat("n"), nat("V"), nat("9")
    aces = sum(bit(masks, 8 * s + ACE) for s in range(4)).astype(np.int8) - nat("A").astype(np.int8)
    out("| Atout | 0 As | 1 As | 2 As | 3 As |")
    out("|---|---|---|---|---|")
    cats = [
        ("Valet + 9 + 3 autres atouts ou +", has_v & has_9 & (trumps >= 5)),
        ("Valet + 9 + 2 autres atouts", has_v & has_9 & (trumps == 4)),
        ("Valet + 9 + 1 autre atout", has_v & has_9 & (trumps == 3)),
        ("Valet + 9 seuls", has_v & has_9 & (trumps == 2)),
        ("Valet sans 9, 4 atouts ou +", has_v & ~has_9 & (trumps >= 4)),
        ("Valet sans 9, 3 atouts", has_v & ~has_9 & (trumps == 3)),
        ("9 sans Valet, 4 atouts ou +", ~has_v & has_9 & (trumps >= 4)),
        ("9 sans Valet, 3 atouts", ~has_v & has_9 & (trumps == 3)),
        ("Valet ou 9, 2 atouts", (has_v ^ has_9) & (trumps == 2)),
        ("Valet ou 9 sec", (has_v ^ has_9) & (trumps == 1)),
        ("ni Valet ni 9", ~has_v & ~has_9),
    ]
    for name, cat in cats:
        cells = []
        for a in range(4):
            sel = cat & (np.minimum(aces, 3) == a)
            k = int(sel.sum())
            if k < 200:
                cells.append("–" if k == 0 else f"({k:,} mains)")
                continue
            open_share = (level[sel] > 0).mean()
            if open_share > 0:
                levels, counts = np.unique(level[sel & (level > 0)], return_counts=True)
                top = levels[counts.argmax()]
                top_name = "capot" if top == CAPOT else str(top)
                cells.append(f"ouvre {100 * open_share:.0f} % · **{top_name}** {100 * counts.max() / counts.sum():.0f} %")
            else:
                cells.append("ouvre 0 %")
        out(f"| {name} | " + " | ".join(cells) + " |")
    out("")
    text = "\n".join(lines) + "\n"
    print(text)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Écrit : {out_path}")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Toutes les ouvertures possibles de l'IA de la Coinche à 4.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--calcul", action="store_true", help="passe les 10 518 300 mains dans le réseau")
    parser.add_argument("--lot", type=int, default=32768, help="mains par passage dans le réseau")
    parser.add_argument("--data", default=DATA)
    parser.add_argument("--out", default=REPORT)
    args = parser.parse_args()
    if args.calcul or not os.path.exists(args.data):
        compute(args.model, args.lot, args.data)
    report(args.data, args.out)


if __name__ == "__main__":
    main()
