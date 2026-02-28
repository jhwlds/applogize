Ren'Py does not support AAC audio. To get sound, convert to Opus (video is copied, not re-encoded):

  ffmpeg -i intro_video.av1.mp4 -c:v copy -c:a libopus -b:a 128k intro_video.mkv

Then the game will play video/intro_video.mkv with sound.
Requires ffmpeg with libopus: https://ffmpeg.org/
