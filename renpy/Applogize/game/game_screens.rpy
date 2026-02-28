################################################################################
## Applogize - Game Screens
## (Character Select, Intro, Guess, Apology, Endings)
################################################################################


################################################################################
## Character Select
################################################################################

screen character_select_screen():
    modal True

    add Transform(
        "images/characters/street.png",
        xsize=config.screen_width,
        ysize=config.screen_height,
        fit="cover"
    )

    vbox:
        xalign 0.5
        yalign 0.5
        spacing 40

        text "APPLOGIZE" size 72 color "#000000" xalign 0.5 bold True
        text "Choose your partner" size 26 color "#000000" xalign 0.5

        null height 30

        hbox:
            xalign 0.5
            spacing 60

            # Male - character image
            vbox:
                spacing 15

                button:
                    xsize 260
                    ysize 360
                    background None
                    hover_background Solid("#ffffff20")
                    action [
                        Function(renpy.music.stop, fadeout=1.5),
                        Hide("character_select_screen", transition=fade),
                        Return("male")
                    ]

                    add Transform(
                        "images/characters/Angry_apple-headed_character_in_hoodie-removebg-preview.png",
                        fit="contain",
                        xsize=240,
                        ysize=340
                    ) xalign 0.5 yalign 0.5

            # Female - character image
            vbox:
                spacing 15

                button:
                    xsize 260
                    ysize 360
                    background None
                    hover_background Solid("#ffffff20")
                    action [
                        Function(renpy.music.stop, fadeout=1.5),
                        Hide("character_select_screen", transition=fade),
                        Return("female")
                    ]

                    add Transform(
                        "images/characters/angry_face1.png",
                        fit="contain",
                        xsize=240,
                        ysize=340
                    ) xalign 0.5 yalign 0.5


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
                    vbox:
                        spacing 4
                        text "Voice failed. Type your answer or try again." size 14 color "#ff6666" xalign 0.5
                        if voice_error_message:
                            text "[voice_error_message]" size 12 color "#ff9999" xalign 0.5

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

            hbox:
                xalign 0.5
                spacing 20

                textbutton "< Back to phone":
                    text_size 16
                    text_color "#888888"
                    text_hover_color "#ffffff"
                    action Return("back_to_phone")

                textbutton ">> Go to Video Call":
                    xpadding 20
                    ypadding 10
                    background Solid("#2a3a5e")
                    hover_background Solid("#3a4a7e")
                    text_size 16
                    text_color "#ffffff"
                    action Jump("stage2")

    # Refresh while recording so status updates
    if voice_status == "recording":
        timer 0.5 repeat True action NullAction()


################################################################################
## Call Recording Overlay (Stage 1) - shown during phone call, auto-starts STT
################################################################################

