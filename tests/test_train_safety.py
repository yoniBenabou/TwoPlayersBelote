import contextlib
import os
import sys
import tempfile

import torch

import scripts.train as train_module
from scripts.watchdog import decide

SMALL = {"rollout_episodes": 16, "eval_every_n_games": 32, "seed": 3}


def fake_evaluation_suite(agent):
    """Remplace l'évaluation (~2200 parties) pour garder les tests rapides."""
    return {"Stub": {"win_rate": 0.5, "win_rate_ci95": 0.0, "avg_point_diff": 0.0, "avg_point_diff_ci95": 0.0}}


@contextlib.contextmanager
def in_temp_dir():
    previous = os.getcwd()
    with tempfile.TemporaryDirectory() as d:
        os.chdir(d)
        try:
            yield d
        finally:
            os.chdir(previous)


@contextlib.contextmanager
def patched(name, value):
    original = getattr(train_module, name)
    setattr(train_module, name, value)
    try:
        yield
    finally:
        setattr(train_module, name, original)


def final_weights():
    return torch.load(os.path.join("checkpoints", "ppo_0000064.pt"))


def check_resume_is_exact():
    """Interrompu à 32 parties puis repris jusqu'à 64 = exactement les mêmes
    poids qu'un entraînement de 64 parties d'une traite (poids, Adam,
    compteurs et générateurs aléatoires restaurés)."""
    with patched("run_evaluation_suite", fake_evaluation_suite):
        with in_temp_dir():
            train_module.train(total_games=64, **SMALL)
            straight = final_weights()
        with in_temp_dir():
            train_module.train(total_games=32, **SMALL)
            assert os.path.exists(train_module.RESUME_FILE)
            state = torch.load(train_module.RESUME_FILE, weights_only=False)
            assert state["games_trained"] == 32 and "optimizer" in state and "rng" in state
            # La reprise ne doit refaire que les mises à jour de 32 à 64 parties
            # (sinon une reprise "ratée" qui recommencerait de zéro avec la même
            # graine donnerait aussi les mêmes poids).
            real_update, calls = train_module.ppo_update, {"n": 0}

            def counting_update(*args, **kwargs):
                calls["n"] += 1
                return real_update(*args, **kwargs)

            with patched("ppo_update", counting_update):
                train_module.train(total_games=64, resume=True, **SMALL)
            assert calls["n"] == (64 - 32) // SMALL["rollout_episodes"], calls["n"]
            resumed = final_weights()
    for key in straight:
        assert torch.equal(straight[key], resumed[key]), f"poids différents après reprise : {key}"


def check_nan_guard_stops_with_dump():
    """Si une mise à jour rend les poids NaN, l'entraînement s'arrête net et
    sauvegarde l'état d'avant (fini) et le rollout fautif."""
    real_update = train_module.ppo_update
    calls = {"n": 0}

    def poisoned_update(agent, optimizer, buffer, **kwargs):
        metrics = real_update(agent, optimizer, buffer, **kwargs)
        calls["n"] += 1
        if calls["n"] == 2:
            with torch.no_grad():
                agent.network.value_head.bias.fill_(float("nan"))
        return metrics

    with patched("run_evaluation_suite", fake_evaluation_suite), patched("ppo_update", poisoned_update):
        with in_temp_dir():
            try:
                train_module.train(total_games=128, **SMALL)
                raise AssertionError("l'entraînement aurait dû s'arrêter")
            except train_module.NonFiniteTrainingError:
                pass
            dump = torch.load(train_module.NAN_DUMP_FILE, weights_only=False)
            assert dump["games_trained"] == 16, dump["games_trained"]
            assert len(dump["buffer"]) > 0
            assert all(torch.isfinite(v).all() for v in dump["network_before"].values())
            assert not os.path.exists(os.path.join("checkpoints", "ppo_0000032.pt")), "aucun checkpoint après le NaN"


def check_watchdog_decisions():
    common = {"stall_minutes": 60, "max_restarts": 3}
    assert decide(True, False, 5, 0, True, **common) == "done"
    assert decide(False, True, 5, 0, True, **common) == "ok"
    assert decide(False, False, 5, 0, True, **common) == "restart"
    assert decide(False, True, 90, 0, True, **common) == "kill_restart"
    assert decide(False, False, 5, 3, True, **common) == "give_up"
    assert decide(False, False, 5, 0, False, **common) == "give_up", "sans état de reprise, rien à relancer"


def main():
    check_resume_is_exact()
    print("Reprise (--resume) : mêmes poids qu'un entraînement d'une traite : OK")

    check_nan_guard_stops_with_dump()
    print("Garde-fou NaN : arrêt net + état d'avant et rollout fautif sauvegardés : OK")

    check_watchdog_decisions()
    print("Surveillance : décisions (terminé, actif, relance, bloqué, abandon) : OK")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
