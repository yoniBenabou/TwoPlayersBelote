"""Comment l'IA de la Coinche à 4 joue : enchères disputées, contrats et jeu de la carte.

Complète l'analyse des ouvertures et des réponses (toutes_ouvertures.py, toutes_reponses.py) : on fait
jouer l'IA (le réseau seul, coup le plus probable, comme « IA » sur le site) aux 4 places sur des donnes
tirées au hasard, et on note pour chaque décision la situation (place, pli, rôle, ce qu'elle a en main,
ce qui est déjà tombé) et son choix. On ne garde que les décisions où elle avait le choix.

En plus, sur une partie des donnes, on demande à la recherche (« IA + recherche », PIMC) quelle carte elle
jouerait à chaque coup : là où elle n'est pas d'accord avec le réseau, c'est en général une faiblesse du
réseau que la recherche corrige.

    python -m analyse_ia.jeu_complet --calcul --donnes 200000 --heures-recherche 6   # la nuit
    python -m analyse_ia.jeu_complet                                                # le rapport seul

Les décisions sont gardées dans analyse_ia/donnees/ (non versionné), le rapport va dans
analyse_ia/rapports/jeu_complet.md.
"""
import argparse
import gzip
import pickle
import random
import time
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import torch

from belote.coinche.engine import CAPOT, SUITS, partner_of, team_of, trick_winner
from belote.coinche.pimc import CoinchePIMC
from belote.coinche.rl_env import CARD_INDEX, INDEX_CARD, CoincheEnv, action_to_bid
from belote.core.cards import Rank, build_deck
from coinche4.game import load_network
from coinche4.server import DEFAULT_MODEL

HERE = Path(__file__).parent
DATA = HERE / "donnees"
REPORT = HERE / "rapports" / "jeu_complet.md"
DECK = build_deck()
RANK_LABEL = {Rank.SEVEN: "7", Rank.EIGHT: "8", Rank.NINE: "9", Rank.TEN: "10", Rank.JACK: "V",
              Rank.QUEEN: "D", Rank.KING: "R", Rank.ACE: "A"}
WORKERS = 15


# ---------- description d'une situation ----------
def trump_category(hand, suit):
    """Ce qu'on a dans une couleur, de la plus forte à la plus faible (comme echantillon.py)."""
    ranks = {c.rank for c in hand if c.suit == suit}
    n, j, nine = len(ranks), Rank.JACK in ranks, Rank.NINE in ranks
    if j and nine:
        return "V+9, 4 atouts ou +" if n >= 4 else "V+9, 3 atouts" if n == 3 else "V+9 seuls"
    if j or nine:
        if n >= 3:
            return "V sans 9, 3 atouts ou +" if j else "9 sans V, 3 atouts ou +"
        return "V ou 9, 2 atouts" if n == 2 else "V ou 9 sec"
    return "ni V ni 9"


def best_suit(hand):
    """Meilleure couleur d'atout de la main (le plus de majeures V/9, puis le plus de cartes, puis l'As)."""
    def key(s):
        ranks = {c.rank for c in hand if c.suit == s}
        return ((Rank.JACK in ranks) + (Rank.NINE in ranks), len(ranks), Rank.ACE in ranks)
    return max(SUITS, key=key)


def aces_outside(hand, trump):
    return sum(c.rank == Rank.ACE and c.suit != trump for c in hand)


def unplayed(game):
    """Cartes pas encore jouées (pli en cours compris comme joué)."""
    gone = {c for p in game.played for c in p} | {c for _, c in game.trick}
    return [c for c in DECK if c not in gone]


def is_master(card, game, me):
    """La carte est la plus forte restante de sa couleur (vu de me : ses propres cartes comptent)."""
    trump = game.trump
    rest = [c for c in unplayed(game) if c.suit == card.suit and c != card]
    return all(c.strength(trump) < card.strength(trump) for c in rest)


def bid_suits(game):
    """{couleur: équipes qui l'ont annoncée} pendant les enchères de la donne."""
    out = defaultdict(set)
    for seat, b in game.bids:
        if b[0] == "bid" and b[2] is not None:
            out[b[2]].add(team_of(seat))
    return out


