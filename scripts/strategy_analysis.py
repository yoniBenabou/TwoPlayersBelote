"""Étude des stratégies (point B) à partir des décisions collectées par
scripts.strategy_collect : jeu de la carte (entames, atouts, coupes,
défausses, dix de der, prises de risque), annonces, preneur contre défenseur,
agent avec ou sans annonces. Imprime des tableaux markdown et écrit les
figures dans figures/.

    python -m scripts.strategy_analysis
"""
import argparse
import os
import pickle
import sys
from collections import Counter

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from belote.core.cards import Card, Rank  # noqa: E402
from belote.rl.agents import BID_THRESHOLD, trump_strength  # noqa: E402
from belote.rl.env import PASS, SUIT_OF_ACTION, SUITS, TAKE  # noqa: E402
from scripts.strategy_collect import DEFAULT_OUT  # noqa: E402

SUBJECTS = [  # (clé, nom affiché, couleur)
    ("new", "PPO with bidding", "#2a78d6"),
    ("old", "PPO without bidding (+ heuristic bids)", "#1baf7a"),
    ("old_native", "PPO without bidding, random trump", "#8c99a8"),
    ("trumpcount", "TrumpCount (heuristic)", "#eda100"),
    ("heuristic", "Heuristic", "#eb6834"),
]
NAMES = {k: n for k, n, _ in SUBJECTS}
COLORS = {k: c for k, _, c in SUBJECTS}
SMALL = (Rank.SEVEN, Rank.EIGHT, Rank.NINE)
FACES = (Rank.JACK, Rank.QUEEN, Rank.KING)
PHASES = (("tricks 1-3", 1, 3), ("tricks 4-6", 4, 6), ("tricks 7-8", 7, 8))


def pct(num, den):
    return 100.0 * num / den if den else float("nan")


def fmt(x, n=None):
    s = "–" if x != x else f"{x:.1f}%"
    return f"{s} (n={n})" if n is not None else s


# ---------------------------------------------------------------- cartes
def lead_kind(card, trump):
    if card.suit == trump:
        return "trump"
    if card.rank == Rank.ACE:
        return "ace"
    if card.rank == Rank.TEN:
        return "ten"
    return "face" if card.rank in FACES else "small"


LEAD_KINDS = ("trump", "ace", "ten", "face", "small")


def lead_profile(plays):
    leads = [p for p in plays if p["lead"]]
    out = {"n": len(leads), "all": Counter(lead_kind(p["card"], p["trump"]) for p in leads)}
    for name, lo, hi in PHASES:
        out[name] = Counter(lead_kind(p["card"], p["trump"]) for p in leads if lo <= p["t"] <= hi)
    return out


def trumps(cards, trump):
    return [c for c in cards if c.suit == trump]


def is_master_trump(card, trump, played, turned):
    """Plus fort atout encore en jeu : tous les atouts plus forts sont tombés (ou retournés)."""
    gone = set(played) | {turned}
    stronger = [Card(trump, r) for r in Rank if Card(trump, r).strength(trump) > card.strength(trump)]
    return all(c in gone for c in stronger)


def trump_management(plays):
    out = {}
    # Entame atout quand il a le choix (atout et non-atout en main), selon que l'adversaire a encore de l'atout.
    choice = [p for p in plays if p["lead"] and trumps(p["hand"], p["trump"]) and len(trumps(p["hand"], p["trump"])) < len(p["hand"])]
    opp_has = [p for p in choice if trumps(p["opp"], p["trump"])]
    opp_none = [p for p in choice if not trumps(p["opp"], p["trump"])]
    out["lead_trump_opp_has"] = (pct(sum(p["card"].suit == p["trump"] for p in opp_has), len(opp_has)), len(opp_has))
    out["lead_trump_opp_none"] = (pct(sum(p["card"].suit == p["trump"] for p in opp_none), len(opp_none)), len(opp_none))
    # Moment où partent le Valet et le 9 d'atout.
    for rank, key in ((Rank.JACK, "jack"), (Rank.NINE, "nine")):
        ts = [p["t"] for p in plays if p["card"].suit == p["trump"] and p["card"].rank == rank]
        out[f"{key}_mean_trick"] = sum(ts) / len(ts) if ts else float("nan")
        out[f"{key}_early"] = (pct(sum(t <= 2 for t in ts), len(ts)), len(ts))
        out[f"{key}_late"] = (pct(sum(t >= 7 for t in ts), len(ts)), len(ts))
        led = [p for p in plays if p["card"].suit == p["trump"] and p["card"].rank == rank]
        out[f"{key}_led"] = (pct(sum(p["lead"] for p in led), len(led)), len(led))
    return out


