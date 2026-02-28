################################################################################
## Applogize - Main Game Script
################################################################################

## Game Variables ##############################################################

default energy = 20
default max_energy = 20
default rage_gauge = 70
default idle_seconds = 0
default stage = 0
default player_gender = None
default found_clues = set()
default total_clues = 8
default timer_seconds = 180
default timer_running = False
default rescue_used = False

## Voice guess (Stage 1) – STT via speechemotionanalysis server /analyze; answer check via server
default analyze_url = "http://localhost:19000/analyze"
default answer_check_url = "http://localhost:8000/check_answer"
default guess_text = ""
default voice_status = ""  # "", "recording", "ok", "error"
default voice_error_message = ""  # last exception message when voice_status == "error"
default server_guess_result = None  # True/False/None after submit
default heart_rescue_success = False  # True if heart detected in grab-one-last-chance flow

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
        """Proceed after STT finished; block if still recording."""
        def __call__(self):
            # If voice recording/STT is still running, keep the screen open
            # so the player can see the final transcript once it arrives.
            if store.voice_status == "recording":
                try:
                    renpy.notify("Still analyzing voice... please wait.")
                except Exception:
                    pass
                return None

            return renpy.store.Return("correct")

    class SubmitGuessAction(renpy.store.Action):
        """POST guess_text to answer_check_url and return correct/wrong."""
        def __call__(self):
            try:
                data = json.dumps({"answer": (store.guess_text or "").strip()}).encode("utf-8")
                req = urllib.request.Request(
                    store.answer_check_url,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = json.loads(resp.read().decode("utf-8"))
                ok = bool(body.get("correct", False))
                store.server_guess_result = ok
                return renpy.store.Return("correct" if ok else "wrong")
            except Exception as e:
                store.server_guess_result = None
                store.voice_status = "error"
                store.voice_error_message = "Server error: " + str(e)[:80]
                renpy.restart_interaction()
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
exec "$TRACKER_DIR/.venv/bin/python3" tracker.py --output-file "$TRACKER_DIR/smile_session.json"
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
                smile_file = os.path.join(tracker_dir, "smile_session.json")
                subprocess.Popen(["cmd", "/c", "start", "cmd", "/k", venv_python, tracker_py, "--output-file", smile_file], cwd=tracker_dir)
            else:
                smile_file = os.path.join(tracker_dir, "smile_session.json")
                subprocess.Popen([venv_python, tracker_py, "--output-file", smile_file], cwd=tracker_dir, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

    def stop_and_check_heart():
        """Stop tracker, read heart_detected from file, set store.heart_rescue_success."""
        import json
        import os
        import time
        run_tracker_stop()
        time.sleep(0.6)
        base = renpy.config.basedir
        tracker_dir = os.path.abspath(os.path.join(base, "..", "..", "backend", "tracker"))
        if not os.path.isdir(tracker_dir):
            gamedir = renpy.config.gamedir
            tracker_dir = os.path.abspath(os.path.join(gamedir, "..", "..", "..", "backend", "tracker"))
        session_path = os.path.join(tracker_dir, "smile_session.json")
        store.heart_rescue_success = False
        try:
            if os.path.isfile(session_path):
                with open(session_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                store.heart_rescue_success = bool(data.get("heart_detected", False))
                try:
                    os.remove(session_path)
                except Exception:
                    pass
        except Exception:
            pass

    def stop_and_apply_smile_rage():
        """Stop tracker, read smile count from file, add rage_gauge += smile_count * 2."""
        import json
        import os
        import time
        run_tracker_stop()
        time.sleep(0.6)
        base = renpy.config.basedir
        tracker_dir = os.path.abspath(os.path.join(base, "..", "..", "backend", "tracker"))
        if not os.path.isdir(tracker_dir):
            gamedir = renpy.config.gamedir
            tracker_dir = os.path.abspath(os.path.join(gamedir, "..", "..", "..", "backend", "tracker"))
        smile_path = os.path.join(tracker_dir, "smile_session.json")
        try:
            if os.path.isfile(smile_path):
                with open(smile_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                cnt = int(data.get("smile_count", 0))
                store.rage_gauge = min(100, store.rage_gauge + cnt * 2)
                try:
                    os.remove(smile_path)
                except Exception:
                    pass
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

    $ renpy.movie_cutscene("video/we_are_done.mkv", stop_music=True)

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

    mc "(What did I do wrong...?)"
    mc "(Let me check my phone for clues.)"

    $ quick_menu = False

label stage1_phone_loop:
    $ timer_running = True
    call screen phone_main_screen

    if _return == "make_call":
        $ idle_seconds = 0
        jump stage1_call
    elif _return == "timeout":
        jump stage1_timeout
    elif _return == "idle_warning":
        jump stage1_idle_warning
    else:
        $ idle_seconds = 0
        jump stage1_phone_loop

label stage1_phone_after_call:
    call screen phone_main_screen

    if _return == "make_call":
        $ idle_seconds = 0
        jump stage1_call_retry
    elif _return == "timeout":
        jump stage1_timeout
    elif _return == "idle_warning":
        jump stage1_idle_warning
    else:
        $ idle_seconds = 0
        jump stage1_phone_after_call

label stage1_idle_warning:
    $ rage_gauge = min(100, rage_gauge + 5)
    $ quick_menu = True

    scene bg_dark
    show gf angry1 at truecenter
    with vpunch

    gf "Are you spacing out right now?"

    hide gf
    with dissolve

    $ quick_menu = False
    $ idle_seconds = 0
    jump stage1_phone_loop

label stage1_timeout:
    $ timer_running = False
    jump ending_gameover


label stage1_call:
    $ timer_running = False
    $ guess_text = ""
    $ voice_status = ""
    $ voice_error_message = ""
    $ quick_menu = False

    phone call "gf"
    phone_gf "..."
    phone_gf "Why are you calling me right now?"
    phone_mc "I know you're upset. I want to explain."
    phone_gf "Fine. Tell me — why do you think I'm angry?"

    $ start_voice_record()

    call screen call_recording_overlay

    phone end call

    if _return == "back_to_phone":
        # $ timer_seconds = max(timer_seconds, 60)
        jump stage1_phone_after_call
    elif _return == "skip" or voice_status == "ok":
        jump stage1_correct
    else:
        jump stage1_wrong

label stage1_call_retry:
    $ timer_running = False
    $ quick_menu = False

    phone call "gf"

    $ start_voice_record()

    call screen call_recording_overlay

    phone end call

    if _return == "back_to_phone":
        jump stage1_phone_after_call
    elif _return == "skip" or voice_status == "ok":
        jump stage1_correct
    else:
        jump stage1_wrong

label stage1_wrong:
    $ rage_gauge = min(100, rage_gauge + 10)
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
    jump stage1_call_retry

label stage1_correct:
    $ quick_menu = True

    scene bg_dark
    show gf angry1 at truecenter
    with dissolve

    gf "You know exactly what you did wrong, and that’s how you apologize?"

    mc "(I figured it out. Now I need to actually apologize.)"

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
        gf "You call that an apology?!"
    elif result == "idle_warning":
        $ rage_gauge = min(100, rage_gauge + 5)
        scene bg_videocall
        show gf angry1 at truecenter
        with vpunch
        gf "Are you spacing out right now?"
    elif result == "end_response":
        scene bg_videocall
        show gf angry2 at truecenter
        with dissolve
        gf "You were smiling! This is serious!"
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
                    jump stage1_phone_loop
                else:
                    $ run_tracker_start()
                    call screen grab_one_last_chance_screen
                    $ run_tracker_stop()
                    $ stop_and_check_heart()
                    if heart_rescue_success:
                        $ rage_gauge = 30
                        jump stage2_loop
                    else:
                        $ rage_gauge = 100
                        jump ending_gameover
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
