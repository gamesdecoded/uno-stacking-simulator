"""50,000-match confirmation -- APPROVED 2026-10-27 14:09 PKT by Decoder.

Confirms the three diagnostic arms that replace the mislabelled
production Bluffer / Revenge-Saver arms, at production size:
- true bluffer, challenge off
- true bluffer, challenge always
- true revenge-saver, challenge off

True bluffer: play Draw 4 whenever held, even with playable non-wilds.
True revenge: numbers first normally; actions first when any opponent
has <=2 cards. Both vs 3 Sensible bots, stacking OFF, first to 500.

Checkpointed per arm in confirmation_results.json. New seeds 70000+.
These are NOT part of the original 650,000-match production total;
quote them as a 50,000-match confirmation, or fold them into the
script's stated total only with that labelling made explicit.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import Bot, run_arm, playable, DRAW4, is_wild

N = 50000
OUT = __file__.rsplit("/", 1)[0] + "/confirmation_results.json"
LOG = __file__.rsplit("/", 1)[0] + "/confirmation.log"


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
        target_low = any(i != me and s <= 2 for i, s in enumerate(sizes))
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


def log(msg):
    print(msg, flush=True)
    with open(LOG, "a") as f:
        f.write(msg + "\n")


S = lambda: Bot("sensible", "always")
ARMS = [
    ("confirm_true_bluffer_off", [TrueBluffer()] + [S()] * 3, "off", "off", 70000),
    ("confirm_true_bluffer_challenge_always", [TrueBluffer()] + [S()] * 3, "off", "always", 70001),
    ("confirm_true_revenge_off", [TrueRevenge()] + [S()] * 3, "off", "off", 70002),
]


def main():
    done = {}
    if os.path.exists(OUT):
        try:
            with open(OUT) as f:
                done = json.load(f)
        except Exception:
            done = {}
    t_start = time.time()
    for name, bots, stacking, challenge, seed in ARMS:
        if name in done and isinstance(done[name], dict) and done[name].get("n_matches") == N:
            log(f"SKIP (already done): {name}")
            continue
        t0 = time.time()
        r = run_arm(bots, N, seed=seed, stacking=stacking, challenge=challenge)
        p = r["match_win_rate"][0]
        se = math.sqrt(p * (1 - p) / N)
        r["test_bot_match_win_ci95"] = [round(p - 1.96 * se, 5), round(p + 1.96 * se, 5)]
        done[name] = r
        with open(OUT, "w") as f:
            json.dump(done, f, indent=2)
        log(f"DONE {name}: match {p:.4f} CI {r['test_bot_match_win_ci95']} "
            f"round {r['round_win_rate'][0]:.4f} turns/m {r['mean_turns_per_match']:.0f} "
            f"capped {r['capped_matches']}/{r['capped_rounds']} in {time.time() - t0:.0f}s")
    total = sum(v["n_matches"] for v in done.values() if isinstance(v, dict) and "n_matches" in v)
    rounds = sum(v["rounds_total"] for v in done.values() if isinstance(v, dict) and "rounds_total" in v)
    done["_meta"] = {"n_matches_per_arm": N, "total_matches": total, "total_rounds": rounds,
                     "elapsed_s": round(time.time() - t_start, 1)}
    with open(OUT, "w") as f:
        json.dump(done, f, indent=2)
    log(f"CONFIRMATION COMPLETE: {total} matches, {rounds} rounds, {time.time() - t_start:.0f}s")


if __name__ == "__main__":
    main()
