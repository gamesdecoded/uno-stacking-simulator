"""Validation gates for the Uno engine. All must PASS before a production run.

Gates (from the approved design):
1. Deck composition: 108 cards, exact counts.
2. Starting-hand Wild probability vs exact combinatorial value.
3. Random vs Random, 4 players: each near 25%.
4. Random vs Random, 2 players: each near 50%.
5. Sensible beats Random, clearly but not totally.
6. Forced cases (unit-style, via play_round_clean with seeded decks is
   hard to force, so these check the primitives directly):
   - playable() matching rules, Draw 4 legality, stacking sets,
     card points, Reverse-in-2p handled in match code path (checked
     by a 2p run completing without error and sensible advantage).
7. Throughput benchmark (matches/sec, 4p sensible vs sensible).
8. No capped rounds in a sane sample, or capped rate reported.
"""
import math
import random
import sys
import time
from collections import Counter

sys.path.insert(0, __file__.rsplit("/", 1)[0])
from engine import (Bot, build_deck, card_points, legal_draw4, playable,
                    play_round_clean, run_arm, stackable_cards)

FAILURES = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'}: {name} {detail}")
    if not cond:
        FAILURES.append(name)


def main():
    # 1. Deck composition
    deck = build_deck()
    check("deck size 108", len(deck) == 108, f"got {len(deck)}")
    cnt = Counter(deck)
    ok = True
    for c in range(4):
        ok &= cnt[(c, 0)] == 1
        for v in range(1, 10):
            ok &= cnt[(c, v)] == 2
        for v in (10, 11, 12):
            ok &= cnt[(c, v)] == 2
    ok &= cnt[(4, 13)] == 4 and cnt[(4, 14)] == 4
    check("deck composition exact", ok)

    # 2. Starting-hand Wild probability (8 wild-type cards in 108, 7 dealt)
    # P(at least one) = 1 - C(100,7)/C(108,7)
    theory = 1 - math.comb(100, 7) / math.comb(108, 7)
    rng = random.Random(12345)
    trials = 20000
    hits = 0
    for _ in range(trials):
        d = build_deck()
        rng.shuffle(d)
        hand = d[:7]
        if any(c[0] == 4 for c in hand):
            hits += 1
    observed = hits / trials
    se = math.sqrt(observed * (1 - observed) / trials)
    check("starting-hand wild prob vs theory",
          abs(observed - theory) < 3 * se,
          f"theory={theory:.4f} observed={observed:.4f} se={se:.4f}")

    # 3/4. Random vs Random
    r4 = run_arm([Bot("random")] * 4, 1000, seed=777, stacking="off")
    print("  random 4p match rates:", [f"{x:.3f}" for x in r4["match_win_rate"]],
          "rounds/match", f"{r4['mean_rounds_per_match']:.2f}")
    check("random 4p each near 25%",
          all(abs(x - 0.25) < 0.05 for x in r4["match_win_rate"]))
    r2 = run_arm([Bot("random")] * 2, 1000, seed=778, stacking="off")
    print("  random 2p match rates:", [f"{x:.3f}" for x in r2["match_win_rate"]])
    check("random 2p each near 50%",
          all(abs(x - 0.5) < 0.05 for x in r2["match_win_rate"]))

    # 5. Sensible vs Random (1 sensible vs 3 random, 4p)
    sr = run_arm([Bot("sensible")] + [Bot("random")] * 3, 1000, seed=779, stacking="off")
    print("  sensible vs 3 random match rates:",
          [f"{x:.3f}" for x in sr["match_win_rate"]])
    check("sensible beats random", sr["match_win_rate"][0] > 0.30)
    check("sensible does not win everything", sr["match_win_rate"][0] < 0.90)

    # 6. Primitives
    check("playable colour match", playable((0, 5), (1, 5), 0) or playable((0, 3), (1, 7), 0))
    check("playable number match", playable((1, 5), (0, 5), 0))
    check("playable wild", playable((4, 13), (0, 5), 0))
    check("not playable", not playable((1, 3), (0, 5), 0))
    check("draw4 legal when no colour", legal_draw4([(1, 3), (2, 4)], 0))
    check("draw4 illegal when colour held", not legal_draw4([(0, 3), (1, 4)], 0))
    check("stack same draw2", stackable_cards([(0, 12), (1, 5)], "draw2", "same") == [(0, 12)])
    check("stack off empty", stackable_cards([(0, 12)], "draw2", "off") == [])
    check("stack cross draw4 on draw2",
          (4, 14) in stackable_cards([(4, 14)], "draw2", "cross"))
    check("stack cross no draw2 on draw4",
          stackable_cards([(0, 12)], "draw4", "cross") == [])
    check("card points", card_points((0, 9)) == 9 and card_points((0, 12)) == 20
          and card_points((4, 14)) == 50)

    # 7. Throughput: 4p sensible vs sensible, 200 matches
    t0 = time.time()
    bench = run_arm([Bot("sensible")] * 4, 200, seed=780, stacking="off")
    dt = time.time() - t0
    rate = 200 / dt if dt else 0
    print(f"  throughput: 200 matches in {dt:.1f}s = {rate:.1f} matches/s, "
          f"rounds/match {bench['mean_rounds_per_match']:.2f}, "
          f"turns/match {bench['mean_turns_per_match']:.0f}")
    check("throughput measured", rate > 0, f"{rate:.1f} matches/s")
    check("no capped matches in bench", bench["capped_matches"] == 0,
          f"capped={bench['capped_matches']}")
    check("no capped rounds in bench", bench["capped_rounds"] == 0,
          f"capped={bench['capped_rounds']}")

    # 8. Stacking symmetric arm completes and stays near 25% (validation only)
    sym = run_arm([Bot("sensible")] * 4, 500, seed=781, stacking="same")
    print("  symmetric stacking ON match rates:",
          [f"{x:.3f}" for x in sym["match_win_rate"]])
    check("symmetric stacking near 25%",
          all(abs(x - 0.25) < 0.06 for x in sym["match_win_rate"]))

    print()
    if FAILURES:
        print("VALIDATION FAILED:", FAILURES)
        return 1
    print("ALL VALIDATION GATES PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
