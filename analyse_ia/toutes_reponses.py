"""Toutes les réponses de l'IA de la Coinche à 4 : son partenaire a ouvert, l'adversaire suivant a passé.

Dans cette situation, l'IA voit ses 8 cartes et l'ouverture de son partenaire (valeur et couleur) ;
l'adversaire qui a passé n'ajoute rien à son observation. Sa réponse ne dépend donc que de sa main, du
niveau d'ouverture et de la couleur. On passe les 10 518 300 mains possibles dans le réseau pour chaque
ouverture de 80 à 120 dans chacune des 4 couleurs (≈ 210 millions de situations), et on garde la
réponse la plus probable (celle que joue le site).

    python -m analyse_ia.toutes_reponses --calcul   # ≈ 10 minutes, écrit analyse_ia/donnees/reponses.npz
    python -m analyse_ia.toutes_reponses            # rapport (analyse_ia/rapports/reponses.md)

Fichier : choix (uint8, forme (5 niveaux, 4 couleurs, 10 518 300 mains), même codage et même ordre des
mains que analyse_ia.toutes_ouvertures : 0 = passe, 1 + 4 * k + c = CONTRACTS[k] dans SUITS[c]).
"""
import argparse
import os
import random
import sys
import time
from itertools import combinations, islice

import numpy as np
import torch

from belote.coinche.engine import CAPOT, CONTRACTS, SUITS, CoincheGame
from belote.coinche.rl_env import OFFSET, PASS, CoincheEnv
from coinche4.game import load_network
from coinche4.server import DEFAULT_MODEL
from analyse_ia.toutes_ouvertures import ACE, JACK, N_HANDS, NINE, SYMBOL, bit, decode

DATA = os.path.join("analyse_ia", "donnees", "reponses.npz")
REPORT = os.path.join("analyse_ia", "rapports", "reponses.md")
LEVELS = (80, 90, 100, 110, 120)


def situation(level, suit_index):
    """Observation sans la main (partenaire ouvre level dans la couleur, adversaire passe) et annonces
    permises, pour la place qui répond."""
    game = CoincheGame(rng=random.Random(0))
    opener = game.current
    game.bid(opener, ("bid", level, SUITS[suit_index]))
    game.bid(game.current, ("pass",))
    env = CoincheEnv(bidding=True)
    env.game = game
    env.voids = [set() for _ in range(4)]
    env.trump_cap = [None] * 4
    env.belote_seen = None
    env.bid_seats = set(range(4))
    obs = env._observe()
    obs[OFFSET["hand"]: OFFSET["hand"] + 32] = 0
    return obs, torch.as_tensor(env.legal_mask())


def compute(model, batch, out_path):
    network = load_network(model)
    if network is None:
        sys.exit(f"Modèle introuvable : {model}")
    torch.set_num_threads(os.cpu_count() or 1)
    situations = [[situation(lv, s) for s in range(4)] for lv in LEVELS]
    choix = np.empty((len(LEVELS), 4, N_HANDS), dtype=np.uint8)
    it = combinations(range(32), 8)
    done, start = 0, time.time()
    with torch.no_grad():
        while True:
            chunk = np.array(list(islice(it, batch)), dtype=np.int64)
            if not len(chunk):
                break
            n = len(chunk)
            hands = np.zeros((n, 32), dtype=np.float32)
            hands[np.arange(n)[:, None], chunk] = 1
            for i in range(len(LEVELS)):
                for s in range(4):
                    template, legal = situations[i][s]
                    obs = np.repeat(template[None, :], n, axis=0)
                    obs[:, OFFSET["hand"]: OFFSET["hand"] + 32] = hands
                    logits, _ = network(torch.from_numpy(obs))
                    best = logits.masked_fill(~legal, float("-inf")).argmax(dim=-1)
                    choix[i, s, done: done + n] = (best - PASS).numpy().astype(np.uint8)
            done += n
            if done % (batch * 8) == 0 or done == N_HANDS:
                rate = done / (time.time() - start)
                print(f"  {done:>10,} / {N_HANDS:,} mains × 20 ouvertures  (reste ≈ {(N_HANDS - done) / rate / 60:.1f} min)",
                      flush=True)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    np.savez_compressed(out_path, choix=choix)
    print(f"Écrit : {out_path}")


def hand_masks():
    weights = (1 << np.arange(32, dtype=np.uint64))
    masks = np.empty(N_HANDS, dtype=np.uint32)
    it = combinations(range(32), 8)
    done = 0
    while True:
        chunk = np.array(list(islice(it, 1 << 18)), dtype=np.int64)
        if not len(chunk):
            return masks
        masks[done: done + len(chunk)] = weights[chunk].sum(axis=1).astype(np.uint32)
        done += len(chunk)


