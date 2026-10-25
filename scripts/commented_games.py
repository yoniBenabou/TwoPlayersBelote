"""Parties commentées (point B.9) : pour chaque comportement mis en évidence
par scripts.strategy_analysis, une donne typique de l'agent avec annonces
contre TrumpCount, racontée pli par pli (en anglais, pour le rapport et la
présentation). Les donnes viennent de scripts.strategy_collect --subject new.

    python -m scripts.commented_games --out report/commented_games.md
"""
import argparse
import os
import pickle
import sys

from belote.core.cards import SUIT_SYMBOLS, Card, Rank, sort_hand
from belote.core.engine import trick_winner
from belote.rl.agents import BID_THRESHOLD, trump_strength
from belote.rl.env import PASS, SUIT_OF_ACTION, SUITS, TAKE
from scripts.strategy_analysis import is_master_trump
from scripts.strategy_collect import DEFAULT_OUT, make_subject
from scripts.strategy_counterfactual import cheapest, replay

RANK = {Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9", Rank.TEN: "10", Rank.JACK: "J", Rank.QUEEN: "Q",
        Rank.KING: "K", Rank.ACE: "A"}
SUIT_NAME = {s: n for s, n in zip(SUITS, ("spades", "hearts", "diamonds", "clubs"))}


def c(card):
    return f"{RANK[card.rank]}{SUIT_SYMBOLS[card.suit]}"


def hand_str(cards, trump):
    return " ".join(c(x) for x in sort_hand(cards, trump))


def who(seat, me):
    return "**Agent**" if seat == me else "TrumpCount"


def bid_str(action, turned):
    if action == PASS:
        return "pass"
    suit = turned.suit if action == TAKE else SUIT_OF_ACTION[action]
    return f"{'takes' if action == TAKE else 'names'} {SUIT_NAME[suit]} {SUIT_SYMBOLS[suit]}"


def tricks(log):
    """[(n°, meneur, carte menée, second, carte, gagnant, points)]"""
    trump = log["trump"]
    out = []
    plays = log["plays"]
    for n in range(8):
        (s1, c1), (s2, c2) = plays[2 * n], plays[2 * n + 1]
        w = s1 if trick_winner(c1, c2, trump) == "leader" else s2
        out.append((n + 1, s1, c1, s2, c2, w, c1.points(trump) + c2.points(trump) + (10 if n == 7 else 0)))
    return out


def narrate(log, title, comment, highlight=None):
    """highlight : {n° de pli: note} ajoutée en fin de ligne."""
    me, trump, turned = log["me"], log["trump"], log["turned"]
    lines = [f"### {title}", "", comment, ""]
    lines.append(f"- Agent's hand: {hand_str(log['hands'][me], trump)}")
    lines.append(f"- TrumpCount's hand (hidden from the agent): {hand_str(log['hands'][1 - me], trump)}")
    lines.append(f"- Turned card: {c(turned)}; {'the agent' if log['first'] == me else 'TrumpCount'} speaks first.")
    bids = "; ".join(f"{'Agent' if s == me else 'TrumpCount'} ({'round 1' if ph == 'bid1' else 'round 2'}): "
                     f"{bid_str(a, turned)}" for s, ph, a in log["bids"])
    lines.append(f"- Bidding: {bids}. Trump: {SUIT_NAME[trump]} {SUIT_SYMBOLS[trump]}.")
    lines += ["", "| Trick | Lead | Reply | Winner | Points | Note |", "|---|---|---|---|---|---|"]
    for n, s1, c1, s2, c2, w, pts in tricks(log):
        note = (highlight or {}).get(n, "")
        lines.append(f"| {n} | {who(s1, me)} {c(c1)} | {who(s2, me)} {c(c2)} | {'Agent' if w == me else 'TrumpCount'} | {pts} | {note} |")
    res = f"Final: agent {log['my_points']} – TrumpCount {log['opp_points']}"
    if log["dedans"]:
        res += f" ({'the agent' if log['role'] == 'taker' else 'TrumpCount'} took and was set: “dedans”)"
    lines += ["", res + ".", ""]
    return "\n".join(lines)


def first(rounds, pred):
    return next((r for r in rounds if not r["redeal"] and pred(r)), None)


def my_bid(r, phase):
    return next((a for s, ph, a in r["bids"] if s == r["me"] and ph == phase), None)


