# Commented deals: the PPO agent with bidding against TrumpCount

Deals drawn from the 20,000 analysed in `scripts.strategy_analysis` (`python -m scripts.commented_games` regenerates this file). The agent never sees its opponent's hand; it is shown here to explain the play.

### 1. Passing in round 1 to choose a better trump in round 2

The turned suit (hearts) is worth 41 in the agent's hand, above the heuristic threshold (40), yet the agent passes: its diamonds are worth 60. In round 2 it names that suit. Over 20,000 deals, with a turned suit worth 40+, it takes only 54% of the time when another suit is clearly stronger, against 85% otherwise.

- Agent's hand: A♦ 9♦ J♦ 9♠ J♥ A♥ J♣ K♣
- TrumpCount's hand (hidden from the agent): 8♠ Q♠ K♠ A♠ K♥ 7♣ 8♣ A♣
- Turned card: 7♥; the agent speaks first.
- Bidding: Agent (round 1): pass; TrumpCount (round 1): pass; Agent (round 2): names diamonds ♦. Trump: diamonds ♦.

| Trick | Lead | Reply | Winner | Points | Note |
|---|---|---|---|---|---|
| 1 | **Agent** J♦ | TrumpCount 7♣ | Agent | 20 |  |
| 2 | **Agent** A♥ | TrumpCount K♥ | Agent | 15 |  |
| 3 | **Agent** K♣ | TrumpCount A♣ | TrumpCount | 15 |  |
| 4 | TrumpCount A♠ | **Agent** 9♠ | TrumpCount | 11 |  |
| 5 | TrumpCount K♠ | **Agent** A♦ | Agent | 15 |  |
| 6 | **Agent** J♣ | TrumpCount 8♣ | Agent | 2 |  |
| 7 | **Agent** J♥ | TrumpCount 8♠ | Agent | 2 |  |
| 8 | **Agent** 9♦ | TrumpCount Q♠ | Agent | 27 |  |

Final: agent 81 – TrumpCount 26.

### 2. A light take as second speaker

Trump strength only 28 (the heuristic needs 40), but the opponent has just passed, which says its hand is weak in that suit. As second speaker the agent takes 40% of hands of strength 20-29, against 9% when it speaks first.

- Agent's hand: K♦ 9♦ Q♠ K♠ 9♥ A♥ J♣ Q♣
- TrumpCount's hand (hidden from the agent): Q♦ 8♠ 9♠ 7♥ 8♥ Q♥ K♣ 10♣
- Turned card: 10♦; TrumpCount speaks first.
- Bidding: TrumpCount (round 1): pass; Agent (round 1): takes diamonds ♦. Trump: diamonds ♦.

| Trick | Lead | Reply | Winner | Points | Note |
|---|---|---|---|---|---|
| 1 | TrumpCount Q♥ | **Agent** A♥ | Agent | 14 |  |
| 2 | **Agent** 9♥ | TrumpCount 7♥ | Agent | 0 |  |
| 3 | **Agent** K♠ | TrumpCount 8♠ | Agent | 4 |  |
| 4 | **Agent** Q♠ | TrumpCount 9♠ | Agent | 3 |  |
| 5 | **Agent** Q♣ | TrumpCount K♣ | TrumpCount | 7 |  |
| 6 | TrumpCount 8♥ | **Agent** K♦ | Agent | 4 |  |
| 7 | **Agent** J♣ | TrumpCount 10♣ | TrumpCount | 12 |  |
| 8 | TrumpCount Q♦ | **Agent** 9♦ | Agent | 27 |  |

Final: agent 52 – TrumpCount 19.

### 3. The taker draws trumps

As taker, the agent leads trump early while the opponent still holds some, so its long suits are safe afterwards. As taker it leads trump 31% of the time, as defender 6%.

- Agent's hand: 8♣ Q♣ K♣ 9♣ J♣ J♠ 8♥ A♦
- TrumpCount's hand (hidden from the agent): 10♣ A♣ 7♠ K♠ A♠ 9♥ 10♥ K♦
- Turned card: 10♠; the agent speaks first.
- Bidding: Agent (round 1): pass; TrumpCount (round 1): pass; Agent (round 2): names clubs ♣. Trump: clubs ♣.

| Trick | Lead | Reply | Winner | Points | Note |
|---|---|---|---|---|---|
| 1 | **Agent** J♣ | TrumpCount 10♣ | Agent | 30 | trump lead |
| 2 | **Agent** 8♣ | TrumpCount A♣ | TrumpCount | 11 | trump lead |
| 3 | TrumpCount A♠ | **Agent** J♠ | TrumpCount | 13 |  |
| 4 | TrumpCount K♠ | **Agent** Q♣ | Agent | 7 |  |
| 5 | **Agent** 8♥ | TrumpCount 9♥ | TrumpCount | 0 |  |
| 6 | TrumpCount 7♠ | **Agent** K♣ | Agent | 4 |  |
| 7 | **Agent** A♦ | TrumpCount K♦ | Agent | 15 |  |
| 8 | **Agent** 9♣ | TrumpCount 10♥ | Agent | 34 |  |

Final: agent 110 – TrumpCount 24.

### 4. Keeping the master trump for the last trick

