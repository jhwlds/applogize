################################################################################
## Applogize - Smartphone UI
################################################################################

screen phone_main_screen():
    modal True

    default current_app = "home"
    default instagram_tab = "feed"
    default gallery_tab = "photos"

    add Solid("#050510")

    # --- HUD: Timer + Energy + Clue count (above phone) ---
    if timer_running:
        frame:
            xalign 0.5
            ypos 15
            xpadding 30
            ypadding 10
            background Frame(Solid("#1a1a2ecc"), 4, 4)

            hbox:
                spacing 30
                yalign 0.5

                text "TIME  [format_timer(timer_seconds)]":
                    size 32
                    color ("#ff4444" if timer_seconds < 30 else "#ffffff")

                hbox:
                    spacing 6
                    text "HP" size 20 color "#ff6b9d" yalign 0.5
                    frame:
                        yalign 0.5
                        xsize 120
                        ysize 16
                        background Solid("#2a2a3e")
                        frame:
                            xsize max(1, int(120.0 * energy / max_energy))
                            ysize 16
                            background Solid("#ff6b9d")

                text "CLUES  [len(found_clues)]/[total_clues]":
                    size 20
                    color "#aaaaaa"
                    yalign 0.5

        timer 1.0 repeat True action SetVariable("timer_seconds", max(0, timer_seconds - 1))

        if timer_seconds <= 0:
            timer 0.1 action Return("timeout")

    # --- Phone Body ---
    frame:
        xalign 0.5
        yalign 0.55
        xsize 440
        ysize 800
        background Solid("#1c1c2c")
        xpadding 0
        ypadding 0

        vbox:
            xfill True

            # Status bar
            frame:
                xfill True
                ysize 32
                background Solid("#111118")
                xpadding 14

                hbox:
                    yalign 0.5
                    xfill True
                    text "12:34" size 13 color "#999999"
                    text "LTE     100%%" size 13 color "#999999" xalign 1.0

            # Screen content
            frame:
                xfill True
                ysize 724
                background Solid("#0a0a16")
                xpadding 0
                ypadding 0

                if current_app == "home":
                    use phone_home_content
                elif current_app == "instagram":
                    use phone_instagram_content(instagram_tab=instagram_tab)
                elif current_app == "gallery":
                    use phone_gallery_content(gallery_tab=gallery_tab)
                elif current_app == "calendar":
                    use phone_calendar_content
                elif current_app == "creditcard":
                    use phone_creditcard_content
                elif current_app == "memo":
                    use phone_memo_content

            # Home button bar
            frame:
                xfill True
                ysize 44
                background Solid("#111118")

                textbutton "---":
                    xalign 0.5
                    yalign 0.5
                    text_size 18
                    text_color "#444444"
                    text_hover_color "#ffffff"
                    action SetScreenVariable("current_app", "home")

    # --- "Make Guess" button (outside phone) ---
    if len(found_clues) >= 3:
        frame:
            xalign 0.9
            yalign 0.88
            xpadding 24
            ypadding 14
            background Frame(Solid("#cc333399"), 4, 4)

            textbutton "INVESTIGATE":
                text_size 24
                text_color "#ffffff"
                text_hover_color "#ffd700"
                action Return("make_guess")

    # Clue count hint
    if len(found_clues) < 3:
        frame:
            xalign 0.9
            yalign 0.88
            xpadding 24
            ypadding 14
            background Frame(Solid("#33333399"), 4, 4)

            text "Find at least 3 clues to investigate":
                size 16
                color "#888888"


################################################################################
## Home Screen
################################################################################

