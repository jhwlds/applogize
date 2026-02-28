#!/usr/bin/env python3
"""Record 6 seconds from mic, save to record_temp.wav in current dir. For use with /analyze STT."""
import sys

def main():
    try:
        import pyaudio
        import wave
        import struct
    except ImportError as e:
        print("ERROR: " + str(e)[:200])
        sys.exit(1)
    try:
        RATE = 16000
        CHUNK = 1024
        SECONDS = 15
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        out_path = "record_temp.wav"
        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
        frames = []
        for _ in range(0, int(RATE / CHUNK * SECONDS)):
            data = stream.read(CHUNK, exception_on_overflow=False)
            frames.append(data)
        stream.stop_stream()
        stream.close()
        p.terminate()
        raw = b"".join(frames)

        # If input level is low, apply a safe digital gain to help STT.
        # (Hume sometimes returns empty transcript when audio is too quiet.)
        if raw:
            samples = struct.unpack("<%dh" % (len(raw) // 2), raw)
            peak = max(abs(s) for s in samples) if samples else 0
            if 0 < peak < 8000:
                target = 20000
                gain = min(8.0, target / float(peak))
                scaled = []
                for s in samples:
                    v = int(s * gain)
                    if v > 32767:
                        v = 32767
                    elif v < -32768:
                        v = -32768
                    scaled.append(v)
                raw = struct.pack("<%dh" % len(scaled), *scaled)

        with wave.open(out_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)  # 16-bit
            wf.setframerate(RATE)
            wf.writeframes(raw)
        samples = struct.unpack("<%dh" % (len(raw) // 2), raw)
        peak = max(abs(s) for s in samples) if samples else 0
        if peak < 100:
            print("ERROR: Recorded audio is silence (peak=%d). Check macOS mic permission for this app." % peak)
            sys.exit(1)
        print("OK peak=%d" % peak)
    except Exception as e:
        print("ERROR: " + str(e)[:200])
        sys.exit(1)

if __name__ == "__main__":
    main()
