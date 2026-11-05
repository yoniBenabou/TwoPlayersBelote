"""Conventions d'annonce connues de l'IA, et suivi de la façon d'annoncer de chaque joueur.

L'IA connaît les conventions qui existent (celles des robots : Simple, Petit jeu, Papi Robert, AsR), mais
ne sait pas qui joue quoi, et sait que personne ne les suit à 100 % (surtout un humain). Pour chaque
place, elle tient des chances sur des « hypothèses » :
- (convention, fidélité) : le joueur annonce comme cette convention une fois sur fidélité (95 % ou 70 %),
  et le reste du temps comme un joueur ordinaire (le réseau) ;
- « réseau » : il n'en suit aucune, il annonce comme le réseau.

Pendant une donne, la recherche (pimc.py) pèse chaque répartition imaginée des mains cachées par la
probabilité des annonces entendues sous ce mélange. À la fin de chaque donne, toutes les cartes ont été
jouées : on revoit alors chaque annonce avec la vraie main de chacun, et les chances de chaque
hypothèse se mettent à jour (règle de Bayes). Un peu d'oubli à chaque donne les ramène vers le départ,
pour qu'aucune ne devienne certaine et qu'un joueur qui change de façon de faire soit suivi.
"""
import copy

import numpy as np
import torch

from .asr import AsRBot
from .bots import CoincheBot
from .papi_robert import PapiRobertBot
from .petit_jeu import PetitJeuBot
from .rl_env import CARD_INDEX, OFFSET, bid_to_action

CONVENTIONS = {"simple": CoincheBot, "petitjeu": PetitJeuBot, "papirobert": PapiRobertBot, "asr": AsRBot}
NETWORK = "réseau"
FIDELITIES = (0.95, 0.7)


class AuctionStep:
    """Une annonce entendue : la place, l'annonce, si c'était une coinche à la volée (hors de son tour),
    la partie telle qu'elle était juste avant (sans aucune main), et l'observation du réseau sans la main."""

    def __init__(self, seat, bid, volley, game, obs, mask):
        self.seat, self.bid, self.volley = seat, bid, volley
        self.action = bid_to_action(bid)
        self.game, self.obs, self.mask = game, obs, mask


def auction_steps(env, me=None, totals=None):
    """Annonces de la donne en cours, sauf celles de me. Ne dépend que de ce qui est public (les mains
    sont retirées des copies). totals : les scores au moment des annonces (par défaut ceux de la partie)."""
    game = env.game
    view = copy.copy(env)
    contract, passes, coinche_seat = None, 0, None
    turn = (game.dealer + 1) % 4
    steps = []
    for k, (seat, bid) in enumerate(game.bids):
        if seat != me:
            g = copy.copy(game)
            g.phase, g.tricks, g.trick, g.trump, g.result, g.belote_seat = "bidding", [], [], None, None, None
            g.played = [[] for _ in range(4)]
            g.hands = [[] for _ in range(4)]
            g.dealt = [[] for _ in range(4)]
            g.bids = game.bids[:k]
            g.contract = dict(contract) if contract is not None else None
            g.passes, g.coinche_seat, g.current = passes, coinche_seat, seat
            if totals is not None:
                g.totals = list(totals)
            view.game = g
            steps.append(AuctionStep(seat, bid, seat != turn, g, view._observe(), view.legal_mask()))
        if bid[0] == "pass":
            passes += 1
        elif bid[0] == "bid":
            contract = {"seat": seat, "value": bid[1], "suit": bid[2], "mult": 1}
            passes = 0
        elif bid[0] == "coinche":
            contract["mult"] = 2
            coinche_seat, passes = seat, 0
        elif bid[0] == "surcoinche":
            contract["mult"] = 3
        turn = (seat + 1) % 4
    return steps


def network_probs(network, steps, hands, temperature):
    """[C, S] : probabilité (adoucie par temperature) que le réseau fasse chaque annonce entendue, avec les
    mains de chaque candidate (hands[c][place] = les 8 cartes données)."""
    obs = np.stack([st.obs for st in steps] * len(hands))
    for c, h in enumerate(hands):
        for j, st in enumerate(steps):
            obs[c * len(steps) + j, [OFFSET["hand"] + CARD_INDEX[card] for card in h[st.seat]]] = 1
    masks = torch.as_tensor(np.stack([st.mask for st in steps] * len(hands)))
    actions = torch.as_tensor([st.action for st in steps] * len(hands))
    with torch.no_grad():
        logits, _ = network(torch.as_tensor(obs))
        logp = torch.log_softmax((logits / temperature).masked_fill(~masks, float("-inf")), dim=-1)
    return logp.gather(1, actions[:, None])[:, 0].exp().view(len(hands), len(steps)).numpy()


