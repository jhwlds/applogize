################################################################################
## Applogize - Game Screens
## (Character Select, Intro, Guess, Apology, Endings)
################################################################################


################################################################################
## Character Select
################################################################################

screen character_select_screen():
    modal True

    add Solid("#0a0a14")

    vbox:
        xalign 0.5
        yalign 0.5
        spacing 40

        text "APPLOGIZE" size 72 color "#ffffff" xalign 0.5 bold True
        text "Choose your character" size 26 color "#888888" xalign 0.5

        null height 30

        hbox:
            xalign 0.5
            spacing 60

            # Male
            vbox:
                spacing 15

                button:
                    xsize 260
                    ysize 360
                    background Solid("#1a2a4e")
                    hover_background Solid("#2a3a6e")
                    action Return("male")

                    vbox:
                        xalign 0.5
                        yalign 0.5
                        spacing 15
                        text "MALE" size 36 color "#4a90d9" xalign 0.5 bold True
                        frame:
                            xsize 100
                            ysize 100
                            xalign 0.5
                            background Solid("#2a3a5e")
                            text "M" size 48 color "#ffffff" xalign 0.5 yalign 0.5

                text "Male Character" size 16 color "#888888" xalign 0.5

            # Female
            vbox:
                spacing 15

                button:
                    xsize 260
                    ysize 360
                    background Solid("#4e1a3e")
                    hover_background Solid("#6e2a5e")
                    action Return("female")

                    vbox:
                        xalign 0.5
                        yalign 0.5
                        spacing 15
                        text "FEMALE" size 36 color "#ff6b9d" xalign 0.5 bold True
                        frame:
                            xsize 100
                            ysize 100
                            xalign 0.5
                            background Solid("#5e2a4e")
                            text "F" size 48 color "#ffffff" xalign 0.5 yalign 0.5

                text "Female Character" size 16 color "#888888" xalign 0.5


################################################################################
## Intro Video
################################################################################

screen intro_video_screen():
    modal True

    add "intro_video"

    # Skip button
    textbutton "SKIP >>":
        xalign 0.95
        yalign 0.95
        text_size 20
        text_color "#ffffff44"
        text_hover_color "#ffffff"
        action [Stop("movie_intro"), Return()]

    # Auto-advance when video ends (adjust 120 if your video is longer)
    timer 120 action Return()


################################################################################
## Voice Guess Screen (Stage 1) - Speak or type answer, send to server
################################################################################

screen voice_guess_screen():
    modal True

    add Solid("#0a0a14dd")

    frame:
        xalign 0.5
        yalign 0.5
        xsize 800
        ypadding 40
        xpadding 40
        background Solid("#1a1a2e")

        vbox:
            spacing 20
            xfill True

            text "INVESTIGATION" size 34 color "#ffffff" xalign 0.5 bold True
            text "Why is she upset? Say or type your answer." size 20 color "#aaaaaa" xalign 0.5

            null height 5

            # Evidence summary
            if len(found_clues) > 0:
                frame:
                    xfill True
                    background Solid("#12121e")
                    xpadding 15
                    ypadding 12

                    vbox:
                        spacing 3
                        text "Evidence collected:" size 13 color "#666666"
                        if "instagram_story" in found_clues:
                            text "- IG: She's spending anniversary alone" size 12 color "#cccccc"
                        if "instagram_reel" in found_clues:
                            text "- IG: Liked 'Anniversary Gift Ideas' reel" size 12 color "#cccccc"
                        if "gallery_date_photo" in found_clues:
                            text "- Gallery: Old Tokyo date photos" size 12 color "#cccccc"
                        if "gallery_ticket" in found_clues:
                            text "- Gallery: Solo flight ticket screenshot" size 12 color "#cccccc"
                        if "calendar_anniversary" in found_clues:
                            text "- Calendar: 100 Day Anniversary (Feb 28)" size 12 color "#cccccc"
                        if "calendar_flight" in found_clues:
                            text "- Calendar: Tokyo flight scheduled" size 12 color "#cccccc"
                        if "creditcard_airline" in found_clues:
                            text "- Card: Airline ticket x1 purchased" size 12 color "#cccccc"
                        if "memo_preference" in found_clues:
                            text "- Notes: Promised anniversary trip together" size 12 color "#cccccc"

            null height 10

            # Answer input (voice result or typed)
            frame:
                xfill True
                background Solid("#12121e")
                xpadding 15
                ypadding 12

                vbox:
                    spacing 8
                    text "Your answer (sent to server for check):" size 13 color "#888888"
                    input:
                        value VariableInputValue("guess_text")
                        xsize 750
                        length 200
                        size 22
                        color "#ffffff"
                        allow ""

            # Voice status
            hbox:
                xalign 0.5
                spacing 15

                if voice_status == "recording":
                    text "Recording... (speak now)" size 16 color "#ffaa00" xalign 0.5
                elif voice_status == "ok":
                    text "Voice captured." size 16 color "#44ff44" xalign 0.5
                elif voice_status == "error":
                    text "Voice failed. Type your answer or try again." size 14 color "#ff6666" xalign 0.5

            null height 5

            # Buttons
            hbox:
                xalign 0.5
                spacing 20

                textbutton "Record (voice)":
                    xpadding 24
                    ypadding 14
                    background Solid("#2a3a5e")
                    hover_background Solid("#3a4a7e")
                    text_size 18
                    text_color "#ffffff"
                    action Function(start_voice_record)

                textbutton "Submit to server":
                    xpadding 24
                    ypadding 14
                    background Solid("#2a5e2a")
                    hover_background Solid("#3a7e3a")
                    text_size 18
                    text_color "#ffffff"
                    action SubmitGuessAction()

            null height 10

            textbutton "< Back to phone":
                xalign 0.5
                text_size 16
                text_color "#888888"
                text_hover_color "#ffffff"
                action Return("back_to_phone")

    # Refresh while recording so status updates
    if voice_status == "recording":
        timer 0.5 repeat True action NullAction()