screen call_recording_overlay():
    modal True

    default call_remaining = 15

    # Right-side panel (phone_call screen occupies the left ~40%)
    frame:
        xalign 0.97
        yalign 0.5
        xsize 420
        ypadding 28
        xpadding 22
        background Frame(Solid("#0e0e1eee"), 8, 8)

        vbox:
            spacing 18
            xfill True

            # Header + countdown
            hbox:
                xfill True
                yalign 0.5

                text "On the phone..." size 18 color "#ff6b9d" bold True

                # Countdown badge - turns red under 5s
                frame:
                    xalign 1.0
                    yalign 0.5
                    xpadding 10
                    ypadding 4
                    background Solid(("#cc2222" if call_remaining <= 5 else "#2a2a3e"))
                    text "[call_remaining]s" size 16 color "#ffffff" bold True

            # Countdown progress bar (376 = panel 420 - xpadding 22*2)
            frame:
                xsize 376
                ysize 6
                background Solid("#2a2a3e")

                frame:
                    xsize int(376 * call_remaining / 15.0)
                    ysize 6
                    background Solid(("#ff4444" if call_remaining <= 5 else "#44aaff"))

            # Recording status indicator
            frame:
                xfill True
                ypadding 14
                xpadding 14
                background Solid("#12121e")

                vbox:
                    spacing 8
                    xfill True

                    if voice_status == "recording":
                        hbox:
                            xalign 0.5
                            spacing 8
                            text "●" size 20 color "#ffaa00"
                            text "Recording..." size 18 color "#ffaa00"
                        text "Speak into the microphone now." size 13 color "#888888" xalign 0.5

                    elif voice_status == "ok":
                        hbox:
                            xalign 0.5
                            spacing 8
                            text "●" size 20 color "#44ff44"
                            text "Voice captured" size 18 color "#44ff44"
                        if guess_text:
                            null height 4
                            frame:
                                xfill True
                                background Solid("#1a2a1a")
                                xpadding 10
                                ypadding 8
                                text "[guess_text]" size 14 color "#cccccc" text_align 0.0

                    elif voice_status == "error":
                        hbox:
                            xalign 0.5
                            spacing 8
                            text "●" size 20 color "#ff4444"
                            text "Recording failed" size 18 color "#ff4444"
                        if voice_error_message:
                            text "[voice_error_message]" size 11 color "#ffaa66" xalign 0.5 text_align 0.5

                    else:
                        text "Connecting..." size 18 color "#888888" xalign 0.5

            null height 4

            # Hang Up button
            frame:
                xalign 0.5
                background None

                textbutton "🔴  Hang Up":
                    xsize 200
                    ysize 60
                    xpadding 14
                    background Solid("#cc0000")
                    hover_background Solid("#ee2222")
                    text_size 20
                    text_color "#ffffff"
                    text_xalign 0.5
                    action ContinueGuessAction()

            # Skip recording
            textbutton "⏭  Skip recording":
                xalign 0.5
                text_size 14
                text_color "#666666"
                text_hover_color "#aaaaaa"
                action [Function(stop_voice_record_if_running), Return("skip")]

            # Cancel / back
            textbutton "< Check your phone again":
                xalign 0.5
                text_size 13
                text_color "#666666"
                text_hover_color "#aaaaaa"
                action Return("back_to_phone")

    # Tick down every second; auto-hang-up when time runs out
    timer 1.0 repeat True action If(
        call_remaining > 1,
        SetScreenVariable("call_remaining", call_remaining - 1),
        ContinueGuessAction()
    )

    # Poll every 0.5s while recording so status text updates live
    if voice_status == "recording":
        timer 0.5 repeat True action NullAction()

    # Close screen as soon as _call_overlay_result is set by ContinueGuessAction
    timer 0.1 repeat True action If(
        _call_overlay_result != "",
        Return(_call_overlay_result),
        NullAction()
    )


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

            hbox:
                xalign 0.5
                spacing 20

                textbutton "< Back to phone":
                    text_size 16
                    text_color "#888888"
                    text_hover_color "#ffffff"
                    action Return("back_to_phone")

                textbutton ">> Go to Video Call":
                    xpadding 20
                    ypadding 10
                    background Solid("#2a3a5e")
                    hover_background Solid("#3a4a7e")
                    text_size 16
                    text_color "#ffffff"
                    action Jump("stage2")


################################################################################
## Apology Input Screen (Stage 2) - Phone Video Call 우측 패널
## phone call "gf" video 사용 시, 왼쪽에 전화기 프레임·비디오 피드가 보이고
## 오른쪽에 이 컨트롤 패널이 오버레이됨.
################################################################################

