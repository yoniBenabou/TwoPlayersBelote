"""De quoi sont faites les réponses de l'IA : son partenaire a ouvert (80 à 120), l'adversaire suivant a
passé ; pour chaque réponse (passe, +10, +20, +30, autre couleur…), la part de chaque type de main parmi
toutes les mains où elle fait cette réponse.

Type de main (comme types_de_mains.py) : majeures d'atout (Valet + 9, Valet, 9, aucune), nombre
d'autres atouts, nombre d'As hors atout. Il est lu dans la couleur du partenaire, sauf quand l'IA
annonce une autre couleur : il est alors lu dans la couleur qu'elle annonce.

On part des choix de l'IA pour les 10 518 300 mains possibles et les 20 ouvertures possibles du
partenaire (donnees/reponses.npz, voir toutes_reponses.py), les 4 couleurs d'ouverture regroupées :
ces parts sont exactes, chaque main comptant pareil.

    python -m analyse_ia.types_reponses                 # rapport (rapports/types_reponses.md)
    python -m analyse_ia.types_reponses --seuil 95
"""
import argparse
import os
import sys
from collections import Counter

import numpy as np

from analyse_ia.toutes_ouvertures import decode
from analyse_ia.toutes_reponses import DATA, LEVELS, hand_masks
from analyse_ia.types_de_mains import hand_types, type_name
from belote.coinche.engine import CAPOT

REPORT = os.path.join("analyse_ia", "rapports", "types_reponses.md")
MASKS = os.path.join("analyse_ia", "donnees", "ouvertures.npz")
ANSWERS = ("Passe", "+10", "+20", "+30", "+40 ou plus", "Capot", "Autre couleur")


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Types de mains derrière chaque réponse de l'IA.")
    parser.add_argument("--data", default=DATA)
    parser.add_argument("--mains", default=MASKS)
    parser.add_argument("--out", default=REPORT)
    parser.add_argument("--seuil", type=float, default=90)
    parser.add_argument("--min", type=float, default=1.0)
    args = parser.parse_args()
    if not os.path.exists(args.data):
        sys.exit(f"{args.data} manque : lance d'abord python -m analyse_ia.toutes_reponses --calcul")
    choix = np.load(args.data)["choix"]
    masks = np.load(args.mains)["mains"] if os.path.exists(args.mains) else hand_masks()
    n = len(masks)
    in_suit = [hand_types(masks, np.full(n, s)) for s in range(4)]  # type lu dans chaque couleur

    lines = []
    out = lines.append
    out("# De quoi sont faites les réponses de l'IA\n")
    out("Son partenaire ouvre (80 à 120), l'adversaire suivant passe, l'IA répond. Pour chaque réponse : la part "
        "de chaque type de main parmi toutes les mains où elle fait cette réponse (10 518 300 mains × 4 couleurs "
        "d'ouverture regroupées, donc des parts exactes, chaque main comptant pareil).\n")
    out("Type de main : majeures d'atout, nombre d'**autres** atouts, As hors atout, lu **dans la couleur du "
        "partenaire** (pour « Autre couleur » : dans la couleur qu'elle annonce). Exemple : « V + 2 atouts + 1 As » "
        "= le Valet, deux autres atouts (3 atouts en tout) et un As à côté.\n")
    out(f"Les types sont listés du plus fréquent au moins fréquent, jusqu'à {args.seuil:.0f} % de la réponse "
        f"(et pas en dessous de {args.min:g} %). Une réponse donnée par moins de 0,5 % des mains n'a pas de tableau.\n")
    for i, lv in enumerate(LEVELS):
        counts = {a: Counter() for a in ANSWERS}
        for s in range(4):
            level, bid_suit = decode(choix[i, s])
            same = (level > 0) & (bid_suit == s)
            other = (level > 0) & (bid_suit != s)
            jump = np.where(level == CAPOT, 999, level - lv)
            groups = {
                "Passe": level == 0,
                "+10": same & (jump == 10), "+20": same & (jump == 20), "+30": same & (jump == 30),
                "+40 ou plus": same & (jump >= 40) & (jump < 999), "Capot": same & (jump == 999),
            }
            for name, sel in groups.items():
                codes, k = np.unique(in_suit[s][sel], return_counts=True)
                counts[name].update(dict(zip(codes.tolist(), k.tolist())))
            # autre couleur : type lu dans la couleur qu'elle annonce
            for t in range(4):
                if t == s:
                    continue
                sel = other & (bid_suit == t)
                codes, k = np.unique(in_suit[t][sel], return_counts=True)
                counts["Autre couleur"].update(dict(zip(codes.tolist(), k.tolist())))
        total_all = 4 * n
        out(f"## Sur {lv} du partenaire\n")
        summary = " · ".join(f"{a} {100 * sum(counts[a].values()) / total_all:.1f} %" for a in ANSWERS
                             if sum(counts[a].values()))
        out(f"Réponses : {summary}\n")
        for a in ANSWERS:
            total = sum(counts[a].values())
            if total < 0.005 * total_all:
                continue
            where = "dans sa couleur à elle" if a == "Autre couleur" else "dans la couleur du partenaire"
            out(f"### {a} ({100 * total / total_all:.1f} % des mains) — type lu {where}\n")
            out("| Type de main | Part de cette réponse | Cumul |")
            out("|---|---|---|")
            cum, shown = 0.0, 0
            for code, k in counts[a].most_common():
                share = 100 * k / total
                if cum >= args.seuil or share < args.min:
                    break
                cum += share
                shown += 1
                out(f"| {type_name(int(code))} | {share:.1f} % | {cum:.0f} % |")
            if 100 - cum > 0.05:
                out(f"| *autres types ({len(counts[a]) - shown})* | {100 - cum:.1f} % | 100 % |")
            out("")
    text = "\n".join(lines) + "\n"
    print(text)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Écrit : {args.out}")


if __name__ == "__main__":
    main()