################################################################################
## Guess Reason Screen (Stage 1) - legacy multiple choice
################################################################################

screen guess_reason_screen():
    modal True

    add Solid("#0a0a14dd")

    frame:
        xalign 0.5
        yalign 0.5
        xsize 800
        ypadding 40
        xpadding 40
        background Solid("#1a1a2e")

        vbox:
            spacing 20
            xfill True

            text "INVESTIGATION" size 34 color "#ffffff" xalign 0.5 bold True
            text "Why is she upset?" size 20 color "#aaaaaa" xalign 0.5

            null height 5

            # Found clues summary
            if len(found_clues) > 0:
                frame:
                    xfill True
                    background Solid("#12121e")
                    xpadding 15
                    ypadding 12

                    vbox:
                        spacing 3
                        text "Evidence collected:" size 13 color "#666666"
                        if "instagram_story" in found_clues:
                            text "- IG: She's spending anniversary alone" size 12 color "#cccccc"
                        if "instagram_reel" in found_clues:
                            text "- IG: Liked 'Anniversary Gift Ideas' reel" size 12 color "#cccccc"
                        if "gallery_date_photo" in found_clues:
                            text "- Gallery: Old Tokyo date photos" size 12 color "#cccccc"
                        if "gallery_ticket" in found_clues:
                            text "- Gallery: Solo flight ticket screenshot" size 12 color "#cccccc"
                        if "calendar_anniversary" in found_clues:
                            text "- Calendar: 100 Day Anniversary (Feb 28)" size 12 color "#cccccc"
                        if "calendar_flight" in found_clues:
                            text "- Calendar: Tokyo flight scheduled" size 12 color "#cccccc"
                        if "creditcard_airline" in found_clues:
                            text "- Card: Airline ticket x1 purchased" size 12 color "#cccccc"
                        if "memo_preference" in found_clues:
                            text "- Notes: Promised anniversary trip together" size 12 color "#cccccc"

            null height 10

            # Answer choices
            vbox:
                spacing 10
                xfill True

                textbutton "\"I forgot her birthday.\"":
                    xfill True
                    xpadding 20
                    ypadding 14
                    background Solid("#2a2a3e")
                    hover_background Solid("#3a3a5e")
                    text_size 18
                    text_color "#ffffff"
                    action Return("wrong")

                textbutton "\"I forgot our anniversary and booked a solo trip.\"":
                    xfill True
                    xpadding 20
                    ypadding 14
                    background Solid("#2a2a3e")
                    hover_background Solid("#3a3a5e")
                    text_size 18
                    text_color "#ffffff"
                    action Return("correct")

                textbutton "\"I haven't been texting her back.\"":
                    xfill True
                    xpadding 20
                    ypadding 14
                    background Solid("#2a2a3e")
                    hover_background Solid("#3a3a5e")
                    text_size 18
                    text_color "#ffffff"
                    action Return("wrong")

                textbutton "\"I've been seeing someone else.\"":
                    xfill True
                    xpadding 20
                    ypadding 14
                    background Solid("#2a2a3e")
                    hover_background Solid("#3a3a5e")
                    text_size 18
                    text_color "#ffffff"
                    action Return("wrong")

            null height 5

            textbutton "< Back to phone":
                xalign 0.5
                text_size 16
                text_color "#888888"
                text_hover_color "#ffffff"
                action Return("back_to_phone")


################################################################################
## Apology Input Screen (Stage 2)
################################################################################

