# Loto 6/49 generator

A small desktop app (Python + Tkinter) with a single button, **Genereaza numerele loto**, that shows
six numbers picked from the Romanian Loto 6/49 draw history.

## Run

```
run.bat
```

or `python app.py`. Python 3 is all you need (Tkinter ships with it, no extra packages).

## Data

`data/loto649.csv` holds 2,311 draws, from 1998 up to 18 October 2026, taken from
[loto.ro](https://www.loto.ro). To refresh it after new draws:

```
python scrape.py
```

## How the numbers are chosen

1. Each number gets a weight: 60% of how often it was drawn over the whole history plus 40% of how
   often it was drawn in the last 300 draws.
2. Six distinct numbers are sampled with those weights.
3. The set is kept only if it looks like a typical winning draw: sum between 100 and 200, 2 to 4 odd
   numbers, at most one pair of neighbours, and at least one number above 31.

## Please read: no method can predict the lottery

I backtested several approaches on the last 800 draws (each predicting from earlier draws only):

| Method                         | Avg. numbers matched per draw |
|--------------------------------|-------------------------------|
| Random picks                   | 0.753                         |
| Most frequent overall          | 0.766                         |
| Most frequent in last 200      | 0.750                         |
| "Overdue" numbers (longest gap)| 0.759                         |
| Frequency-weighted sampling    | 0.709                         |
| *Expected by pure chance*      | *0.735*                       |

Every method lands on the chance level, and a chi-square test finds the whole history
statistically consistent with a fair, uniform draw. Each draw is independent, so past results say
nothing about the next one. The app follows the history because that was the request; it does not
improve your odds. The structure filter has one real, small benefit: it avoids lopsided sets that
many players choose, so a win is less likely to be shared with others.

Play responsibly.
