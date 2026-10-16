# Projects

Two small Python games built with [pygame](https://www.pygame.org/).

| Game | Folder |
|------|--------|
| High Noon Reloaded | [`HighNoonReloaded/`](HighNoonReloaded) |
| Iron Fist Temple | [`IronFistTemple/`](IronFistTemple) |

Each folder has its own README with controls and gameplay details.

## Requirements

- Windows
- [Python 3](https://www.python.org/downloads/) (tick "Add Python to PATH" during install)

The only dependency is `pygame>=2.5`, listed in each game's `requirements.txt`.

## Run from source

Open the game's folder and double-click `run.bat`, or from a terminal:

```bash
cd HighNoonReloaded
run.bat
```

`run.bat` installs `pygame` if it is missing, then starts `main.py`.
The same works for `IronFistTemple`.

## Build a standalone `.exe`

The `.exe` files are not stored in this repo (`dist/` is git-ignored). They can be
rebuilt from the source with [PyInstaller](https://pyinstaller.org/), which bundles
the game code, `pygame` and a Python runtime into a single file. The resulting
exe runs on machines without Python.

1. Clone the repo and install Python (see Requirements).
2. Open a terminal in the game's folder:

   ```bash
   cd HighNoonReloaded
   ```

3. Run the build script:

   ```bash
   build_exe.bat
   ```

   It does the following:
   - `pip install -r requirements.txt pyinstaller`
   - `python -m PyInstaller --noconfirm --onefile --windowed --name HighNoonReloaded main.py`

4. The result is `HighNoonReloaded\dist\HighNoonReloaded.exe`.

Repeat in `IronFistTemple` to get `IronFistTemple\dist\IronFistTemple.exe`.

Notes:
- The first build takes a minute or two; each exe is about 14 MB.
- `build/` and `*.spec` files are created next to `dist/` as build leftovers and can be deleted.
- Some antivirus tools flag unsigned PyInstaller exes; if that happens, run from source instead.
