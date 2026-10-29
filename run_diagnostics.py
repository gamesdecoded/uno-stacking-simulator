"""DIAGNOSTIC ONLY -- NOT production results.

Purpose: test whether two production arms actually measured what their
names say, after code inspection showed they did not.

1. Bluffer (production): only plays Draw 4 when no non-wild is playable.
   In that case Draw 4 is ALWAYS legal (a colour-matching card would be
   playable), so the production Bluffer never bluffed. True bluffer here:
   play Draw 4 whenever held, even with playable non-wilds, colour =
   most-held. Run with challenge off and with always-challenge.
2. Revenge-Saver (production): code never reads opponent hand sizes, so
   it never saved actions "until target has <=2". It is strict
   numbers-first. True revenge here: numbers first normally; actions
   first when any opponent has <=2 cards.
3. Action-Dumper decomposition: which action type drives the win?
   - skip_reverse_first: Skip/Reverse first, then numbers, Draw 2 last.
   - draw2_first: Draw 2 first, then numbers, Skip/Reverse last.

20,000 matches per arm, new seeds 60000+. Labelled diagnostic, do not
quote as production totals.
"""
import json
import math
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import Bot, run_arm, playable, DRAW4, DRAW2, SKIP, REVERSE, is_wild
from collections import Counter


class TrueBluffer(Bot):
    def __init__(self):
        super().__init__("sensible", "always")

    def choose(self, hand, top, active_colour, ctx, rng):
        options = [c for c in hand if playable(c, top, active_colour)]
        if not options:
            return None
        for c in options:
            if len(hand) == 1:
                return c
        for c in options:
            if c[1] == DRAW4:
                return c
        return super().choose(hand, top, active_colour, ctx, rng)


class TrueRevenge(Bot):
    def __init__(self):
        super().__init__("sensible", "always")

    def choose(self, hand, top, active_colour, ctx, rng):
        options = [c for c in hand if playable(c, top, active_colour)]
        if not options:
            return None
        for c in options:
            if len(hand) == 1:
                return c
        non_wild = [c for c in options if not is_wild(c)]
        sizes = ctx.get("hand_sizes", [])
        me = ctx.get("player_index", 0)
        target_low = any(
            i != me and s <= 2 for i, s in enumerate(sizes)
        )
        if target_low:
            actions = [c for c in non_wild if c[1] >= 10]
            if actions:
                return self._sensible_pick(hand, actions)
        numbers = [c for c in non_wild if c[1] <= 9]
        if numbers:
            return self._sensible_pick(hand, numbers)
        if non_wild:
            return self._sensible_pick(hand, non_wild)
        for c in options:
            if c[1] == 13:
                return c
        return options[0]


class SkipReverseFirst(Bot):
    def __init__(self):
        super().__init__("sensible", "always")

    def choose(self, hand, top, active_colour, ctx, rng):
        options = [c for c in hand if playable(c, top, active_colour)]
        if not options:
            return None
        for c in options:
            if len(hand) == 1:
                return c
        non_wild = [c for c in options if not is_wild(c)]
        sr = [c for c in non_wild if c[1] in (SKIP, REVERSE)]
        if sr:
            return self._sensible_pick(hand, sr)
        numbers = [c for c in non_wild if c[1] <= 9]
        if numbers:
            return self._sensible_pick(hand, numbers)
        if non_wild:
            return self._sensible_pick(hand, non_wild)
        for c in options:
            if c[1] == 13:
                return c
        return options[0]


class Draw2First(Bot):
    def __init__(self):
        super().__init__("sensible", "always")

    def choose(self, hand, top, active_colour, ctx, rng):
        options = [c for c in hand if playable(c, top, active_colour)]
        if not options:
            return None
        for c in options:
            if len(hand) == 1:
                return c
        non_wild = [c for c in options if not is_wild(c)]
        d2 = [c for c in non_wild if c[1] == DRAW2]
        if d2:
            return self._sensible_pick(hand, d2)
        numbers = [c for c in non_wild if c[1] <= 9]
        if numbers:
            return self._sensible_pick(hand, numbers)
        if non_wild:
            return self._sensible_pick(hand, non_wild)
        for c in options:
            if c[1] == 13:
                return c
        return options[0]


N = 20000
S = lambda: Bot("sensible", "always")
ARMS = [
    ("diag_true_bluffer_off", [TrueBluffer()] + [S()] * 3, "off", "off", 60000),
    ("diag_true_bluffer_challenge_always", [TrueBluffer()] + [S()] * 3, "off", "always", 60001),
    ("diag_true_revenge_off", [TrueRevenge()] + [S()] * 3, "off", "off", 60002),
    ("diag_skip_reverse_first_off", [SkipReverseFirst()] + [S()] * 3, "off", "off", 60003),
    ("diag_draw2_first_off", [Draw2First()] + [S()] * 3, "off", "off", 60004),
]

out = {}
for name, bots, stacking, challenge, seed in ARMS:
    t0 = time.time()
    r = run_arm(bots, N, seed=seed, stacking=stacking, challenge=challenge)
    p = r["match_win_rate"][0]
    se = math.sqrt(p * (1 - p) / N)
    r["test_bot_match_win_ci95"] = [round(p - 1.96 * se, 5), round(p + 1.96 * se, 5)]
    out[name] = r
    print(f"DONE {name}: match {p:.4f} CI {r['test_bot_match_win_ci95']} "
          f"round {r['round_win_rate'][0]:.4f} turns/m {r['mean_turns_per_match']:.0f} "
          f"in {time.time() - t0:.0f}s", flush=True)

with open(__file__.rsplit("/", 1)[0] + "/diagnostics.json", "w") as f:
    json.dump(out, f, indent=2)
print("DIAGNOSTICS COMPLETE", flush=True)
