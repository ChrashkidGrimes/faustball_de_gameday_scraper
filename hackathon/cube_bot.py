#!/usr/bin/env python3
"""Rubik's-cube bot for https://hackathon.kleopi.net

Game (from /docs and probing the API):
  GET  /cube   -> {"scramble": "<100 moves, Singmaster notation>"}  (new scramble every round)
  POST /cube   <- {"team_name": ..., "solution": "<moves>"}
               -> {"solved": true, "moves": n, "score": s, "Optimal Moves": k, "recorded": true}
  GET  /timer  -> "Next reset in MM:SS\nRound N\nPeriod 10 minutes"

Scoring (observed): score ~= 120 * "Optimal Moves" / moves, e.g. 100 moves -> 5 pts,
18 moves vs. optimal 20 -> 133 pts. The scoreboard TOTAL sums every recorded submission.

Fewer moves = more points, so the bot searches for the shortest solution it can find
(Kociemba two-phase, iteratively tightening the length bound) within a time budget,
verifies it locally and submits once per round.

Usage:
  pip install RubikTwoPhase requests
  python cube_bot.py --team claudine            # solve + submit the current round
  python cube_bot.py --team claudine --loop     # keep going, once per round
  python cube_bot.py --team claudine --dry-run  # solve only, don't submit

Optional, much stronger (finds 17/18-move solutions more often):
  git clone https://github.com/efrantar/rob-twophase && make -C rob-twophase
  python cube_bot.py --team claudine --loop --rob rob-twophase/twophase

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
ROB = None  # (binary, table_dir) for rob-twophase, set from the command line


def rob_solve(facelets, seconds, threads):
    """Best solution rob-twophase finds in `seconds` (it always uses the full time)."""
    import subprocess
    binary, table_dir = ROB
    p = subprocess.Popen([binary, "-t", str(threads), "-m", str(int(seconds * 1000)), "-l", "-1"],
                         cwd=table_dir, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        p.stdin.write(f"solve {facelets}\n")
        p.stdin.flush()
        timed = False
        for line in p.stdout:
            line = line.strip()
            if timed:
                m = re.fullmatch(r"(.*)\((\d+)\)", line)
                return parse_moves(m.group(1)) if m else None
            if "error" in line.lower():
                raise RuntimeError("rob-twophase: " + line)
            timed = line.endswith("ms")
    finally:
        p.kill()


def solve(scramble, budget, min_len=0, verbose=True, threads=4):
    """Shortest solution found within `budget` seconds, as a list of moves."""
    import twophase.solver as sv
    from twophase.cubie import CubieCube

    state = apply_moves(CubieCube(), parse_moves(scramble))
    facelets = state.to_facelet_cube().to_string()
    t0 = time.monotonic()
    deadline = t0 + budget
    log = lambda msg: verbose and print(f"  {msg} after {time.monotonic() - t0:.1f}s")

    # quick fallback (~20 moves within a fraction of a second)
    best = parse_moves(sv.solve(facelets, 20, 1).split("(")[0])
    log(f"found {len(best)} moves")

    if ROB:
        # rob-twophase: multithreaded C++, searches the remaining time for the shortest solution
        left = deadline - time.monotonic() - 3  # table loading
        if left > 1:
            sol = rob_solve(facelets, left, threads)
            if sol and len(sol) < len(best):
                best = sol
            log(f"rob-twophase: {len(sol) if sol else '-'} moves")
    else:
        target = len(best) - 1
        while target >= min_len:
            left = deadline - time.monotonic()
            if left <= 1:
                break
            sol = parse_moves(sv.solve(facelets, target, left).split("(")[0])
            if len(sol) >= len(best):
                break  # timed out without improving
            best = sol
            log(f"found {len(best)} moves")
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
    best = solve(scramble, budget, args.min_len, threads=args.threads)
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
    ap.add_argument("--budget", type=float, default=480, help="max solve time per round in seconds")
    ap.add_argument("--min-len", type=int, default=12, help="stop searching below this length")
    ap.add_argument("--safety", type=float, default=20, help="seconds to keep before round end")
    ap.add_argument("--rob", help="path to a compiled rob-twophase binary (github.com/efrantar/rob-twophase)")
    ap.add_argument("--threads", type=int, default=os.cpu_count() or 4, help="threads for rob-twophase")
    ap.add_argument("--table-dir", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".tables"))
    args = ap.parse_args()

    # twophase stores/loads its tables in ./twophase relative to the cwd
    global ROB
    os.makedirs(args.table_dir, exist_ok=True)
    if args.rob:
        rob_dir = os.path.join(args.table_dir, "rob")  # rob-twophase writes its 676MB table here on first run
        os.makedirs(rob_dir, exist_ok=True)
        ROB = (os.path.abspath(args.rob), rob_dir)
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
