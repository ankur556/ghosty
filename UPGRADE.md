# Music + typing companion

This upgrade extends the existing pet; the drawing, emotions, dragging, tray,
speech, transparency, and Exit remain in place. No permanent panel is added.

## Start

The dependencies were installed into your existing virtual environment. From this
project folder in VS Code:

```powershell
& 'C:\Users\kante\Ghosty\.venv\Scripts\python.exe' main.py
```

With that environment activated, `python main.py` works as before. For another
environment, install the dependencies first:

```powershell
python -m pip install -r requirements.txt
python main.py
```

New dependencies: **NumPy** (small audio feature calculations), **SoundCard**
(Windows output-loopback access), and **comtypes** (accessibility metadata used
to restrict key highlighting). Missing audio/accessibility support does not prevent
the base pet from running. It disables the unavailable reaction instead.

## Enable the features

Right-click Ghosty or its tray icon:

1. **Typing companion (generic motions)**: enables global activity notifications.
   A keyboard appears on the first key-down; hands tap without revealing which key
   was pressed. This also works outside the approved editor list.
2. **Show individual keys (approved editors only)**: a separate, explicit opt-in.
   This also enables the typing companion. Keycap highlights require a recognized,
   focused, non-password editor control in `notepad.exe` or `code.exe`.
3. **Dance to computer audio**: enables output-only loopback. Start music through
   your default speakers or headphones and allow about two seconds for dancing.

All three options default to **off** on a fresh installation. The previous typing
preference is preserved, but it never grants permission to show individual keys.
Explicitly enabled preferences survive restarts.

**Disable typing and key highlights now** clears the keyboard immediately and
uninstalls monitoring. **Pause** stops both monitoring workers and clears transient
input state. **Sleep** deliberately stays asleep; automatic idle sleep can wake
gently to sustained, sufficiently loud audio. **Quiet mode** reduces movement and
suppresses speech, dramatic bass reactions, and spins. Existing click-through and
tray recovery still work.

## What you will see

- Rounded miniature US-QWERTY layout, key shadows, a soft halo, and independent
  eased keycap presses. Shift and other held keys stay lit until release.
- Temporary hands alternate taps, eyes look down, and the body gently squashes.
  Faster typing adds excitement, tiny stars, and a playful wobble.
- After 2.5 seconds without activity, the keyboard fades away. Resuming typing
  reverses that fade smoothly. Holding a recognized key keeps the keyboard visible.
- Music produces a quiet sway or a livelier wiggle depending on smoothed energy
  and onset activity. Strong onsets add spring bounces; occasional strong bass
  increases cause a surprised hop. Spins and note particles have cooldowns.
- During typing, the same music glow and a smaller sway continue underneath.
  Stopping typing restores the fuller dance. Dragging takes priority immediately.

The keyboard is part of the same non-focusable transparent window. The ghost body
stays about 120 logical pixels tall; the window reserves extra transparent space
below it for the keyboard and clamps that space within monitor work areas.

## Privacy boundaries and limitations

**No text decoding, typed sentences, clipboard reads, key logs, audio files,
network requests, or external services.** Fixed keycap labels are artwork, not
text reconstructed from your input. In generic mode, the keyboard-data pointer
is never dereferenced. In highlight mode only the virtual-key identifier is read,
and only after the privacy gate accepts the current context.

The gate reads only process identity and accessibility metadata: focused control
class/type, process ID, focus flag, and password flag. It never reads accessible
names, values, document text, or window titles. Allowed controls are Notepad
Edit/RichEdit controls and VS Code's specifically identified Monaco `inputarea`.
Terminals, browsers, dialogs, generic VS Code textboxes, password controls, and
unknown providers do **not** receive individual-key visualization.

Foreground/focus/desktop changes invalidate approval. Metadata approvals expire
after 200 ms and must match the live foreground/native-focus identity. Key states
are cleared on invalidation, release, pause, disable, dragging, and exit. Windows
secure desktops suppress all activity and clear the keyboard. Accessibility
providers vary: **password detection is not perfect**, and an editor which does
not expose the required metadata gets generic motions only. Even an approved code
editor can contain secrets as ordinary code; turn highlights off when working
with sensitive material. The tray disable control is always available.

