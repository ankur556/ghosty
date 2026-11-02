# Ghosty 👻

A hand-drawn, animated Windows desktop companion. No image assets or network
services are needed. The original version is
preserved as `main_original.py`.

**New: music-reactive dancing and a miniature typing keyboard.** See
[UPGRADE.md](UPGRADE.md) for setup, privacy controls, feature checks, and limitations.
Both additions are opt-in; no permanent panel is displayed.

## Run

In VS Code, select your existing environment with **Python: Select Interpreter**,
then open a new terminal in this folder:

```powershell
python main.py
```

Your working environment was found at `C:\Users\kante\Ghosty\.venv`.
You can also run directly without activating it:

```powershell
& 'C:\Users\kante\Ghosty\.venv\Scripts\python.exe' main.py
```

For a new environment only: `python -m pip install -r requirements.txt`.
Close the old Ghosty instance before starting the upgraded version.

## Interactions

| Action | Reaction |
| --- | --- |
| Click | Happy eyes, bounce, hearts |
| Double-click | Excitement (single click waits for the double-click interval) |
| Hold for 650 ms | Embarrassed blush |
| Drag | Spring following, directional tilt and stretch |
| Release a drag | Squash and elastic settling |
| Repeated clicks | Playful anger |
| Bring the pointer near | Curiosity and smooth eye tracking |
| Move quickly toward Ghosty | A brief startled retreat |
| Leave Ghosty alone | Occasional personality actions, then sleepiness and sleep |
| Right-click Ghosty or tray icon | Controls, settings, emotion previews, Exit |
| Double-click tray icon | Disable click-through and bring Ghosty home |

The ghost body remains about 120 logical pixels tall. The larger transparent
window reserves space for glow, particles, and a fading speech bubble. Windows
display scaling can make logical pixels occupy more physical screen pixels.
The entire window stays within a monitor's available work area, above its taskbar.

## Settings

- **Pause** freezes animation, autonomous actions, and typing monitoring; dragging
  and the menu remain available.
- **Sleep** keeps Ghosty asleep until awakened through the menu or direct interaction.
- **Quiet mode** suppresses speech and autonomous travel, and reduces animation intensity.
- **React to typing** is **off by default**. Enable it explicitly in the menu.
- **Allow wandering**, **Movement speed**, **Animation intensity**, and **Speech
  frequency** customize the companion.
- **Click-through** passes mouse input to apps beneath Ghosty. It is only available
  when the system tray exists. Right-click the tray to disable it, or double-click
  the tray icon to recover. It resets on restart to prevent accidental lockout.
- **Preview emotion** exposes all twelve emotions and idle for testing.
- **Bring Ghosty home** resets the position to the primary monitor's bottom right.

Preferences persist through Qt's Windows settings storage under
`HKEY_CURRENT_USER\Software\Ghosty\DesktopCompanion`. Pause, manual sleep, and
click-through are deliberately session-only.

## Keyboard privacy

`activity.py` installs a Windows `WH_KEYBOARD_LL` callback **only when enabled**.
Generic typing reactions count activity without reading key identifiers. Individual
key highlights require a separate opt-in and a fail-closed editor/privacy check.
Only temporary pressed-key animation state is retained; text is never decoded,
displayed, logged, or transmitted. No clipboard access is used. See
[the full privacy boundaries](UPGRADE.md#privacy-boundaries-and-limitations).

The callback runs through Qt's Windows message loop. It performs no I/O and never
blocks or suppresses keyboard shortcuts. Disable the option or pause Ghosty to
remove the hook immediately. Cleanup also removes it on exit. Activity includes
shortcut/repeat events; Ghosty cannot distinguish writing from other key usage.
Windows secure desktops and some protected applications may not report activity.

Immediate typing pulses now summon the keyboard and animate the hands; the
keyboard fades after 2.5 seconds of inactivity. Sleepiness starts after roughly 150 seconds without
pet interaction or detected typing; sleep starts after 300 seconds. With typing
monitoring off, typing cannot reset the idle timer. Cursor tracking refers to the
mouse pointer, not the text caret or application contents.

## Architecture and staged checks

The base pet uses PySide6 and the standard library. The music/typing upgrade adds
NumPy, SoundCard, and comtypes; install from `requirements.txt`.
Run the app with `python main.py` after each change. Tests use isolated preferences
and never enable global keyboard monitoring.

| Stage | Files | How to check |
| --- | --- | --- |
| 1. Artwork and eyes | `renderer.py` | Look for white gradient body, halo, cheeks, moving gaze, and waving hem. |
| 2. Emotions | `behavior.py`, `renderer.py` | Right-click → Preview emotion; inspect every expression. |
| 3. Body animation | `animations.py`, `movement.py` | Observe breathing, blinking, hover, and elastic settling. |
| 4. Mouse gestures | `interactions.py`, `ghost.py` | Try click, double-click, hold, drag, release, and repeated clicks. |
| 5. Typing | `activity.py`, `ghost.py` | Enable typing reactions; type in Notepad/VS Code, pause, then disable. |
| 6. Personality | `behavior.py`, `ghost.py` | Wait 18–40 seconds between idle actions; direct interactions take priority. |
| 7. Effects and speech | `particles.py`, `dialogue.py` | Preview Love/Sad/Confused/Sleeping; test Quiet mode. |
| 8. Controls and performance | `settings.py`, `ghost.py`, `main.py` | Restart after changing settings; test tray recovery and screen edges. |

```powershell
python -m unittest -v test_ghosty
python preview.py
python smoke_windows.py
```

`preview.py` writes `ghosty-expressions.png`. The native smoke check briefly shows
the pet, checks focus preservation and tray flags, installs/removes the activity
hook without decoding input, then exits automatically after two seconds.

The automated suite covers gesture exclusivity, behavior priorities, idle sleep,
typing cooldowns, spring stability at different frame rates, bounded particles,
transparent expression rendering, persistence, screen clamping, and cleanup.

Manual Windows checks still matter: drag across your monitor arrangement, unplug a
monitor, try different DPI scales, use click-through over a real app, and verify
ordinary shortcuts while typing reactions are enabled. The native smoke test
checks API wiring, not every application's input handling. Animations target
about 60 FPS while active and 30 FPS when idle/asleep; Pause uses a 10 Hz timer
without repainting. Particle count is capped at 28. Actual CPU usage depends on
your desktop and display scale.

Implementation references: [Qt translucent widgets](https://doc.qt.io/qtforpython-6/PySide6/QtWidgets/QWidget.html)
and [Microsoft low-level keyboard callback](https://learn.microsoft.com/en-us/windows/win32/winmsg/lowlevelkeyboardproc).
