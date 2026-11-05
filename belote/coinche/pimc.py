"""Recherche au moment de jouer pour la Coinche à 4 : PIMC (Perfect
Information Monte Carlo), comme belote/rl/pimc.py pour la belote à 2.

Avant chaque carte, le joueur imagine n_samples répartitions possibles des
cartes qu'il ne voit pas entre les trois autres joueurs, compatibles avec
tout ce qui est public : sa main, les cartes tombées, le nombre de cartes de
chacun, les couleurs où un joueur a montré qu'il n'en avait plus, l'atout
maximal d'un joueur qui n'a pas pu monter (CoincheEnv._possible_mask), et la
belote annoncée (la deuxième carte reste chez celui qui l'a annoncée).

Les annonces comptent aussi : le joueur tire d'abord bien plus de
répartitions (candidates fois n_samples), puis donne à chacune un poids, la
probabilité des annonces vraiment entendues (passes, contrats, coinches des
trois autres) avec les mains de cette répartition. Cette probabilité vient
des conventions connues (Simple, Petit jeu, Papi Robert, AsR) et du réseau,
mélangés selon ce que le suivi des joueurs (conventions.py) a appris de
chacun aux donnes précédentes. Il garde n_samples répartitions différentes,
tirées selon ces poids : celui qui a ouvert à 90 cœur a le plus souvent de
quoi le faire, celui qui a passé n'a pas de grosse main. Pour chaque répartition et chaque carte jouable, il finit la donne en faisant
jouer le réseau aux quatre places, puis joue la carte qui rapporte le plus
en moyenne (score de son équipe moins celui de l'autre, barème complet).

Les annonces, et les coups où une seule carte est jouable, restent au réseau
seul. Les simulations d'une décision avancent ensemble : à chaque étape, un
seul passage du réseau pour toutes. La recherche ne lit jamais les mains
cachées : elles sont remplacées par des mains tirées au hasard dans des
copies de la partie (et la belote des copies est recalculée sur ces mains).
"""
import copy
import random

import numpy as np
import torch

from ..core.cards import Card, Rank
from .engine import legal_cards, team_of
from .conventions import CONVENTIONS, ConventionTracker
from .rl_env import CARD_INDEX, COINCHE, INDEX_CARD, NUM_ACTIONS_BIDDING, NUM_CARDS, OFFSET, PASS


def clone_env(env):
    """Copie indépendante d'un CoincheEnv (partie et déductions), assez rapide pour des milliers de copies."""
    g = env.game
    game = copy.copy(g)
    game.hands = [list(h) for h in g.hands]
    game.dealt = [list(h) for h in g.dealt]
    game.played = [list(p) for p in g.played]
    game.trick = list(g.trick)
    game.tricks = list(g.tricks)
    game.trick_points = list(g.trick_points)
    game.tricks_won = list(g.tricks_won)
    game.totals = list(g.totals)
    game.history = list(g.history)
    game.bids = list(g.bids)
    game.contract = dict(g.contract) if g.contract is not None else None
    new = copy.copy(env)
    new.game = game
    new.voids = [set(v) for v in env.voids]
    new.trump_cap = list(env.trump_cap)
    return new


def sample_hidden_hands(env, me, rng, tries=50):
    """Répartition au hasard des cartes que me ne voit pas entre les trois autres places, compatible
    avec les déductions publiques. Retourne {place: [cartes]}."""
    game = env.game
    others = [s for s in range(4) if s != me]
    unseen = env._unseen(me)
    allowed = {s: env._possible_mask(unseen, s) for s in others}
    need = {s: len(game.hands[s]) for s in others}
    cards = [i for i in np.flatnonzero(unseen)]
    forced = {}
    seen = env.belote_seen
    if seen is not None and seen != me:
        for rank in (Rank.KING, Rank.QUEEN):
            card = Card(game.trump, rank)
            if card not in game.played[seen] and CARD_INDEX[card] in cards:
                forced[CARD_INDEX[card]] = seen  # la seconde carte de la belote annoncée
    for _ in range(tries):
        hands = {s: [] for s in others}
        left = dict(need)
        ok = True
        for i, s in forced.items():
            hands[s].append(i)
            left[s] -= 1
        free = [i for i in cards if i not in forced]
        rng.shuffle(free)
        free.sort(key=lambda i: sum(allowed[s][i] for s in others))  # les plus contraintes d'abord
        for i in free:
            options = [s for s in others if allowed[s][i] and left[s] > 0]
            if not options:
                ok = False
                break
            s = rng.choices(options, weights=[left[o] for o in options])[0]
            hands[s].append(i)
            left[s] -= 1
        if ok:
            return {s: [INDEX_CARD[i] for i in h] for s, h in hands.items()}
    # déductions incohérentes (ne devrait pas arriver) : répartition sans contrainte
    free = list(cards)
    rng.shuffle(free)
    out, k = {}, 0
    for s in others:
        out[s] = [INDEX_CARD[i] for i in free[k:k + need[s]]]
        k += need[s]
    return out


