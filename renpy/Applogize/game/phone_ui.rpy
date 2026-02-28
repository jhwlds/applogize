################################################################################
## Applogize - Smartphone UI (Better EMR Phone _phone() frame)
################################################################################

# 전역으로 현재 앱 상태를 관리.
default current_app = "home"
default gallery_zoom_photo = None
default instagram_story_zoom_photo = None
default gallery_photos = [
    "images/clues/photo_1.png",
    "images/clues/photo_2.png",
    "images/clues/photo_3.png",
    "images/clues/photo_4.png",
    "images/clues/photo_5.png",
    "images/clues/photo_6.png",
]

transform phone_ui_scale:
    xalign 0.5
    yalign 0.5
    zoom 1.1


screen phone_main_screen():
    modal True
    on "show" action [SetVariable("gallery_zoom_photo", None), SetVariable("instagram_story_zoom_photo", None)]

    default instagram_tab = "feed"
    default gallery_tab = "photos"

    fixed:
        xfill True
        yfill True
        add "images/characters/room.jpg" fit "cover"

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

                text "CLUES  [len(found_clues)]/[total_clues]":
                    size 20
                    color "#aaaaaa"
                    yalign 0.5

        timer 1.0 repeat True action SetVariable("timer_seconds", max(0, timer_seconds - 1))

        if timer_seconds <= 0:
            timer 0.1 action Return("timeout")

    # --- Phone: Better EMR Phone _phone() base ---
    fixed:
        xfill True
        yfill True
        at phone_ui_scale

        use _phone(xpos=0.5, xanchor=0.5, ypos=0.5, yanchor=0.5):
            fixed:
                xfill True
                yfill True

                vbox:
                    xfill True
                    yfill True

                    # Reserve space for status bar so content doesn't overlap
                    null height gui.phone_status_bar_height

                    # App content area
                    frame:
                        xfill True
                        yfill True
                        background None
                        xpadding 0
                        ypadding 0
                        has fixed

                        # Phone wallpaper (auto-fit to the content area).
                        add "images/ui/screen_wallpaper.png" fit "cover"

                        # Dim layer above wallpaper when an app is open.
                        if current_app == "instagram":
                            add Solid("#000000")
                        elif current_app != "home":
                            add Solid("#00000088")

                        if current_app == "home":
                            use phone_home_content
                        elif current_app == "instagram":
                            use phone_instagram_content(instagram_tab=instagram_tab)
                        elif current_app == "gallery":
                            use phone_gallery_content(gallery_tab=gallery_tab)
                        elif current_app == "calendar":
                            use phone_calendar_content
                        elif current_app == "wallet":
                            use phone_wallet_content
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

                # Show story full-screen over the whole phone area (including status bar).
                if instagram_story_zoom_photo:
                    use phone_instagram_story_zoom(photo_path=instagram_story_zoom_photo)

    # --- "Make Guess" button (outside phone) ---
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


################################################################################
## Home Screen
################################################################################