def card_decision(game, me, legal, choice, prob):
    """Un coup de la carte où il y avait le choix : la situation et la carte choisie."""
    trump, trick, hand = game.trump, game.trick, game.hands[me]
    c = game.contract
    taker = c["seat"]
    role = "preneur" if me == taker else "partenaire du preneur" if me == partner_of(taker) else "défense"
    pos = len(trick)
    rest = unplayed(game)
    my_trumps = [x for x in hand if x.suit == trump]
    trumps_out = [x for x in rest if x.suit == trump and x not in hand]
    led = trick[0][1].suit if trick else None
    winner = trick[trick_winner(trick, trump)] if trick else None
    partner_winning = winner is not None and winner[0] == partner_of(me)
    partner_master = partner_winning and (pos == 3 or (winner[1].suit == trump or not any(
        x.suit == trump for x in rest if x not in hand)) and is_master(winner[1], game, me))

    def wins(card):
        return trick_winner(trick + [(me, card)], trump) == len(trick) if trick else True

    kind = ("entame" if not trick else "fournit" if choice.suit == led
            else "coupe" if choice.suit == trump else "défausse")
    same = [x for x in legal if x.suit == choice.suit]
    rec = {
        "role": role, "pli": len(game.tricks), "pos": pos, "contrat": c["value"], "mult": c["mult"],
        "atouts": len(my_trumps), "atouts_dehors": len(trumps_out), "n_legal": len(legal),
        "maitre_atout": bool(my_trumps) and is_master(max(my_trumps, key=lambda x: x.strength(trump)), game, me),
        "pts_pli": sum(x.points(trump) for _, x in trick),
        "part_gagne": partner_winning, "part_maitre": bool(partner_master),
        "couleur_demandee_atout": led == trump if led else None,
        "peut_fournir": led is not None and any(x.suit == led for x in hand),
        "peut_couper": bool(my_trumps), "peut_gagner": any(wins(x) for x in legal),
        "choix": kind, "carte": RANK_LABEL[choice.rank], "atout": choice.suit == trump,
        "points": choice.points(trump), "maitre": is_master(choice, game, me), "gagne": wins(choice),
        "plus_haute": choice.strength(trump) == max(x.strength(trump) for x in same),
        "plus_basse": choice.strength(trump) == min(x.strength(trump) for x in same),
        "max_points_jouables": max(x.points(trump) for x in legal),
        "a_maitre_hors_atout": any(x.suit != trump and is_master(x, game, me) for x in hand),
        "a_atout_jouable": any(x.suit == trump for x in legal),
        "a_hors_atout_jouable": any(x.suit != trump for x in legal),
        "confiance": prob,
    }
    if kind in ("entame", "défausse"):
        suit = choice.suit
        cards = [x for x in hand if x.suit == suit]
        announced = bid_suits(game).get(suit, set())
        rec.update({
            "long_couleur": len(cards), "as_couleur": any(x.rank == Rank.ACE for x in cards),
            "dix_couleur": any(x.rank == Rank.TEN for x in cards),
            "annoncee_par": ("contrat" if suit == trump else "partenaire" if team_of(me) in announced and
                             team_of(me) != team_of(taker) else "son équipe" if team_of(me) in announced
                             else "adversaires" if announced else "personne"),
            "longueurs": sorted((sum(x.suit == s for x in hand) for s in SUITS if s != trump), reverse=True),
            "couleur_plus_courte": len(cards) == min(sum(x.suit == s for x in hand) for s in SUITS
                                                     if s != trump and any(x.suit == s for x in hand))
            if suit != trump else None,
            "couleur_plus_longue": len(cards) == max(sum(x.suit == s for x in hand) for s in SUITS if s != trump)
            if suit != trump else None,
        })
    return rec


