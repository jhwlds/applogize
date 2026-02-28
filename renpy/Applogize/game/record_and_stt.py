#!/usr/bin/env python3
"""Standalone script: record 6s from mic, Google STT, print text. Used by Ren'Py via subprocess.
Run with system Python that has: pip install SpeechRecognition pyaudio
Output: one line of transcribed text, or "ERROR: <message>" on failure."""
import sys

def main():
    try:
        import speech_recognition as sr
    except ImportError as e:
        print("ERROR: Need SpeechRecognition and PyAudio: pip install SpeechRecognition pyaudio", file=sys.stderr)
        print("ERROR: " + str(e)[:200])
        sys.exit(1)
    try:
        r = sr.Recognizer()
        with sr.Microphone() as source:
            r.adjust_for_ambient_noise(source, duration=0.5)
            audio = r.record(source, duration=6)
        text = r.recognize_google(audio, language="en-US")
        text = (text or "").strip()
        print(text)
    except Exception as e:
        print("ERROR: " + str(e)[:200])
        sys.exit(1)

if __name__ == "__main__":
    main()