screen phone_home_content():
    frame:
        xfill True
        yfill True
        background None
        ypadding 40
        xpadding 0

        vbox:
            xfill True
            spacing 15

            text "Applogize" size 24 color "#ffffff22" xalign 0.5

            null height 30

            # 홈 화면을 가로로 드래그해서 여러 페이지를 볼 수 있게 한다.
            viewport:
                xfill True
                yfill True
                draggable True
                mousewheel False

                hbox:
                    spacing 80

                    # 페이지 1: 기존 앱 아이콘들
                    frame:
                        background None

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
                                    background None
                                    hover_background None
                                    action SetScreenVariable("current_app", "instagram")

                                    add "images/ui/icons/Instagram_icon.png":
                                        fit "contain"
                                        xalign 0.5
                                        yalign 0.5
                                        xsize 76
                                        ysize 76

                                text "Instagram" size 13 color "#ffffff" xalign 0.5 bold True outlines [(2, "#00000088", 0, 0)]

                            # Gallery
                            vbox:
                                xsize 155
                                spacing 6

                                button:
                                    xsize 76
                                    ysize 76
                                    xalign 0.5
                                    background None
                                    hover_background None
                                    action SetScreenVariable("current_app", "gallery")

                                    add "images/ui/icons/photos_icon.png":
                                        fit "contain"
                                        xalign 0.5
                                        yalign 0.5
                                        xsize 76
                                        ysize 76

                                text "Gallery" size 13 color "#ffffff" xalign 0.5 bold True outlines [(2, "#00000088", 0, 0)]

                            # Calendar
                            vbox:
                                xsize 155
                                spacing 6

                                button:
                                    xsize 76
                                    ysize 76
                                    xalign 0.5
                                    background None
                                    hover_background None
                                    action SetScreenVariable("current_app", "calendar")

                                    add "images/ui/icons/calendar_icon.png":
                                        fit "contain"
                                        xalign 0.5
                                        yalign 0.5
                                        xsize 76
                                        ysize 76

                                text "Calendar" size 13 color "#ffffff" xalign 0.5 bold True outlines [(2, "#00000088", 0, 0)]

                            # Wallet
                            vbox:
                                xsize 155
                                spacing 6

                                button:
                                    xsize 76
                                    ysize 76
                                    xalign 0.5
                                    background None
                                    hover_background None
                                    action SetScreenVariable("current_app", "wallet")

                                    add "images/ui/icons/wallet_icon.png":
                                        fit "contain"
                                        xalign 0.5
                                        yalign 0.5
                                        xsize 76
                                        ysize 76

                                text "Wallet" size 13 color "#ffffff" xalign 0.5 bold True outlines [(2, "#00000088", 0, 0)]

                            # Memo
                            vbox:
                                xsize 155
                                spacing 6

                                button:
                                    xsize 76
                                    ysize 76
                                    xalign 0.5
                                    background None
                                    hover_background None
                                    action SetScreenVariable("current_app", "memo")

                                    add "images/ui/icons/note_icon.png":
                                        fit "contain"
                                        xalign 0.5
                                        yalign 0.5
                                        xsize 76
                                        ysize 76

                                text "Memo" size 13 color "#ffffff" xalign 0.5 bold True outlines [(2, "#00000088", 0, 0)]

                            # Empty cell
                            null

                    # 페이지 2: 추후 확장을 위한 빈 페이지 (예시 아이콘)
                    frame:
                        background None

                        grid 2 3:
                            xalign 0.5
                            spacing 25

                            vbox:
                                xsize 155
                                spacing 6
                                button:
                                    xsize 76
                                    ysize 76
                                    xalign 0.5
                                    background Solid("#444444")
                                    hover_background Solid("#666666")
                                    action NullAction()
                                    text "+" size 28 color "#ffffff" xalign 0.5 yalign 0.5 bold True
                                text "Empty" size 12 color "#777777" xalign 0.5

                            null
                            null
                            null
                            null
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
                xfill True
                xalign 0.5
                spacing 10
                yalign 0.5

                vbox:
                    xsize 64
                    xalign 0.5
                    spacing 3
                    button:
                        xsize 56
                        ysize 56
                        xalign 0.5
                        background None
                        hover_background None
                        action SetVariable("instagram_story_zoom_photo", "images/clues/photo_story.png")

                        fixed:
                            xsize 56
                            ysize 56

                            # Green story ring for girlfriend.
                            add "phone/assets/circle.png":
                                xalign 0.5
                                yalign 0.5
                                xsize 56
                                ysize 56
                                fit "contain"
                                matrixcolor TintMatrix("#24d366")

                            # Inner cutout to make the ring visible.
                            add "phone/assets/circle.png":
                                xalign 0.5
                                yalign 0.5
                                xsize 52
                                ysize 52
                                fit "contain"
                                matrixcolor TintMatrix("#12121e")

                            if renpy.loadable("images/clues/photo_5.png"):
                                add RoundedCorners(
                                    Transform("images/clues/photo_5.png", fit="cover", xsize=48, ysize=48),
                                    radius=24
                                ):
                                    xalign 0.5
                                    yalign 0.5
                            else:
                                circle border 0 color "#e1306c":
                                    xalign 0.5
                                    yalign 0.5
                                    xsize 50
                                    ysize 50
                                text "GF" size 16 color "#ffffff" xalign 0.5 yalign 0.5 bold True
                    fixed:
                        xsize 56
                        ysize 14
                        xalign 0.5
                        xoffset 6
                        yoffset 2
                        text "Apple":
                            size 10
                            color "#ffffff"
                            xalign 0.5
                            yalign 0.5

                for name in ["Alex", "Sam", "Jay"]:
                    vbox:
                        xsize 64
                        xalign 0.5
                        spacing 3
                        button:
                            xsize 56
                            ysize 56
                            xalign 0.5
                            background None
                            hover_background None
                            action NullAction()

                            fixed:
                                xsize 56
                                ysize 56
                                add "phone/assets/circle.png":
                                    xalign 0.5
                                    yalign 0.5
                                    xsize 56
                                    ysize 56
                                    fit "contain"
                                    matrixcolor TintMatrix("#6a6a7a")
                                add "phone/assets/circle.png":
                                    xalign 0.5
                                    yalign 0.5
                                    xsize 52
                                    ysize 52
                                    fit "contain"
                                    matrixcolor TintMatrix("#2a2a36")
                                text name[0] size 20 color "#888888" xalign 0.5 yalign 0.5
                        fixed:
                            xsize 56
                            ysize 14
                            xalign 0.5
                            xoffset 6
                            yoffset 2
                            text "[name]":
                                size 10
                                color "#666666"
                                xalign 0.5
                                yalign 0.5

        # Feed
        viewport:
            xfill True
            yfill True
            mousewheel True
            draggable True

            frame:
                xfill True
                background None
                xpadding 0
                ypadding 10

                vbox:
                    xfill True
                    spacing 8

                    # Feed images (top: feed_1, bottom: feed_2)
                    for feed_path in ["images/clues/feed_1.png", "images/clues/feed_2.png"]:
                        if renpy.loadable(feed_path):
                            add feed_path:
                                fit "cover"
                                xsize 356
                                ysize 220
                                xalign 0.5
                        else:
                            frame:
                                xsize 356
                                ysize 220
                                xalign 0.5
                                background Solid("#151522")
                                text "Missing: [feed_path]":
                                    size 13
                                    color "#888888"
                                    xalign 0.5
                                    yalign 0.5