def ruffs(plays):
    """Coupes (obligatoires dans nos règles) : avec quel atout, quand il en a au moins 2."""
    cut = [p for p in plays if not p["lead"] and p["led"].suit != p["trump"]
           and not any(c.suit == p["led"].suit for c in p["hand"]) and len(trumps(p["hand"], p["trump"])) >= 2]
    lowest = sum(p["card"] == min(trumps(p["hand"], p["trump"]), key=lambda c: c.strength(p["trump"])) for p in cut)
    big = sum(p["card"].rank in (Rank.JACK, Rank.NINE) for p in cut)
    has_small = [p for p in cut if any(c.rank not in (Rank.JACK, Rank.NINE) for c in trumps(p["hand"], p["trump"]))]
    big_when_small = sum(p["card"].rank in (Rank.JACK, Rank.NINE) for p in has_small)
    pts = [p for p in cut if p["led"].points(p["trump"]) >= 10]
    lowest_pts = sum(p["card"] == min(trumps(p["hand"], p["trump"]), key=lambda c: c.strength(p["trump"])) for p in pts)
    return {"n": len(cut), "lowest": pct(lowest, len(cut)), "jack_or_nine": pct(big, len(cut)),
            "big_when_small": (pct(big_when_small, len(has_small)), len(has_small)),
            "lowest_on_ace_ten": (pct(lowest_pts, len(pts)), len(pts))}


def discards(plays):
    """Défausses : ni fournir ni couper."""
    d = [p for p in plays if not p["lead"] and not any(c.suit == p["led"].suit for c in p["hand"])
         and not trumps(p["hand"], p["trump"])]
    n = len(d)
    if not n:
        return {"n": 0}
    min_pts = sum(p["card"].points(p["trump"]) == min(c.points(p["trump"]) for c in p["hand"]) for p in d)
    ace_ten = sum(p["card"].rank in (Rank.ACE, Rank.TEN) for p in d)
    counts = [Counter(c.suit for c in p["hand"]) for p in d]
    shortest = sum(cnt[p["card"].suit] == min(cnt.values()) for p, cnt in zip(d, counts))
    void = sum(cnt[p["card"].suit] == 1 for p, cnt in zip(d, counts))
    has_low = [p for p in d if any(c.points(p["trump"]) == 0 for c in p["hand"])]
    ace_ten_low = sum(p["card"].rank in (Rank.ACE, Rank.TEN) for p in has_low)
    return {"n": n, "mean_points": sum(p["card"].points(p["trump"]) for p in d) / n,
            "min_points": pct(min_pts, n), "ace_ten": pct(ace_ten, n),
            "ace_ten_with_low": (pct(ace_ten_low, len(has_low)), len(has_low)),
            "shortest_suit": pct(shortest, n), "makes_void": pct(void, n)}


def last_trick(data):
    rounds = [r for r in data["rounds"] if not r["redeal"]]
    won = sum(r["tricks"][7] for r in rounds)
    # Pli 7, il entame avec 2 cartes : le plus fort atout restant + une carte hors atout.
    cases = []
    for p in data["plays"]:
        if p["t"] == 7 and p["lead"] and len(p["hand"]) == 2:
            tr = trumps(p["hand"], p["trump"])
            if len(tr) == 1 and is_master_trump(tr[0], p["trump"], p["played"], p["turned"]):
                cases.append(p["card"].suit != p["trump"])
    return {"win_last": (pct(won, len(rounds)), len(rounds)), "keeps_master": (pct(sum(cases), len(cases)), len(cases))}


def risky_tens(plays):
    leads = [p for p in plays if p["lead"]]
    risky = [p for p in leads if p["card"].suit != p["trump"] and p["card"].rank == Rank.TEN
             and Card(p["card"].suit, Rank.ACE) not in set(p["hand"]) | p["played"] | {p["turned"]}]
    opp_ace = sum(Card(p["card"].suit, Rank.ACE) in p["opp"] for p in risky)
    return {"rate": (pct(len(risky), len(leads)), len(leads)), "opp_has_ace": (pct(opp_ace, len(risky)), len(risky)),
            "won": pct(sum(p["won"] for p in risky), len(risky))}


