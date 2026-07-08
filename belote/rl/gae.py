def compute_gae(episode_transitions, gamma: float = 1.0, lam: float = 1.0) -> None:
    """Calcule advantage/return (GAE) pour les transitions d'UNE manche, en place.

    episode_transitions doit être l'ordre chronologique complet d'une manche
    (16 transitions, telles que retournées par self_play.collect_episode) :
    la manche se termine toujours proprement, donc le seul bootstrap à zéro a
    lieu après la dernière transition de la liste. Appeler cette fonction
    séparément pour chaque manche d'un rollout, jamais sur un buffer de
    plusieurs manches concaténées, pour ne pas faire fuiter le bootstrap
    d'une manche sur l'autre.
    """
    next_value = 0.0
    next_advantage = 0.0

    for transition in reversed(episode_transitions):
        delta = transition.reward + gamma * next_value - transition.value
        advantage = delta + gamma * lam * next_advantage

        transition.advantage = advantage
        transition.return_ = advantage + transition.value

        next_value = transition.value
        next_advantage = advantage