def bid_decision(game, me, action, prob):
    """Une annonce de l'IA, vue sous l'angle des enchères disputées."""
    hand, c = game.hands[me], game.contract
    own = best_suit(hand)
    rec = {
        "tour": len(game.bids), "contrat": c["value"] if c else None, "mult": c["mult"] if c else None,
        "camp": None if c is None else "partenaire" if team_of(c["seat"]) == team_of(me) and c["seat"] != me
        else "moi" if c["seat"] == me else "adversaires",
        "ouverture_adverse_seule": c is not None and team_of(c["seat"]) != team_of(me) and all(
            b[0] == "pass" for s, b in game.bids if team_of(s) == team_of(me)),
        "ma_couleur": trump_category(hand, own), "ma_couleur_atouts": sum(x.suit == own for x in hand),
        "as_hors_ma_couleur": aces_outside(hand, own), "annonce": action[0],
        "valeur": action[1] if action[0] == "bid" else None, "confiance": prob,
    }
    if c is not None:
        cs = c["suit"]
        rec.update({
            "atout_contrat": trump_category(hand, cs), "atouts_contrat": sum(x.suit == cs for x in hand),
            "as_hors_contrat": aces_outside(hand, cs),
            "dix_hors_contrat": sum(x.rank == Rank.TEN and x.suit != cs for x in hand),
            "meme_couleur": action[0] == "bid" and action[2] == cs,
            "saut": (action[1] - c["value"]) if action[0] == "bid" else None,
        })
    return rec


def deal_record(game):
    """Le contrat de la donne et ce qu'il est devenu."""
    c, r = game.contract, game.result
    taker, trump = c["seat"], c["suit"]
    hand, part = game.dealt[taker], game.dealt[partner_of(taker)]
    att = team_of(taker)
    return {
        "contrat": c["value"], "mult": c["mult"], "reussi": r["made"],
        "points_attaque": game.trick_points[att], "score_attaque": r["scores"][att],
        "score_defense": r["scores"][1 - att], "plis_attaque": game.tricks_won[att],
        "preneur_atout": trump_category(hand, trump), "preneur_atouts": sum(x.suit == trump for x in hand),
        "preneur_as": aces_outside(hand, trump), "partenaire_atouts": sum(x.suit == trump for x in part),
        "partenaire_as": aces_outside(part, trump), "equipe_atouts": sum(x.suit == trump for x in hand + part),
        "coinche_par": None if game.coinche_seat is None else "défense",
        "nb_annonces": sum(b[0] == "bid" for _, b in game.bids),
        "dispute": len({team_of(s) for s, b in game.bids if b[0] == "bid"}) == 2,
    }


# ---------- collecte ----------
def network_move(network, env):
    obs = env._observe()
    mask = torch.as_tensor(env.legal_mask())
    with torch.no_grad():
        logits, _ = network(torch.as_tensor(obs))
        probs = torch.softmax(logits.masked_fill(~mask, float("-inf")), dim=-1)
    a = int(probs.argmax())
    return a, float(probs[a])


def collect(args):
    """Un processus : des donnes jouées par le réseau aux 4 places ; avec search_until, la recherche
    donne aussi son avis à chaque coup de la carte (sans changer le coup joué)."""
    worker, n_deals, model, search_until, seed = args
    torch.set_num_threads(1)
    network = load_network(model)
    env = CoincheEnv(bidding=True, seed=seed + worker)
    search = CoinchePIMC(network, n_samples=20, seed=worker) if search_until else None
    cards, bids, deals, compare = [], [], [], []
    k = 0
    while (search_until and time.time() < search_until) or (not search_until and k < n_deals):
        k += 1
        env.reset()
        game = env.game
        if search:
            search.new_game()
        while not env.done:
            me = game.current
            phase = game.phase
            a, p = network_move(network, env)
            legal = np.flatnonzero(env.legal_mask())
            if phase == "bidding":
                if not search_until:
                    bids.append(bid_decision(game, me, action_to_bid(a), p))
            elif len(legal) > 1:
                rec = card_decision(game, me, [INDEX_CARD[int(i)] for i in legal], INDEX_CARD[a], p)
                if search:
                    s = search.act(env)
                    if search.last_values:
                        vals = search.last_values
                        rec_s = card_decision(game, me, [INDEX_CARD[int(i)] for i in legal], INDEX_CARD[s], 0.0)
                        compare.append({"reseau": rec, "recherche": rec_s, "accord": s == a,
                                        "gain": vals[s] - vals[a]})
                else:
                    cards.append(rec)
            env.step(a)
        if game.phase == "done":
            if search:
                search.end_deal(env, {s: list(game.played[s]) for s in range(4)})
            elif not search_until:
                deals.append(deal_record(game))
    return {"cards": cards, "bids": bids, "deals": deals, "compare": compare}


