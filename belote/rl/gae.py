def compute_gae(episode_transitions, gamma: float = 1.0, lam: float = 1.0) -> None:
    """Calcule advantage/return (GAE) pour les transitions d'UNE manche, en place.

    episode_transitions doit être l'ordre chronologique complet d'une manche
    (16 transitions, telles que retournées par self_play.collect_episode) :
    la manche se termine toujours proprement, donc le seul bootstrap à zéro a
    lieu après la dernière transition de chaque joueur. Appeler cette fonction
    séparément pour chaque manche d'un rollout, jamais sur un buffer de
    plusieurs manches concaténées, pour ne pas faire fuiter le bootstrap
    d'une manche sur l'autre.

    En self-play, les transitions des deux sièges sont entrelacées dans la
    liste. Le calcul est fait séparément sur la sous-suite de chaque siège
    (transition.player) : le return d'un coup ne doit sommer que les rewards
    du joueur qui l'a joué, et le bootstrap doit utiliser la value de SON
    prochain coup (même perspective), jamais celle du coup adverse. Mélanger
    les deux sommerait les points des deux joueurs, ce qui efface le signal
    "qui gagne les points" dans un jeu à somme nulle.
    """
    for player in {t.player for t in episode_transitions}:
        player_transitions = [t for t in episode_transitions if t.player == player]
        _compute_gae_single_player(player_transitions, gamma, lam)


def _compute_gae_single_player(transitions, gamma: float, lam: float) -> None:
    """GAE classique sur la suite chronologique des coups d'un seul joueur."""
    next_value = 0.0
    next_advantage = 0.0

    for transition in reversed(transitions):
        delta = transition.reward + gamma * next_value - transition.value
        advantage = delta + gamma * lam * next_advantage

        transition.advantage = advantage
        transition.return_ = advantage + transition.value

        next_value = transition.value
        next_advantage = advantage