def convention_matches(bots, steps, hands):
    """[C, S, K] : 1 si la convention k aurait fait l'annonce entendue avec la main de la candidate."""
    out = np.zeros((len(hands), len(steps), len(bots)))
    for j, st in enumerate(steps):
        g = st.game
        for c, h in enumerate(hands):
            hand = list(h[st.seat])
            g.hands[st.seat], g.dealt[st.seat] = hand, hand
            for k, bot in enumerate(bots):
                if st.volley:
                    out[c, j, k] = bool(getattr(bot, "volley_coinche", None) and bot.volley_coinche(g, st.seat))
                else:
                    out[c, j, k] = bot.bid(g, st.seat) == st.bid
        g.hands[st.seat], g.dealt[st.seat] = [], []
    return out


class ConventionTracker:
    """Chances de chaque hypothèse (convention, fidélité) pour chacune des 4 places, apprises donne après
    donne. conventions : noms de CONVENTIONS ; [] : seulement le réseau (comme avant ce module)."""

    def __init__(self, network, conventions=tuple(CONVENTIONS), fidelities=FIDELITIES, temperature=2.0,
                 forget=0.05):
        self.network = network
        self.names = list(conventions)
        self.bots = [CONVENTIONS[n]() for n in self.names]
        self.hyps = [(n, f) for n in self.names for f in fidelities] + [(NETWORK, 0.0)]
        self.temperature = temperature
        self.forget = forget
        # départ : chaque convention (et le réseau) a la même chance, partagée entre ses fidélités
        share = 1.0 / (len(self.names) + 1)
        self.prior = np.array([share / len(fidelities)] * (len(self.hyps) - 1) + [share])
        self.reset()

    def reset(self):
        """Nouvelle partie (nouveaux joueurs) : retour aux chances de départ."""
        self.post = np.tile(self.prior, (4, 1))

    def log_likelihoods(self, steps, hands):
        """[C, 4, H] : log de la probabilité des annonces de chaque place, sous chaque hypothèse, pour
        chaque candidate (0 pour une place qui n'a rien annoncé)."""
        out = np.zeros((len(hands), 4, len(self.hyps)))
        if not steps or not hands:
            return out
        p_net = network_probs(self.network, steps, hands, self.temperature)                  # [C, S]
        match = convention_matches(self.bots, steps, hands) if self.bots else None            # [C, S, K]
        seats = np.array([st.seat for st in steps])
        for h, (name, fidelity) in enumerate(self.hyps):
            if name == NETWORK:
                p = p_net
            else:
                p = fidelity * match[:, :, self.names.index(name)] + (1 - fidelity) * p_net
            logp = np.log(np.maximum(p, 1e-12))
            for s in range(4):
                out[:, s, h] = logp[:, seats == s].sum(axis=1)
        return out

    def log_weights(self, env, me, hands):
        """Pour chaque candidate (hands[c][place] = les 8 cartes données aux autres places), log de la
        probabilité des annonces entendues, mélangée selon les chances de chaque hypothèse."""
        ll = self.log_likelihoods(auction_steps(env, me), hands)
        mixed = ll + np.log(self.post)[None]
        top = mixed.max(axis=2, keepdims=True)
        return (top[:, :, 0] + np.log(np.exp(mixed - top).sum(axis=2))).sum(axis=1)

    def end_deal(self, env, hands, totals=None):
        """Donne finie : hands[place] = les 8 cartes de chacun (toutes ont été jouées, donc publiques).
        Met à jour les chances de chaque hypothèse pour chaque place."""
        ll = self.log_likelihoods(auction_steps(env, None, totals), [hands])[0]             # [4, H]
        log_post = np.log(self.post) + ll
        log_post -= log_post.max(axis=1, keepdims=True)
        post = np.exp(log_post)
        post /= post.sum(axis=1, keepdims=True)
        self.post = (1 - self.forget) * post + self.forget * self.prior

    def beliefs(self, seat):
        """{convention: chance} pour une place (fidélités additionnées), de la plus probable à la moins."""
        out = {}
        for (name, _f), p in zip(self.hyps, self.post[seat]):
            out[name] = out.get(name, 0.0) + float(p)
        return dict(sorted(out.items(), key=lambda kv: -kv[1]))