def make_world(env, me, rng, hands=None):
    """Copie de la partie où les mains cachées sont remplacées par une répartition (hands, sinon tirée
    au hasard)."""
    world = clone_env(env)
    game = world.game
    if hands is None:
        hands = sample_hidden_hands(env, me, rng)
    for s, hand in hands.items():
        game.hands[s] = hand
        game.dealt[s] = hand + game.played[s]
    # la belote de la copie dépend des mains tirées (la vraie n'est connue qu'une fois annoncée) ;
    # pendant les annonces, le moteur la calcule lui-même au début du jeu
    trump = game.trump
    if trump is not None:
        king, queen = Card(trump, Rank.KING), Card(trump, Rank.QUEEN)
        game.belote_seat = next((s for s in range(4) if king in game.dealt[s] and queen in game.dealt[s]), None)
    return world


def play_steps(env, me):
    """Cartes déjà jouées par les trois autres, revues telles qu'ils les ont jouées : liste de (place, rang
    de la carte dans les cartes de cette place, observation du réseau sans la main, pli en cours, carte).
    Ne dépend que de ce qui est public : la partie est rejouée avec, pour mains, les cartes que chacun a
    déjà posées (toujours jouables : la vraie main les contenait), et la main du joueur est retirée de
    l'observation (elle sera remplacée par celle de chaque répartition imaginée)."""
    game = env.game
    history = [sc for trick, _w in game.tricks for sc in trick] + list(game.trick)
    if not history:
        return []
    replay = clone_env(env)
    g = replay.game
    g.hands = [list(game.played[s]) for s in range(4)]
    g.dealt = [list(game.played[s]) for s in range(4)]
    g.played = [[] for _ in range(4)]
    g.trick, g.tricks, g.trick_points, g.tricks_won = [], [], [0, 0], [0, 0]
    g.current, g.phase, g.belote_seat = (game.dealer + 1) % 4, "play", env.belote_seen
    replay.voids, replay.trump_cap, replay.belote_seen, replay.done = [set() for _ in range(4)], [None] * 4, None, False
    steps = []
    for seat, card in history:
        if seat != me:
            hand = g.hands[seat]
            g.hands[seat] = []
            steps.append((seat, len(g.played[seat]), replay._observe(), list(g.trick), card))
            g.hands[seat] = hand
        replay.step(CARD_INDEX[card])
    return steps