def card_play_summary(data, role=None):
    plays = [p for p in data["plays"] if role is None or p["role"] == role]
    return {"leads": lead_profile(plays), "trumps": trump_management(plays), "ruffs": ruffs(plays),
            "discards": discards(plays), "risky": risky_tens(plays)}


# ---------------------------------------------------------------- annonces
BINS = list(range(0, 80, 10))


def bin_of(x):
    return min(x // 10 * 10, BINS[-1])


def bidding_summary(data):
    bids = data["bids"]
    r1 = [b for b in bids if b["phase"] == "bid1"]
    r2 = [b for b in bids if b["phase"] == "bid2"]
    out = {}
    # Prise au tour 1 selon la force de la couleur retournée, premier / second à parler.
    for who, sel in (("all", r1), ("first", [b for b in r1 if b["first"]]), ("second", [b for b in r1 if not b["first"]])):
        curve = {}
        for b in sel:
            s = bin_of(trump_strength(b["hand"], b["turned"].suit))
            n, k = curve.get(s, (0, 0))
            curve[s] = (n + 1, k + (b["action"] == TAKE))
        out[f"r1_curve_{who}"] = {s: (pct(k, n), n) for s, (n, k) in sorted(curve.items())}
        out[f"r1_take_{who}"] = (pct(sum(b["action"] == TAKE for b in sel), len(sel)), len(sel))
    # Tour 2 : nomme-t-il sa meilleure couleur ?
    named = [b for b in r2 if b["action"] != PASS]
    best = 0
    for b in named:
        allowed = [s for s in SUITS if s != b["turned"].suit]
        strengths = {s: trump_strength(b["hand"], s) for s in allowed}
        best += strengths[SUIT_OF_ACTION[b["action"]]] == max(strengths.values())
    out["r2_named"] = (pct(len(named), len(r2)), len(r2))
    out["r2_best_suit"] = (pct(best, len(named)), len(named))
    curve = {}
    for b in r2:
        s = bin_of(max(trump_strength(b["hand"], s) for s in SUITS if s != b["turned"].suit))
        n, k = curve.get(s, (0, 0))
        curve[s] = (n + 1, k + (b["action"] != PASS))
    out["r2_curve"] = {s: (pct(k, n), n) for s, (n, k) in sorted(curve.items())}
    for who, sel in (("first", [b for b in r2 if b["first"]]), ("second", [b for b in r2 if not b["first"]])):
        out[f"r2_take_{who}"] = (pct(sum(b["action"] != PASS for b in sel), len(sel)), len(sel))
    # Passe-t-il exprès au tour 1 ? Main où la couleur retournée suffirait (>= seuil heuristique) :
    # prise selon qu'une autre couleur est nettement plus forte.
    strong = [b for b in r1 if trump_strength(b["hand"], b["turned"].suit) >= BID_THRESHOLD]
    better = [b for b in strong if max(trump_strength(b["hand"], s) for s in SUITS if s != b["turned"].suit)
              >= trump_strength(b["hand"], b["turned"].suit) + 15]
    other = [b for b in strong if b not in better]
    out["r1_strong_take_if_better_elsewhere"] = (pct(sum(b["action"] == TAKE for b in better), len(better)), len(better))
    out["r1_strong_take_otherwise"] = (pct(sum(b["action"] == TAKE for b in other), len(other)), len(other))
    # Ces passes avec une meilleure couleur ailleurs : que fait-il au tour 2 (s'il y arrive) ?
    passed = {b["r"] for b in better if b["action"] == PASS}
    r2_after = [b for b in r2 if b["r"] in passed]
    out["r2_after_strategic_pass"] = (pct(sum(b["action"] != PASS for b in r2_after), len(r2_after)), len(r2_after))
    # Résultat des prises, selon la force de l'atout choisi.
    takes = [b for b in bids if b["action"] != PASS]
    res = {}
    for b in takes:
        suit = b["turned"].suit if b["action"] == TAKE else SUIT_OF_ACTION[b["action"]]
        s = bin_of(trump_strength(b["hand"], suit))
        o = b["outcome"]
        n, d, m = res.get(s, (0, 0, 0))
        res[s] = (n + 1, d + o["dedans"], m + o["my_points"] - o["opp_points"])
    out["take_outcome"] = {s: (pct(d, n), m / n, n) for s, (n, d, m) in sorted(res.items())}
    out["take_rate"] = pct(len(takes), len({b["r"] for b in bids}))
    out["dedans_rate"] = pct(sum(b["outcome"]["dedans"] for b in takes), len(takes))
    return out


# ---------------------------------------------------------------- figures
def style(ax):
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", color="#e4e3df")
    ax.set_axisbelow(True)


def fig_bidding(results, out_dir):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    ax = axes[0]
    for key, label, ls in (("new", "PPO with bidding — first to speak", "-"),
                           ("new", "PPO with bidding — second to speak", "--")):
        who = "first" if "first" in label else "second"
        curve = results[key]["bidding"][f"r1_curve_{who}"]
        xs = [s for s, (_, n) in curve.items() if n >= 30]
        ax.plot([x + 5 for x in xs], [curve[x][0] for x in xs], ls, marker="o", color=COLORS["new"], label=label)
    ax.step([0, BID_THRESHOLD, 80], [0, 100, 100], where="post", color=COLORS["heuristic"], label="Heuristic (threshold 40)")
    ax.set_xlabel("Strength of the turned suit in hand (trump points + 5 per card)")
    ax.set_ylabel("Takes in round 1 (%)")
    ax.set_title("Round 1: probability of taking")
    ax.set_xlim(0, 80)
    style(ax)
    ax.legend(frameon=False, fontsize=9)
    ax = axes[1]
    curve = results["new"]["bidding"]["take_outcome"]
    xs = [s for s, (_, _, n) in curve.items() if n >= 30]
    ax.bar([x + 5 for x in xs], [curve[x][0] for x in xs], width=8, color=COLORS["new"])
    ax.set_xlabel("Strength of the chosen trump suit in hand")
    ax.set_ylabel("Taker set (“dedans”) (%)")
    ax.set_title("When the PPO agent takes: how often it is set")
    style(ax)
    fig.tight_layout()
    path = os.path.join(out_dir, "strategy_bidding_en.png")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def fig_leads(results, out_dir, keys=("new", "old", "trumpcount", "heuristic")):
    colors = {"trump": "#2a78d6", "ace": "#1baf7a", "ten": "#eda100", "face": "#8c99a8", "small": "#eb6834"}
    labels = {"trump": "trump", "ace": "Ace", "ten": "10", "face": "J/Q/K", "small": "7/8/9"}
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.4), sharey=True)
    for ax, (phase, _, _) in zip(axes, PHASES):
        bottom = [0] * len(keys)
        for kind in LEAD_KINDS:
            vals = []
            for key in keys:
                c = results[key]["play"]["leads"][phase]
                vals.append(pct(c[kind], sum(c.values())))
            ax.bar(range(len(keys)), vals, bottom=bottom, color=colors[kind], label=labels[kind])
            bottom = [b + v for b, v in zip(bottom, vals)]
        ax.set_xticks(range(len(keys)), [NAMES[k].replace(" (", "\n(").replace(" without", "\nwithout").replace(" with ", "\nwith ")
                                         for k in keys], fontsize=8)
        ax.set_title(f"Leads, {phase}")
        style(ax)
    axes[0].set_ylabel("Share of leads (%)")
    axes[-1].legend(frameon=False, fontsize=9, bbox_to_anchor=(1, 1), loc="upper left")
    fig.tight_layout()
    path = os.path.join(out_dir, "strategy_leads_en.png")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def fig_trump_timing(datasets, out_dir, keys=("new", "old", "trumpcount")):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2), sharey=True)
    for ax, rank, name in ((axes[0], Rank.JACK, "Jack"), (axes[1], Rank.NINE, "9")):
        width = 0.8 / len(keys)
        for i, key in enumerate(keys):
            ts = [p["t"] for p in datasets[key]["plays"] if p["card"].suit == p["trump"] and p["card"].rank == rank]
            c = Counter(ts)
            ax.bar([t + (i - (len(keys) - 1) / 2) * width for t in range(1, 9)], [pct(c[t], len(ts)) for t in range(1, 9)],
                   width=width, color=COLORS[key], label=NAMES[key])
        ax.set_xticks(range(1, 9))
        ax.set_xlabel("Trick number")
        ax.set_title(f"When the {name} of trump is played")
        style(ax)
    axes[0].set_ylabel("Share (%)")
    axes[1].legend(frameon=False, fontsize=9)
    fig.tight_layout()
    path = os.path.join(out_dir, "strategy_trump_timing_en.png")
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


