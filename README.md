# Uno Stacking Simulator

Monte Carlo simulation code behind the humandecoded Uno video: a mistakes
tournament with stacking ON vs OFF as the headline.

## What was tested

- 4 players, race to 500 points (round points from losers' hands: numbers at
  face value, action cards 20, Wild / Wild Draw Four 50).
- Classic 108-card deck, 7 cards dealt, 1,000 turns/round and 50 rounds/match
  caps (zero capped rounds/matches in every run below).
- Stacking, where used, is same-symbol only: Draw Two on Draw Two, Draw Four
  on Draw Four, as a house rule. The official classic rules do not allow
  stacking.
- Challenges OFF in the main runs, except the always-correct challenge arm,
  which is the enforcement bound. Bots never forget to say Uno, and no bot
  peeks at another player's hand.

## Headline results (match win rate, 95% CI, 50,000 matches per test)

| Test | Win rate |
|---|---|
| Wrong-Colour (extreme, least-held colour — an upper bound) | 3.52% [3.36, 3.68] |
| Random | 4.59% [4.41, 4.77] |
| True Bluffer, always-correct challenge | 9.81% [9.55, 10.07] |
| True Bluffer, unchallenged | 14.73% [14.42, 15.04] |
| Wild-Spender | 14.86% [14.55, 15.18] |
| Draw-Keeper | 21.48% [21.12, 21.84] |
| Sensible baseline | 24.77% [24.39, 25.14] |
| True Revenge-Saver | 27.29% [26.90, 27.68] |
| Action-Dumper (action cards first) | 30.31% [29.91, 30.71] |
| Lone Stacker vs 3 Passers, stacking ON | 31.97% [31.56, 32.38] |
| Same Stacker forced to take penalties, stacking OFF | 25.19% [24.81, 25.57] |
| Refuser at an all-stacking table | 16.83% [16.50, 17.15] |
| Action-Dumper policy at an all-stacking table (Combo) | 28.46% [28.07, 28.86] |

Symmetric stacking (four identical Sensible players): 25.36% ON vs 25.09%
OFF — no win-rate effect, as expected. Game length: 500 turns/match OFF vs
498 ON (means). Comebacks (eventual round winner had trailed by 10+ cards):
2.00% OFF vs 3.37% ON.

Totals quoted in the video: 750,000 matches, more than five million rounds
(10 quoted production arms + confirmation + new arms). All runs including
two superseded production arms: 900,000 matches, more than seven million
rounds.

## Correction notice

Two production arms originally labelled "Bluffer" and "Revenge-Saver" did
not measure bluffing or revenge timing (the Bluffer only played Draw Four
when no non-wild card was playable, so it was always legal; the
Revenge-Saver never read opponent hand sizes). They are NOT quoted in the
video and are excluded from the quoted totals. The bluffing and revenge
figures above come from corrected confirmation runs.

## Files

- `engine.py` — Uno engine (deck, rules, bots, stacking).
- `validate.py` — validation gates (deck exactness, starting-hand Wild
  probability, seat fairness, symmetric stacking).
- `run_pilot.py`, `run_production.py`, `run_diagnostics.py`,
  `run_confirmation.py`, `run_new_arms.py` — run scripts.
- `*_results.json` — result files for each run (pilot, production,
  diagnostics, confirmation, new arms).

## Running

```bash
python3 validate.py
python3 run_production.py   # 50,000 matches per arm; takes tens of minutes
```

Pure Python, no third-party dependencies.