def play_log_likelihoods(network, env, me, hands, temperature=2.0, fidelity=0.8):
    """Pour chaque répartition (hands[c][place] = les 8 cartes données), log de la probabilité des cartes
    que les autres ont déjà jouées : fidelity fois le coup du réseau (adouci par temperature), le reste
    une carte jouable au hasard (personne ne joue comme le réseau à 100 %)."""
    steps = play_steps(env, me)
    if not steps or not hands:
        return np.zeros(len(hands))
    game = env.game
    trump = game.trump
    n, m = len(hands), len(steps)
    obs = np.repeat(np.stack([st[2] for st in steps])[None], n, axis=0)          # [C, S, obs]
    masks = np.zeros((n, m, network.num_actions), dtype=bool)
    actions = np.array([CARD_INDEX[st[4]] for st in steps])
    for c, h in enumerate(hands):
        for j, (seat, k, _obs, trick, _card) in enumerate(steps):
            hand = [x for x in h[seat] if x not in game.played[seat][:k]]
            idx = [CARD_INDEX[x] for x in hand]
            obs[c, j, OFFSET["hand"] + np.array(idx)] = 1
            for r in range(3):
                obs[c, j, OFFSET["possible"] + r * NUM_CARDS + np.array(idx)] = 0
            masks[c, j, [CARD_INDEX[x] for x in legal_cards(hand, trick, trump, seat)]] = True
    flat_masks = torch.as_tensor(masks.reshape(n * m, -1))
    with torch.no_grad():
        logits, _ = network(torch.as_tensor(obs.reshape(n * m, -1)))
        probs = torch.softmax((logits / temperature).masked_fill(~flat_masks, float("-inf")), dim=-1)
    probs = probs.numpy().reshape(n, m, -1)
    legal = masks[np.arange(n)[:, None], np.arange(m)[None], actions[None]]           # carte jouable ?
    chosen = probs[np.arange(n)[:, None], np.arange(m)[None], actions[None]]
    p = np.where(legal, fidelity * chosen + (1 - fidelity) / np.maximum(masks.sum(axis=2), 1), 0.0)
    return np.log(np.maximum(p, 1e-12)).sum(axis=1)


