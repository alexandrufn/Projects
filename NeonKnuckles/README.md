# Neon Knuckles

A 16-bit style co-op street brawler for Windows, inspired by the late-80s "walk right, clear the street"
beat-'em-up formula. Two fighters, Kai and Vera, battle through four stages of the Iron Serpent gang to get
Vera's kid brother Tomo back. It runs at the Mega Drive / Genesis resolution (320x224) with a limited,
dithered palette. All characters, art, music and sounds are original and generated in code.

## Play

```
run.bat
```

or `python -m pip install -r requirements.txt` then `python main.py`.
Options: `python main.py --stage 3 --diff 2 --players 2` starts on stage 3 on HARD with two players.
To build a standalone Windows executable, run `build_exe.bat` (output: `dist\NeonKnuckles.exe`).

## Controls

| Action       | Player 1          | Player 2           | Gamepad       |
|--------------|-------------------|--------------------|---------------|
| Move         | W A S D           | Arrow keys         | Stick / D-pad |
| Punch        | J or F            | Z, comma or Num 1  | X             |
| Kick         | K or G            | X, period or Num 2 | B or Y        |
| Jump         | L, Space or H     | C, slash or Num 3  | A             |
| Start / join | Enter             | Right Shift        | Start         |
| Pause        | Esc, P or Enter   |                    | Start         |
| Fullscreen   | F11               |                    |               |

With only one player in the game, player 1 can use either keyboard layout. Player 2 can join at any time
by pressing their Start, and a player who runs out of lives can press Start to jump back in.

## Moves

- **Punch combo**: jab, cross, uppercut (the uppercut knocks down). **Kick combo**: kick, roundhouse.
  The combo only continues while your hits connect.
- **Back elbow**: press kick when an enemy is behind you and nobody is in front.
- **Spin kick**: punch + kick together. Hits on both sides and knocks down, but costs 4 health when it lands.
- **Flying kick**: jump, then punch or kick.
- **Grab**: walk into an enemy who is reeling from a hit. Punch for knee strikes (the third one knocks
  them down) or kick to throw them over your shoulder. A thrown enemy bowls over anyone they hit.
- **Weapons**: press punch while standing on one to pick it up. Bats and pipes swing (they break after a
  while), knives are thrown (kick stabs instead), and crates and barrels are lifted and thrown. Crates may
  hold food or cash. Barrels roll.
- **Food** (chicken, soda) and **cash** are collected by walking over them.
- **Grabbed** by a bruiser? Wiggle left and right to break free.

## Stages

| # | Stage | Boss | Hazards and new enemies |
|---|-------|------|--------------------------|
| 1 | Neon Row | **Tank**, a charging, stomping giant who grabs | Street punks, bat swingers, Bruno the grappler |
| 2 | Rustwater Docks | **Razor**, a knife fighter with dash slashes, knife fans and a jumping stab | Gaps in the pier: step into the water and you lose health. Knocked-down enemies drown. Knife throwers, Boulder the heavy |
| 3 | The Ironworks | **Mamba**, who fights with a long chain whip and a spinning chain attack | Steam vents hiss, then blast anyone standing on them, enemies included. Chain fighters |
| 4 | Serpent Tower | **Viper**, a katana boss who calls in backup at half health | A rematch with Tank, then Razor and Mamba together |

Bosses block, wind up with armour (you can't interrupt them then), and get faster at half health.
Every enemy is knocked down after a few hits in a row, so you can't lock anyone in an endless combo.

## Rules

- 64 health, 3 lives, an extra life every 30,000 points. Each stage has a timer. At zero, everyone loses a life.
- Game over offers a **continue** from the same spot (score resets).
- Stage clear bonuses for time left and health left.
- Stages you reach are unlocked on the title screen's STAGE selector. Difficulty (EASY, NORMAL, HARD) scales
  enemy health, damage and how many enemies attack at once. Progress and hi-score are saved in
  `%APPDATA%\NeonKnuckles`.
- The first launch synthesises the music and sound effects (a few seconds). They are cached after that.

## Code layout

| File | Purpose |
|------|---------|
| `main.py` | Window, main loop, save file, command line |
| `config.py` | Resolution, characters, attack table, enemies, bosses, stages, difficulty |
| `inputs.py` | Two-player keyboard and gamepad input |
| `gfx.py` | Pose-driven fighter renderer (IK limbs) with weapons, props, parallax city backgrounds, HUD |
| `textgfx.py` | Pixel font and text helpers (shared with Iron Fist Temple) |
| `entities.py` | Players, enemies and bosses (scripted move system), items, projectiles, steam vents |
| `game.py` | The stage: camera, waves, hit resolution, effects, HUD, pause |
| `scenes.py` | Title, controls, story, stage clear, continue, ending |
| `audio.py` | Synthesised sound effects and five music loops (cached after the first run) |