screen apology_input_screen():
    modal True

    # 우측 패널 (Stage 1 call_recording_overlay와 동일 레이아웃)
    frame:
        xalign 0.97
        yalign 0.5
        xsize 420
        ypadding 28
        xpadding 22
        background Frame(Solid("#0e0e1eee"), 8, 8)

        vbox:
            spacing 18
            xfill True

            # 헤더 + 통화 시간
            hbox:
                xfill True
                yalign 0.5
                text "Video call..." size 18 color "#ff6b9d" bold True
                frame:
                    xalign 1.0
                    yalign 0.5
                    xpadding 10
                    ypadding 4
                    background Solid("#2a2a3e")
                    text "[format_videocall_duration()]" size 16 color "#88ff88" bold True

            # Rage gauge
            hbox:
                xfill True
                text "Her patience" size 13 color "#aaaaaa"
                text "[rage_gauge]%" size 13 color "#ffffff" xalign 1.0

            frame:
                xsize 376
                ysize 8
                background Solid("#2a2a3e")
                padding (0, 0)
                frame:
                    xsize max(4, int(376 * rage_gauge / 100.0))
                    ysize 8
                    background Solid(get_apple_color())
                    padding (0, 0)

            null height 4

            # 가이드
            text "Be careful with your facial expression, tone, and word choice when you apologize.":
                size 12
                color "#888888"
                text_align 0.5
                xalign 0.5

            null height 8

            # Voice status (Stage2 record → analyze)
            if voice_status:
                hbox:
                    spacing 8
                    text "Voice:" size 12 color "#aaaaaa"
                    if voice_status == "recording":
                        text "Recording..." size 12 color "#ffcc00"
                    elif voice_status == "ok":
                        text "OK" size 12 color "#88ff88"
                    elif voice_status == "error":
                        text "[voice_error_message]" size 11 color "#ff6666"
            null height 4

            # 컨트롤 버튼: Apologize / Done 토글
            vbox:
                spacing 12
                xfill True

                if voice_status == "recording":
                    textbutton "Done":
                        xfill True
                        xsize 376
                        ysize 50
                        background Solid("#2a5e2a")
                        hover_background Solid("#3a8a3a")
                        text_size 16
                        text_color "#ffffff"
                        text_xalign 0.5
                        action Return("evaluate")
                else:
                    textbutton "Apologize":
                        xfill True
                        xsize 376
                        ysize 50
                        background Solid("#2a5e2a")
                        hover_background Solid("#3a8a3a")
                        text_size 16
                        text_color "#ffffff"
                        text_xalign 0.5
                        action [Function(run_tracker_start), Function(start_voice_record)]

                textbutton "End call":
                    xfill True
                    xsize 376
                    ysize 50
                    background Solid("#cc2222")
                    hover_background Solid("#ee3333")
                    text_size 16
                    text_color "#ffffff"
                    text_xalign 0.5
                    action [Function(stop_and_apply_smile_rage), Return("end_response")]

    # [DEBUG] 분노100 테스트
    textbutton "[[DEBUG]] 분노100":
        xalign 0.98
        yalign 0.02
        xpadding 10
        ypadding 4
        background Solid("#5e2e5e88")
        hover_background Solid("#7e4e7ecc")
        text_size 14
        text_color "#ffcccc"
        action [SetVariable("rage_gauge", 100), Return("end_response")]

    # 녹음 중일 때 화면 갱신 (voice_status 표시용)
    if voice_status == "recording":
        timer 0.5 repeat True action NullAction()

    # 타이머: videocall_duration + idle_seconds (idle 30초 시 경고)
    timer 1.0 repeat True action [
        SetVariable("videocall_duration", videocall_duration + 1),
        SetVariable("idle_seconds", idle_seconds + 1)
    ]
    # if idle_seconds >= 30:
    #     timer 0.1 action [SetVariable("idle_seconds", 0), Return("idle_warning")]


################################################################################
## Grab One Last Chance - 5 Second Heart Screen
################################################################################

screen grab_one_last_chance_screen():
    modal True

    add Solid("#0f0f23")

    vbox:
        xalign 0.5
        yalign 0.5
        spacing 20

        text "Show your heart!" size 36 color "#ff6b9d" xalign 0.5 bold True
        text "10 seconds..." size 24 color "#aaaaaa" xalign 0.5

    timer 10.0 action Return("done")


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