screen phone_home_content():
    frame:
        xfill True
        yfill True
        background None
        ypadding 40
        xpadding 30

        vbox:
            xfill True
            spacing 15

            text "Applogize" size 24 color "#ffffff22" xalign 0.5

            null height 30

            grid 2 3:
                xalign 0.5
                spacing 25

                # Instagram
                vbox:
                    xsize 155
                    spacing 6

                    button:
                        xsize 76
                        ysize 76
                        xalign 0.5
                        background Solid("#e1306c")
                        hover_background Solid("#f0508c")
                        action SetScreenVariable("current_app", "instagram")

                        text "IG" size 24 color "#ffffff" xalign 0.5 yalign 0.5 bold True

                    text "Instagram" size 12 color "#cccccc" xalign 0.5

                # Gallery
                vbox:
                    xsize 155
                    spacing 6

                    button:
                        xsize 76
                        ysize 76
                        xalign 0.5
                        background Solid("#34a853")
                        hover_background Solid("#54c873")
                        action SetScreenVariable("current_app", "gallery")

                        text "Pic" size 24 color "#ffffff" xalign 0.5 yalign 0.5 bold True

                    text "Gallery" size 12 color "#cccccc" xalign 0.5

                # Calendar
                vbox:
                    xsize 155
                    spacing 6

                    button:
                        xsize 76
                        ysize 76
                        xalign 0.5
                        background Solid("#ea4335")
                        hover_background Solid("#ff6355")
                        action SetScreenVariable("current_app", "calendar")

                        text "Cal" size 24 color "#ffffff" xalign 0.5 yalign 0.5 bold True

                    text "Calendar" size 12 color "#cccccc" xalign 0.5

                # Credit Card
                vbox:
                    xsize 155
                    spacing 6

                    button:
                        xsize 76
                        ysize 76
                        xalign 0.5
                        background Solid("#1a237e")
                        hover_background Solid("#3a439e")
                        action SetScreenVariable("current_app", "creditcard")

                        text "Pay" size 24 color "#ffffff" xalign 0.5 yalign 0.5 bold True

                    text "Credit Card" size 12 color "#cccccc" xalign 0.5

                # Memo
                vbox:
                    xsize 155
                    spacing 6

                    button:
                        xsize 76
                        ysize 76
                        xalign 0.5
                        background Solid("#fdd835")
                        hover_background Solid("#ffee55")
                        action SetScreenVariable("current_app", "memo")

                        text "Memo" size 20 color "#333333" xalign 0.5 yalign 0.5 bold True

                    text "Notes" size 12 color "#cccccc" xalign 0.5

                # Empty cell
                null


################################################################################
## Instagram
################################################################################

