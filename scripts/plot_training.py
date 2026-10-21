import argparse
import os
import re
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# Ordre fixe des adversaires (une couleur par adversaire, jamais réattribuée).
OPPONENTS = [
    ("RandomAgent", "Random", "#2a78d6"),
    ("HeuristicAgent", "Heuristic", "#eb6834"),
    ("VoidExploitAgent", "VoidExploit", "#1baf7a"),
    ("TrumpCountAgent", "TrumpCount", "#eda100"),
]

TEXT_PRIMARY = "#0b0b0b"
TEXT_SECONDARY = "#52514e"
GRID = "#e4e3df"
SURFACE = "#fcfcfb"

EVAL_RE = re.compile(r"Évaluation à (\d+)")
RESULT_RE = re.compile(
    r"(\w+Agent)\s+win_rate=\s*([\d.]+)% \(±([\d.]+)pp\) \| écart points\s+([+-][\d.]+) \(±([\d.]+)\)"
)


def parse_log(path):
    """Lit un train.log de scripts.train. Retourne
    {adversaire: [(parties, win_rate%, ic_win, écart_points, ic_points), ...]}."""
    results = {}
    games = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            m = EVAL_RE.search(line)
            if m:
                games = int(m.group(1))
                continue
            m = RESULT_RE.search(line)
            if m and games is not None:
                name = m.group(1)
                results.setdefault(name, []).append(
                    (games, float(m.group(2)), float(m.group(3)), float(m.group(4)), float(m.group(5)))
                )
    return results


def _style_axes(ax, title, ylabel):
    ax.set_facecolor(SURFACE)
    ax.set_title(title, loc="left", fontsize=14, color=TEXT_PRIMARY, pad=14)
    ax.set_xlabel("Parties d'entraînement (millions)", color=TEXT_SECONDARY)
    ax.set_ylabel(ylabel, color=TEXT_SECONDARY)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.tick_params(colors=TEXT_SECONDARY, length=0)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)


def plot_metric(results, value_idx, ci_idx, reference, title, ylabel, unit, out_path):
    fig, ax = plt.subplots(figsize=(10, 5.6), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    _style_axes(ax, title, ylabel)

    ax.axhline(reference, color=TEXT_SECONDARY, linewidth=1, linestyle="--", zorder=1)

    label_positions = []
    for key, label, color in OPPONENTS:
        points = results.get(key)
        if not points:
            continue
        x = [p[0] / 1e6 for p in points]
        y = [p[value_idx] for p in points]
        ci = [p[ci_idx] for p in points]
        ax.fill_between(x, [v - c for v, c in zip(y, ci)], [v + c for v, c in zip(y, ci)],
                        color=color, alpha=0.10, linewidth=0, zorder=2)
        ax.plot(x, y, color=color, linewidth=2, label=label, zorder=3)
        ax.plot(x[-1], y[-1], "o", color=color, markersize=7,
                markeredgecolor=SURFACE, markeredgewidth=2, zorder=4)
        label_positions.append([y[-1], f"{label}  {y[-1]:+.1f}{unit}" if unit != "%" else f"{label}  {y[-1]:.1f} %"])

    # Étiquettes directes en bout de courbe, écartées pour ne pas se chevaucher.
    label_positions.sort()
    y_min, y_max = ax.get_ylim()
    min_gap = (y_max - y_min) * 0.055
    for i in range(1, len(label_positions)):
        if label_positions[i][0] - label_positions[i - 1][0] < min_gap:
            label_positions[i][0] = label_positions[i - 1][0] + min_gap
    x_end = max(p[0] for pts in results.values() for p in pts) / 1e6
    for y, text in label_positions:
        ax.annotate(text, xy=(x_end, y), xytext=(10, 0), textcoords="offset points",
                    va="center", fontsize=10, color=TEXT_PRIMARY)

    ax.set_xlim(left=0, right=x_end * 1.0)
    ax.margins(x=0)
    ax.legend(loc="upper left", bbox_to_anchor=(0, 1.0), ncol=4, frameon=False,
              fontsize=10, labelcolor=TEXT_SECONDARY, handlelength=1.6)
    fig.text(0.01, 0.01,
             "Évaluation par donnes dupliquées. Bande = intervalle de confiance à 95 %. "
             f"Ligne pointillée = jeu égal ({reference:g}{'' if unit != '%' else ' %'}).",
             fontsize=8.5, color=TEXT_SECONDARY)
    fig.subplots_adjust(left=0.08, right=0.80, top=0.86, bottom=0.14)
    fig.savefig(out_path, facecolor=SURFACE)
    plt.close(fig)
    print(f"Figure sauvegardée : {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Courbes d'apprentissage à partir d'un train.log.")
    parser.add_argument("log", help="chemin du train.log produit par scripts.train")
    parser.add_argument("--out-dir", default="figures")
    parser.add_argument("--prefix", default="", help="préfixe des noms de fichiers PNG")
    args = parser.parse_args()

    results = parse_log(args.log)
    if not results:
        sys.exit(f"Aucune évaluation trouvée dans {args.log}")
    os.makedirs(args.out_dir, exist_ok=True)

    plot_metric(
        results, value_idx=3, ci_idx=4, reference=0,
        title="Écart moyen de points par partie de l'agent PPO contre chaque adversaire",
        ylabel="Points agent − points adversaire", unit=" pts",
        out_path=os.path.join(args.out_dir, f"{args.prefix}ecart_points.png"),
    )
    plot_metric(
        results, value_idx=1, ci_idx=2, reference=50,
        title="Taux de victoire de l'agent PPO contre chaque adversaire",
        ylabel="Taux de victoire (%)", unit="%",
        out_path=os.path.join(args.out_dir, f"{args.prefix}win_rate.png"),
    )


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
