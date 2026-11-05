"""De quoi sont faites les ouvertures de l'IA : pour chaque annonce (80, 90, 100…), la part de chaque type
de main parmi toutes les mains où elle fait cette annonce.

Type de main, lu dans la couleur annoncée (pour une passe : dans la meilleure couleur de la main) :
- les majeures d'atout : Valet + 9, Valet, 9, ou aucune ;
- le nombre d'autres atouts (en plus des majeures ; l'As d'atout compte comme un autre atout) ;
- le nombre d'As hors atout ;
- le nombre de couleurs de la main (2, 3 ou 4).
Exemple : « V + 2 atouts + 1 As · 3 couleurs » = le Valet, deux autres atouts (3 atouts en tout), un As à
côté, et une couleur absente de la main.

On part des choix de l'IA pour les 10 518 300 mains possibles (donnees/ouvertures.npz, voir
toutes_ouvertures.py) : comme chaque main est aussi probable qu'une autre, ces parts sont exactes.
« 20 % des 80 sont des V + 2 atouts » veut dire : quand l'IA ouvre à 80, elle a cette main 1 fois sur 5.

    python -m analyse_ia.types_de_mains                 # rapport (rapports/types_ouvertures.md)
    python -m analyse_ia.types_de_mains --seuil 95      # liste les types jusqu'à 95 % de chaque annonce
"""
import argparse
import os
import sys

import numpy as np

from analyse_ia.toutes_ouvertures import ACE, DATA, JACK, NINE, bit, decode
from belote.coinche.engine import CAPOT, CONTRACTS

REPORT = os.path.join("analyse_ia", "rapports", "types_ouvertures.md")
MAJORS = ("V + 9", "V", "9", "ni V ni 9")


def hand_types(masks, ref_suit):
    """Code de type pour chaque main, lu dans la couleur ref_suit (tableau de 0 à 3)."""
    base = (8 * ref_suit).astype(np.uint32)
    has = lambda rank: ((masks >> (base + np.uint32(rank))) & np.uint32(1)).astype(bool)
    v, n9 = has(JACK), has(NINE)
    trumps = sum(has(r).astype(np.int8) for r in range(8))
    major = np.where(v & n9, 0, np.where(v, 1, np.where(n9, 2, 3)))
    others = trumps - v.astype(np.int8) - n9.astype(np.int8)
    aces = sum(bit(masks, 8 * s + ACE) for s in range(4)).astype(np.int8) - has(ACE).astype(np.int8)
    colours = sum((sum(bit(masks, 8 * s + r) for r in range(8)) > 0).astype(np.int8) for s in range(4))
    return (major.astype(np.int16) * 1000 + others.astype(np.int16) * 100 + aces.astype(np.int16) * 10
            + colours.astype(np.int16))


def type_name(code):
    major, others, aces, colours = code // 1000, code // 100 % 10, code // 10 % 10, code % 10
    parts = [MAJORS[major]]
    if others:
        parts.append(f"{others} atout{'s' if others > 1 else ''}")
    elif major == 3:
        parts.append("aucun atout")
    if aces:
        parts.append(f"{aces} As")
    name = " + ".join(parts).replace("ni V ni 9 + ", "ni V ni 9, ")
    return f"{name} · {colours} couleurs"


def best_suit(masks):
    """Meilleure couleur de chaque main : le plus de majeures, puis le plus d'atouts."""
    scores = []
    for s in range(4):
        v = bit(masks, 8 * s + JACK).astype(np.int16)
        n9 = bit(masks, 8 * s + NINE).astype(np.int16)
        n = sum(bit(masks, 8 * s + r) for r in range(8)).astype(np.int16)
        scores.append(20 * (v + n9) + n)
    return np.stack(scores, axis=1).argmax(axis=1)


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Types de mains derrière chaque ouverture de l'IA.")
    parser.add_argument("--data", default=DATA)
    parser.add_argument("--out", default=REPORT)
    parser.add_argument("--seuil", type=float, default=90, help="lister les types jusqu'à ce pourcentage cumulé")
    parser.add_argument("--min", type=float, default=1.0, help="ne pas lister un type sous ce pourcentage")
    args = parser.parse_args()
    if not os.path.exists(args.data):
        sys.exit(f"{args.data} manque : lance d'abord python -m analyse_ia.toutes_ouvertures --calcul")
    data = np.load(args.data)
    masks, choice = data["mains"], data["annonce"]
    level, suit = decode(choice)
    ref = np.where(suit >= 0, suit, best_suit(masks))
    types = hand_types(masks, ref)

    lines = []
    out = lines.append
    out("# De quoi sont faites les ouvertures de l'IA\n")
    out("Pour chaque annonce de l'IA quand elle parle la première : la part de chaque type de main parmi "
        "toutes les mains où elle fait cette annonce (sur les 10 518 300 mains possibles, donc des parts exactes). "
        "Type de main lu dans la couleur annoncée (pour la passe : dans sa meilleure couleur) : majeures d'atout, "
        "nombre d'**autres** atouts, As hors atout, nombre de couleurs en main. Exemple : « V + 2 atouts + 1 As · "
        "3 couleurs » = le Valet, deux autres atouts (3 atouts en tout), un As à côté et une couleur absente.\n")
    out(f"Les types sont listés du plus fréquent au moins fréquent, jusqu'à {args.seuil:.0f} % de l'annonce "
        f"(et pas en dessous de {args.min:g} %).\n")
    for lv in [c for c in CONTRACTS if (level == c).any()] + [0]:
        sel = level == lv
        total = int(sel.sum())
        name = "Passe" if lv == 0 else ("Capot" if lv == CAPOT else str(lv))
        codes, counts = np.unique(types[sel], return_counts=True)
        order = np.argsort(-counts)
        out(f"## {name} — {total:,} mains ({100 * total / len(masks):.1f} % de toutes les mains)\n")
        if total < 1000:
            out("Trop peu de mains pour un tableau utile.\n")
            continue
        out("| Type de main | Part de cette annonce | Cumul |")
        out("|---|---|---|")
        cum = 0.0
        shown = 0
        for i in order:
            share = 100 * counts[i] / total
            if cum >= args.seuil or share < args.min:
                break
            cum += share
            shown += 1
            out(f"| {type_name(int(codes[i]))} | {share:.1f} % | {cum:.0f} % |")
        rest = 100 - cum
        if rest > 0.05:
            out(f"| *autres types ({len(codes) - shown})* | {rest:.1f} % | 100 % |")
        out("")
    text = "\n".join(lines) + "\n"
    print(text)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Écrit : {args.out}")


if __name__ == "__main__":
    main()