class CoinchePIMC:
    """Joueur "IA + recherche" : le réseau annonce ; pendant le jeu, la carte est choisie par PIMC."""

    def __init__(self, network, n_samples=20, seed=0, candidates=10, temperature=2.0,
                 conventions=tuple(CONVENTIONS), read_plays=False, bid_search=False, bid_samples=16,
                 bid_options=3):
        """candidates : répartitions tirées par répartition gardée, pondérées par les annonces (1 : pas de
        pondération) ; temperature : plus elle est haute, moins les probabilités du réseau comptent ;
        conventions : celles que l'IA connaît ([] : elle lit les annonces avec le réseau seul) ;
        read_plays : les répartitions sont aussi pesées par les cartes déjà jouées par les autres ;
        bid_search : pendant les annonces, la recherche compare les bid_options annonces que le réseau
        préfère (plus passer, et coincher si c'est possible) sur bid_samples répartitions."""
        self.network = network
        self.n_samples = n_samples
        self.candidates = candidates
        self.read_plays = read_plays
        self.bid_search = bid_search
        self.bid_samples = bid_samples
        self.bid_options = bid_options
        self.rng = random.Random(seed)
        self.last_values = None  # {action: gain moyen} de la dernière décision
        self.tracker = ConventionTracker(network, conventions, temperature=temperature)

    def new_game(self):
        """Nouvelle partie (d'autres joueurs) : le suivi des conventions repart de zéro."""
        self.tracker.reset()

    def end_deal(self, env, hands, totals=None):
        """Donne finie : hands[place] = les 8 cartes de chacun (toutes jouées, donc publiques) ; totals : les
        scores au moment des annonces. Le suivi apprend la façon d'annoncer de chaque joueur."""
        if getattr(self.network, "num_actions", 0) == NUM_ACTIONS_BIDDING:
            self.tracker.end_deal(env, hands, totals)

    def sample_worlds(self, env, me, n=None):
        """n (par défaut n_samples) répartitions des mains cachées, tirées selon les annonces (et les cartes
        jouées avec read_plays) : liste de ({place: main}, nombre de fois tirée)."""
        n = self.n_samples if n is None else n
        if self.candidates <= 1 or getattr(self.network, "num_actions", 0) != NUM_ACTIONS_BIDDING:
            return [(sample_hidden_hands(env, me, self.rng), 1) for _ in range(n)]
        pool = [sample_hidden_hands(env, me, self.rng) for _ in range(n * self.candidates)]
        played = env.game.played
        dealt = [{s: h + played[s] for s, h in hands.items()} for hands in pool]
        logw = self.tracker.log_weights(env, me, dealt)
        if self.read_plays and env.game.phase == "play":
            logw = logw + play_log_likelihoods(self.network, env, me, dealt, self.tracker.temperature)
        # tirage sans remise selon les poids (Gumbel top-k) : n répartitions différentes, sinon quelques
        # mains très probables reviendraient plusieurs fois et la décision reposerait sur trop peu de cas
        keys = logw + np.array([-np.log(-np.log(self.rng.random() or 1e-300)) for _ in pool])
        return [(pool[i], 1) for i in np.argsort(-keys)[:n]]

    def network_choice(self, env):
        """(action, probabilité) du réseau seul (coup le plus probable)."""
        obs = env._observe()
        mask = torch.as_tensor(env.legal_mask())
        with torch.no_grad():
            logits, _ = self.network(torch.as_tensor(obs))
            probs = torch.softmax(logits.masked_fill(~mask, float("-inf")), dim=-1)
        action = int(probs.argmax())
        return action, probs

    def act(self, env):
        """Action (indice) pour la place courante de env (un CoincheEnv avec annonces)."""
        action, probs = self.network_choice(env)
        legal = np.flatnonzero(env.legal_mask())
        if env.game.phase == "bidding" and self.bid_search and len(legal) > 1:
            return self._search_bid(env, probs)
        if env.game.phase != "play" or len(legal) == 1 or self.n_samples <= 0:
            self.last_values = None
            return action
        me = env.game.current
        sims, owners = [], []
        for hands, count in self.sample_worlds(env, me):
            world = make_world(env, me, self.rng, hands)
            for a in legal:
                sim = clone_env(world)
                sim.step(int(a))
                sims.append(sim)
                owners.append((int(a), count))
        margins = self._rollout(sims, team_of(me))
        totals = {int(a): 0.0 for a in legal}
        for (a, count), m in zip(owners, margins):
            totals[a] += count * m
        values = {a: t / self.n_samples for a, t in totals.items()}
        self.last_values = values
        # égalité : la carte que le réseau préfère
        return max(values, key=lambda a: (round(values[a], 6), float(probs[a])))

    def _search_bid(self, env, probs):
        """Annonce choisie en jouant la donne jusqu'au bout : pour chaque répartition imaginée et chaque
        annonce envisagée, le réseau finit les annonces puis joue les cartes aux quatre places."""
        me = env.game.current
        options = [int(a) for a in torch.argsort(probs, descending=True)[: self.bid_options] if probs[a] > 0]
        mask = env.legal_mask()
        for extra in (PASS, COINCHE):
            if mask[extra] and extra not in options:
                options.append(extra)
        if len(options) == 1:
            self.last_values = None
            return options[0]
        sims, owners = [], []
        for hands, count in self.sample_worlds(env, me, self.bid_samples):
            world = make_world(env, me, self.rng, hands)
            for a in options:
                sim = clone_env(world)
                sim.step(a)
                sims.append(sim)
                owners.append((a, count))
        margins = self._rollout(sims, team_of(me))
        totals = {a: 0.0 for a in options}
        for (a, count), m in zip(owners, margins):
            totals[a] += count * m
        values = {a: t / self.bid_samples for a, t in totals.items()}
        self.last_values = values
        return max(values, key=lambda a: (round(values[a], 6), float(probs[a])))

    def _rollout(self, sims, team):
        """Finit chaque simulation avec le réseau aux quatre places ; écart de score final (mon équipe - l'autre)."""
        active = [i for i, s in enumerate(sims) if not s.done]
        while active:
            obs = np.stack([sims[i]._observe() for i in active])
            masks = np.stack([sims[i].legal_mask() for i in active])
            with torch.no_grad():
                logits, _ = self.network(torch.as_tensor(obs))
            actions = logits.masked_fill(~torch.as_tensor(masks), float("-inf")).argmax(dim=-1).tolist()
            for i, a in zip(active, actions):
                sims[i].step(a)
            active = [i for i in active if not sims[i].done]
        out = []
        for s in sims:
            if s.game.phase == "redeal":  # tout le monde a passé : donne redistribuée, 0 point
                out.append(0.0)
                continue
            scores = s.game.result["scores"]
            out.append(scores[team] - scores[1 - team])
        return out
