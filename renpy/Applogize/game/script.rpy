################################################################################
## Applogize - Main Game Script
################################################################################

## Game Variables ##############################################################

default energy = 20
default max_energy = 20
default rage_gauge = 70
default stage = 0
default player_gender = None
default found_clues = set()
default total_clues = 8
default timer_seconds = 180
default timer_running = False
default rescue_used = False

## Voice guess (Stage 1) – STT via speechemotionanalysis server /analyze only (no check_answer)
default analyze_url = "http://localhost:19000/analyze"
default guess_text = ""
default voice_status = ""  # "", "recording", "ok", "error"
default voice_error_message = ""  # last exception message when voice_status == "error"
default server_guess_result = None  # True/False/None after submit

## Characters ##################################################################

define gf = Character("Girlfriend", color="#ff6b9d", what_color="#ffffff")
define mc = Character("Me", color="#4a90d9", what_color="#ffffff")

## Placeholder Images ##########################################################

image bg_black = Solid("#000000")
image bg_dark = Solid("#0a0a14")
image bg_room = Solid("#1a1a2e")
image bg_videocall = Solid("#0f0f23")

image gf normal = "images/characters/idle_pose.png"
image gf angry1 = "images/characters/angry_face1.png"
image gf angry2 = "images/characters/angry_face2.png"

image firegirl = "images/characters/firegirl.jpeg"
image badending = Transform(
    "images/characters/badending.jpeg",
    xsize=config.screen_width,
    ysize=config.screen_height,
)

image goldengirl = "images/characters/goldengirl.jpeg"
image happyending = Transform(
    "images/characters/happyending.jpeg",
    xsize=config.screen_width,
    ysize=config.screen_height,
)

screen bad_ending_title():
    zorder 100
    text "GAME OVER":
        xalign 0.02
        yalign 0.95
        size 80
        color "#ffffff"
        outlines [(4, "#000000", 0, 0)]

screen clear_title():
    zorder 100
    text "CLEAR":
        xalign 0.5
        yalign 0.2
        size 80
        color "#ffffff"
        outlines [(4, "#000000", 0, 0)]

## Helper Functions ############################################################