def run(n_deals, hours_search, model, seed):
    DATA.mkdir(exist_ok=True)
    t0 = time.time()
    with Pool(WORKERS) as pool:
        parts = pool.map(collect, [(w, n_deals // WORKERS, model, 0, seed) for w in range(WORKERS)])
    data = {k: [x for p in parts for x in p[k]] for k in ("cards", "bids", "deals")}
    with gzip.open(DATA / "jeu_complet_reseau.pkl.gz", "wb") as f:
        pickle.dump(data, f)
    print(f"réseau : {len(data['deals'])} donnes, {len(data['cards'])} coups, {len(data['bids'])} annonces "
          f"({(time.time() - t0) / 60:.0f} min)", flush=True)
    if hours_search > 0:
        until = time.time() + 3600 * hours_search
        with Pool(WORKERS) as pool:
            parts = pool.map(collect, [(w, 0, model, until, seed + 1000) for w in range(WORKERS)])
        compare = [x for p in parts for x in p["compare"]]
        with gzip.open(DATA / "jeu_complet_recherche.pkl.gz", "wb") as f:
            pickle.dump({"compare": compare}, f)
        print(f"recherche : {len(compare)} coups comparés", flush=True)


# ---------- rapport ----------
def num(n):
    return f"{n:,}".replace(",", "\u202f")


def show(k):
    return " · ".join(map(str, k)) if isinstance(k, tuple) else k


def pct(x, n):
    return f"{100 * x / n:.0f} %" if n else "–"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    out += ["| " + " | ".join(str(show(c)) for c in r) + " |" for r in rows]
    return "\n".join(out)


def rate_table(recs, key, test, label, keys=None, min_n=200):
    """Pour chaque valeur de key : nombre de cas et part où test est vrai."""
    groups = defaultdict(list)
    for r in recs:
        groups[key(r)].append(r)
    keys = keys or sorted(groups, key=lambda k: (str(type(k)), k))
    rows = [(k, len(groups[k]), pct(sum(map(test, groups[k])), len(groups[k])))
            for k in keys if len(groups[k]) >= min_n]
    return table([label, "cas", "part"], rows)


def dist_table(recs, key, value, label, min_n=200, top=None):
    """Pour chaque valeur de key : la répartition des choix value."""
    groups = defaultdict(Counter)
    for r in recs:
        groups[key(r)][value(r)] += 1
    vals = Counter(value(r) for r in recs)
    cols = [v for v, _ in vals.most_common(top)]
    rows = []
    for k in sorted(groups, key=lambda k: (str(type(k)), k)):
        n = sum(groups[k].values())
        if n >= min_n:
            rows.append([k, n] + [pct(groups[k][v], n) for v in cols])
    return table([label, "cas"] + [str(v) for v in cols], rows)


CAT_ORDER = ("V+9, 4 atouts ou +", "V+9, 3 atouts", "V+9 seuls", "V sans 9, 3 atouts ou +",
             "9 sans V, 3 atouts ou +", "V ou 9, 2 atouts", "V ou 9 sec", "ni V ni 9")


def report():
    with gzip.open(DATA / "jeu_complet_reseau.pkl.gz", "rb") as f:
        data = pickle.load(f)
    cards, bids, deals = data["cards"], data["bids"], data["deals"]
    L = ["# Comment l'IA joue : enchères disputées, contrats et jeu de la carte", "",
         f"Le réseau (`models/coinche_4p.pt`, coup le plus probable) joue les 4 places sur "
         f"{num(len(deals))} donnes tirées au hasard ; {num(len(cards))} coups de la carte où il avait le choix, "
         f"{num(len(bids))} annonces. Chaque case : la part des cas (sur « cas » situations). On ne compte que "
         "les coups où elle avait le choix. Place dans le pli : 0 = elle entame, 1 = elle joue en 2e, "
         "2 = en 3e, 3 = en dernier.", ""]

    # --- contrats
    L += ["## 1. Les contrats qu'elle prend", ""]
    L.append(dist_table(deals, lambda d: "capot" if d["contrat"] == CAPOT else d["contrat"],
                        lambda d: "réussi" if d["reussi"] else "chuté", "contrat", min_n=50))
    L += ["", "Réussite selon ce que le preneur a à l'atout :", ""]
    L.append(rate_table(deals, lambda d: d["preneur_atout"], lambda d: d["reussi"], "atout du preneur",
                        keys=CAT_ORDER, min_n=50))
    L += ["", "Réussite selon les atouts de l'équipe qui prend (preneur + partenaire) :", ""]
    L.append(rate_table(deals, lambda d: d["equipe_atouts"], lambda d: d["reussi"], "atouts de l'équipe", min_n=50))
    L += ["", "Points faits par l'attaque, en moyenne, selon le contrat :", ""]
    g = defaultdict(list)
    for d in deals:
        g[d["contrat"]].append(d["points_attaque"])
    L.append(table(["contrat", "cas", "points de l'attaque (moyenne)", "marge moyenne"],
                   [(k, len(v), f"{np.mean(v):.0f}", f"{np.mean(v) - k:+.0f}") for k, v in sorted(g.items())
                    if len(v) >= 50 and k != CAPOT]))
    co = [d for d in deals if d["mult"] >= 2]
    L += ["", f"Coinches : {pct(len(co), len(deals))} des contrats ; l'attaque coinchée réussit "
          f"{pct(sum(d['reussi'] for d in co), len(co))} du temps (sur {len(co)} coinches). Surcoinches : "
          f"{sum(d['mult'] == 3 for d in deals)}. Contrats disputés (les deux équipes ont annoncé) : "
          f"{pct(sum(d['dispute'] for d in deals), len(deals))}.", ""]
    L += ["Réussite des contrats coinchés, selon le contrat :", ""]
    L.append(rate_table(co, lambda d: d["contrat"], lambda d: d["reussi"], "contrat coinché", min_n=30))

    # --- enchères disputées
    L += ["", "## 2. Les enchères disputées", "",
          "### Quand l'adversaire a ouvert (et que son équipe à elle n'a encore rien annoncé)", ""]
    opp = [b for b in bids if b["camp"] == "adversaires" and b["ouverture_adverse_seule"] and b["mult"] == 1]
    kind = lambda b: ("passe" if b["annonce"] == "pass" else "coinche" if b["annonce"] == "coinche"
                      else "surenchère")
    L.append(dist_table(opp, lambda b: b["contrat"], kind, "contrat adverse"))
    L += ["", "Selon sa meilleure couleur à elle (sur 80 à 100 adverses) :", ""]
    low = [b for b in opp if b["contrat"] <= 100]
    L.append(dist_table(low, lambda b: b["ma_couleur"], kind, "sa meilleure couleur"))
    L += ["", "### Quand elle coinche", "",
          "Part de coinche selon ce qu'elle a dans l'atout du contrat adverse (adversaire à 80-100) :", ""]
    L.append(rate_table(low, lambda b: b["atout_contrat"], lambda b: b["annonce"] == "coinche",
                        "dans l'atout adverse", keys=CAT_ORDER))
    L += ["", "… selon ses As hors de l'atout adverse :", ""]
    L.append(rate_table(low, lambda b: b["as_hors_contrat"], lambda b: b["annonce"] == "coinche", "As hors atout"))
    L += ["", "… selon le nombre d'atouts adverses qu'elle tient :", ""]
    L.append(rate_table(opp, lambda b: (b["contrat"], min(b["atouts_contrat"], 4)),
                        lambda b: b["annonce"] == "coinche", "(contrat, atouts adverses en main)"))
    allco = [b for b in bids if b["annonce"] == "coinche"]
    if allco:
        L += ["", f"Main typique quand elle coinche ({len(allco)} coinches) :", ""]
        L.append(table(["dans l'atout adverse", "part des coinches"],
                       [(k, pct(v, len(allco))) for k, v in Counter(b["atout_contrat"] for b in allco).most_common()]))
        L += ["", table(["As hors atout adverse", "part des coinches"],
                        [(k, pct(v, len(allco))) for k, v in sorted(Counter(b["as_hors_contrat"] for b in allco).items())])]
    sur = [b for b in bids if b["camp"] in ("moi", "partenaire") and b["mult"] == 2]
    if sur:
        L += ["", "### Quand son équipe est coinchée", ""]
        L.append(rate_table(sur, lambda b: (b["camp"], b["ma_couleur"] if b["camp"] == "moi" else b["atout_contrat"]),
                            lambda b: b["annonce"] == "surcoinche", "(qui a pris, atout)", min_n=50))
    L += ["", "### Quand l'adversaire surenchérit sur son équipe", "",
          "Son équipe a un contrat, l'adversaire a annoncé par-dessus : elle relance, passe ou coinche ?", ""]
    fight = [b for b in bids if b["camp"] == "adversaires" and not b["ouverture_adverse_seule"] and b["mult"] == 1]
    L.append(dist_table(fight, lambda b: b["contrat"], kind, "contrat adverse", min_n=100))

    # --- entame
    L += ["", "## 3. L'entame du premier pli", ""]
    first = [r for r in cards if r["pli"] == 0 and r["pos"] == 0]
    side = lambda r: "attaque" if r["role"] != "défense" else "défense"
    lead_kind = lambda r: ("atout" if r["atout"] else "As" if r["carte"] == "A" else
                           "10" if r["carte"] == "10" else "Roi/Dame/Valet" if r["carte"] in "RDV" else "petite")
    L.append(dist_table(first, lambda r: (r["role"]), lead_kind, "qui entame"))
    L += ["", "La couleur entamée par la défense, selon qui l'a annoncée :", ""]
    L.append(dist_table([r for r in first if side(r) == "défense"], lambda r: "défense",
                        lambda r: r["annoncee_par"], ""))
    L += ["", "Défense : entame-t-elle sa couleur la plus courte (hors atout) ?", ""]
    dfirst = [r for r in first if side(r) == "défense" and not r["atout"]]
    L.append(rate_table(dfirst, lambda r: "As" if r["carte"] == "A" else "autre", lambda r: r["couleur_plus_courte"],
                        "carte entamée"))
    L += ["", "Défense : quand elle entame une couleur sans As, avec quelle carte ?", ""]
    noace = [r for r in dfirst if not r["as_couleur"]]
    L.append(dist_table(noace, lambda r: f"{r['long_couleur']} carte(s)", lambda r: r["carte"], "longueur", top=8))

    # --- les atouts de l'attaque
    L += ["", "## 4. L'attaque et ses atouts", "",
          "Quand le preneur (ou son partenaire) entame, joue-t-il atout ? Selon les atouts encore dehors :", ""]
    att = [r for r in cards if r["pos"] == 0 and r["role"] != "défense" and r["a_atout_jouable"]
           and r["a_hors_atout_jouable"]]
    L.append(dist_table(att, lambda r: (r["role"], r["atouts_dehors"]), lambda r: "atout" if r["atout"] else "autre",
                        "(qui, atouts adverses restants)", min_n=150))
    L += ["", "… selon qu'il a l'atout maître :", ""]
    L.append(rate_table(att, lambda r: (r["role"], "atout maître" if r["maitre_atout"] else "pas maître",
                                        "dehors" if r["atouts_dehors"] else "plus d'atout dehors"),
                        lambda r: r["atout"], "situation", min_n=150))
    L += ["", "Quand l'attaque entame atout, avec quelle carte ?", ""]
    L.append(dist_table([r for r in att if r["atout"]], lambda r: r["role"], lambda r: r["carte"], "qui", top=8))
    L += ["", "La défense entame-t-elle atout ?", ""]
    dlead = [r for r in cards if r["pos"] == 0 and r["role"] == "défense" and r["a_atout_jouable"]
             and r["a_hors_atout_jouable"]]
    L.append(rate_table(dlead, lambda r: r["pli"], lambda r: r["atout"], "pli (0 = premier)", min_n=150))

    # --- entames en cours de donne
    L += ["", "## 5. Les entames en cours de donne", "",
          "Quand elle a une carte maître hors atout, la joue-t-elle ?", ""]
    lead = [r for r in cards if r["pos"] == 0 and r["pli"] > 0]
    has_m = [r for r in lead if r["a_maitre_hors_atout"]]
    L.append(rate_table(has_m, lambda r: (side(r), r["pli"]), lambda r: r["maitre"] and not r["atout"],
                        "(camp, pli)", min_n=150))
    L += ["", "Entame d'une couleur annoncée :", ""]
    L.append(dist_table([r for r in lead if not r["atout"]], lambda r: side(r), lambda r: r["annoncee_par"], "camp"))

    # --- en cours de pli
    L += ["", "## 6. En cours de pli", "", "### Son partenaire est maître du pli", "",
          "Elle fournit la couleur demandée : met-elle des points (« charge ») ?", ""]
    pm = [r for r in cards if r["pos"] > 0 and r["part_maitre"] and r["choix"] == "fournit" and not r["atout"]
          and r["max_points_jouables"] >= 10]
    L.append(rate_table(pm, lambda r: (r["pos"], side(r)), lambda r: r["points"] >= 10,
                        "(place dans le pli, camp)", min_n=150))
    L += ["", "Elle ne peut pas fournir : coupe-t-elle quand même (ce n'est pas obligé) ?", ""]
    nf = [r for r in cards if r["pos"] > 0 and r["part_gagne"] and not r["peut_fournir"] and r["peut_couper"]
          and r["a_hors_atout_jouable"]]
    L.append(rate_table(nf, lambda r: (r["pos"], "partenaire maître" if r["part_maitre"] else "partenaire pas sûr"),
                        lambda r: r["atout"], "(place, partenaire)", min_n=150))
    L += ["", "Elle défausse sur son partenaire : donne-t-elle des points (10 ou As) ?", ""]
    dis = [r for r in cards if r["choix"] == "défausse" and r["part_gagne"] and r["max_points_jouables"] >= 10]
    L.append(rate_table(dis, lambda r: (r["pos"], "maître" if r["part_maitre"] else "pas sûr"),
                        lambda r: r["points"] >= 10, "(place, partenaire)", min_n=150))
    L += ["", "### L'adversaire gagne le pli", "",
          "Elle peut prendre le pli : le prend-elle ?", ""]
    ow = [r for r in cards if r["pos"] > 0 and not r["part_gagne"] and r["peut_gagner"]]
    L.append(rate_table(ow, lambda r: (r["pos"], side(r), "peut fournir" if r["peut_fournir"] else "ne peut pas fournir"),
                        lambda r: r["gagne"], "(place, camp, couleur demandée)", min_n=150))
    L += ["", "Quand elle prend en fournissant, avec sa plus haute carte ou juste ce qu'il faut ?", ""]
    take = [r for r in ow if r["gagne"] and r["choix"] == "fournit" and not r["atout"]]
    L.append(rate_table(take, lambda r: r["pos"], lambda r: r["plus_haute"], "place dans le pli"))
    L += ["", "Elle ne prend pas en fournissant : met-elle sa plus petite carte ?", ""]
    duck = [r for r in cards if r["pos"] > 0 and not r["part_gagne"] and r["choix"] == "fournit"
            and not r["gagne"] and not r["atout"]]
    L.append(rate_table(duck, lambda r: r["pos"], lambda r: r["plus_basse"], "place dans le pli"))
    L += ["", "### Les défausses", "", "Quand elle défausse (pas de la couleur demandée, pas d'atout joué) :", ""]
    allD = [r for r in cards if r["choix"] == "défausse"]
    L.append(dist_table(allD, lambda r: "partenaire gagne" if r["part_gagne"] else "adversaire gagne",
                        lambda r: "couleur la plus courte" if r["couleur_plus_courte"] else
                        "couleur la plus longue" if r["couleur_plus_longue"] else "autre", "pli"))
    L += ["", "Défausse dans une couleur où elle a l'As (« appel ») :", ""]
    L.append(rate_table(allD, lambda r: "partenaire gagne" if r["part_gagne"] else "adversaire gagne",
                        lambda r: r["as_couleur"] and r["carte"] != "A", "pli"))

    # --- recherche vs réseau
    path = DATA / "jeu_complet_recherche.pkl.gz"
    if path.exists():
        with gzip.open(path, "rb") as f:
            comp = pickle.load(f)["compare"]
        L += ["", "## 7. Là où la recherche corrige le réseau", "",
              f"Sur {num(len(comp))} coups (le réseau joue, la recherche dit ce qu'elle jouerait avec 20 mains "
              f"imaginées), elle est d'accord {pct(sum(c['accord'] for c in comp), len(comp))} du temps. "
              "« gain » : ce que la recherche pense gagner (en points de donne) en changeant de carte ; c'est "
              "une estimation bruitée, la médiane est plus sûre que la moyenne.", ""]
        dis = [c for c in comp if not c["accord"]]
        g = defaultdict(list)
        for c in comp:
            g[(side(c["reseau"]), c["reseau"]["pli"])].append(c)
        L.append(table(["(camp, pli)", "coups", "désaccord", "gain moyen quand désaccord"],
                       [(k, len(v), pct(sum(not c["accord"] for c in v), len(v)),
                         f"{np.mean([c['gain'] for c in v if not c['accord']] or [0]):.1f}")
                        for k, v in sorted(g.items()) if len(v) >= 100]))
        L += ["", "Les corrections les plus fréquentes (ce que joue le réseau → ce que préfère la recherche) :", ""]
        def kind2(r):
            size = ("As" if r["carte"] == "A" else "10" if r["carte"] == "10" else
                    "V/9" if r["atout"] and r["carte"] in ("V", "9") else
                    "figure" if r["carte"] in "RDV" else "petite")
            what = (r["choix"] + (" atout" if r["atout"] and r["choix"] != "coupe" else "")
                    + (" maître" if r["maitre"] else ""))
            if r["choix"] != "entame":
                what += " qui prend" if r["gagne"] else " qui ne prend pas"
            return f"{what} ({size})"
        pairs = Counter((c["reseau"]["pos"], kind2(c["reseau"]), kind2(c["recherche"])) for c in dis)
        gains = defaultdict(list)
        for c in dis:
            gains[(c["reseau"]["pos"], kind2(c["reseau"]), kind2(c["recherche"]))].append(c["gain"])
        L.append(table(["place", "le réseau joue", "la recherche préfère", "cas", "gain moyen", "gain médian"],
                       [(k[0], k[1], k[2], n, f"{np.mean(gains[k]):.1f}", f"{np.median(gains[k]):.1f}")
                        for k, n in pairs.most_common(50) if k[1] != k[2]]))
        L += ["", "Par type de situation (désaccord et gain moyen) :", ""]
        sit = lambda c: (c["reseau"]["pos"], c["reseau"]["role"],
                         "partenaire gagne" if c["reseau"]["part_gagne"] else "-")
        g = defaultdict(list)
        for c in comp:
            g[sit(c)].append(c)
        L.append(table(["(place, rôle, partenaire)", "coups", "désaccord", "gain total par 1000 coups"],
                       [(k, len(v), pct(sum(not c["accord"] for c in v), len(v)),
                         f"{1000 * sum(c['gain'] for c in v) / len(v):.0f}") for k, v in sorted(g.items())
                        if len(v) >= 100]))
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text("\n".join(L) + "\n")
    print(f"rapport : {REPORT}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--calcul", action="store_true", help="rejoue les donnes (sinon : rapport seul)")
    parser.add_argument("--donnes", type=int, default=200_000, help="donnes jouées par le réseau seul")
    parser.add_argument("--heures-recherche", type=float, default=0, help="temps donné à la comparaison avec la recherche")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    if args.calcul:
        run(args.donnes, args.heures_recherche, args.model, args.seed)
    report()


if __name__ == "__main__":
    main()