def main():
    parser = argparse.ArgumentParser(description="Parties commentées de l'agent avec annonces.")
    parser.add_argument("--data-dir", default=DEFAULT_OUT)
    parser.add_argument("--out", default="report/commented_games.md")
    args = parser.parse_args()
    with open(os.path.join(args.data_dir, "new.pkl"), "rb") as f:
        data = pickle.load(f)
    rounds = data["rounds"]
    sections = ["# Commented deals: the PPO agent with bidding against TrumpCount", "",
                "Deals drawn from the 20,000 analysed in `scripts.strategy_analysis` "
                "(`python -m scripts.commented_games` regenerates this file). "
                "The agent never sees its opponent's hand; it is shown here to explain the play.", ""]

    # 1. Passe au tour 1 malgré une couleur retournée correcte, pour nommer mieux au tour 2.
    def strategic(r):
        h = r["hands"][r["me"]]
        st = trump_strength(h, r["turned"].suit)
        best = max(trump_strength(h, s) for s in SUITS if s != r["turned"].suit)
        return (st >= BID_THRESHOLD and best >= st + 15 and my_bid(r, "bid1") == PASS
                and r["role"] == "taker" and r["trump"] != r["turned"].suit and r["my_points"] > r["opp_points"])
    r = first(rounds, strategic)
    if r:
        h = r["hands"][r["me"]]
        sections.append(narrate(r, "1. Passing in round 1 to choose a better trump in round 2",
            f"The turned suit ({SUIT_NAME[r['turned'].suit]}) is worth {trump_strength(h, r['turned'].suit)} in the agent's hand, "
            f"above the heuristic threshold ({BID_THRESHOLD}), yet the agent passes: its {SUIT_NAME[r['trump']]} are worth "
            f"{trump_strength(h, r['trump'])}. In round 2 it names that suit. Over 20,000 deals, with a turned suit worth 40+, "
            "it takes only 54% of the time when another suit is clearly stronger, against 85% otherwise."))

    # 2. Prise légère en second à parler.
    r = first(rounds, lambda r: r["first"] != r["me"] and my_bid(r, "bid1") == TAKE
              and 20 <= trump_strength(r["hands"][r["me"]], r["turned"].suit) < 30 and r["my_points"] > r["opp_points"])
    if r:
        sections.append(narrate(r, "2. A light take as second speaker",
            f"Trump strength only {trump_strength(r['hands'][r['me']], r['turned'].suit)} (the heuristic needs {BID_THRESHOLD}), "
            "but the opponent has just passed, which says its hand is weak in that suit. As second speaker the agent takes "
            "40% of hands of strength 20-29, against 9% when it speaks first."))

    # 3. Le preneur fait tomber les atouts.
    def pulls(r):
        if r["role"] != "taker":
            return False
        ts = tricks(r)
        leads = [t for t in ts[:3] if t[1] == r["me"] and t[2].suit == r["trump"]]
        opp_trumps = [x for x in r["hands"][1 - r["me"]] if x.suit == r["trump"]]
        return len(leads) >= 2 and len(opp_trumps) >= 2 and r["my_points"] - r["opp_points"] >= 60
    r = first(rounds, pulls)
    if r:
        sections.append(narrate(r, "3. The taker draws trumps",
            "As taker, the agent leads trump early while the opponent still holds some, so its long suits are safe "
            "afterwards. As taker it leads trump 31% of the time, as defender 6%.",
            {n: "trump lead" for n, s1, c1, *_ in tricks(r)[:3] if s1 == r["me"] and c1.suit == r["trump"]}))

    # 4. Garde l'atout maître pour le dix de der.
    def keeps(r):
        me, trump = r["me"], r["trump"]
        t7, t8 = tricks(r)[6], tricks(r)[7]
        mine8 = t8[2] if t8[1] == me else t8[4]
        played = {x for t in tricks(r)[:6] for x in (t[2], t[4])}
        return (t7[1] == me and t7[2].suit != trump and mine8.suit == trump and t8[5] == me
                and is_master_trump(mine8, trump, played, r["turned"]))
    r = first(rounds, keeps)
    if r:
        sections.append(narrate(r, "4. Keeping the master trump for the last trick",
            "At trick 7 the agent holds a side card and the master trump: it plays the side card first and keeps the "
            "trump to win the last trick and its 10-point bonus (it does so in 99% of such positions; TrumpCount 53%). "
            "It wins the last trick in 73% of deals, against 50% for TrumpCount on the same deals.",
            {7: "side card first", 8: "master trump: last trick +10"}))

    # 5. Le 10 entamé sans avoir vu l'As.
    def risky(r):
        me = r["me"]
        seen = set()
        for n, s1, c1, s2, c2, w, pts in tricks(r):
            if s1 == me and c1.suit != r["trump"] and c1.rank == Rank.TEN:
                ace = Card(c1.suit, Rank.ACE)
                if ace not in r["hands"][me] and ace not in seen and ace != r["turned"] and w == me and ace not in r["hands"][1 - me]:
                    return n
            seen |= {c1, c2}
        return None
    r = first(rounds, lambda r: risky(r) is not None and r["my_points"] > r["opp_points"])
    if r:
        n = risky(r)
        sections.append(narrate(r, "5. Leading a 10 without having seen the Ace",
            "The agent leads a 10 although the Ace of that suit has not appeared. It is a bet: with 16 cards never dealt, "
            "the opponent holds that Ace only 11% of the time, and the agent wins 76% of those tricks.",
            {n: "10 led, Ace unseen"}))

    # 6. Faiblesse : défausse d'un As ou d'un 10 sur une entame atout.
    agent = make_subject("new")[0]
    by_k = {x["k"]: x for x in rounds}
    found = None
    counter = {}
    for p in data["plays"]:
        i = counter.get(p["r"], 0)
        counter[p["r"]] = i + 1
        if (found is None and p["led"] is not None and p["led"].suit == p["trump"] and p["role"] == "defender"
                and not any(x.suit == p["trump"] for x in p["hand"]) and p["card"].rank in (Rank.ACE, Rank.TEN)
                and any(x.points(p["trump"]) == 0 for x in p["hand"])):
            alt = cheapest(p["hand"], p["trump"])
            log = by_k[p["r"]]
            delta = replay(agent, log) - replay(agent, log, i, alt)
            if delta <= -20:
                found = (log, p, alt, delta)
    if found:
        log, p, alt, delta = found
        sections.append(narrate(log, "6. A weakness: throwing away an Ace or a 10 on a trump lead",
            f"As defender with no trump left, the agent answers the taker's trump lead with {c(p['card'])} although it holds "
            f"{c(alt)} (0 points). Replaying the deal with {c(alt)} instead (everything else identical) changes the round "
            f"margin by {-delta:+d} points in the agent's favour. Over all such positions the measured cost is about 17 points "
            "each time (~1,000 cases in 20,000 deals): the clearest mistake found, and a target for search at play time.",
            {p["t"]: f"discards {c(p['card'])} instead of {c(alt)}"}))

    with open(args.out, "w", encoding="utf-8") as f:
        f.write("\n".join(sections))
    print(f"{len(sections) - 4} donnes commentées -> {args.out}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