init python:
    def add_clue(clue_name):
        store.found_clues = store.found_clues | {clue_name}

    def get_apple_color():
        g = store.rage_gauge
        # In Stage 1 and 2, rage_gauge represents anger:
        # 0 = calm, 100 = maximum anger.
        if g <= 0:
            return "#ffd700"   # calm / best state
        elif g <= 25:
            return "#88cc33"
        elif g <= 50:
            return "#33cc33"
        elif g <= 75:
            return "#ff6666"
        else:
            return "#cc3333"   # very angry

    def format_timer(seconds):
        m = seconds // 60
        s = seconds % 60
        return "{:01d}:{:02d}".format(m, s)

    # ---- Voice guess: STT via speechemotionanalysis server POST /analyze (WAV -> transcript) ----
    import urllib.request
    import urllib.error
    import json
    import subprocess
    import os

    def _record_and_stt_worker():
        """Record WAV via script, POST to analyze_url, set guess_text from transcript."""
        script_dir = renpy.config.gamedir
        wav_path = os.path.join(script_dir, "record_temp.wav")
        record_script = os.path.join(script_dir, "record_to_wav.py")
        url = store.analyze_url
        try:
            proc = subprocess.run(
                ["python3", record_script],
                capture_output=True,
                text=True,
                timeout=15,
                cwd=script_dir,
            )
            out = (proc.stdout or "").strip()
            if out.startswith("ERROR:") or proc.returncode != 0:
                err = (out[6:].strip().lstrip(" ") if out.startswith("ERROR:") else (proc.stderr or "Recording failed")[:120])[:120]
                def set_err():
                    store.voice_status = "error"
                    store.voice_error_message = err
                    store.guess_text = store.guess_text
                renpy.invoke_in_main_thread(set_err)
                return
            if not os.path.isfile(wav_path):
                def set_err():
                    store.voice_status = "error"
                    store.voice_error_message = "No WAV file created."
                    store.guess_text = store.guess_text
                renpy.invoke_in_main_thread(set_err)
                return
            with open(wav_path, "rb") as f:
                wav_data = f.read()
            boundary = "----RenPyFormBoundary" + str(abs(hash(wav_path)))
            body = (
                b"--" + boundary.encode() + b"\r\n"
                b'Content-Disposition: form-data; name="file"; filename="audio.wav"\r\n'
                b"Content-Type: audio/wav\r\n\r\n"
                + wav_data + b"\r\n"
                b"--" + boundary.encode() + b"--\r\n"
            )
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "multipart/form-data; boundary=" + boundary},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=70) as resp:
                body_json = json.loads(resp.read().decode("utf-8"))
            transcript = (body_json.get("transcript") or "").strip()
            # Keep wav for debugging; uncomment to clean up:
            # try:
            #     os.remove(wav_path)
            # except Exception:
            #     pass
            def set_result():
                store.guess_text = transcript
                store.voice_status = "ok" if transcript else "error"
            renpy.invoke_in_main_thread(set_result)
        except subprocess.TimeoutExpired:
            def set_err():
                store.voice_status = "error"
                store.voice_error_message = "Recording timed out."
                store.guess_text = store.guess_text
            renpy.invoke_in_main_thread(set_err)
        except FileNotFoundError:
            def set_err():
                store.voice_status = "error"
                store.voice_error_message = "python3 or record_to_wav.py not found. Install Python 3 and pyaudio."
                store.guess_text = store.guess_text
            renpy.invoke_in_main_thread(set_err)
        except Exception as e:
            err = str(e)[:120]
            def set_err():
                store.voice_status = "error"
                store.voice_error_message = err
                store.guess_text = store.guess_text
            renpy.invoke_in_main_thread(set_err)

    def start_voice_record():
        """Start recording in a thread; UI shows status via store.voice_status."""
        import threading
        store.voice_status = "recording"
        store.voice_error_message = ""
        try:
            renpy.restart_interaction()
            renpy.notify("Recording...")
        except Exception:
            pass
        t = threading.Thread(target=_record_and_stt_worker)
        t.daemon = True
        t.start()

    class ContinueGuessAction(renpy.store.Action):
        """Proceed without server check (STT only)."""
        def __call__(self):
            return renpy.store.Return("correct")

    def run_tracker_start():
        """Start tracker (camera) in background. On macOS uses .app bundle for GUI without Terminal."""
        import subprocess
        import os
        import sys
        base = renpy.config.basedir
        tracker_dir = os.path.abspath(os.path.join(base, "..", "..", "backend", "tracker"))
        tracker_py = os.path.join(tracker_dir, "tracker.py")
        if not os.path.isfile(tracker_py):
            gamedir = renpy.config.gamedir
            tracker_dir = os.path.abspath(os.path.join(gamedir, "..", "..", "..", "backend", "tracker"))
            tracker_py = os.path.join(tracker_dir, "tracker.py")
        venv_python = os.path.join(tracker_dir, ".venv", "bin", "python3") if sys.platform != "win32" else os.path.join(tracker_dir, ".venv", "Scripts", "python.exe")
        if not os.path.isfile(venv_python):
            venv_python = "python3" if sys.platform != "win32" else "python"
        try:
            if sys.platform == "darwin":
                # macOS: use .app bundle so it runs with full GUI permissions (no Terminal)
                app_path = os.path.join(tracker_dir, "Tracker.app")
                macos_dir = os.path.join(app_path, "Contents", "MacOS")
                launcher_path = os.path.join(macos_dir, "launcher")
                plist_path = os.path.join(app_path, "Contents", "Info.plist")
                if not os.path.exists(macos_dir):
                    os.makedirs(macos_dir)
                launcher_script = '''#!/bin/bash
TRACKER_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$TRACKER_DIR"
exec "$TRACKER_DIR/.venv/bin/python3" tracker.py
'''
                with open(launcher_path, "w") as f:
                    f.write(launcher_script)
                os.chmod(launcher_path, 0o755)
                plist_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>launcher</string>
