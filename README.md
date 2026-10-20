# TwoPlayersBelote

Un jeu de Belote à deux joueurs, jouable en ligne de commande (CLI) en Python.

Cette variante se joue avec 16 cartes (8 par joueur) tirées d'un jeu de 32 cartes ; l'atout est tiré aléatoirement à chaque manche.

## Lancer le jeu

```bash
python main.py
```

Le jeu demande le nom des deux joueurs, puis le score cible pour gagner la partie (501 points par défaut). À chaque tour, le joueur actif choisit une carte en indiquant son numéro dans la liste affichée.

## Règles principales

- Chaque manche distribue 8 cartes par joueur (16 cartes restent inutilisées).
- L'atout est choisi aléatoirement au début de chaque manche.
- Il faut respecter la couleur demandée, couper à l'atout si on n'a pas la couleur, et monter à l'atout si l'atout est demandé et qu'on le peut.
- Valeurs des cartes : classiques hors atout (As=11, 10=10, Roi=4, Dame=3, Valet=2), spécifiques à l'atout (Valet=20, 9=14, As=11, 10=10, Roi=4, Dame=3).
- Bonus de fin de manche : +10 points pour le dernier pli ("dix de der"), +20 points pour la Belote-Rebelote (Roi + Dame d'atout dans la main distribuée).
- La partie se termine dès qu'un joueur atteint le score cible.

## Structure du projet

- [main.py](main.py) — point d'entrée, lance la CLI.
- [belote/core/](belote/core/) — moteur du jeu : cartes ([cards.py](belote/core/cards.py)), règles ([engine.py](belote/core/engine.py)), joueur ([player.py](belote/core/player.py)), CLI ([cli.py](belote/core/cli.py)).
- [belote/rl/](belote/rl/) — apprentissage par renforcement : environnement Gym ([env.py](belote/rl/env.py)), agents de référence ([agents.py](belote/rl/agents.py)), réseau et PPO (`networks.py`, `ppo_agent.py`, `self_play.py`, `gae.py`, `ppo_loss.py`, `ppo_update.py`), évaluation ([evaluation.py](belote/rl/evaluation.py)).
- [scripts/](scripts/) — entraînement, benchmark, smoke test, visualisation de parties.
- [tests/](tests/) — tests de l'environnement et de chaque brique PPO.

## Lancer les scripts et les tests

Toujours depuis la racine du projet, en mode module (`-m`) :

```bash
python -m scripts.train
python -m scripts.benchmark
python -m tests.test_env
```
