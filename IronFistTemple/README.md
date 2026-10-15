# Iron Fist: Temple of the Dragon

A 16-bit style kung-fu tower brawler for Windows, inspired by the classic 8-bit "climb the temple, beat
the boss on every floor" formula. Fight up through five floors, each ending in a guardian boss, to
free Lotus from the Dragon Lord. All characters, art and sounds are original and generated in code.

## Play

```
run.bat
```

or `python -m pip install -r requirements.txt` then `python main.py`.
Options: `python main.py --floor 3 --diff 2` starts on floor 3 on HARD.
To build a standalone Windows executable, run `build_exe.bat` (output: `dist\IronFistTemple.exe`).

## Controls

| Action     | Keyboard              | Gamepad       |
|------------|-----------------------|---------------|
| Move       | Left / Right or A / D | Stick / D-pad |
| Jump       | Up, W or Space        | A             |
| Crouch     | Down or S             | Stick down    |
| Punch      | Z or J                | X             |
| Kick       | X or K                | B or Y        |
| Pause      | Esc or P              | Start         |
| Fullscreen | F11                   |               |

- Standing punch (1 dmg), standing kick (2, hits head height), crouch punch (1), crouch kick (2, hits the
  ground), and a **flying kick** (3) by pressing punch or kick in mid-air.
- **Duck** high knives; **jump** low ones. Hit a projectile to knock it out of the air for points.
- **Grabbers** hold you and drain energy. Tap Left and Right alternately to shake them off.

## The floors

| # | Floor | Guardian | What to expect |
|---|-------|----------|----------------|
| 1 | The Gate of Embers | **Master Hu** | Staff thrusts (high or low, he reads your stance), a spinning attack and a leaping strike |
| 2 | The Moonlit Hall (falling pots) | **Mei the Twin Blade** | Boomerang discs high and low, dash combos, dive attacks |
| 3 | The Jade Corridor (snakes) | **Gorr the Stone** | Huge. Ground-shockwave stomps, a charge you must jump, bone-crushing swings |
| 4 | The Spirit Chamber (flame jets) | **Sen the Seer** | Teleports behind you, fireball volleys, summons imps, point-blank spirit bursts |
| 5 | The Dragon Throne | **Zhao the Dragon Lord** | All of the above plus a flame breath and combos. 60 hit points. Three phases |

### Why the bosses are harder than the usual boss in this genre
- 26 to 60 hit points (a punch does 1, a kick 2, a flying kick 3) and **three phases**: below 66% and 33% health
  they roar, get faster and add moves (more discs, more shockwaves, longer fireball volleys).
- **Armour while winding up**: you can hit them but they won't flinch, so you can't just button-mash.
- They **block** your attacks and counter-attack, and they **read your stance** (crouch and they go low).
- Every attack is telegraphed by a distinct pose, and most end in a recovery window. That is your opening.
- Difficulty (title screen): EASY, NORMAL, HARD change boss health, boss damage and speed.

## Rules

- 48 energy, 3 lives, an extra life every 25,000 points. Each floor has a time limit.
- Dying restarts you at the floor's checkpoint (or the arena if you were fighting the boss).
  The boss keeps the damage you dealt.
- Game over lets you **continue from the same floor** (score resets). Floors you reach are unlocked on the
  title screen's FLOOR selector. Progress and hi-score are saved in `%APPDATA%\IronFistTemple`.

## Code layout

| File | Purpose |
|------|---------|
| `main.py` | Window, main loop, save file, command line |
| `config.py` | Floors, enemy mixes, characters, boss stats, attack table, difficulty |
| `gfx.py` | Pose-driven fighter renderer (IK limbs), temple backgrounds, effects, HUD |
| `textgfx.py` | Pixel font and text helpers |
| `fighters.py` | Player, enemies (grabber, knife thrower, imp, monk, snake), projectiles, hazards |
| `bosses.py` | The five bosses and all of their move scripts |
| `scenes.py` | Title, controls, floor intro, the floor itself, results, game over, ending |
| `audio.py` | Synthesised sound effects and two music loops (cached after the first run) |
