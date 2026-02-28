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

################################################################################
## Game Flow
################################################################################

label start:
    scene bg_black
    with fade

    $ quick_menu = False

    call screen character_select_screen
    $ player_gender = _return

    call screen intro_video_screen

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
    $ quick_menu = True

    scene bg_dark
    show gf angry2 at truecenter
    with vpunch

    gf "Time's up. You don't even care, do you?"

    $ energy -= 10
    $ gf_anger_level += 1

    if energy <= 0:
        jump check_rescue

    mc "(I need to hurry up...)"

    hide gf
    with dissolve
    $ quick_menu = False
    $ timer_seconds = 180
    jump stage1_phone_loop

label stage1_guess:
    $ timer_running = False
    call screen guess_reason_screen

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

    call screen ending_gameover_screen
    return

label ending_clear:
    $ quick_menu = False

    scene bg_black
    with fade

    call screen ending_clear_screen
    return
