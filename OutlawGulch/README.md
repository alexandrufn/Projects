# Outlaw Gulch

A vertical-scrolling western shoot-'em-up in the spirit of Capcom's arcade classic *Gun.Smoke*
(1985), written from scratch with Python and pygame. All graphics and sounds are generated in
code, so there are no image or audio files.

You are a bounty hunter pushing up the trail. Gun down the outlaws, gunmen, dynamite throwers and
charging riders, grab the pickups, and take down the boss waiting at the end of each stage.

## Stages and bosses

| Stage | Setting | Boss |
|-------|---------|------|
| 1 | Dusty Town | One-Eyed Jack: sweeps the street, fires fans and rings of bullets |
| 2 | Canyon Pass | Lola La Loca: fans of knives and wild dashes at you |
| 3 | Rail Yard | Iron Mike: a gatling gun that sprays spirals, calls in outlaws |
| 4 | Silver Mine | El Cobra: triple dynamite lobs and cavalry charges |
| 5 | Hacienda | General Diablo: changes tactics as he gets hurt |

Each boss gets a Wanted poster before the fight.

## What's different from the original

- You have **3 hearts** (up to 5) instead of dying in one hit, plus **bombs** that wipe the screen.
- **Free aim:** hold the left mouse button to shoot towards the cursor, or use the classic
  three fixed shots (left diagonal, straight ahead, right diagonal).
- Smashable **barrels**, five different **bosses**, and gun smoke.

## Play

```
run.bat
```

or `python -m pip install -r requirements.txt` followed by `python main.py`.

To make a standalone Windows executable (no Python needed to play it), run `build_exe.bat`.
The file is written to `dist\OutlawGulch.exe`.

## Controls

| Action              | Keys                              |
|---------------------|-----------------------------------|
| Move                | WASD or arrow keys                |
| Shoot ahead         | K or Space                        |
| Shoot diagonally    | J (left) / L (right); hold both with K for a triple shot |
| Free aim            | Hold left mouse button            |
| Bomb                | B or right mouse button           |
| Pause / quit        | Esc / Q (while paused)            |

## Pickups

| Item     | Effect                              |
|----------|-------------------------------------|
| Heart    | +1 health                           |
| Boots    | Faster movement (lost if you die)   |
| Shotgun  | Spread shot, short range, 22 s      |
| Rifle    | Rapid piercing shots, 22 s          |
| Bomb     | +1 bomb (max 3)                     |
| Cash bag | +$500                               |

Barrels always drop something. You get an extra life every $20,000. Your best score is saved in
`%APPDATA%\OutlawGulch\save.json`.
