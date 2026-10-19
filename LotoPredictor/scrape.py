"""Download the Romanian Loto 6/49 draw history from loto.ro into data/loto649.csv.

Run:  python scrape.py            (all years, 1998 to now)
      python scrape.py 2024 2026  (a year range)
"""
import csv
import datetime
import os
import re
import sys
import time
import urllib.parse
import urllib.request

URL = ("https://www.loto.ro/loto-new/newLotoSiteNexioFinalVersion/web/app2.php/"
       "jocuri/649_si_noroc/rezultate_extragere.html")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "loto649.csv")
BLOCK = re.compile(r'numere-extrase">(.*?)</div>.*?Detalii castiguri\s+la\s+(\S+)\s+din <span>(\d\d\.\d\d\.\d{4})', re.S)


def fetch(year, month):
    data = urllib.parse.urlencode({"select-year": year, "select-month": month}).encode()
    req = urllib.request.Request(URL, data=data, headers={"User-Agent": "Mozilla/5.0 (LotoPredictor history import)"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read().decode("utf-8", "replace")


def parse(html):
    """Yield (date, [six numbers]) for every 6/49 draw on the page."""
    for balls, game, date in BLOCK.findall(html):
        if game != "6/49":
            continue
        nums = [int(n) for n in re.findall(r"/bile/(\d+)\.png", balls)]
        if len(nums) == 6 and len(set(nums)) == 6 and all(1 <= n <= 49 for n in nums):
            d, m, y = date.split(".")
            yield "%s-%s-%s" % (y, m, d), nums


def main():
    now = datetime.date.today()
    y0 = int(sys.argv[1]) if len(sys.argv) > 1 else 1998
    y1 = int(sys.argv[2]) if len(sys.argv) > 2 else now.year
    draws = {}
    for y in range(y0, y1 + 1):
        for m in range(1, 13):
            if (y, m) > (now.year, now.month):
                break
            try:
                for date, nums in parse(fetch(y, m)):
                    draws[date] = sorted(nums)
            except OSError as e:
                print("failed", y, m, e)
            time.sleep(0.4)           # be gentle with the server
        print(y, "->", len(draws), "draws so far", flush=True)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["date", "n1", "n2", "n3", "n4", "n5", "n6"])
        for date in sorted(draws):
            w.writerow([date] + draws[date])
    print("wrote", len(draws), "draws to", OUT)


if __name__ == "__main__":
    main()
