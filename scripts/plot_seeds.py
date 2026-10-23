import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from scripts.plot_training import SURFACE, TEXT_SECONDARY, _style_axes, parse_log  # noqa: E402

# Une couleur par entraînement, distinctes de celles des adversaires de plot_training.
RUN_COLORS = ["#2a78d6", "#6250d6", "#e87ba4", "#008300", "#e34948", "#eb6834"]

STRINGS = {
    "fr": {
        "title": "Écart de points contre {opp} : {n} entraînements indépendants",
        "ylabel": "Points agent − points adversaire",
        "xlabel": "Parties d'entraînement (millions)",
        "footnote": "Même configuration, graines différentes. Évaluation par donnes dupliquées. Ligne pointillée = jeu égal.",
    },
    "en": {
        "title": "Point margin vs {opp}: {n} independent training runs",
        "ylabel": "Agent points − opponent points",
        "xlabel": "Training games (millions)",
        "footnote": "Same configuration, different seeds. Duplicate-deal evaluation. Dashed line = break-even.",
    },
}


def main():
    parser = argparse.ArgumentParser(
        description="Superpose les courbes de plusieurs entraînements (ex. graines différentes) contre un adversaire."
    )
    parser.add_argument("logs", nargs="+", help="train.log de chaque entraînement")
    parser.add_argument("--labels", nargs="+", help="nom de chaque entraînement (même ordre que les logs)")
    parser.add_argument("--opponent", default="TrumpCountAgent")
    parser.add_argument("--max-games", type=int, help="tronque les courbes à ce nombre de parties")
    parser.add_argument("--out", default="figures/seeds.png")
    parser.add_argument("--lang", default="fr", choices=sorted(STRINGS))
    parser.add_argument("--footnote", help="remplace la note en bas de figure (ex. si les configurations diffèrent)")
    args = parser.parse_args()

    labels = args.labels or [f"run {i + 1}" for i in range(len(args.logs))]
    if len(args.logs) > len(RUN_COLORS):
        parser.error(f"au plus {len(RUN_COLORS)} entraînements par figure")
    if len(labels) != len(args.logs):
        parser.error("il faut autant de --labels que de logs")
    texts = STRINGS[args.lang]
    opp_label = args.opponent.replace("Agent", "")

    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    _style_axes(ax, texts["title"].format(opp=opp_label, n=len(args.logs)), texts["ylabel"], texts["xlabel"])
    ax.axhline(0, color=TEXT_SECONDARY, linewidth=1, linestyle="--", zorder=1)

    x_end = 0
    for log, label, color in zip(args.logs, labels, RUN_COLORS):
        points = [p for p in parse_log(log)[args.opponent] if args.max_games is None or p[0] <= args.max_games]
        x = [p[0] / 1e6 for p in points]
        y = [p[3] for p in points]
        x_end = max(x_end, x[-1])
        ax.plot(x, y, color=color, linewidth=2, label=label, zorder=3)

    ax.set_xlim(0, x_end)
    ax.legend(loc="lower right", frameon=False, fontsize=10, labelcolor=TEXT_SECONDARY)
    fig.text(0.01, 0.01, args.footnote or texts["footnote"], fontsize=8.5, color=TEXT_SECONDARY)
    fig.subplots_adjust(left=0.08, right=0.97, top=0.88, bottom=0.14)
    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    fig.savefig(args.out, facecolor=SURFACE)
    print(f"Figure sauvegardée : {args.out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
