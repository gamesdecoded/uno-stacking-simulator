"""Uno engine for humandecoded video #6.

Locked design (2026-10-26, Decoder-approved):
- Mistakes tournament, stacking ON vs OFF headline, never luck framing.
- Classic 108-card deck, 4 players primary, first to 500 primary metric,
  single-round win rate secondary.
- Headline stacking = same-symbol only. Cross-stacking / No Mercy are
  bonus beats, not in this engine's main arms (No Mercy is a separate
  deck and is NOT modelled here).
- Seven-zero is excluded from the main tournament.
- No bot sees another player's hand. The only exception is the
  challenge='always' bound arm, which is a disclosed perfect-enforcement
  bound, not a human policy.
- Challenge='off' is the main run: an illegal Draw 4 is unpunished.
- Bots never forget to say Uno in the main run (disclosed simplification).

Cards are (colour, value):
  colour 0-3 = red, yellow, green, blue (order is arbitrary); 4 = wild.
  value 0-9 = number; 10 = Skip; 11 = Reverse; 12 = Draw 2;
  13 = Wild; 14 = Wild Draw 4.
"""

import random
from collections import Counter

COLORS = (0, 1, 2, 3)
WILD = 4
SKIP, REVERSE, DRAW2, WILD_CARD, DRAW4 = 10, 11, 12, 13, 14


def build_deck():
    deck = []
    for c in COLORS:
        deck.append((c, 0))
        for v in range(1, 10):
            deck.extend([(c, v), (c, v)])
        for v in (SKIP, REVERSE, DRAW2):
            deck.extend([(c, v), (c, v)])
    deck.extend([(WILD, WILD_CARD)] * 4)
    deck.extend([(WILD, DRAW4)] * 4)
    assert len(deck) == 108, len(deck)
    return deck


def card_points(card):
    _, v = card
    if v <= 9:
        return v
    if v in (SKIP, REVERSE, DRAW2):
        return 20
    return 50


def is_wild(card):
    return card[0] == WILD


def playable(card, top, active_colour):
    """Normal-turn playability. Pending (forced) turns are handled separately."""
    if is_wild(card):
        return True
    if card[0] == active_colour:
        return True
    if top is not None and card[1] == top[1]:
        return True
    return False


def legal_draw4(hand, active_colour):
    """A Draw 4 is legal only if the player holds no card of the active colour."""
    return not any(c[0] == active_colour for c in hand)


