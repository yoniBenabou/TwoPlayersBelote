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

By default the demo uses the agent trained with trump bidding ([models/ppo_bidding_2M.pt](models/ppo_bidding_2M.pt)): each round starts with the turned card in the middle of the table and the buttons "Take ♠ / Pass" (round 1) or "♥ ♦ ♣ / Pass" (round 2); the taker is shown next to their hand, in the header and in the Contract panel, and the Rounds table records who took and who was set ("dedans"). `--checkpoint models/ppo_CA_3M.pt` brings back the version without bidding (random trump).

**Games against humans (study).** Each browser gets its own game, so several people can play at the same time; the page asks for the player's name first. Every round (deal, bids, cards, points) and every game (player, score, winner, finished or abandoned) is appended to `demo/logs/games.jsonl` (`--log` to change it; not committed, since it holds players' names). For volunteers, start the server with `--study` (add `--search 50` to play against the strongest agent, the network plus PIMC search over 50 imagined hands, about 0.05 s of thinking per card): the agent's hand is never sent to the browser and the "Show agent's hand" button disappears (outside study mode, a game where the hand was shown is marked and left out of the results). Then:

```bash
python -m scripts.human_results --exclude Noa Yoni
```

gives the agent's win rate against humans with a 95% confidence interval (Wilson), per-player results and per-round statistics, counting only finished games where the agent's hand stayed hidden. Games against the network alone and against the search agent are reported separately (`--search K` keeps a single setting).

**Four-player Coinche (test table)**: you play South with North as your partner, against East and West, all three played by simple rule-based bots (no trained AI yet). The "Rules" button lists the exact rules used, and "Show all hands" reveals the other hands to check them.

```bash
python -m demo4.server
```

Then open `http://localhost:8100`. Engine: [belote/coinche/engine.py](belote/coinche/engine.py) (bidding 80 to 160 or capot, coinche ×2, surcoinche ×3, follow suit, overtrump, free card when your partner is winning, the table's scoring with rounding and the "useful belote" rule, 1,500-point games); tests: `python -m tests.test_coinche`.

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

**Trump bidding (`--bidding`)**: a card drawn from the 16 undealt cards is turned face up and proposes its suit. Round 1: take or pass; round 2: name one of the 3 other suits or pass; if both players pass twice, the cards are redealt. The first player to speak leads the first trick. If the taker scores fewer points than the opponent, they are "dedans" (set): the opponent scores all trick points (each player keeps their own Belote-Rebelote). `--no-dedans` trains without this rule (control experiment; evaluation still applies it).

```bash
python -m scripts.train --bidding --init-from models/ppo_CA_3M.pt --out-dir experiments/bidding --seed 1
```

**Training a four-player AI**: [belote/coinche/rl_env.py](belote/coinche/rl_env.py) wraps the Coinche engine for learning (one deal per episode, each seat sees the table from its own position, with the cards each other player can still hold deduced from the rules; reward at the end of the deal = the team's score minus the other team's, with the real scoring). One network plays all four seats in self-play. By default the bots do the bidding and the network learns the card play; `--bidding` makes the network bid too (75 actions); `--vs-bots-share 0.25` plays a quarter of the deals against a team of bots. Every 50,000 deals it is evaluated against a team of bots, on duplicate deals (each deal played twice, the AI on one side then the other) and in full 1,500-point games. Tests: `python -m tests.test_coinche_env`.

```bash
python -m scripts.train_coinche --out-dir experiments/coinche_play --seed 1 --total-deals 4000000
python -m scripts.train_coinche --out-dir experiments/coinche_bid --seed 1 --total-deals 4000000 --bidding
```

**Larger network (`--hidden-size`)**: size of the two hidden layers (128 by default, as for every model so far). Saved models record their size, so every script reloads them unchanged.

**League of past versions (`--league`)**: instead of pure self-play, half of the rounds (`--self-play-share`) are played against a frozen past version drawn at random from a league: the models given with `--league-init`, then every checkpoint of the run (the 20 most recent, `--league-max`). Past versions sample their moves, as in self-play. It works with `--resume`: the league is rebuilt from the run's checkpoints.

```bash
python -m scripts.train --bidding --league --init-from models/ppo_bidding_2M.pt --league-init <earlier checkpoints .pt> --out-dir experiments/league --seed 4
```

**Exploitability (`--exploit <model.pt>`)**: trains an agent only against that frozen model, which plays as in a real game (its most likely move), to look for hidden weaknesses; every evaluation also reports the margin against it (`Cible`). Starting from the same model (`--init-from`), the exploiter begins at exactly 50%.

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
- `evaluate_full_games`: win rate over full games (first to 501 points), with duplicate deals. `--opponent` also accepts a model, and `heurbid:<model.pt>` gives a model trained without bidding the heuristic bids (e.g. `--opponent heurbid:models/ppo_CA_3M.pt` for the head-to-head against the old agent).
- Strategy study (how the agents play and bid, on the same 20,000 deals against TrumpCount):
  `strategy_collect --subject new|old|old_native|trumpcount|heuristic` records every decision (`--shadow old` also asks the agent without bidding what it would have played in the exact same position); `strategy_analysis` prints the tables (leads, trump management, ruffs, discards, last trick, risky 10s, bidding, taker vs defender) and writes `figures/strategy_*_en.png`; `strategy_counterfactual` replays deals with a different card at one decision to measure what a choice is worth in points; `commented_games` writes [report/commented_games.md](report/commented_games.md).
- `plot_bidding_ablations`: [figures/bidding_ablations_en.png](figures/bidding_ablations_en.png), learning curves of the bidding runs (warm start, from scratch, without the "dedans" rule) and how often each agent takes depending on its hand.
- Search at play time (PIMC, [belote/rl/pimc.py](belote/rl/pimc.py)): before each card, the agent imagines K possible hands for the opponent, consistent with everything public (cards played, turned card, suits the opponent has shown to be void in), finishes the round with the network on both sides for each playable card, and plays the card that scores most on average. Bids stay with the network. Use it anywhere an agent is expected, as `pimc:<model.pt>:K` (e.g. `--agent pimc:models/ppo_bidding_2M.pt:20`); `python -m tests.test_pimc` checks among other things that it never looks at the opponent's real hand. Over 1,000 501-point games (same deals), the network alone wins 81.9% against TrumpCount, 87.1% with K=20 and 87.8% with K=50; head to head against the network alone, search wins 58.8% (K=20) and 63.2% (K=50) of games, for about 0.2 s (K=20) to 0.5 s (K=50) of thinking per round.
- `bidding_stats`: how an agent bids: how often it takes (round 1, round 2), how often it is set ("dedans"), average margin as taker.
- `oracle`: theoretical ceiling, a player who sees the opponent's hand against Random (`--mode round` or `--mode game`).
- `watch_self_play_game`: detailed games, trick by trick (`--opponent self|random|heuristic|voidexploit|trumpcount`, `--duplicate` replays the deal with the hands swapped).

All evaluations use **duplicate deals**: each deal is played twice with the hands swapped, which cancels out the luck of the deal.

**Tests:**

```bash
python -m tests.test_env
```

(likewise for `test_network`, `test_ppo_agent`, `test_self_play`, `test_gae`, `test_ppo_loss`, `test_ppo_update`, `test_bidding`, `test_train_safety`, `test_pimc`)