VS Code may not expose its Monaco class through accessibility on every version or
configuration. Ghosty deliberately does not relax the rule to make those versions
highlight keys. This is an intentional privacy boundary, not song/text recognition.
The displayed keyboard is a compact US-QWERTY layout, not a configurable mapping
of every national keyboard, numpad, or IME.

Audio uses only the loopback endpoint corresponding to the **default Windows
output device**, never a microphone fallback. Each 1024-frame block is reduced
to RMS, 30–180 Hz energy, and onset estimates, then discarded. Only feature tuples
reach Qt. Output-device changes are checked about every two seconds. If a device
disconnect or protected/exclusive audio stream makes capture fail, Ghosty disables
music reactions and shows a tray message; select a working output and enable it again.

Music detection is an energy/onset heuristic, **not song identification, exact BPM,
or reliable separation of music from speech**. Short notification sounds do not
usually meet the two-second activity threshold, but sustained speech/game audio
can also trigger dancing. Silence fades dancing out after about two seconds.

The audio and accessibility checks use separate, bounded worker processes. This
keeps blocking device reads and slow accessibility providers out of Qt's GUI
thread and allows deterministic cleanup if a driver/provider stalls. Queues are
bounded; no audio buffers or key histories are sent through them. Rendering runs
at about 60 FPS while active and returns to the existing idle rate otherwise.

## Stages and checks

All stages are integrated; these commands and checks let you inspect them separately.

| Stage | Implementation | Check |
| --- | --- | --- |
| 1. Keyboard appearance | `keyboard_overlay.py` | Run the synthetic preview; verify the compact layout and transparent margins. |
| 2. Opt-in keys | `activity.py`, `input_privacy.py` | Enable highlights in Notepad; test A, Space, Enter, held Shift and combinations. Switch to a browser: highlights clear. |
| 3. Hands | `typing_animation.py` | Type at different speeds; stop for three seconds; resume during the fade. |
| 4. Loopback/features | `audio_reactive.py` | Enable music with output playing. Switch the Windows default output to headphones. |
| 5–6. Dancing/effects | `dance.py`, `renderer.py`, `particles.py` | Compare quiet and energetic audio; stop playback; verify fade-out and occasional notes. |
| 7. Blending | `animation_controller.py`, `ghost.py` | Type while listening, then stop; drag during both. |
| 8. Settings/cleanup | `settings.py`, tests | Pause, disable, restart, and Exit; ensure no worker remains. |

```powershell
python -m unittest -v test_ghosty test_reactions
python preview_reactions.py
python smoke_windows.py
python smoke_reactions_windows.py
```

The unit tests and preview use **synthetic** input/audio only. The first native
smoke script briefly checks the keyboard-hook lifecycle without decoding input.
The second checks metadata-worker startup and cleanup without a keyboard hook.
To explicitly test output capture for five seconds, with no audio saved:

```powershell
python smoke_reactions_windows.py --audio
```

The rendered preview is `ghosty-reactions.png`. Native checks passed with the
installed Python 3.15/PySide6 6.12 environment. comtypes emits a Python 3.15
compatibility warning; the metadata worker's native smoke test passed here.

Manual verification is still needed for your editor's accessibility provider,
actual simultaneous key input, secure-desktop transitions, device unplugging,
and mixed-DPI monitor layouts. The tests do not type into your applications or
claim those application-specific scenarios have already been exercised.

API references: [SoundCard loopback documentation](https://soundcard.readthedocs.io/en/stable/),
[Windows loopback capture](https://learn.microsoft.com/en-gb/windows/win32/coreaudio/loopback-recording),
and [UI Automation focused element](https://learn.microsoft.com/en-us/windows/desktop/api/UIAutomationClient/nf-uiautomationclient-iuiautomation-getfocusedelement).