class Bot:
    """One policy deviation at most, on top of Sensible.

    policy: sensible, random, wild_spender, wrong_colour, draw_keeper,
            bluffer, revenge_saver, action_dumper
    stack_mode: 'always' (stack when possible) or 'never' (take the penalty).
    Sensible's default stack_mode is 'always'; a Passer is Sensible with
    stack_mode='never'. A Stacker is Sensible with stack_mode='always'
    measured against Passers.
    """

    def __init__(self, policy="sensible", stack_mode="always"):
        self.policy = policy
        self.stack_mode = stack_mode

    def __repr__(self):
        return f"Bot({self.policy},stack={self.stack_mode})"

    # -- colour choice -------------------------------------------------
    def choose_colour(self, hand, rng):
        counts = Counter(c for c, _ in hand if c != WILD)
        if self.policy == "random":
            return rng.randrange(4)
        if self.policy == "wrong_colour":
            # Least-held colour, including colours held zero times.
            return min(COLORS, key=lambda c: (counts.get(c, 0), c))
        # Sensible and all mistake bots except wrong_colour: most-held.
        return max(COLORS, key=lambda c: (counts.get(c, 0), -c))

    # -- drawn card ----------------------------------------------------
    def play_drawn(self, card):
        if self.policy == "draw_keeper":
            return False
        return True

    # -- stacking ------------------------------------------------------
    def should_stack(self):
        return self.stack_mode == "always"

    # -- normal card choice -------------------------------------------
    def choose(self, hand, top, active_colour, ctx, rng):
        """Return a playable card, or None to draw. ctx has hand_sizes,
        player_index, direction, n_players."""
        options = [c for c in hand if playable(c, top, active_colour)]
        if not options:
            return None
        # Winning card first, whatever the policy.
        for c in options:
            if len(hand) == 1:
                return c
        if self.policy == "random":
            return rng.choice(options)

        if self.policy == "wild_spender":
            # Draw 4 only if legal; otherwise Wild. This keeps the spender
            # deviation about timing, not about illegal play (that is Bluffer).
            for c in options:
                if c[1] == DRAW4 and legal_draw4(hand, active_colour):
                    return c
            for c in options:
                if c[1] == WILD_CARD:
                    return c
            # No (legal) wild available: fall through to Sensible.

        if self.policy == "bluffer":
            # Only deviation: when Sensible would play a wild (no non-wild
            # playable), play Draw 4 even if illegal, instead of Wild.
            non_wild = [c for c in options if not is_wild(c)]
            if not non_wild:
                for c in options:
                    if c[1] == DRAW4:
                        return c
            # Otherwise fall through to Sensible.

        non_wild = [c for c in options if not is_wild(c)]
        if self.policy == "revenge_saver":
            numbers = [c for c in non_wild if c[1] <= 9]
            if numbers:
                return self._sensible_pick(hand, numbers)
            if non_wild:
                return self._sensible_pick(hand, non_wild)
        elif self.policy == "action_dumper":
            actions = [c for c in non_wild if c[1] >= 10]
            if actions:
                return self._sensible_pick(hand, actions)
            if non_wild:
                return self._sensible_pick(hand, non_wild)
        else:
            if non_wild:
                return self._sensible_pick(hand, non_wild)
        # Only wilds playable.
        for c in options:
            if c[1] == WILD_CARD:
                return c
        return options[0]

    @staticmethod
    def _sensible_pick(hand, options):
        """Prefer the move leaving the most cards of the new active colour;
        numbers before actions; lower value as a final tie-break."""
        def key(c):
            remaining = [x for x in hand if x != c]
            colour = c[0]
            n_same = sum(1 for x in remaining if x[0] == colour)
            is_action = 1 if c[1] >= 10 else 0
            return (-n_same, is_action, c[1], c[0])

        return sorted(options, key=key)[0]


def stackable_cards(hand, pending_type, stacking):
    """Cards that may be played in a forced (pending) turn."""
    if stacking == "off":
        return []
    if pending_type == "draw2":
        if stacking == "same":
            return [c for c in hand if c[1] == DRAW2]
        if stacking == "cross":
            return [c for c in hand if c[1] in (DRAW2, DRAW4)]
    if pending_type == "draw4":
        # Draw 2 on Draw 4 is never allowed, even in cross-stacking.
        return [c for c in hand if c[1] == DRAW4]
    return []



def play_round(bots, rng, starter, stacking="off", challenge="off"):
    """Wrapper that tracks Draw 4 legality correctly.

    Legality must be judged on the hand before the Draw 4 is played, against
    the colour active before the Draw 4. Round.play() above handles the
    mechanics; this wrapper re-implements the Draw 4 branch cleanly by
    monkey-patching is not used -- instead, see play_round_clean below.
    """
    return play_round_clean(bots, rng, starter, stacking, challenge)


