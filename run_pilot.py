"""Pilot only -- NOT production results.

Small sample (1,000 matches per arm) to estimate variance, direction,
and throughput while #5's Monopoly sim is running. Pilot numbers must
not be quoted as results: 95% CIs at n=1,000 are roughly +/-3 points
on a match win rate near 25%.
"""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import Bot, run_arm

N = 1000
out = {}
t0 = time.time()


def arm(name, bots, stacking="off", challenge="off", seed=1000):
    r = run_arm(bots, N, seed=seed, stacking=stacking, challenge=challenge)
    out[name] = r
    print(f"{name}: test-bot match win {r['match_win_rate'][0]:.3f} "
          f"round win {r['round_win_rate'][0]:.3f} "
          f"rounds/match {r['mean_rounds_per_match']:.2f} "
          f"turns/match {r['mean_turns_per_match']:.0f} "
          f"capped_rounds {r['capped_rounds']}")
    return r


S = lambda: Bot("sensible", "always")
P = lambda: Bot("sensible", "never")  # Passer

# Stage A: one mistake bot vs 3 Sensible, stacking OFF.
for i, policy in enumerate([
    "sensible", "random", "wild_spender", "wrong_colour",
    "draw_keeper", "bluffer", "revenge_saver", "action_dumper",
]):
    arm(f"stageA_{policy}_vs_sensible_OFF",
        [Bot(policy)] + [S()] * 3, stacking="off", seed=2000 + i)

# Stage B: stacking test.
arm("stageB_stacker_vs_passers_ON_same",
    [S()] + [P()] * 3, stacking="same", seed=3000)
arm("stageB_stacker_vs_passers_OFF",
    [S()] + [P()] * 3, stacking="off", seed=3001)
arm("stageB_symmetric_ON_same",
    [S()] * 4, stacking="same", seed=3002)
arm("stageB_symmetric_OFF",
    [S()] * 4, stacking="off", seed=3003)
# Challenge bound arm: Bluffer vs 3 Sensible, challenge always-correct.
arm("stageA_bluffer_vs_sensible_challenge_always",
    [Bot("bluffer")] + [S()] * 3, stacking="off", challenge="always", seed=4000)

out["_pilot_info"] = {
    "n_matches_per_arm": N,
    "elapsed_s": round(time.time() - t0, 1),
    "note": "PILOT ONLY, not production results. CIs at n=1000 are ~+/-0.03.",
}
with open(__file__.rsplit("/", 1)[0] + "/pilot_results.json", "w") as f:
    json.dump(out, f, indent=2)
print(f"pilot done in {time.time() - t0:.1f}s, saved to pilot_results.json")