At trick 7 the agent holds a side card and the master trump: it plays the side card first and keeps the trump to win the last trick and its 10-point bonus (it does so in 99% of such positions; TrumpCount 53%). It wins the last trick in 73% of deals, against 50% for TrumpCount on the same deals.

- Agent's hand: 7♥ 9♥ J♥ J♠ 10♠ 9♦ J♦ 7♣
- TrumpCount's hand (hidden from the agent): Q♥ 8♠ Q♠ K♠ A♠ 7♦ K♦ J♣
- Turned card: 9♣; the agent speaks first.
- Bidding: Agent (round 1): pass; TrumpCount (round 1): pass; Agent (round 2): names hearts ♥. Trump: hearts ♥.

| Trick | Lead | Reply | Winner | Points | Note |
|---|---|---|---|---|---|
| 1 | **Agent** 9♦ | TrumpCount K♦ | TrumpCount | 4 |  |
| 2 | TrumpCount A♠ | **Agent** J♠ | TrumpCount | 13 |  |
| 3 | TrumpCount K♠ | **Agent** 10♠ | Agent | 14 |  |
| 4 | **Agent** J♦ | TrumpCount 7♦ | Agent | 2 |  |
| 5 | **Agent** 7♥ | TrumpCount Q♥ | TrumpCount | 3 |  |
| 6 | TrumpCount Q♠ | **Agent** 9♥ | Agent | 17 |  |
| 7 | **Agent** 7♣ | TrumpCount J♣ | TrumpCount | 2 | side card first |
| 8 | TrumpCount 8♠ | **Agent** J♥ | Agent | 30 | master trump: last trick +10 |

Final: agent 63 – TrumpCount 22.

### 5. Leading a 10 without having seen the Ace

The agent leads a 10 although the Ace of that suit has not appeared. It is a bet: with 16 cards never dealt, the opponent holds that Ace only 11% of the time, and the agent wins 76% of those tricks.

- Agent's hand: K♣ 9♣ 9♠ Q♠ K♠ 7♥ 10♥ A♦
- TrumpCount's hand (hidden from the agent): 10♣ J♣ 7♠ 8♠ J♠ 8♥ J♥ Q♦
- Turned card: 8♣; the agent speaks first.
- Bidding: Agent (round 1): pass; TrumpCount (round 1): takes clubs ♣. Trump: clubs ♣.

| Trick | Lead | Reply | Winner | Points | Note |
|---|---|---|---|---|---|
| 1 | **Agent** 9♠ | TrumpCount J♠ | TrumpCount | 2 |  |
| 2 | TrumpCount 8♠ | **Agent** K♠ | Agent | 4 |  |
| 3 | **Agent** Q♠ | TrumpCount 7♠ | Agent | 3 |  |
| 4 | **Agent** A♦ | TrumpCount Q♦ | Agent | 14 |  |
| 5 | **Agent** 10♥ | TrumpCount 8♥ | Agent | 10 | 10 led, Ace unseen |
| 6 | **Agent** 7♥ | TrumpCount J♥ | TrumpCount | 2 |  |
| 7 | TrumpCount J♣ | **Agent** K♣ | TrumpCount | 24 |  |
| 8 | TrumpCount 10♣ | **Agent** 9♣ | Agent | 34 |  |

Final: agent 93 – TrumpCount 0 (TrumpCount took and was set: “dedans”).

### 6. A weakness: throwing away an Ace or a 10 on a trump lead

As defender with no trump left, the agent answers the taker's trump lead with 10♦ although it holds 7♦ (0 points). Replaying the deal with 7♦ instead (everything else identical) changes the round margin by +24 points in the agent's favour. Over all such positions the measured cost is about 17 points each time (~1,000 cases in 20,000 deals): the clearest mistake found, and a target for search at play time.

- Agent's hand: 10♠ 9♥ J♥ 7♦ 10♦ 8♣ K♣ A♣
- TrumpCount's hand (hidden from the agent): K♠ A♠ 9♠ 8♥ A♥ J♦ Q♦ Q♣
- Turned card: 9♦; TrumpCount speaks first.
- Bidding: TrumpCount (round 1): pass; Agent (round 1): pass; TrumpCount (round 2): names spades ♠. Trump: spades ♠.

| Trick | Lead | Reply | Winner | Points | Note |
|---|---|---|---|---|---|
| 1 | TrumpCount A♥ | **Agent** 9♥ | TrumpCount | 11 |  |
| 2 | TrumpCount A♠ | **Agent** 10♠ | TrumpCount | 21 |  |
| 3 | TrumpCount 9♠ | **Agent** 10♦ | TrumpCount | 24 | discards 10♦ instead of 7♦ |
| 4 | TrumpCount Q♦ | **Agent** 7♦ | TrumpCount | 3 |  |
| 5 | TrumpCount K♠ | **Agent** J♥ | TrumpCount | 6 |  |
| 6 | TrumpCount 8♥ | **Agent** 8♣ | TrumpCount | 0 |  |
| 7 | TrumpCount J♦ | **Agent** A♣ | TrumpCount | 13 |  |
| 8 | TrumpCount Q♣ | **Agent** K♣ | Agent | 17 |  |

Final: agent 17 – TrumpCount 78.
