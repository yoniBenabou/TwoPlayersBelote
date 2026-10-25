# TwoPlayersBelote

A two-player Belote card game, playable from the command line (CLI), written in Python.

This variant is played with 16 cards (8 per player) drawn from a 32-card deck; the trump suit is drawn at random each round.

## Project status

The tag `projet-tout-fonctionne-avant-atout` marks the last validated version before trump bidding was added: all tests pass, and the best agent ([models/ppo_CA_3M.pt](models/ppo_CA_3M.pt)) wins 83% of its 501-point games against Random and 62% against TrumpCount, a result reproduced over 3 training runs. To go back to it: `git checkout projet-tout-fonctionne-avant-atout`.

## Running the game

```bash
python main.py
```

The game asks for both players' names, then the target score to win the game (501 points by default). On each turn, the active player picks a card by typing its number in the displayed list.

### Playing against the trained agent

```bash
python -m scripts.play_vs_agent --name Noa
```

The agent uses the best trained model ([models/ppo_CA_3M.pt](models/ppo_CA_3M.pt): self-play, 3 million games). Its hand stays hidden; `--reveal` shows it (handy for a demo), `--target` changes the score to reach, and `q` quits the game.

**Web version with real cards** (English text, for presentations):

```bash
python -m demo.server
```

Then open the address shown (`http://localhost:8000`, or the next free port if 8000 is taken). On the Technion machine, the VS Code **Ports** tab forwards this port to your browser. Click a card to play it (only legal cards are clickable); "Show agent's hand" reveals the agent's hand, and each of the agent's moves shows its confidence.

## Main rules

- Each round deals 8 cards per player (16 cards are left unused).
- The trump suit is chosen at random at the start of each round.
- You must follow the suit led, trump if you cannot follow suit, and play a higher trump if trump is led and you can.
- Card values: standard for non-trump suits (Ace=11, 10=10, King=4, Queen=3, Jack=2), specific for trump (Jack=20, 9=14, Ace=11, 10=10, King=4, Queen=3).
- End-of-round bonuses: +10 points for the last trick ("dix de der"), +20 points for Belote-Rebelote (King + Queen of trump in the dealt hand).
- The game ends as soon as a player reaches the target score.

## Project structure

- [main.py](main.py) — entry point, launches the CLI.
- [belote/core/](belote/core/) — game engine: cards ([cards.py](belote/core/cards.py)), rules ([engine.py](belote/core/engine.py)), player ([player.py](belote/core/player.py)), CLI ([cli.py](belote/core/cli.py)).
- [belote/rl/](belote/rl/) — reinforcement learning: Gym environment ([env.py](belote/rl/env.py)), baseline agents ([agents.py](belote/rl/agents.py)), network and PPO (`networks.py`, `ppo_agent.py`, `self_play.py`, `gae.py`, `ppo_loss.py`, `ppo_update.py`), evaluation ([evaluation.py](belote/rl/evaluation.py)).
- [scripts/](scripts/) — training, evaluation, game visualization and learning curves.
- [tests/](tests/) — tests for the environment and for each PPO component.
- [figures/](figures/) — learning curves from the long training run (3 million games).
- [models/](models/) — best trained agent, used by `scripts/play_vs_agent.py`.

## Installation

```bash
pip install -r requirements.txt
```

## Running scripts and tests

Always from the project root, in module mode (`-m`).

**Training** ([scripts/train.py](scripts/train.py)). With no options, it uses the best configuration found: self-play, reward without win bonus, learning rate 3e-4, 2 million games, evaluation every 50,000 games.

```bash
python -m scripts.train --out-dir experiments/my_run --seed 1
```

Options: `--total-games`, `--eval-every`, `--lr`, `--entropy-coef`, `--win-bonus` (adds the ±1 win term to the reward), `--vs-heuristics` (heuristic opponents instead of self-play), `--belief` (table of cards the opponent may hold), `--bidding` (trump bidding, see below), `--init-from` (warm start from an already trained model), `--seed`, `--out-dir` (where to write `checkpoints/`, TensorBoard `runs/`, `config.json`). The evaluation log is printed to standard output: redirect it to a `train.log` to plot the curves.

**Trump bidding (`--bidding`)**: a card drawn from the 16 undealt cards is turned face up and proposes its suit. Round 1: take or pass; round 2: name one of the 3 other suits or pass; if both players pass twice, the cards are redealt. The first player to speak leads the first trick. If the taker scores fewer points than the opponent, they are "dedans" (set): the opponent scores all trick points (each player keeps their own Belote-Rebelote).

```bash
python -m scripts.train --bidding --init-from models/ppo_CA_3M.pt --out-dir experiments/bidding --seed 1
```

**Long training runs: resuming, safeguard and monitoring**

- At each evaluation, `checkpoints/resume_state.pt` saves the full state (weights, Adam optimizer, counters, random generators). An interrupted run resumes exactly where it left off with `python -m scripts.train --resume --out-dir experiments/my_run` (the configuration is read back from `config.json`).
- If an update produces non-finite weights (NaN), training stops immediately and writes `nan_dump.pt`: the state just before the faulty update and the matching rollout, so it can be replayed.
- `scripts/watchdog.py` monitors tmux training sessions and restarts with `--resume` any that have died or stalled (at most 3 restarts, logged to `watchdog.log`):

```bash
tmux new-session -d -s watchdog "python -m scripts.watchdog experiments/run1:session1 experiments/run2:session2"
```

**Evaluation and analysis:**

```bash
python -m scripts.benchmark
python -m scripts.plot_training experiments/my_run/train.log --out-dir figures --prefix my_run_
python -m scripts.compare_checkpoints experiments/my_run/checkpoints
python -m scripts.watch_self_play_game --checkpoint experiments/my_run/checkpoints/ppo_2000000.pt --opponent trumpcount --duplicate --seed 138
```

- `benchmark`: baseline agents against each other.
- `plot_training`: point-difference and win-rate curves against the 4 opponents.
- `compare_checkpoints`: final agent against its earlier versions.
- `evaluate_full_games`: win rate over full games (first to 501 points), with duplicate deals.
- `oracle`: theoretical ceiling, a player who sees the opponent's hand against Random (`--mode round` or `--mode game`).
- `watch_self_play_game`: detailed games, trick by trick (`--opponent self|random|heuristic|voidexploit|trumpcount`, `--duplicate` replays the deal with the hands swapped).

All evaluations use **duplicate deals**: each deal is played twice with the hands swapped, which cancels out the luck of the deal.

**Tests:**

```bash
python -m tests.test_env
```

(likewise for `test_network`, `test_ppo_agent`, `test_self_play`, `test_gae`, `test_ppo_loss`, `test_ppo_update`, `test_bidding`, `test_train_safety`)