screen phone_instagram_content(instagram_tab="feed"):
    vbox:
        xfill True
        yfill True

        # Header
        use phone_app_header("Instagram")

        # Stories row
        frame:
            xfill True
            ysize 90
            background Solid("#12121e")
            xpadding 10
            ypadding 8

            hbox:
                spacing 10
                yalign 0.5

                vbox:
                    spacing 3
                    button:
                        xsize 56
                        ysize 56
                        background Solid("#e1306c")
                        hover_background Solid("#ff5090")
                        action [Function(add_clue, "instagram_story"), SetScreenVariable("instagram_tab", "story")]

                        text "GF" size 16 color "#ffffff" xalign 0.5 yalign 0.5 bold True
                    text "Her" size 10 color "#cccccc" xalign 0.5

                for name in ["Alex", "Sam", "Jay"]:
                    vbox:
                        spacing 3
                        frame:
                            xsize 56
                            ysize 56
                            background Solid("#333344")
                            text name[0] size 20 color "#888888" xalign 0.5 yalign 0.5
                        text "[name]" size 10 color "#666666" xalign 0.5

        # Feed
        viewport:
            xfill True
            yfill True
            mousewheel True
            draggable True

            frame:
                xfill True
                background None
                xpadding 10
                ypadding 10

                vbox:
                    xfill True
                    spacing 8

                    # Story expanded view
                    if instagram_tab == "story":
                        frame:
                            xfill True
                            ysize 180
                            background Solid("#2a1a2e")
                            xpadding 15
                            ypadding 15

                            vbox:
                                spacing 10
                                text "Her Story" size 14 color "#ff6b9d" bold True
                                text "\"It's our anniversary and\nI'm spending it alone... \"" size 17 color "#ffffff"
                                if "instagram_story" in found_clues:
                                    text "[[ CLUE FOUND ]]" size 12 color "#44ff44"

                    # Reel clue
                    frame:
                        xfill True
                        ysize 130
                        background Solid("#1e1e2e")
                        xpadding 12
                        ypadding 10

                        vbox:
                            spacing 5
                            hbox:
                                spacing 8
                                frame:
                                    xsize 28
                                    ysize 28
                                    background Solid("#e1306c")
                                    text "G" size 14 color "#ffffff" xalign 0.5 yalign 0.5
                                text "Girlfriend" size 13 color "#ffffff" yalign 0.5

                            button:
                                xfill True
                                ysize 70
                                background Solid("#2a2a3e")
                                hover_background Solid("#3a3a5e")
                                action Function(add_clue, "instagram_reel")

                                frame:
                                    background None
                                    xpadding 10
                                    ypadding 8
                                    vbox:
                                        text "Liked a reel" size 11 color "#aaaaaa"
                                        text "\"Top 5 Anniversary Gift Ideas\"" size 14 color "#ffffff"
                                        if "instagram_reel" in found_clues:
                                            text "[[ CLUE FOUND ]]" size 11 color "#44ff44"

                    # Filler posts
                    for i in range(2):
                        frame:
                            xfill True
                            ysize 80
                            background Solid("#1e1e2e")
                            xpadding 12
                            ypadding 10

                            vbox:
                                hbox:
                                    spacing 8
                                    frame:
                                        xsize 28
                                        ysize 28
                                        background Solid("#444455")
                                        text "?" size 14 color "#888888" xalign 0.5 yalign 0.5
                                    text "Friend[i+1]" size 13 color "#888888" yalign 0.5
                                null height 6
                                text "Great weather today!" size 13 color "#666666"


################################################################################
## Gallery
################################################################################

screen phone_gallery_content(gallery_tab="photos"):
    vbox:
        xfill True
        yfill True

        use phone_app_header("Gallery")

        # Tabs
        frame:
            xfill True
            ysize 40
            background Solid("#12121e")

            hbox:
                xalign 0.5
                spacing 40
                yalign 0.5

                textbutton "Photos":
                    text_size 14
                    text_color ("#ffffff" if gallery_tab == "photos" else "#666666")
                    text_hover_color "#ffffff"
                    action SetScreenVariable("gallery_tab", "photos")

                textbutton "Screenshots":
                    text_size 14
                    text_color ("#ffffff" if gallery_tab == "screenshots" else "#666666")
                    text_hover_color "#ffffff"
                    action SetScreenVariable("gallery_tab", "screenshots")

        viewport:
            xfill True
            yfill True
            mousewheel True
            draggable True

            frame:
                xfill True
                background None
                xpadding 8
                ypadding 10

                vbox:
                    xfill True
                    spacing 8

                    if gallery_tab == "photos":
                        text "Recent Photos" size 13 color "#888888"

                        grid 3 2:
                            xalign 0.5
                            spacing 6

                            button:
                                xsize 125
                                ysize 125
                                background Solid("#4a2a5e")
                                hover_background Solid("#6a4a7e")
                                action Function(add_clue, "gallery_date_photo")

                                vbox:
                                    xalign 0.5
                                    yalign 0.5
                                    spacing 4
                                    text "DATE" size 14 color "#ffffff" xalign 0.5 bold True
                                    text "Tokyo Trip" size 10 color "#cccccc" xalign 0.5
                                    if "gallery_date_photo" in found_clues:
                                        text "[[CLUE]]" size 9 color "#44ff44" xalign 0.5

                            for i in range(5):
                                frame:
                                    xsize 125
                                    ysize 125
                                    background Solid("#2a2a3e")
                                    text "img" size 14 color "#444444" xalign 0.5 yalign 0.5

                    elif gallery_tab == "screenshots":
                        text "Screenshots" size 13 color "#888888"

                        button:
                            xfill True
                            ysize 170
                            xpadding 15
                            ypadding 12
                            background Solid("#1e2a3e")
                            hover_background Solid("#2e3a5e")
                            action Function(add_clue, "gallery_ticket")

                            vbox:
                                spacing 6
                                text "FLIGHT TICKET" size 15 color "#4a90d9" bold True
                                text "Tokyo - One Way" size 13 color "#ffffff"
                                text "Passenger: 1" size 13 color "#ff6b6b"
                                text "Date: 2026.03.02" size 13 color "#aaaaaa"
                                if "gallery_ticket" in found_clues:
                                    text "[[ CLUE FOUND ]]" size 11 color "#44ff44"

                        null height 8

                        frame:
                            xfill True
                            ysize 60
                            background Solid("#2a2a3e")
                            xpadding 15
                            ypadding 10
                            text "Game score screenshot" size 13 color "#666666" yalign 0.5