def report(path, out_path, masks_path):
    choix = np.load(path)["choix"]
    if os.path.exists(masks_path):
        masks = np.load(masks_path)["mains"]
    else:
        masks = hand_masks()
    total_aces = sum(bit(masks, 8 * s + ACE) for s in range(4)).astype(np.int8)
    lines = []
    out = lines.append
    out("# Toutes les réponses de l'IA\n")
    out("Son partenaire ouvre (80 à 120, dans chacune des 4 couleurs), l'adversaire suivant passe, l'IA répond. "
        f"Les {N_HANDS:,} mains possibles ont été passées dans le réseau pour chacune des 20 ouvertures : les "
        "pourcentages sont exacts. « Atout » = la couleur du partenaire ; « As » = ses As hors de cette couleur. "
        "Réponse retenue : la plus probable pour le réseau, comme sur le site.\n")
    out("Toutes les mains comptent pareil, même celles qui deviennent rares quand le partenaire a ouvert "
        "(par exemple 5 atouts chez l'IA) : on lit donc *ce qu'elle ferait avec telle main*.\n")
    for i, lv in enumerate(LEVELS):
        stats = []  # par couleur, puis cumul
        rows = {}
        kinds_total = {}
        for s in range(4):
            level, bid_suit = decode(choix[i, s])
            same = (level > 0) & (bid_suit == s)
            other = (level > 0) & (bid_suit != s)
            jump = np.where(same, np.where(level == CAPOT, -1, level - lv), 0)
            v, n9 = bit(masks, 8 * s + JACK).astype(bool), bit(masks, 8 * s + NINE).astype(bool)
            count = sum(bit(masks, 8 * s + r) for r in range(8)).astype(np.int8)
            aces = np.minimum(total_aces - bit(masks, 8 * s + ACE).astype(np.int8), 3)
            cats = [
                ("Valet + 9 + 2 autres atouts ou +", v & n9 & (count >= 4)),
                ("Valet + 9 + 1 autre atout", v & n9 & (count == 3)),
                ("Valet + 9 seuls", v & n9 & (count == 2)),
                ("Valet sans 9, 3 atouts ou +", v & ~n9 & (count >= 3)),
                ("Valet sans 9, 2 atouts", v & ~n9 & (count == 2)),
                ("Valet sec", v & ~n9 & (count == 1)),
                ("9 sans Valet, 3 atouts ou +", ~v & n9 & (count >= 3)),
                ("9 sans Valet, 2 atouts", ~v & n9 & (count == 2)),
                ("9 sec", ~v & n9 & (count == 1)),
                ("atouts sans Valet ni 9", ~v & ~n9 & (count >= 1)),
                ("aucun atout", count == 0),
            ]
            for name, cat in cats:
                for a in range(4):
                    sel = cat & (aces == a)
                    acc = rows.setdefault((name, a), Counter2())
                    acc.add(sel, same, other, jump)
            for key, mask in (("passe", level == 0), ("même couleur", same), ("autre couleur", other)):
                kinds_total[key] = kinds_total.get(key, 0) + int(mask.sum())
            for j in (10, 20, 30, 40):
                kinds_total[f"+{j}"] = kinds_total.get(f"+{j}", 0) + int((jump == j).sum())
            kinds_total["+50 ou plus / capot"] = kinds_total.get("+50 ou plus / capot", 0) + int(((jump >= 50) | (jump == -1)).sum())
        total = 4 * N_HANDS
        out(f"## Sur {lv} du partenaire\n")
        out(f"Passe **{100 * kinds_total['passe'] / total:.0f} %** · répond dans sa couleur "
            f"**{100 * kinds_total['même couleur'] / total:.0f} %** (+10 : {100 * kinds_total['+10'] / total:.0f} %, "
            f"+20 : {100 * kinds_total['+20'] / total:.0f} %, +30 : {100 * kinds_total['+30'] / total:.0f} %, "
            f"+40 : {100 * kinds_total['+40'] / total:.1f} %, plus ou capot : {100 * kinds_total['+50 ou plus / capot'] / total:.1f} %) · "
            f"annonce une autre couleur **{100 * kinds_total['autre couleur'] / total:.0f} %**\n")
        out("Chaque case : part des mains où elle répond dans la couleur du partenaire, puis la réponse la plus "
            "fréquente dans ce cas (et sa part). « autre » : part où elle annonce une autre couleur, si elle "
            "dépasse 10 %.\n")
        out("| Dans l'atout du partenaire | 0 As | 1 As | 2 As | 3 As |")
        out("|---|---|---|---|---|")
        for name, _ in cats:
            out(f"| {name} | " + " | ".join(rows[(name, a)].cell() for a in range(4)) + " |")
        out("")
    text = "\n".join(lines) + "\n"
    print(text)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Écrit : {out_path}")


class Counter2:
    """Cumul d'une case : mains, réponses dans la couleur, autre couleur, sauts (+10, +20…, -1 = capot)."""

    def __init__(self):
        self.n = 0
        self.same = 0
        self.other = 0
        self.jumps = {}

    def add(self, sel, same, other, jump):
        self.n += int(sel.sum())
        self.same += int((sel & same).sum())
        self.other += int((sel & other).sum())
        values, counts = np.unique(jump[sel & same], return_counts=True)
        for v, c in zip(values.tolist(), counts.tolist()):
            self.jumps[v] = self.jumps.get(v, 0) + c

    def cell(self):
        if self.n < 400:
            return "–" if self.n == 0 else f"({self.n:,} mains)"
        text = f"répond {100 * self.same / self.n:.0f} %"
        if self.same:
            top = max(self.jumps, key=self.jumps.get)
            name = "capot" if top == -1 else f"+{top}"
            text += f" · **{name}** {100 * self.jumps[top] / self.same:.0f} %"
        if self.other / self.n >= 0.10:
            text += f" · autre {100 * self.other / self.n:.0f} %"
        return text


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Toutes les réponses possibles de l'IA de la Coinche à 4.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--calcul", action="store_true")
    parser.add_argument("--lot", type=int, default=16384)
    parser.add_argument("--data", default=DATA)
    parser.add_argument("--mains", default=os.path.join("analyse_ia", "donnees", "ouvertures.npz"),
                        help="fichier des ouvertures (pour réutiliser la liste des mains)")
    parser.add_argument("--out", default=REPORT)
    args = parser.parse_args()
    if args.calcul or not os.path.exists(args.data):
        compute(args.model, args.lot, args.data)
    report(args.data, args.out, args.mains)


if __name__ == "__main__":
    main()