<key>CFBundleIdentifier</key><string>com.applogize.tracker</string>
<key>CFBundleName</key><string>Tracker</string>
<key>LSUIElement</key><true/>
</dict></plist>
'''
                with open(plist_path, "w") as f:
                    f.write(plist_content)
                subprocess.Popen(["open", app_path])
            elif sys.platform == "win32":
                # Windows: use start to open new window
                subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", venv_python, tracker_py], cwd=tracker_dir)
            else:
                subprocess.Popen([venv_python, tracker_py], cwd=tracker_dir, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            renpy.notify("Camera started. Close the camera window when done.")
        except Exception as e:
            renpy.notify("Could not start camera: " + str(e)[:50])

    def run_tracker_stop():
        """Kill the tracker (camera) process."""
        import subprocess
        import sys
        try:
            if sys.platform == "darwin":
                # pkill kills process by command line match (tracker.py)
                subprocess.run(["pkill", "-f", "tracker.py"], capture_output=True, timeout=2)
            elif sys.platform == "win32":
                subprocess.run(["taskkill", "/F", "/FI", "WINDOWTITLE eq*tracker*"], capture_output=True, timeout=2)
        except Exception:
            pass

    class RunTrackerAction(renpy.store.Action):
        """Start tracker (camera) in background."""
        def __call__(self):
            run_tracker_start()
            return None

################################################################################
## Game Flow
################################################################################

label start:
    scene bg_black
    with fade

    $ quick_menu = False

    call screen character_select_screen
    $ player_gender = _return

    # Intro video (click or key to skip). Use .mkv with Opus audio; Ren'Py does not support AAC.
    $ renpy.movie_cutscene("video/intro_video.mkv", stop_music=True)

    jump stage1

## Stage 1 - Find the Reason ###################################################

label stage1:
    $ stage = 1
    $ timer_seconds = 180
    $ timer_running = True
    $ found_clues = set()
    $ rage_gauge = 70

    scene bg_dark
    with dissolve

    $ quick_menu = True
    show gf normal at truecenter
    with dissolve

    gf "..."
    gf "You seriously don't know? It's pathetic you have no idea why I'm upset."

    mc "(What did I do wrong...?)"
    mc "(Let me check my phone for clues.)"

    hide gf
    with dissolve

    $ quick_menu = False

label stage1_phone_loop:
    $ timer_running = True
    call screen phone_main_screen

    if _return == "make_guess":
        jump stage1_guess
    elif _return == "timeout":
        jump stage1_timeout
    else:
        jump stage1_phone_loop

label stage1_timeout:
    $ timer_running = False
    jump ending_gameover

label stage1_guess:
    $ timer_running = False
    $ guess_text = ""
    $ voice_status = ""
    $ voice_error_message = ""
    call screen voice_guess_screen

    if _return == "correct":
        jump stage1_correct
    elif _return == "back_to_phone":
        $ timer_seconds = max(timer_seconds, 60)
        jump stage1_phone_loop
    else:
        jump stage1_wrong

label stage1_wrong:
    $ rage_gauge = min(100, rage_gauge + 20)
    $ quick_menu = True

    scene bg_dark
    show gf angry1 at truecenter
    with vpunch

    gf "That's not it at all."
    gf "Are you even trying right now?"

    mc "(No, that wasn't it... Let me think again.)"

    hide gf
    with dissolve
    $ quick_menu = False
    $ timer_seconds = 180
    jump stage1_phone_loop

label stage1_correct:
    $ quick_menu = True

    scene bg_dark
    show gf normal at truecenter
    with dissolve

    gf "...Yeah."
    gf "That's why I'm upset."
    gf "But knowing the reason isn't enough."
    gf "You need to apologize. For real."

    mc "(I figured it out. Now I need to apologize sincerely.)"

    hide gf
    with dissolve
    jump stage2

## Stage 2 - Apologize ##########################################################

label stage2:
    $ stage = 2
    # Carry over anger from Stage 1: start from current rage_gauge,
    # then give the player a small 10-point forgiveness.
    $ rage_gauge = max(0, rage_gauge - 10)
    $ quick_menu = False

    scene bg_videocall
    with dissolve

    $ quick_menu = True
    show gf angry1 at truecenter

    gf "..."

    mc "(Time for a video call apology. I need to mean it...)"
    mc "(Her anger is rising... I need to bring it down!)"

    $ quick_menu = False

label stage2_loop:
    call screen apology_input_screen

    $ result = _return
    $ quick_menu = True

    if result == "great":
        $ rage_gauge = max(0, rage_gauge - 10)
        scene bg_videocall
        show gf normal at truecenter
        with dissolve
        gf "...Took you long enough to actually apologize properly."
        jump stage2_success
    elif result == "bad":
        $ rage_gauge = min(100, rage_gauge + 10)
        scene bg_videocall
        show gf angry2 at truecenter
        with vpunch
        gf "You call that an apology?! Do you even care how I feel?"
    else:
        # Any non-great, non-bad result still increases rage slightly.
        $ rage_gauge = min(100, rage_gauge + 10)
        gf "...This isn't good enough."

    $ quick_menu = False

    if rage_gauge >= 100:
        jump check_rescue
    else:
        jump stage2_loop

label stage2_success:
    $ quick_menu = True

    scene bg_videocall
    show goldengirl at truecenter
    with dissolve

    gf "...Okay."
    gf "I'll let it go this time."

    mc "I'm truly sorry. I promise this won't happen again."

    gf "You promise?"
    mc "I promise."

    hide gf
    with dissolve
    jump ending_clear

## Rescue Event ################################################################

label check_rescue:
    $ quick_menu = True

    if not rescue_used:
        $ rescue_used = True

        scene bg_dark
        with dissolve

        "You've pushed things too far..."
        "But it's not over yet."

        menu:
            "Grab one last chance":
                mc "(One more shot. I can't mess this up!)"
                $ quick_menu = False
                if stage == 1:
                    $ timer_seconds = 180
                    jump stage1_phone_loop
                else:
                    $ rage_gauge = max(0, rage_gauge - 30)
                    jump stage2_loop
            "Give up...":
                jump ending_gameover
    else:
        jump ending_gameover

## Endings #####################################################################

label ending_gameover:
    $ quick_menu = False

    scene bg_black
    with fade

    show firegirl at truecenter
    with dissolve

    gf "You're the absolute worst. Don't you dare contact me again!"

    scene badending
    with fade
    show screen bad_ending_title
    pause
    hide screen bad_ending_title

    call screen ending_gameover_screen
    return

label ending_clear:
    $ quick_menu = False

    scene bg_black
    with fade
    scene happyending
    with fade
    show screen clear_title
    pause
    hide screen clear_title

    call screen ending_clear_screen
    return