################################################################################
## Calendar
################################################################################

screen phone_calendar_content():
    vbox:
        xfill True
        yfill True

        use phone_app_header("Calendar")

        # Month header
        frame:
            xfill True
            ysize 40
            background Solid("#ea4335")
            text "March 2026" size 18 color "#ffffff" xalign 0.5 yalign 0.5 bold True

        viewport:
            xfill True
            yfill True
            mousewheel True
            draggable True

            frame:
                xfill True
                background None
                xpadding 10
                ypadding 10

                vbox:
                    xfill True
                    spacing 8

                    # Anniversary clue
                    button:
                        xfill True
                        ysize 70
                        background Solid("#3e1a2e")
                        hover_background Solid("#5e3a4e")
                        xpadding 12
                        ypadding 8
                        action Function(add_clue, "calendar_anniversary")

                        hbox:
                            spacing 14
                            vbox:
                                yalign 0.5
                                text "FEB" size 11 color "#ff6b9d"
                                text "28" size 24 color "#ff6b9d" bold True
                            vbox:
                                yalign 0.5
                                text "100 Day Anniversary" size 15 color "#ffffff"
                                if "calendar_anniversary" in found_clues:
                                    text "[[ CLUE FOUND ]]" size 11 color "#44ff44"

                    # Flight clue
                    button:
                        xfill True
                        ysize 70
                        background Solid("#1a2a3e")
                        hover_background Solid("#2a3a5e")
                        xpadding 12
                        ypadding 8
                        action Function(add_clue, "calendar_flight")

                        hbox:
                            spacing 14
                            vbox:
                                yalign 0.5
                                text "MAR" size 11 color "#4a90d9"
                                text "02" size 24 color "#4a90d9" bold True
                            vbox:
                                yalign 0.5
                                text "Flight to Tokyo" size 15 color "#ffffff"
                                text "ICN > NRT  10:30 AM" size 12 color "#aaaaaa"
                                if "calendar_flight" in found_clues:
                                    text "[[ CLUE FOUND ]]" size 11 color "#44ff44"

                    # Filler events
                    for ev in [("MAR", "05", "Team meeting"), ("MAR", "10", "Dentist appointment")]:
                        frame:
                            xfill True
                            ysize 50
                            background Solid("#1e1e2e")
                            xpadding 12
                            ypadding 8

                            hbox:
                                spacing 14
                                vbox:
                                    yalign 0.5
                                    text ev[0] size 10 color "#666666"
                                    text ev[1] size 18 color "#666666"
                                text ev[2] size 13 color "#888888" yalign 0.5


################################################################################
## Credit Card
################################################################################