def play_round_clean(bots, rng, starter, stacking="off", challenge="off"):
    """Clean round implementation with correct Draw 4 legality handling.

    This is the function used by matches and validation. Round.play()
    is retained as reference; play_round_clean is authoritative.
    """
    n = len(bots)
    deck = build_deck()
    rng.shuffle(deck)
    draw_pile = deck
    hands = [[draw_pile.pop() for _ in range(7)] for _ in range(n)]

    def draw_cards(k):
        nonlocal draw_pile, discard
        out = []
        for _ in range(k):
            if not draw_pile:
                if len(discard) <= 1:
                    break
                top_card = discard[-1]
                rest = discard[:-1]
                rng.shuffle(rest)
                draw_pile = rest
                discard = [top_card]
            out.append(draw_pile.pop())
        return out

    while True:
        top = draw_pile.pop()
        if top[1] == DRAW4:
            draw_pile.append(top)
            rng.shuffle(draw_pile)
            continue
        break
    discard = [top]
    direction = 1
    pending = 0
    pending_type = None
    illegal_draw4 = 0
    challenged = 0
    max_deficit = [0] * n
    turns = 0
    capped = False
    if top[1] == WILD_CARD:
        active_colour = bots[starter].choose_colour(hands[starter], rng)
        current = starter
    elif top[1] == SKIP:
        active_colour = top[0]
        current = (starter + 1) % n
    elif top[1] == REVERSE:
        direction = -1
        active_colour = top[0]
        current = (starter - 1) % n
    elif top[1] == DRAW2:
        active_colour = top[0]
        hands[starter].extend(draw_cards(2))
        current = (starter + 1) % n
    else:
        active_colour = top[0]
        current = starter

    def nxt(player, steps=1):
        return (player + direction * steps) % n

    winner = None
    while turns < 1000:
        turns += 1
        p = current
        hand = hands[p]
        others = [len(hands[i]) for i in range(n) if i != p]
        deficit = len(hand) - min(others) if others else 0
        if deficit > max_deficit[p]:
            max_deficit[p] = deficit
        bot = bots[p]
        top_card = discard[-1]

        if pending > 0:
            options = stackable_cards(hand, pending_type, stacking)
            if options and bot.should_stack():
                card = next((c for c in options if c[1] == DRAW2), options[0])
                hand.remove(card)
                discard.append(card)
                if card[1] == DRAW4:
                    active_colour = bot.choose_colour(hand, rng)
                    pending += 4
                    pending_type = "draw4"
                else:
                    pending += 2
                    pending_type = "draw2"
                if not hand:
                    winner = p
                    break
                current = nxt(p, 1)
                continue
            hand.extend(draw_cards(pending))
            pending = 0
            pending_type = None
            current = nxt(p, 1)
            continue

        ctx = {
            "hand_sizes": [len(h) for h in hands],
            "player_index": p,
            "direction": direction,
            "n_players": n,
        }
        card = bot.choose(hand, top_card, active_colour, ctx, rng)
        if card is None:
            drawn = draw_cards(1)
            if drawn:
                d = drawn[0]
                hand.append(d)
                if playable(d, top_card, active_colour) and bot.play_drawn(d):
                    # Play the drawn card.
                    hand.remove(d)
                    discard.append(d)
                    if not hand:
                        winner = p
                        break
                    if d[1] == WILD_CARD:
                        active_colour = bot.choose_colour(hand, rng)
                        current = nxt(p, 1)
                    elif d[1] == DRAW4:
                        active_colour = bot.choose_colour(hand, rng)
                        pending = 4
                        pending_type = "draw4"
                        current = nxt(p, 1)
                    elif d[1] == SKIP:
                        current = nxt(p, 2)
                    elif d[1] == REVERSE:
                        direction *= -1
                        current = p if n == 2 else (p + direction) % n
                    elif d[1] == DRAW2:
                        pending = 2
                        pending_type = "draw2"
                        current = nxt(p, 1)
                    else:
                        current = nxt(p, 1)
                    continue
            current = nxt(p, 1)
            continue

        # Normal play. Judge Draw 4 legality BEFORE removing the card,
        # against the colour active before the play.
        pre_colour = active_colour
        pre_legal = True
        if card[1] == DRAW4:
            pre_legal = legal_draw4(hand, pre_colour)
            if not pre_legal:
                illegal_draw4 += 1
        hand.remove(card)
        discard.append(card)
        if not hand:
            winner = p
            break
        if card[1] == WILD_CARD:
            active_colour = bot.choose_colour(hand, rng)
            current = nxt(p, 1)
        elif card[1] == DRAW4:
            active_colour = bot.choose_colour(hand, rng)
            if not pre_legal and challenge == "always":
                # Perfect-challenge bound: penalty goes to the player who
                # played the illegal Draw 4; the target plays normally.
                challenged += 1
                hands[p].extend(draw_cards(4))
                current = nxt(p, 1)
            else:
                pending = 4
                pending_type = "draw4"
                current = nxt(p, 1)
        elif card[1] == SKIP:
            current = nxt(p, 2)
        elif card[1] == REVERSE:
            direction *= -1
            current = p if n == 2 else (p + direction) % n
        elif card[1] == DRAW2:
            pending = 2
            pending_type = "draw2"
            current = nxt(p, 1)
        else:
            current = nxt(p, 1)

    if winner is None:
        capped = True
        winner = min(range(n), key=lambda i: (len(hands[i]), i))
    points = sum(
        card_points(c) for i, h in enumerate(hands) if i != winner for c in h
    )
    return {
        "winner": winner,
        "points": points,
        "turns": turns,
        "capped": capped,
        "max_deficit_winner": max_deficit[winner],
        "comeback": max_deficit[winner] >= 10,
        "illegal_draw4": illegal_draw4,
        "challenged": challenged,
        "hand_sizes": [len(h) for h in hands],
    }


