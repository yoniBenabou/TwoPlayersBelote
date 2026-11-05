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
probabilité que le réseau aurait faite les annonces vraiment entendues
(passes, contrats, coinches des trois autres) avec les mains de cette
répartition. Il garde n_samples répartitions différentes, tirées selon ces poids : celui
qui a ouvert à 90 cœur a le plus souvent de quoi le faire, celui qui a passé
n'a pas de grosse main. La température adoucit ces probabilités, pour qu'un
joueur aux annonces inhabituelles (humain, robot) n'écarte pas les vraies
mains. Pour chaque répartition et chaque carte jouable, il finit la donne en faisant
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
from .engine import team_of
from .rl_env import CARD_INDEX, INDEX_CARD, NUM_ACTIONS_BIDDING, NUM_CARDS, OFFSET, bid_to_action


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


def auction_steps(env, me):
    """Annonces des trois autres joueurs, telles qu'ils les ont faites : liste de (place, observation sans
    la main, masque des annonces légales, action). Ne dépend que de ce qui est public."""
    game = env.game
    view = copy.copy(env)
    g = view.game = copy.copy(game)
    g.phase, g.tricks, g.trick, g.trump = "bidding", [], [], None
    g.played = [[] for _ in range(4)]
    g.hands = [[] for _ in range(4)]
    contract = None
    steps = []
    for k, (seat, bid) in enumerate(game.bids):
        if seat != me:
            g.bids = game.bids[:k]
            g.contract = dict(contract) if contract is not None else None
            g.current = seat
            steps.append((seat, view._observe(), view.legal_mask(), bid_to_action(bid)))
        if bid[0] == "bid":
            contract = {"seat": seat, "value": bid[1], "suit": bid[2], "mult": 1}
        elif bid[0] == "coinche":
            contract["mult"] = 2
        elif bid[0] == "surcoinche":
            contract["mult"] = 3
    return steps


def auction_log_weights(network, env, me, candidates, temperature=1.0):
    """Pour chaque répartition candidate ({place: main}), log de la probabilité que le réseau aurait faite
    les annonces entendues des autres avec ces mains (adoucie par temperature)."""
    steps = auction_steps(env, me)
    if not steps or not candidates:
        return np.zeros(len(candidates))
    played = env.game.played
    obs = np.stack([o for _, o, _, _ in steps] * len(candidates))
    for c, hands in enumerate(candidates):
        for j, (seat, _, _, _) in enumerate(steps):
            row = c * len(steps) + j
            for card in hands[seat] + played[seat]:
                obs[row, OFFSET["hand"] + CARD_INDEX[card]] = 1
    masks = torch.as_tensor(np.stack([m for _, _, m, _ in steps] * len(candidates)))
    actions = torch.as_tensor([a for _, _, _, a in steps] * len(candidates))
    with torch.no_grad():
        logits, _ = network(torch.as_tensor(obs))
        logp = torch.log_softmax((logits / temperature).masked_fill(~masks, float("-inf")), dim=-1)
    chosen = logp.gather(1, actions[:, None])[:, 0]
    return chosen.view(len(candidates), len(steps)).sum(dim=1).numpy()


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
    # la belote de la copie dépend des mains tirées (la vraie n'est connue qu'une fois annoncée)
    trump = game.trump
    king, queen = Card(trump, Rank.KING), Card(trump, Rank.QUEEN)
    game.belote_seat = next((s for s in range(4) if king in game.dealt[s] and queen in game.dealt[s]), None)
    return world


class CoinchePIMC:
    """Joueur "IA + recherche" : le réseau annonce ; pendant le jeu, la carte est choisie par PIMC."""

    def __init__(self, network, n_samples=20, seed=0, candidates=10, temperature=2.0):
        """candidates : répartitions tirées par répartition gardée, pondérées par les annonces (1 : pas de
        pondération) ; temperature : plus elle est haute, moins les annonces comptent."""
        self.network = network
        self.n_samples = n_samples
        self.candidates = candidates
        self.temperature = temperature
        self.rng = random.Random(seed)
        self.last_values = None  # {action: gain moyen} de la dernière décision

    def sample_worlds(self, env, me):
        """n_samples répartitions des mains cachées, tirées selon les annonces : liste de ({place: main},
        nombre de fois tirée)."""
        n = self.n_samples
        if self.candidates <= 1 or getattr(self.network, "num_actions", 0) != NUM_ACTIONS_BIDDING:
            return [(sample_hidden_hands(env, me, self.rng), 1) for _ in range(n)]
        pool = [sample_hidden_hands(env, me, self.rng) for _ in range(n * self.candidates)]
        logw = auction_log_weights(self.network, env, me, pool, self.temperature)
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
            scores = s.game.result["scores"]
            out.append(scores[team] - scores[1 - team])
        return out
