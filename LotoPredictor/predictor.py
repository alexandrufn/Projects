"""Number picker for Loto 6/49, based on the draw history in data/loto649.csv.

How it works
  1. Every number gets a weight: 60% of its all-time draw frequency plus 40% of its frequency in the
     last RECENT draws, so long-run and recent trends both count.
  2. Six distinct numbers are drawn at random with those weights.
  3. The set is only kept if it looks like a typical winning draw (sum, odd/even mix, few neighbours),
     which also avoids the lopsided combinations most people play.

Honest note: every 6/49 draw is independent and uniform, so no method can raise the odds of winning
(see README.md). This makes the picks follow the history; it cannot predict the next draw.
"""
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data", "loto649.csv")
RECENT = 300
ALL_SHARE = 0.6


def load_draws(path=DATA):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))[1:]
    return [[int(x) for x in r[1:7]] for r in rows if len(r) >= 7]


def weights(draws):
    def share(sub):
        counts = [0] * 50
        for d in sub:
            for n in d:
                counts[n] += 1
        total = sum(counts) or 1
        return [c / total for c in counts]
    allf, rec = share(draws), share(draws[-RECENT:])
    return [ALL_SHARE * allf[n] + (1 - ALL_SHARE) * rec[n] for n in range(50)]


def looks_typical(nums):
    s = sum(nums)
    odd = sum(n % 2 for n in nums)
    pairs = sum(1 for a, b in zip(nums, nums[1:]) if b - a == 1)
    return 100 <= s <= 200 and 2 <= odd <= 4 and pairs <= 1 and any(n > 31 for n in nums)


def generate(draws, rng=random):
    w = weights(draws)
    pool = list(range(1, 50))
    pw = [w[n] for n in pool]
    for _ in range(5000):
        picked = set()
        while len(picked) < 6:
            picked.add(rng.choices(pool, weights=pw)[0])
        nums = sorted(picked)
        if looks_typical(nums):
            return nums
    return nums
