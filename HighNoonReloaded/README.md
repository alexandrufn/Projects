# High Noon: Reloaded

A 16-bit style remake of the classic ZX Spectrum-era western duel (*High Noon*, 1984, and the
*Gunfight* games it grew from). Two gunslingers face off across a frontier street. There's
cover in the middle, bullets ricochet off the fences, and the town clock strikes noon.

## Play

```
run.bat
```

or `python -m pip install -r requirements.txt` followed by `python main.py`.

To make a standalone Windows executable you can share (no Python needed), run `build_exe.bat`.
The file is written to `dist\HighNoonReloaded.exe`.

## Modes

- **1 Player: Bounty Hunt.** Seven outlaws, from *Dusty Pete* to *El Diablo*, each more
  dangerous than the last. Beat one (first to 3 hits) to unlock the next. Progress is saved in
  `%APPDATA%\HighNoonReloaded\save.json`.
- **2 Players: Duel.** Head-to-head on one keyboard (or two gamepads), first to 5. The town and
  time of day are random.

## Controls

| Action        | Player 1 | Player 2   | Gamepad    |
|---------------|----------|------------|------------|
| Move          | W A S D  | Arrow keys | Stick/D-pad|
| Fire up       | R        | I          | Y          |
| Fire straight | F        | K          | A / X      |
| Fire down     | V        | , (comma)  | B          |

In 1-player mode both key sets (plus Space) control the sheriff. Esc/P pauses, F11 toggles fullscreen.

## Rules

- Each round opens with a countdown and the bell of the clock tower: **DRAW!** Fire before that
  and your gun jams.
- 6 shots per cylinder, then an automatic reload that leaves you exposed.
- Angled shots ricochet off the top and bottom fences.
- Cacti, barrels and tumbleweeds can be shot apart. Wagons, rocks and the moving stagecoach can't.
- If neither gunslinger lands a hit within 45 seconds, nobody scores the round.

## The outlaws (CPU difficulty)

| # | Outlaw         | Time of day | What makes them dangerous |
|---|----------------|-------------|----------------------------|
| 1 | Dusty Pete     | Morning     | Slow, wild aim |
| 2 | Slim Jim       | Noon        | Steadier hand, the odd dodge |
| 3 | Mad Dog McGraw | Afternoon   | Aggressive, closes the distance |
| 4 | Black Bart     | Dust storm  | Bank shots off the fences, reloads behind cover |
| 5 | **Two-Gun Rosa** (boss) | Sunset | Queen of the desperados: fires both revolvers at once (twin bullets), takes **2 hits** per round |
| 6 | **The Undertaker** (boss) | Dusk | Rides a black stallion: **2 hits** per round, and hitting the horse counts |
| 7 | **El Diablo** (final boss) | Night | A hulking, muscle-bound devil: takes **3 hits** per round, near-instant draw, dodges |

Bosses have an **energy bar** under the HUD. A wounded boss flashes, staggers back, gets a
moment of invulnerability, and becomes **enraged**: faster to react and quicker to fire for
the rest of the round. Their health refills each round, and you still need 3 round wins.

The CPU sees the world with a reaction delay and aiming noise that shrink as the levels rise.
It plans shots by simulating bullet paths, ricochets included.

## Code layout

| File          | Purpose |
|---------------|---------|
| `main.py`     | Window, main loop, save file |
| `config.py`   | Constants, times of day, characters, cover layouts, CPU ladder tuning |
| `gfx.py`      | All graphics, generated in code: sprites, dithered backgrounds, pixel font, UI |
| `audio.py`    | Synthesised sound effects and the whistled western theme (cached after first run) |
| `entities.py` | Gunslingers, bullets, cover, particles |
| `ai.py`       | CPU opponent |
| `scenes.py`   | Title, controls, bounty board, intro, duel, results, ending |

There are no asset files. Every pixel and every sound is generated at startup.
