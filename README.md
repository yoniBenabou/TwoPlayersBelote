# TwoPlayersBelote

Un jeu de Belote à deux joueurs, jouable en ligne de commande (CLI) en Python.

Cette variante se joue avec 16 cartes (8 par joueur) tirées d'un jeu de 32 cartes ; l'atout est tiré aléatoirement à chaque manche.

## État du projet

Le tag `projet-tout-fonctionne-avant-atout` marque la dernière version validée avant l'ajout du choix de l'atout (annonces) : tous les tests passent, et le meilleur agent ([models/ppo_CA_3M.pt](models/ppo_CA_3M.pt)) gagne 83 % de ses parties de 501 points contre Random et 62 % contre TrumpCount, résultat reproduit sur 3 entraînements. Pour y revenir : `git checkout projet-tout-fonctionne-avant-atout`.

## Lancer le jeu

```bash
python main.py
```

Le jeu demande le nom des deux joueurs, puis le score cible pour gagner la partie (501 points par défaut). À chaque tour, le joueur actif choisit une carte en indiquant son numéro dans la liste affichée.

### Jouer contre l'agent entraîné

```bash
python -m scripts.play_vs_agent --name Noa
```

L'agent utilise le meilleur modèle entraîné ([models/ppo_CA_3M.pt](models/ppo_CA_3M.pt) : self-play, 3 millions de parties). Sa main reste cachée ; `--reveal` l'affiche (pratique pour une démo), `--target` change le score à atteindre, `q` quitte la partie.

**Version web avec de vraies cartes** (textes en anglais, pour les présentations) :

```bash
python -m demo.server
```

Puis ouvrir l'adresse affichée (`http://localhost:8000`, ou le port suivant libre si 8000 est pris). Sur la machine du Technion, l'onglet **Ports** de VS Code redirige ce port vers ton navigateur. On clique sur une carte pour la jouer (seules les cartes légales sont cliquables) ; « Show agent's hand » retourne la main de l'agent, et chaque coup de l'agent affiche sa confiance.

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
- [scripts/](scripts/) — entraînement, évaluation, visualisation de parties et courbes.
- [tests/](tests/) — tests de l'environnement et de chaque brique PPO.
- [figures/](figures/) — courbes d'apprentissage de l'entraînement long (3 millions de parties).
- [models/](models/) — meilleur agent entraîné, utilisé par `scripts/play_vs_agent.py`.

## Installation

```bash
pip install -r requirements.txt
```

## Lancer les scripts et les tests

Toujours depuis la racine du projet, en mode module (`-m`).

**Entraînement** ([scripts/train.py](scripts/train.py)). Sans option, utilise la meilleure configuration trouvée : self-play, reward sans bonus de victoire, learning rate 3e-4, 2 millions de parties, évaluation toutes les 50 000 parties.

```bash
python -m scripts.train --out-dir experiments/mon_run --seed 1
```

Options : `--total-games`, `--eval-every`, `--lr`, `--entropy-coef`, `--win-bonus` (ajoute le ±1 de victoire au reward), `--vs-heuristics` (adversaires heuristiques au lieu du self-play), `--belief` (tableau des cartes possibles chez l'adversaire), `--bidding` (annonce de l'atout, voir ci-dessous), `--init-from` (démarrage à chaud depuis un modèle déjà entraîné), `--seed`, `--out-dir` (où écrire `checkpoints/`, `runs/` TensorBoard, `config.json`). Le log d'évaluation s'affiche sur la sortie standard : le rediriger vers un `train.log` pour tracer les courbes.

**Annonce de l'atout (`--bidding`)** : une carte tirée parmi les 16 non distribuées est retournée et propose sa couleur. Tour 1 : prendre ou passer ; tour 2 : nommer une des 3 autres couleurs ou passer ; si les deux passent deux fois, on redistribue. Le premier à parler mène le premier pli. Si le preneur fait moins de points que l'adversaire, il est « dedans » : l'adversaire marque tous les points des plis (chacun garde sa belote-rebelote).

```bash
python -m scripts.train --bidding --init-from models/ppo_CA_3M.pt --out-dir experiments/bidding --seed 1
```

**Évaluation et analyse :**

```bash
python -m scripts.benchmark
python -m scripts.plot_training experiments/mon_run/train.log --out-dir figures --prefix mon_run_
python -m scripts.compare_checkpoints experiments/mon_run/checkpoints
python -m scripts.watch_self_play_game --checkpoint experiments/mon_run/checkpoints/ppo_2000000.pt --opponent trumpcount --duplicate --seed 138
```

- `benchmark` : agents de référence les uns contre les autres.
- `plot_training` : courbes d'écart de points et de taux de victoire contre les 4 adversaires.
- `compare_checkpoints` : agent final contre ses versions précédentes.
- `evaluate_full_games` : taux de victoire en parties complètes (premier à 501 points), parties dupliquées.
- `oracle` : plafond théorique, un joueur qui voit la main adverse contre Random (`--mode round` ou `--mode game`).
- `watch_self_play_game` : parties détaillées pli par pli (`--opponent self|random|heuristic|voidexploit|trumpcount`, `--duplicate` rejoue la donne en échangeant les mains).

Toutes les évaluations utilisent des **donnes dupliquées** : chaque donne est jouée deux fois en échangeant les mains, ce qui annule la chance de la donne.

**Tests :**

```bash
python -m tests.test_env
```

(de même pour `test_network`, `test_ppo_agent`, `test_self_play`, `test_gae`, `test_ppo_loss`, `test_ppo_update`, `test_bidding`)
