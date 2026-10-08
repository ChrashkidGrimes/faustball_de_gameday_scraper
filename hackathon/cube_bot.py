#!/usr/bin/env python3
"""Rubik's-cube bot for https://hackathon.kleopi.net

Game (from /docs and probing the API):
  GET  /cube   -> {"scramble": "<100 moves, Singmaster notation>"}  (new scramble every round)
  POST /cube   <- {"team_name": ..., "solution": "<moves>"}
               -> {"solved": true, "moves": n, "score": s, "Optimal Moves": k, "recorded": true}
  GET  /timer  -> "Next reset in MM:SS\nRound N\nPeriod 10 minutes"

Fewer moves = more points, so the bot searches for the shortest solution it can find
(Kociemba two-phase, iteratively tightening the length bound) within a time budget,
verifies it locally and submits once per round.

Usage:
  pip install RubikTwoPhase requests
  python cube_bot.py --team claudine            # solve + submit the current round
  python cube_bot.py --team claudine --loop     # keep going, once per round
  python cube_bot.py --team claudine --dry-run  # solve only, don't submit

The first run builds the solver's lookup tables (~ several minutes, cached in --table-dir).
"""
import argparse
import os
import re
import sys
import time

import requests

BASE = "https://hackathon.kleopi.net"


# ---------------------------------------------------------------- notation helpers
def parse_moves(seq):
    """'R U2 F'' -> [('R', 1), ('U', 2), ('F', 3)] (quarter turns clockwise)."""
    out = []
    for tok in seq.split():
        m = re.fullmatch(r"([URFDLB])(2|'|3|1)?", tok)
        if not m:
            raise ValueError(f"unknown move {tok!r}")
        out.append((m.group(1), {None: 1, "1": 1, "2": 2, "'": 3, "3": 3}[m.group(2)]))
    return out


def fmt_moves(moves):
    return " ".join(f + {1: "", 2: "2", 3: "'"}[n] for f, n in moves)


def invert(moves):
    return [(f, (4 - n) % 4) for f, n in reversed(moves)]


def apply_moves(cube, moves):
    """Apply moves to a twophase CubieCube in place."""
    from twophase.cubie import basicMoveCube
    from twophase.enums import Color
    for f, n in moves:
        for _ in range(n):
            cube.multiply(basicMoveCube[Color[f]])
    return cube


# ---------------------------------------------------------------- solving
def solve(scramble, budget, min_len=0, verbose=True):
    """Shortest solution found within `budget` seconds, as a list of moves."""
    import twophase.solver as sv
    from twophase.cubie import CubieCube

    state = apply_moves(CubieCube(), parse_moves(scramble))
    facelets = state.to_facelet_cube().to_string()

    deadline = time.monotonic() + budget
    best = None
    target = 20
    while target >= min_len:
        left = deadline - time.monotonic()
        if left <= 1:
            break
        res = sv.solve(facelets, target, left)
        if "Error" in res:
            raise RuntimeError(res)
        sol = parse_moves(res.split("(")[0])
        if best is not None and len(sol) >= len(best):
            break  # timed out without improving
        best = sol
        if verbose:
            print(f"  found {len(best)} moves after {budget - (deadline - time.monotonic()):.1f}s")
        target = len(best) - 1

    # verify locally before sending anything
    check = apply_moves(CubieCube(), parse_moves(scramble))
    apply_moves(check, best)
    if check != CubieCube():
        raise RuntimeError("solver produced a wrong solution: " + fmt_moves(best))
    return best


# ---------------------------------------------------------------- API
def get_timer(s):
    txt = s.get(f"{BASE}/timer", timeout=15).text
    mm, ss = map(int, re.search(r"(\d+):(\d+)", txt).groups())
    rnd = int(re.search(r"Round\s+(\d+)", txt).group(1))
    return mm * 60 + ss, rnd


def get_scramble(s):
    return s.get(f"{BASE}/cube", timeout=15).json()["scramble"]


def submit(s, team, solution):
    r = s.post(f"{BASE}/cube", json={"team_name": team, "solution": solution}, timeout=30)
    try:
        return r.json()
    except ValueError:
        return {"http": r.status_code, "body": r.text}


def play_round(s, args):
    remaining, rnd = get_timer(s)
    scramble = get_scramble(s)
    print(f"Round {rnd}: {remaining}s left, scramble has {len(scramble.split())} moves")
    budget = max(5, min(args.budget, remaining - args.safety))
    best = solve(scramble, budget, args.min_len)
    sol = fmt_moves(best)
    print(f"  solution ({len(best)}): {sol}")

    # make sure the scramble did not change while we were thinking
    if get_scramble(s) != scramble:
        print("  round rolled over while solving - skipping")
        return rnd
    if args.dry_run:
        print("  dry run - not submitted")
    else:
        print("  server:", submit(s, args.team, sol))
    return rnd


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--team", required=True)
    ap.add_argument("--loop", action="store_true", help="play every round until interrupted")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--budget", type=float, default=240, help="max solve time per round in seconds")
    ap.add_argument("--min-len", type=int, default=16, help="stop searching below this length")
    ap.add_argument("--safety", type=float, default=20, help="seconds to keep before round end")
    ap.add_argument("--table-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tables"))
    args = ap.parse_args()

    # twophase stores/loads its tables in ./twophase relative to the cwd
    os.makedirs(args.table_dir, exist_ok=True)
    os.chdir(args.table_dir)
    print("loading solver tables (first run builds them, takes a while)...")
    import twophase.solver  # noqa: F401  (triggers table load/generation)

    s = requests.Session()
    last = None
    while True:
        remaining, rnd = get_timer(s)
        if rnd != last:
            last = play_round(s, args)
        if not args.loop:
            break
        remaining, rnd = get_timer(s)
        time.sleep(min(remaining + 3, 60) if rnd == last else 1)


if __name__ == "__main__":
    sys.exit(main())