screen phone_creditcard_content():
    vbox:
        xfill True
        yfill True

        use phone_app_header("Credit Card")

        # Card display
        frame:
            xfill True
            ysize 110
            background Solid("#0d1b3e")
            xpadding 20
            ypadding 12

            vbox:
                spacing 6
                text "My Card" size 13 color "#aaaaaa"
                text "**** **** **** 1234" size 15 color "#ffffff"
                text "This month" size 11 color "#aaaaaa"
                text "$892.00" size 26 color "#ffd700" bold True

        viewport:
            xfill True
            yfill True
            mousewheel True
            draggable True

            frame:
                xfill True
                background None
                xpadding 10
                ypadding 10

                vbox:
                    xfill True
                    spacing 6

                    text "Recent Transactions" size 13 color "#888888"

                    # Airline ticket clue
                    button:
                        xfill True
                        ysize 70
                        background Solid("#1a1a3e")
                        hover_background Solid("#2a2a5e")
                        xpadding 12
                        ypadding 8
                        action Function(add_clue, "creditcard_airline")

                        hbox:
                            xfill True
                            vbox:
                                text "Korean Air" size 14 color "#ffffff"
                                text "Feb 25 - Online" size 11 color "#888888"
                                if "creditcard_airline" in found_clues:
                                    text "[[ CLUE FOUND ]]" size 11 color "#44ff44"
                            vbox:
                                xalign 1.0
                                yalign 0.5
                                text "$450.00" size 15 color "#ff6b6b"
                                text "1 ticket" size 11 color "#ff6b6b"

                    # Filler transactions
                    for tx in [("Starbucks", "Feb 27", "$5.80"), ("Convenience Store", "Feb 26", "$3.20"), ("Food Delivery", "Feb 25", "$18.50")]:
                        frame:
                            xfill True
                            ysize 50
                            background Solid("#1e1e2e")
                            xpadding 12
                            ypadding 8

                            hbox:
                                xfill True
                                vbox:
                                    text tx[0] size 13 color "#cccccc"
                                    text tx[1] size 10 color "#666666"
                                text tx[2] size 13 color "#cccccc" xalign 1.0 yalign 0.5


################################################################################
## Memo / Notes
################################################################################

screen phone_memo_content():
    vbox:
        xfill True
        yfill True

        use phone_app_header("Notes")

        viewport:
            xfill True
            yfill True
            mousewheel True
            draggable True

            frame:
                xfill True
                background None
                xpadding 10
                ypadding 10

                vbox:
                    xfill True
                    spacing 8

                    # GF preferences memo (clue)
                    button:
                        xfill True
                        ypadding 14
                        xpadding 14
                        background Solid("#2e2a1a")
                        hover_background Solid("#4e4a3a")
                        action Function(add_clue, "memo_preference")

                        vbox:
                            spacing 5
                            text "Girlfriend Notes" size 15 color "#fdd835" bold True
                            null height 3
                            text "- Wants to go on a trip to Tokyo" size 13 color "#ffffff"
                            text "- Promised to travel together for" size 13 color "#ffffff"
                            text "  our anniversary" size 13 color "#ffffff"
                            text "- Fav food: ramen, sushi" size 13 color "#cccccc"
                            text "- Wants: limited edition perfume" size 13 color "#cccccc"
                            null height 4
                            if "memo_preference" in found_clues:
                                text "[[ CLUE FOUND ]]" size 11 color "#44ff44"

                    # Filler memos
                    frame:
                        xfill True
                        ypadding 10
                        xpadding 14
                        background Solid("#1e1e2e")

                        vbox:
                            text "Grocery List" size 14 color "#cccccc"
                            text "Milk, eggs, bread..." size 12 color "#666666"

                    frame:
                        xfill True
                        ypadding 10
                        xpadding 14
                        background Solid("#1e1e2e")

                        vbox:
                            text "Passwords" size 14 color "#cccccc"
                            text "****" size 12 color "#666666"


################################################################################
## Reusable App Header
################################################################################

screen phone_app_header(title="App"):
    frame:
        xfill True
        ysize 48
        background Solid("#14141e")
        xpadding 10

        hbox:
            yalign 0.5
            xfill True

            textbutton "< Back":
                text_size 14
                text_color "#aaaaaa"
                text_hover_color "#ffffff"
                action SetScreenVariable("current_app", "home")

            text "[title]" size 18 color "#ffffff" xalign 0.5 bold True

            null xsize 60
