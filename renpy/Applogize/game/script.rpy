# The script of the game goes in this file.

# Declare characters used by this game. The color argument colorizes the
# name of the character.
image apple normal = "images/characters/idle_pose.png"
define apple = Character("Apple")


# The game starts here.

label start:

    # Show a background. This uses a placeholder by default, but you can
    # add a file (named either "bg room.png" or "bg room.jpg") to the
    # images directory to show it.

    scene bg room

    # This shows a character sprite. A placeholder is used, but you can
    # replace it by adding a file named "eileen happy.png" to the images
    # directory.

    show apple normal

    # These display lines of dialogue.

    apple "Hey bro, I'm sorry but I have to tell you that I'm leaving you."

    apple "I'm sorry but I have to tell you that I'm leaving you. I'm not sure why I'm doing this but I know I have to do it."

    # This ends the game.

    return