screen phone_instagram_story_zoom(photo_path):
    modal True
    zorder 120
    timer 3.0 action SetVariable("instagram_story_zoom_photo", None)

    if renpy.loadable(photo_path):
        add photo_path fit "cover"
    else:
        add Solid("#111111")
        text "Missing: [photo_path]":
            size 14
            color "#bbbbbb"
            xalign 0.5
            yalign 0.5


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
                spacing 0
                yalign 0.5

                textbutton "Recent Photos":
                    xsize 300
                    text_xalign 0.5
                    text_size 14
                    text_color "#ffffff"
                    text_hover_color "#ffffff"
                    action SetScreenVariable("gallery_tab", "photos")

        viewport:
            xfill True
            yfill True
            mousewheel True
            draggable True

            frame:
                xfill True
                background None
                xpadding 0
                ypadding 10

                vbox:
                    xfill True
                    spacing 8

                    if gallery_tab == "photos":
                        grid 2 3:
                            xalign 0.0
                            spacing 10

                            for photo_path in gallery_photos:
                                button:
                                    xsize 170
                                    ysize 170
                                    background Solid("#1f1f2f")
                                    hover_background Solid("#2f2f4a")
                                    action SetVariable("gallery_zoom_photo", photo_path)

                                    if renpy.loadable(photo_path):
                                        add photo_path:
                                            fit "cover"
                                            xsize 170
                                            ysize 170
                                    else:
                                        vbox:
                                            xalign 0.5
                                            yalign 0.5
                                            spacing 4
                                            text "PHOTO" size 14 color "#bbbbbb" xalign 0.5 bold True
                                            text photo_path.split("/")[-1] size 9 color "#888888" xalign 0.5

    if gallery_zoom_photo:
        use phone_gallery_photo_zoom(photo_path=gallery_zoom_photo)


