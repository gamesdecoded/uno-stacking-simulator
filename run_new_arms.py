"""New arms for Uno script v3 -- APPROVED 2026-10-27 15:54 PKT by Decoder.

Two arms, 50,000 matches each, same engine build as production, new
seeds 80000+ (disjoint from production 50000-50200, diagnostics 60000+,
confirmation 70000+). Output to new_arms_results.json -- NOT to a
generic results.json, which does not exist in this folder.

Spec fixes applied (from the v3 analysis, 2026-10-27):
- Stacking is same-symbol only, exactly as the production Stacker-on
  arm: Draw Two on Draw Two, Draw Four on Draw Four, never Draw Two
  on Draw Four. Stackers are Sensible with stack_mode always.
- Intervals are the normal approximation (p +/- 1.96*SE), same as
  production/confirmation, for comparability. Wilson differs by
  <0.01 points at n=50,000 and is NOT used here.
- Engine is pure Python, not numba. Cost is still small: ~100,000
  matches at measured throughput.
- Tested-seat permutation is NOT applied: with three identical
  opponents, permuting the tested bot's list index only relabels
  identical opponents and does not change the tested bot's relative
  position (next / second / previous). Starter rotation, which the
  engine already does (random start_offset per match, starter cycles
  per round), is retained, and match_wins for all four seats are
  logged so seat shares can be checked (they must sum to 100%).
- Regression check FIRST, corrected from the spec: the spec's
  "1,000 matches must reproduce stored counts" cannot be checked
  against 50,000-match stored counts. Instead the full 50,000-match
  Stacker-on arm is rerun with its original seed (50100) and must
  reproduce production_results.json exactly. If it does not, the
  script aborts before any new arm runs.

Pre-locked decision rules (spec, with the noted precedence):
- NS upper CI below 25.0 -> "saying no costs you" holds.
- NS CI contains 25.0 -> refusing is free, EXCEPT if NS is within
  0.5 points of 25.0, in which case a 200,000-match rerun takes
  precedence over deciding (flagged in the report, rerun launched
  as pre-locked unless Decoder objects on seeing the trigger).
- NS lower CI above 25.0 -> stop, re-check engine, do not fill slot.
- COMBO lower CI above 32.4 -> Variant A (exceeds best v2 arm).
- COMBO point between 29.9 and 32.4 -> Variant B (edges do not add).
- COMBO below 29.9, or in the gap between those rules -> flag for
  review, do not force a variant.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import Bot, run_arm

N = 50000
OUT = __file__.rsplit("/", 1)[0] + "/new_arms_results.json"
LOG = __file__.rsplit("/", 1)[0] + "/new_arms.log"
PROD = __file__.rsplit("/", 1)[0] + "/production_results.json"


def log(msg):
    print(msg, flush=True)
    with open(LOG, "a") as f:
        f.write(msg + "\n")


def with_ci(r):
    p = r["match_win_rate"][0]
    se = math.sqrt(p * (1 - p) / r["n_matches"])
    r["test_bot_match_win_ci95"] = [round(p - 1.96 * se, 5), round(p + 1.96 * se, 5)]
    return r


def main():
    # --- Regression: full Stacker-on rerun, seed 50100 ---
    prod = json.load(open(PROD))["stageB_stacker_vs_passers_ON_same"]
    S = lambda: Bot("sensible", "always")
    P = lambda: Bot("sensible", "never")
    t0 = time.time()
    reg = run_arm([S()] + [P()] * 3, N, seed=50100, stacking="same", challenge="off")
    match = (
        reg["match_wins"] == prod["match_wins"]
        and reg["rounds_total"] == prod["rounds_total"]
        and reg["turns_total"] == prod["turns_total"]
    )
    log(f"REGRESSION Stacker-on 50k seed 50100: match_wins={reg['match_wins']} "
        f"rounds={reg['rounds_total']} turns={reg['turns_total']} "
        f"expected wins={prod['match_wins']} rounds={prod['rounds_total']} "
        f"turns={prod['turns_total']} MATCH={match} in {time.time() - t0:.0f}s")
    if not match:
        log("REGRESSION FAILED: aborting before new arms, engine must be re-checked.")
        sys.exit(1)

    done = {}
    if os.path.exists(OUT):
        try:
            with open(OUT) as f:
                done = json.load(f)
        except Exception:
            done = {}
    done["_regression"] = {
        "arm": "stageB_stacker_vs_passers_ON_same",
        "seed": 50100,
        "match": match,
        "match_wins": reg["match_wins"],
        "rounds_total": reg["rounds_total"],
        "turns_total": reg["turns_total"],
    }

    arms = [
        ("armA_refuser_vs_stackers", [Bot("sensible", "never")] + [Bot("sensible", "always")] * 3, 80000),
        ("armB_combo_action_dumper_stacker", [Bot("action_dumper", "always")] + [Bot("sensible", "always")] * 3, 80001),
    ]
    t_start = time.time()
    for name, bots, seed in arms:
        if name in done and isinstance(done[name], dict) and done[name].get("n_matches") == N:
            log(f"SKIP (already done): {name}")
            continue
        t0 = time.time()
        r = with_ci(run_arm(bots, N, seed=seed, stacking="same", challenge="off"))
        share_ok = sum(r["match_wins"]) == N
        r["share_sums_to_n_matches"] = share_ok
        done[name] = r
        with open(OUT, "w") as f:
            json.dump(done, f, indent=2)
        log(f"DONE {name}: test-bot match {r['match_win_rate'][0]:.4f} "
            f"CI {r['test_bot_match_win_ci95']} round {r['round_win_rate'][0]:.4f} "
            f"match_wins={r['match_wins']} share_ok={share_ok} "
            f"turns/m {r['mean_turns_per_match']:.1f} rounds/m {r['mean_rounds_per_match']:.2f} "
            f"capped {r['capped_matches']}/{r['capped_rounds']} in {time.time() - t0:.0f}s")
    total = sum(v["n_matches"] for v in done.values() if isinstance(v, dict) and "n_matches" in v)
    rounds = sum(v["rounds_total"] for v in done.values() if isinstance(v, dict) and "rounds_total" in v)
    done["_meta"] = {
        "n_matches_per_arm": N,
        "total_matches": total,
        "total_rounds": rounds,
        "elapsed_s": round(time.time() - t_start, 1),
        "stacking": "same-symbol only (Draw Two on Draw Two, Draw Four on Draw Four)",
        "ci_method": "normal approximation, same as production/confirmation",
    }
    with open(OUT, "w") as f:
        json.dump(done, f, indent=2)
    log(f"NEW ARMS COMPLETE: {total} matches, {rounds} rounds, {time.time() - t_start:.0f}s")


if __name__ == "__main__":
    main()
