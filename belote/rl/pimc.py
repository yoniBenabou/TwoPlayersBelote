"""Recherche au moment de jouer : PIMC (Perfect Information Monte Carlo).

Avant chaque carte, l'agent imagine n_samples mains possibles pour
l'adversaire, compatibles avec tout ce qui est public (sa propre main, les
cartes tombées, la carte retournée, les couleurs où l'adversaire a montré
qu'il n'avait plus rien, cf. env.opponent_possible_cards). Pour chaque main
imaginée et chaque carte jouable, il finit la manche en faisant jouer le
réseau des deux côtés, puis joue la carte qui rapporte le plus de points en
moyenne (écart preneur / défenseur, règle du dedans et belote comprises).

Les annonces, et les coups où une seule carte est jouable, restent au réseau
seul. Les simulations d'une décision avancent ensemble : à chaque étape, un
seul passage du réseau pour toutes.

L'agent a besoin de l'état public de la partie : attach_env(env) avant de
jouer (fait par evaluation.play_episode). Il ne lit jamais la main de
l'adversaire : elle est remplacée par une main tirée au hasard dans chaque
copie de la partie (env.clone, qui ne copie pas la donne d'origine).
"""
import random

import numpy as np
import torch

from .env import INDEX_CARD, NUM_TRICKS, opponent_possible_cards


class PIMCAgent:
    def __init__(self, base_agent, n_samples=20, seed=0):
        """base_agent : PPOAgent (son réseau joue les annonces et les simulations)."""
        self.base = base_agent
        self.network = base_agent.network
        self.n_samples = n_samples
        self.rng = random.Random(seed)
        self.env = None
        self.last_values = None  # {action: gain moyen} de la dernière décision, pour l'analyse

    def env_kwargs(self):
        return self.base.env_kwargs()

    @property
    def uses_bidding(self):
        return self.base.uses_bidding

    def attach_env(self, env):
        self.env = env

    # ---------- informations publiques ----------
    def _public(self, me):
        """(cartes possibles chez l'adversaire, nombre de cartes qu'il a, cartes qu'il a déjà jouées)."""
        env, opp = self.env, 1 - me
        played = [INDEX_CARD[i] for i, p in enumerate(env.played_public) if p]
        known_absent = played + ([env.turned_card] if env.turned_card is not None else [])
        follows, opp_played = [], []
        for i in range(NUM_TRICKS):
            lead, follow = env._trick_leader_card[i], env._trick_follower_card[i]
            if follow is not None and follow[0] == opp:
                follows.append((lead[1], follow[1]))
            for entry in (lead, follow):
                if entry is not None and entry[0] == opp:
                    opp_played.append(entry[1])
        possible, _ = opponent_possible_cards(env.players[me].hand, known_absent, env.trump_suit, follows)
        return sorted(possible, key=lambda c: (c.suit.value, c.rank.value)), len(env.players[opp].hand), opp_played

    # ---------- décision ----------
    def act(self, obs, legal_mask, info=None):
        legal = np.flatnonzero(legal_mask)
        env = self.env
        if env is None or env.phase != "play" or len(legal) == 1:
            self.last_values = None
            return self.base.act(obs, legal_mask, info)
        me = env.current_idx
        opp = 1 - me
        possible, n_opp, opp_played = self._public(me)

        sims, owners = [], []
        for _ in range(self.n_samples):
            hand = self.rng.sample(possible, n_opp)
            world = env.clone()
            world.players[opp].hand = list(hand)
            world.players[opp].dealt_hand = list(hand) + opp_played  # pour la belote-rebelote
            for action in legal:
                sim = world.clone()
                sim.step(int(action))
                sims.append(sim)
                owners.append(int(action))
        margins = self._rollout(sims, me)

        totals = {int(a): 0.0 for a in legal}
        for action, margin in zip(owners, margins):
            totals[action] += margin
        values = {a: t / self.n_samples for a, t in totals.items()}
        self.last_values = values
        # égalité : la carte que le réseau préfère
        with torch.no_grad():
            logits, _ = self.base._masked_logits_and_value(obs, legal_mask)
        return max(values, key=lambda a: (round(values[a], 6), float(logits[a])))

    def _rollout(self, sims, me):
        """Finit chaque simulation avec le réseau (coup le plus probable, des deux côtés).
        Retourne l'écart de points final (moi - adversaire) de chacune."""
        active = [i for i, s in enumerate(sims) if not s.done]
        while active:
            obs = np.stack([sims[i]._observe(sims[i].current_idx) for i in active])
            masks = np.stack([sims[i]._legal_action_mask() for i in active])
            with torch.no_grad():
                logits, _ = self.network(torch.as_tensor(obs))
            logits = logits.masked_fill(~torch.as_tensor(masks), float("-inf"))
            actions = logits.argmax(dim=-1).tolist()
            for i, action in zip(active, actions):
                sims[i].step(action)
            active = [i for i in active if not sims[i].done]
        return [s.final_points[me] - s.final_points[1 - me] for s in sims]