screen phone_gallery_photo_zoom(photo_path):
    modal True
    zorder 120

    add Solid("#000000cc")

    frame:
        xalign 0.5
        yalign 0.5
        xsize 380
        ysize 520
        background Solid("#101018")
        xpadding 12
        ypadding 12

        has vbox
        spacing 8

        if renpy.loadable(photo_path):
            add photo_path:
                fit "contain"
                xalign 0.5
                yalign 0.5
                xsize 356
                ysize 456
        else:
            frame:
                xfill True
                ysize 456
                background Solid("#222233")
                text "Missing: [photo_path]" size 13 color "#bbbbbb" xalign 0.5 yalign 0.5

        textbutton "Close":
            xalign 1.0
            text_size 14
            text_color "#ffffff"
            text_hover_color "#dddddd"
            action SetVariable("gallery_zoom_photo", None)


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
            background Solid("#4735ea")
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
                                text "3rd Anniversary" size 15 color "#ffffff"

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
                                text "OCT" size 11 color "#4a90d9"
                                text "28" size 24 color "#4a90d9" bold True
                            vbox:
                                yalign 0.5
                                text "Flight to Tokyo" size 15 color "#ffffff"
                                text "ICN > HND  08:00 AM" size 12 color "#aaaaaa"


################################################################################
## Wallet
################################################################################

screen phone_wallet_content():
    vbox:
        xfill True
        yfill True

        use phone_app_header("Wallet")

        # Card display
        frame:
            xfill True
            ysize 115
            background Solid("#000000")
            xpadding 20
            ypadding 13

            vbox:
                spacing 6
                text "My Card" size 13 color "#aaaaaa"
                text "**** **** **** 1234" size 15 color "#ffffff"
                text "This month" size 11 color "#aaaaaa"
                text "$3556.70" size 26 color "#ffd700" bold True
                null height 8

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

                    text "Recent Transactions" size 15 color "#FFFFFF"

                    # All transactions share the same card style.
                    for tx in [
                        ("Global Wings Airline", "Feb 28 - Online", "$1775.50", "1 ticket"),
                        ("Korean Games", "Feb 27 - Online", "$2500.00", "In-app purchase"),
                        ("Starbucks", "Feb 26 - In store", "$5.80", "Card present"),
                        ("Convenience Store", "Feb 25 - In store", "$3.20", "Card present"),
                        ("Food Delivery", "Feb 24 - Online", "$18.50", "Delivery order"),
                    ]:
                        button:
                            xfill True
                            ysize 70
                            background Solid("#000000")
                            hover_background Solid("#2a2a5e")
                            xpadding 12
                            ypadding 8
                            action NullAction()

                            hbox:
                                xfill True
                                vbox:
                                    text tx[0] size 14 color "#ffffff"
                                    text tx[1] size 11 color "#888888"
                                vbox:
                                    xfill True
                                    yalign 0.5
                                    text tx[2] size 15 color "#ff6b6b" xalign 1.0
                                    text tx[3] size 11 color "#ff6b6b" xalign 1.0


################################################################################
## Memo / Notes
################################################################################

screen phone_memo_content():
    vbox:
        xfill True
        yfill True

        use phone_app_header("Memo")

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
                            text "About My Girlfriend" size 15 color "#fdd835" bold True
                            null height 3
                            text "- Wants to go on a trip to Tokyo" size 13 color "#ffffff"
                            text "- Promised to travel together for" size 13 color "#ffffff"
                            text "  our anniversary" size 13 color "#ffffff"
                            text "- Fav food: anything with chicken " size 13 color "#cccccc"
                            text "- Wants: limited edition perfume" size 13 color "#cccccc"
                            null height 4

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

        fixed:
            xfill True
            yfill True

            textbutton "< Back":
                xalign 0.0
                yalign 0.5
                text_size 14
                text_color "#aaaaaa"
                text_hover_color "#ffffff"
                action SetScreenVariable("current_app", "home")

            text "[title]":
                xalign 0.5
                yalign 0.5
                size 18
                color "#ffffff"
                bold True
