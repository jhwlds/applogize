Ren'Py does not support AAC audio. For reliable video+audio playback, use WebM (VP9+Opus):

  ffmpeg -i happy_ending.mp4 -c:v libvpx-vp9 -b:v 1500k -c:a libopus -b:a 128k happy_ending.webm

  # 끝 0.5초 페이드아웃 (크레딧 직전용):
  ffmpeg -i happy_ending.webm -vf "fade=t=out:st=12.879:d=0.5" -af "afade=t=out:st=12.879:d=0.5" -c:v libvpx-vp9 -b:v 1500k -c:a libopus -b:a 128k happy_ending_fade.webm

For intro/other clips you can use .mkv with Opus (video copy; sometimes only audio shows):

  ffmpeg -i intro_video.av1.mp4 -c:v copy -c:a libopus -b:a 128k intro_video.mkv

The game prefers video/happy_ending.webm so the ending video is visible; .mkv fallback may show sound only.
Requires ffmpeg with libopus and libvpx: https://ffmpeg.org/