def play_match(bots, rng, stacking="off", challenge="off", max_rounds=50):
    """Play one match to 500 points. Returns match + round aggregates."""
    n = len(bots)
    scores = [0] * n
    start_offset = rng.randrange(n)
    rounds = 0
    total_turns = 0
    round_wins = [0] * n
    round_points = [0] * n
    capped_rounds = 0
    comeback_rounds = 0
    max_hand = 0
    while rounds < max_rounds:
        starter = (start_offset + rounds) % n
        r = play_round_clean(bots, rng, starter, stacking, challenge)
        rounds += 1
        total_turns += r["turns"]
        w = r["winner"]
        round_wins[w] += 1
        round_points[w] += r["points"]
        scores[w] += r["points"]
        if r["capped"]:
            capped_rounds += 1
        if r["comeback"]:
            comeback_rounds += 1
        max_hand = max(max_hand, max(r["hand_sizes"]) if r["hand_sizes"] else 0)
        # Max hand during a round is not fully tracked; hand_sizes at end
        # are a lower bound, so max_hand here is conservative.
        if scores[w] >= 500:
            return {
                "winner": w,
                "scores": scores,
                "rounds": rounds,
                "turns": total_turns,
                "round_wins": round_wins,
                "round_points": round_points,
                "capped_rounds": capped_rounds,
                "capped_match": False,
                "comeback_rounds": comeback_rounds,
            }
    # Match cap hit.
    winner = max(range(n), key=lambda i: (scores[i], -i))
    return {
        "winner": winner,
        "scores": scores,
        "rounds": rounds,
        "turns": total_turns,
        "round_wins": round_wins,
        "round_points": round_points,
        "capped_rounds": capped_rounds,
        "capped_match": True,
        "comeback_rounds": comeback_rounds,
    }


def run_arm(bots, n_matches, seed, stacking="off", challenge="off"):
    """Run n_matches. Returns aggregate stats for each bot index."""
    rng = random.Random(seed)
    n = len(bots)
    match_wins = [0] * n
    round_wins = [0] * n
    rounds_total = 0
    turns_total = 0
    capped_matches = 0
    capped_rounds = 0
    comeback_rounds = 0
    for _ in range(n_matches):
        m = play_match(bots, rng, stacking, challenge)
        match_wins[m["winner"]] += 1
        for i in range(n):
            round_wins[i] += m["round_wins"][i]
        rounds_total += m["rounds"]
        turns_total += m["turns"]
        capped_matches += 1 if m["capped_match"] else 0
        capped_rounds += m["capped_rounds"]
        comeback_rounds += m["comeback_rounds"]
    return {
        "n_matches": n_matches,
        "match_wins": match_wins,
        "match_win_rate": [w / n_matches for w in match_wins],
        "round_wins": round_wins,
        "round_win_rate": [w / rounds_total for w in round_wins] if rounds_total else [0] * n,
        "rounds_total": rounds_total,
        "turns_total": turns_total,
        "mean_rounds_per_match": rounds_total / n_matches if n_matches else 0,
        "mean_turns_per_match": turns_total / n_matches if n_matches else 0,
        "capped_matches": capped_matches,
        "capped_rounds": capped_rounds,
        "comeback_rounds": comeback_rounds,
    }
