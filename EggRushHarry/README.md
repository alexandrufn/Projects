# Egg Rush Harry

A Chuckie Egg-style platform game, written from scratch with Python and pygame. All graphics and
sounds are generated in code, so there are no image or audio files.

Collect every egg on the farm before the timer runs out. Climb the ladders, jump the gaps, grab
the grain for bonus points, and keep away from the hens. Every level brings more and faster hens.

## The big bird

In levels 1-8 the big bird is locked in its cage in the top-left corner. After you clear level 8
it breaks out: from level 9 on it flies after Harry, so the second half of the game is much
harder. There are **16 levels** in total (8 layouts, played twice). Clear level 16 to win.

## Play

```
run.bat
```

or `python -m pip install -r requirements.txt` followed by `python main.py`.

To make a standalone Windows executable (no Python needed to play it), run `build_exe.bat`.
The file is written to `dist\EggRushHarry.exe`.

## Controls

| Action        | Keys                                  |
|---------------|---------------------------------------|
| Move          | Left / Right or A / D                 |
| Climb         | Up / Down or W / S (next to a ladder) |
| Jump          | Space (or Enter, Z, Ctrl)             |
| Pause         | Esc                                   |
| Quit to title | Q (while paused)                      |

Jumps are committed: you can't steer in mid-air, so line them up first. Jumps are low: they
cross gaps but you can't hop over a hen, so you have to time your route or use the ladders.

## Scoring

| Item          | Points               |
|---------------|----------------------|
| Egg           | 100                  |
| Grain         | 50 (hens eat it too) |
| Level cleared | 500                  |
| Time left     | 10 per second        |
| Extra life    | every 10,000 points  |

You start with 5 lives. The best score is saved in `%APPDATA%\EggRushHarry\save.json`.
