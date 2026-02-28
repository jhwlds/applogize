# /!\ default
# pc as in phone character :monikk:
default pc_sayori  = phone.character.Character("Sayori", phone.asset("sayori_icon.png"), "s", 21, "#22Abf8")
default pc_me      = phone.character.Character("Me", phone.asset("me_icon.png"), "me", 35, "#484848")
default pc_yuri    = phone.character.Character("Yuri", phone.asset("yuri_icon.png"), "y", 20, "#a327d6")
default pc_monika  = phone.character.Character("Monika", phone.asset("monika_icon.png"), "m", 40, "#0a0")
default pc_natsuki = phone.character.Character("Natsuki", phone.asset("natsuki_icon.png"), "n", 45, "#fbb")
default pc_gf      = phone.character.Character("Girlfriend", phone.asset("default_icon.png"), "gf", 30, "#ff6b9d")

default pov_key = "me"

define phone_s    = Character("Sayori",     screen="phone_say", who_style="phone_say_label", what_style="phone_say_dialogue")
define phone_me   = Character("Me",         screen="phone_say", who_style="phone_say_label", what_style="phone_say_dialogue")
define phone_gf   = Character("Girlfriend", screen="phone_say", who_style="phone_say_label", what_style="phone_say_dialogue")

init 100 python in phone.application:
    add_app_to_all_characters(message_app)
    add_app_to_all_characters(call_history_app)
    add_app_to_all_characters(calendar_app)

init 100 python in phone.calendar:
    add_calendar_to_all_characters(2023, 6, MONDAY)

# Disabled for Ren'Py 8.5 / Applogize (init order breaks group chat registration)
# init phone register:
#     define "Welcome":
#         add "s" add "me" add "y" add "m" add "n"
#         icon phone.asset("default_icon.png")
#         as thanks_for_using_my_framework key "ddu"

label phone_discussion_test:
    phone discussion "ddu":
        time year 2023 month 6 day 5 hour 16 minute 30 delay -1 # exact date and time at which i wrote this. yes i am feeling quite silly and goofy
        label "'Sayori' has been added to the group" delay -1
        label "'Me' has been added to the group" delay -1
        label "'Yuri' has been added to the group" delay -1
        label "'Monika' has been added to the group" delay -1
        label "'Natsuki' has been added to the group" delay 0.2
        "m" "Hey there!"
        "n" "Thank you for using my framework."
        "n" "I mean {i}of course{/i} you're using {b}this{/b} framework."
        "n" "...not like there are any better ones out there~"
        "s" "natsuki!!!!! {emoji=EllenScream}"
        "s" "no being a meanie!!!!!!!{emoji=EllenScream}{emoji=EllenScream}{emoji=EllenScream}"
        "y" "If you are interested in DDLC mods, be sure to check out our mod {a=https://undercurrentsmod.weebly.com}Doki Doki Undercurrents{/a}! {emoji=Melody}"
        "me" "In case you encounter an issue (or wanna make a suggestion),"
        "me" "you can:"
        "me" "DM me at {i}elckarow{/i} on Discord,"
        "me" "open an issue on {a=https://github.com/Elckarow/Better-EMR-Phone}GitHub{/a},"
        "me" "make a post on the phone's {a=https://elckarow.itch.io/better-emr-phone}Itch page{/a}."
        "s" "Happy coding!" 
    phone end discussion

    return

label phone_call_test:
    phone call "s"
    phone_s "Ohayouuu!!!!!!!!!!!!!!!!"
    phone_me "Hey!"
    "Why is she always this energetic?"
    phone end call
    "..."

    return

## ── Video Call Example ────────────────────────────────────────────────────────
## phone_video_call 레이어에 캐릭터를 먼저 올려야 상대방 "카메라 화면"으로 표시됨.
## video=True 는 Ren'Py 7.6 / 8.1 이상에서만 실제 영상통화 UI를 사용하고,
## 구버전에서는 자동으로 일반 통화 UI로 fallback 됨.

label phone_video_call_test:
    # 1. 상대방 카메라 피드 - 전용 레이어에 캐릭터 표시
    show gf angry1 onlayer phone_video_call

    # 2. 영상통화 시작 (video 키워드만 지정, 값 없음)
    phone call "gf" video

    phone_gf "..."
    phone_gf "Why are you calling me on video right now?"
    phone_me "I wanted you to see my face when I say this."
    phone_me "I'm sorry. I really am."
    phone_gf "..."
    phone_gf "You look terrible, by the way."
    phone_me "Yeah. I haven't slept."

    # 3. 통화 종료
    phone end call

    # 4. 레이어 정리 (다음 씬에 영향 없도록)
    scene onlayer phone_video_call

    return