# ---------------------------------------------------------------- rapport
def print_report(results, keys):
    def row(label, f):
        print(f"| {label} | " + " | ".join(f(results[k]) for k in keys) + " |")

    header = "| | " + " | ".join(NAMES[k] for k in keys) + " |"
    sep = "|---" * (len(keys) + 1) + "|"

    print("\n## 5. Jeu de la carte (sujet contre TrumpCount, mêmes 20 000 donnes)\n")
    print(header); print(sep)
    for kind in LEAD_KINDS:
        row(f"entame {kind}", lambda r, k=kind: fmt(pct(r["play"]["leads"]["all"][k], r["play"]["leads"]["n"])))
    for phase, _, _ in PHASES:
        row(f"entame atout, {phase}", lambda r, ph=phase: fmt(pct(r["play"]["leads"][ph]["trump"], sum(r["play"]["leads"][ph].values()))))
    t = lambda key: (lambda r: fmt(*r["play"]["trumps"][key]) if isinstance(r["play"]["trumps"][key], tuple) else f"{r['play']['trumps'][key]:.2f}")
    row("entame atout (choix) si l'adversaire a de l'atout", t("lead_trump_opp_has"))
    row("entame atout (choix) si l'adversaire n'en a plus", t("lead_trump_opp_none"))
    for key, name in (("jack", "Valet"), ("nine", "9")):
        row(f"{name} d'atout : pli moyen", t(f"{key}_mean_trick"))
        row(f"{name} d'atout joué aux plis 1-2", t(f"{key}_early"))
        row(f"{name} d'atout gardé jusqu'aux plis 7-8", t(f"{key}_late"))
        row(f"{name} d'atout joué en entame", t(f"{key}_led"))
    row("coupe avec son plus petit atout (≥ 2 atouts)", lambda r: fmt(r["play"]["ruffs"]["lowest"], r["play"]["ruffs"]["n"]))
    row("coupe avec Valet/9 alors qu'il a un petit atout", lambda r: fmt(*r["play"]["ruffs"]["big_when_small"]))
    row("coupe un As/10 avec son plus petit atout", lambda r: fmt(*r["play"]["ruffs"]["lowest_on_ace_ten"]))
    row("défausse : points moyens jetés", lambda r: f"{r['play']['discards']['mean_points']:.2f} (n={r['play']['discards']['n']})")
    row("défausse : carte la moins chère", lambda r: fmt(r["play"]["discards"]["min_points"]))
    row("défausse : As ou 10 alors qu'il a une carte à 0", lambda r: fmt(*r["play"]["discards"]["ace_ten_with_low"]))
    row("défausse dans sa couleur la plus courte", lambda r: fmt(r["play"]["discards"]["shortest_suit"]))
    row("défausse qui crée une chicane (dernière carte de la couleur)", lambda r: fmt(r["play"]["discards"]["makes_void"]))
    row("gagne le dernier pli (dix de der)", lambda r: fmt(*r["last"]["win_last"]))
    row("pli 7 : garde l'atout maître pour le dernier pli", lambda r: fmt(*r["last"]["keeps_master"]))
    row("entame un 10 sans avoir vu l'As (% des entames)", lambda r: fmt(*r["play"]["risky"]["rate"]))
    row("… l'adversaire a cet As", lambda r: fmt(*r["play"]["risky"]["opp_has_ace"]))
    row("… pli gagné", lambda r: fmt(r["play"]["risky"]["won"]))

    bid_keys = [k for k in keys if results[k].get("bidding")]
    bh = "| | " + " | ".join(NAMES[k] for k in bid_keys) + " |"
    bs = "|---" * (len(bid_keys) + 1) + "|"
    print("\n## 6. Annonces\n")
    print(bh); print(bs)

    def brow(label, f):
        print(f"| {label} | " + " | ".join(f(results[k]["bidding"]) for k in bid_keys) + " |")
    brow("prend (toutes manches)", lambda b: fmt(b["take_rate"]))
    brow("dedans quand il prend", lambda b: fmt(b["dedans_rate"]))
    brow("tour 1 : prend (premier à parler)", lambda b: fmt(*b["r1_take_first"]))
    brow("tour 1 : prend (second, après une passe)", lambda b: fmt(*b["r1_take_second"]))
    brow("tour 2 : nomme une couleur (premier à parler)", lambda b: fmt(*b["r2_take_first"]))
    brow("tour 2 : nomme une couleur (second)", lambda b: fmt(*b["r2_take_second"]))
    brow("tour 2 : la couleur nommée est sa plus forte", lambda b: fmt(*b["r2_best_suit"]))
    brow("tour 1, couleur retournée ≥ 40 : prend si une autre est nettement plus forte", lambda b: fmt(*b["r1_strong_take_if_better_elsewhere"]))
    brow("tour 1, couleur retournée ≥ 40 : prend sinon", lambda b: fmt(*b["r1_strong_take_otherwise"]))
    brow("… après cette passe, nomme une couleur au tour 2", lambda b: fmt(*b["r2_after_strategic_pass"]))
    print("\nCourbe tour 1 (agent avec annonces) : force -> % prise (premier / second à parler)")
    b = results["new"]["bidding"]
    for s in BINS:
        f = b["r1_curve_first"].get(s, (float("nan"), 0))
        g = b["r1_curve_second"].get(s, (float("nan"), 0))
        o = b["take_outcome"].get(s)
        extra = f" | prises : dedans {o[0]:.1f}%, écart moyen {o[1]:+.1f} (n={o[2]})" if o else ""
        print(f"  force {s:>2}-{s + 9:<2}: premier {fmt(*f)}, second {fmt(*g)}{extra}")

    print("\n## 7. Preneur ou défenseur (agent avec annonces)\n")
    print("| | preneur | défenseur |\n|---|---|---|")
    rr = results["new"]["roles"]
    def rrow(label, f):
        print(f"| {label} | {f(rr['taker'])} | {f(rr['defender'])} |")
    for kind in LEAD_KINDS:
        rrow(f"entame {kind}", lambda r, k=kind: fmt(pct(r["leads"]["all"][k], r["leads"]["n"])))
    rrow("entame atout (choix) si l'adversaire a de l'atout", lambda r: fmt(*r["trumps"]["lead_trump_opp_has"]))
    rrow("Valet d'atout : pli moyen", lambda r: f"{r['trumps']['jack_mean_trick']:.2f}")
    rrow("Valet d'atout joué aux plis 1-2", lambda r: fmt(*r["trumps"]["jack_early"]))
    rrow("9 d'atout : pli moyen", lambda r: f"{r['trumps']['nine_mean_trick']:.2f}")
    rrow("coupe avec son plus petit atout", lambda r: fmt(r["ruffs"]["lowest"], r["ruffs"]["n"]))
    rrow("défausse : points moyens jetés", lambda r: f"{r['discards']['mean_points']:.2f}")
    rrow("entame un 10 sans avoir vu l'As", lambda r: fmt(*r["risky"]["rate"]))


def main():
    parser = argparse.ArgumentParser(description="Étude des stratégies à partir de scripts.strategy_collect.")
    parser.add_argument("--data-dir", default=DEFAULT_OUT)
    parser.add_argument("--fig-dir", default="figures")
    args = parser.parse_args()
    datasets, results = {}, {}
    for key, _, _ in SUBJECTS:
        path = os.path.join(args.data_dir, f"{key}.pkl")
        if not os.path.exists(path):
            continue
        with open(path, "rb") as f:
            data = pickle.load(f)
        datasets[key] = data
        results[key] = {"play": card_play_summary(data), "last": last_trick(data),
                        "bidding": bidding_summary(data) if data["bidding"] else None}
        if key == "new":
            results[key]["roles"] = {role: card_play_summary(data, role) for role in ("taker", "defender")}
    keys = [k for k, _, _ in SUBJECTS if k in results]
    print_report(results, keys)
    os.makedirs(args.fig_dir, exist_ok=True)
    for path in (fig_bidding(results, args.fig_dir), fig_leads(results, args.fig_dir), fig_trump_timing(datasets, args.fig_dir)):
        print(f"\nFigure : {path}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
