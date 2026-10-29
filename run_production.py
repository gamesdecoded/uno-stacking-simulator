"""Uno production run -- APPROVED 2026-10-26 22:33 PKT by Decoder.

50,000 matches per arm, 13 arms (same arms as the pilot, new seeds).
Checkpointed per arm: production_results.json is rewritten after each
arm completes, so an interrupted run resumes by skipping completed arms.

Primary metric: match win rate, 95% CI = p +/- 1.96*sqrt(p*(1-p)/n),
matches are independent trials. Round win rate is secondary and
descriptive only: rounds inside a match are not independent trials,
so no formal round CI is claimed here.
"""
import json
import math
import os
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import Bot, run_arm

N = 50000
OUT = __file__.rsplit("/", 1)[0] + "/production_results.json"
LOG = __file__.rsplit("/", 1)[0] + "/production.log"

S = lambda: Bot("sensible", "always")
P = lambda: Bot("sensible", "never")  # Passer

ARMS = [
    ("stageA_sensible_vs_sensible_OFF", [Bot("sensible")] + [S()] * 3, "off", "off", 50000),
    ("stageA_random_vs_sensible_OFF", [Bot("random")] + [S()] * 3, "off", "off", 50001),
    ("stageA_wild_spender_vs_sensible_OFF", [Bot("wild_spender")] + [S()] * 3, "off", "off", 50002),
    ("stageA_wrong_colour_vs_sensible_OFF", [Bot("wrong_colour")] + [S()] * 3, "off", "off", 50003),
    ("stageA_draw_keeper_vs_sensible_OFF", [Bot("draw_keeper")] + [S()] * 3, "off", "off", 50004),
    ("stageA_bluffer_vs_sensible_OFF", [Bot("bluffer")] + [S()] * 3, "off", "off", 50005),
    ("stageA_revenge_saver_vs_sensible_OFF", [Bot("revenge_saver")] + [S()] * 3, "off", "off", 50006),
    ("stageA_action_dumper_vs_sensible_OFF", [Bot("action_dumper")] + [S()] * 3, "off", "off", 50007),
    ("stageB_stacker_vs_passers_ON_same", [S()] + [P()] * 3, "same", "off", 50100),
    ("stageB_stacker_vs_passers_OFF", [S()] + [P()] * 3, "off", "off", 50101),
    ("stageB_symmetric_ON_same", [S()] * 4, "same", "off", 50102),
    ("stageB_symmetric_OFF", [S()] * 4, "off", "off", 50103),
    ("stageA_bluffer_vs_sensible_challenge_always", [Bot("bluffer")] + [S()] * 3, "off", "always", 50200),
]


def log(msg):
    print(msg, flush=True)
    with open(LOG, "a") as f:
        f.write(msg + "\n")


def with_ci(r):
    n = r["n_matches"]
    out = dict(r)
    cis = []
    for p in r["match_win_rate"]:
        se = math.sqrt(p * (1 - p) / n) if n else 0
        cis.append([round(p - 1.96 * se, 5), round(p + 1.96 * se, 5)])
    out["match_win_ci95"] = cis
    out["test_bot_match_win_ci95"] = cis[0]
    return out


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
        r = with_ci(r)
        done[name] = r
        with open(OUT, "w") as f:
            json.dump(done, f, indent=2)
        log(f"DONE {name}: test-bot match {r['match_win_rate'][0]:.4f} "
            f"CI {r['test_bot_match_win_ci95']} round {r['round_win_rate'][0]:.4f} "
            f"rounds/match {r['mean_rounds_per_match']:.2f} "
            f"turns/match {r['mean_turns_per_match']:.0f} "
            f"capped_rounds {r['capped_rounds']} in {time.time() - t0:.0f}s")
    total_matches = sum(
        v["n_matches"] for v in done.values() if isinstance(v, dict) and "n_matches" in v
    )
    total_rounds = sum(
        v["rounds_total"] for v in done.values() if isinstance(v, dict) and "rounds_total" in v
    )
    done["_meta"] = {
        "n_matches_per_arm": N,
        "n_arms": len(ARMS),
        "total_matches": total_matches,
        "total_rounds": total_rounds,
        "elapsed_s": round(time.time() - t_start, 1),
        "note": "Production results. Match win CI is formal (independent matches); "
                "round win rate is descriptive only.",
    }
    with open(OUT, "w") as f:
        json.dump(done, f, indent=2)
    log(f"PRODUCTION COMPLETE: {total_matches} matches, {total_rounds} rounds, "
        f"{time.time() - t_start:.0f}s total")


if __name__ == "__main__":
    main()
