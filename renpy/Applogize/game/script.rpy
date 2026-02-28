################################################################################
## Applogize - Main Game Script
################################################################################

## Game Variables ##############################################################

default energy = 20
default max_energy = 20
default apology_gauge = 50
default stage = 0
default player_gender = None
default found_clues = set()
default total_clues = 8
default timer_seconds = 180
default timer_running = False
default gf_anger_level = 0
default rescue_used = False

## Voice guess / server (Stage 1)
## Answer is fixed on the server: you decide correct/incorrect there.
## Client: POST JSON {"answer": "user text"} -> Server: JSON {"correct": true} or {"correct": false}
default answer_check_url = "http://localhost:8000/check_answer"
default guess_text = ""
default voice_status = ""  # "", "recording", "ok", "error"
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

screen bad_ending_title():
    zorder 100
    text "GAME OVER":
        xalign 0.02
        yalign 0.95
        size 80
        color "#ffffff"
        outlines [(4, "#000000", 0, 0)]

## Helper Functions ############################################################

init python:
    def add_clue(clue_name):
        store.found_clues = store.found_clues | {clue_name}

    def get_apple_color():
        if store.stage == 1:
            if store.gf_anger_level >= 3:
                return "#990000"
            elif store.gf_anger_level >= 1:
                return "#cc3333"
            else:
                return "#ff6666"
        else:
            g = store.apology_gauge
            if g >= 100:
                return "#ffd700"
            elif g >= 75:
                return "#88cc33"
            elif g >= 50:
                return "#33cc33"
            elif g >= 25:
                return "#ff6666"
            else:
                return "#cc3333"

    def format_timer(seconds):
        m = seconds // 60
        s = seconds % 60
        return "{:01d}:{:02d}".format(m, s)

    # ---- Voice guess: send answer text to server, get correct/incorrect ----
    import urllib.request
    import urllib.error
    import json

    def submit_answer_to_server(text):
        """POST store.guess_text to answer_check_url. Returns True/False/None (None = error)."""
        url = store.answer_check_url
        if not url or not str(text).strip():
            return None
        try:
            data = json.dumps({"answer": str(text).strip()}).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return bool(body.get("correct", False))
        except Exception:
            return None

    def _record_and_stt_worker():
        """Runs in background thread: record mic -> STT -> set store.guess_text + store.voice_status.
        Requires: pip install SpeechRecognition pyaudio (and system mic). If not installed, Record shows error."""
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.Microphone() as source:
                # Optional: adjust for ambient noise (short delay)
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.record(source, duration=6)
            text = r.recognize_google(audio, language="en-US")
            text = (text or "").strip()
            def set_result():
                store.guess_text = text
                store.voice_status = "ok" if text else "error"
            renpy.invoke_in_main_thread(set_result)
        except Exception as e:
            err = str(e)[:80]
            def set_err():
                store.voice_status = "error"
                store.guess_text = store.guess_text  # no change to text
            renpy.invoke_in_main_thread(set_err)

    def start_voice_record():
        """Start recording in a thread; UI shows status via store.voice_status."""
        import threading
        store.voice_status = "recording"
        t = threading.Thread(target=_record_and_stt_worker)
        t.daemon = True
        t.start()

    class SubmitGuessAction(renpy.store.Action):
        """Submit current guess_text to server and return Return('correct') or Return('wrong') or notify error."""
        def __call__(self):
            r = submit_answer_to_server(store.guess_text)
            if r is True:
                return renpy.store.Return("correct")
            if r is False:
                return renpy.store.Return("wrong")
            renpy.notify("Server error. Check URL or try again.")
            return None

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
    $ gf_anger_level = 0

    scene bg_dark
    with dissolve

    $ quick_menu = True
    show gf normal at truecenter
    with dissolve

    gf "..."
    gf "You really don't know? You have no idea why I'm upset?"

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
    call screen voice_guess_screen

    if _return == "correct":
        jump stage1_correct
    elif _return == "back_to_phone":
        $ timer_seconds = max(timer_seconds, 60)
        jump stage1_phone_loop
    else:
        jump stage1_wrong

label stage1_wrong:
    $ energy -= 10
    $ gf_anger_level += 1
    $ quick_menu = True

    scene bg_dark
    show gf angry1 at truecenter
    with vpunch

    gf "That's not it!"
    gf "Are you serious right now?"

    if energy <= 0:
        jump check_rescue

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
    $ apology_gauge = 50
    $ quick_menu = False

    scene bg_videocall
    with dissolve

    $ quick_menu = True
    show gf angry1 at truecenter

    gf "..."

    mc "(Time for a video call apology. I need to mean it...)"
    mc "(Get the apology gauge to 100 to make things right!)"

    $ quick_menu = False

label stage2_loop:
    call screen apology_input_screen

    $ result = _return
    $ quick_menu = True

    if result == "great":
        $ apology_gauge = min(100, apology_gauge + 25)
        scene bg_videocall
        show gf normal at truecenter
        with dissolve
        gf "...Keep going."
    elif result == "good":
        $ apology_gauge = min(100, apology_gauge + 15)
        scene bg_videocall
        show gf normal at truecenter
        with dissolve
        gf "..."
    elif result == "bad":
        $ apology_gauge = max(0, apology_gauge - 20)
        $ energy -= 5
        scene bg_videocall
        show gf angry2 at truecenter
        with vpunch
        gf "You call that an apology?!"
    else:
        $ apology_gauge = max(0, apology_gauge - 5)
        gf "..."

    $ quick_menu = False

    if apology_gauge >= 100:
        jump stage2_success
    elif apology_gauge <= 0 or energy <= 0:
        jump check_rescue
    else:
        jump stage2_loop

label stage2_success:
    $ quick_menu = True

    scene bg_videocall
    show gf normal at truecenter
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

        "Your energy has hit rock bottom..."
        "But it's not over yet."

        menu:
            "Grab one last chance":
                $ energy = 10
                $ gf_anger_level = max(0, gf_anger_level - 1)
                mc "(One more shot. I can't mess this up!)"
                $ quick_menu = False
                if stage == 1:
                    $ timer_seconds = 180
                    jump stage1_phone_loop
                else:
                    $ apology_gauge = 30
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

    call screen ending_clear_screen
    return