screen apology_input_screen():
    modal True

    add Solid("#0f0f23")

    # Video call frame
    frame:
        xalign 0.5
        yalign 0.25
        xsize 600
        ysize 400
        background Solid("#1a1a2e")

        vbox:
            xalign 0.5
            yalign 0.5
            spacing 10

            text "VIDEO CALL" size 16 color "#aaaaaa" xalign 0.5
            frame:
                xsize 200
                ysize 200
                xalign 0.5
                background Solid("#2a1a2e")
                text "GF" size 48 color "#ff6b9d" xalign 0.5 yalign 0.5
            text "Girlfriend" size 18 color "#ffffff" xalign 0.5

    # Rage gauge (formerly apology gauge)
    frame:
        xalign 0.5
        ypos 500
        xsize 620
        ysize 56
        background Solid("#1a1a2e")
        xpadding 12
        ypadding 8

        vbox:
            spacing 4

            hbox:
                xfill True
                text "Rage Gauge" size 13 color "#aaaaaa"
                text "[rage_gauge]%%" size 13 color "#ffffff" xalign 1.0

            frame:
                xfill True
                ysize 18
                background Solid("#2a2a3e")

                frame:
                    xsize max(2, int(5.96 * rage_gauge))
                    ysize 18
                    background Solid(get_apple_color())

    # Energy display
    frame:
        xalign 0.5
        ypos 570
        xpadding 16
        ypadding 8
        background Frame(Solid("#1a1a2eaa"), 4, 4)

        hbox:
            spacing 8
            text "HP" size 16 color "#ff6b9d"
            frame:
                yalign 0.5
                xsize 100
                ysize 12
                background Solid("#2a2a3e")
                frame:
                    xsize max(1, int(100.0 * energy / max_energy))
                    ysize 12
                    background Solid("#ff6b9d")
            text "[energy]/[max_energy]" size 14 color "#aaaaaa"

    # Apology options
    vbox:
        xalign 0.5
        yalign 0.88
        spacing 12
        xsize 700

        text "How will you apologize?" size 22 color "#ffffff" xalign 0.5

        null height 5

        hbox:
            spacing 12
            xalign 0.5

            textbutton "Sincere Apology":
                xsize 210
                ysize 65
                xpadding 10
                background Solid("#1e4e1e")
                hover_background Solid("#2e6e2e")
                text_size 16
                text_color "#ffffff"
                text_xalign 0.5
                action Return("great")

            textbutton "Apology with\nExcuses":
                xsize 210
                ysize 65
                xpadding 10
                background Solid("#4e4e1e")
                hover_background Solid("#6e6e2e")
                text_size 16
                text_color "#ffffff"
                text_xalign 0.5
                action Return("good")

            textbutton "Brush it Off":
                xsize 210
                ysize 65
                xpadding 10
                background Solid("#4e1e1e")
                hover_background Solid("#6e2e2e")
                text_size 16
                text_color "#ffffff"
                text_xalign 0.5
                action Return("bad")


################################################################################
## Ending - Game Over
################################################################################

screen ending_gameover_screen():
    modal True

    add Solid("#1a0000")

    vbox:
        xalign 0.5
        yalign 0.35
        spacing 25

        text "GAME OVER" size 72 color "#cc0000" xalign 0.5 bold True

        null height 10

        text "Her anger has reached the breaking point..." size 22 color "#ff6666" xalign 0.5
        text "She hung up on you." size 20 color "#aaaaaa" xalign 0.5

        null height 30

        # Fake SNS reactions
        frame:
            xalign 0.5
            xsize 500
            background Solid("#1a1a2e")
            xpadding 24
            ypadding 18

            vbox:
                spacing 8
                text "Social Media Reactions" size 16 color "#e1306c" bold True
                null height 4
                text "\"Worst boyfriend award goes to...\"" size 14 color "#cccccc"
                text "\"Forgot the anniversary AND booked a solo trip??\"" size 14 color "#cccccc"
                text "\"That's legendary levels of clueless lmao\"" size 14 color "#cccccc"

    textbutton "Try Again":
        xalign 0.5
        yalign 0.9
        text_size 28
        text_color "#ffffff"
        text_hover_color "#ffd700"
        action Return()


################################################################################
## Ending - Clear
################################################################################

screen ending_clear_screen():
    modal True

    add Solid("#0a0a14")

    vbox:
        xalign 0.5
        yalign 0.3
        spacing 20

        text "Golden Apple" size 42 color "#ffd700" xalign 0.5 bold True
        text "CLEAR!" size 72 color "#ffd700" xalign 0.5 bold True

        null height 20

        text "Your heartfelt apology got through to her." size 22 color "#ffffff" xalign 0.5
        text "You made things right!" size 20 color "#88cc88" xalign 0.5

        null height 30

        # Photo book placeholder
        frame:
            xalign 0.5
            xsize 500
            background Solid("#1a1a2e")
            xpadding 24
            ypadding 18

            vbox:
                spacing 12
                text "PHOTO BOOK" size 18 color "#ffd700" xalign 0.5 bold True

                hbox:
                    xalign 0.5
                    spacing 12

                    frame:
                        xsize 140
                        ysize 100
                        background Solid("#2a2a4e")
                        text "Us" size 20 color "#ffffff" xalign 0.5 yalign 0.5

                    frame:
                        xsize 140
                        ysize 100
                        background Solid("#2a4e2a")
                        text "Tokyo" size 20 color "#ffffff" xalign 0.5 yalign 0.5

                    frame:
                        xsize 140
                        ysize 100
                        background Solid("#4e2a4e")
                        text "Love" size 20 color "#ffffff" xalign 0.5 yalign 0.5

    textbutton "Back to Title":
        xalign 0.5
        yalign 0.9
        text_size 28
        text_color "#ffffff"
        text_hover_color "#ffd700"
        action Return()
