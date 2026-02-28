# Stub for Python 3.13+ where aifc was removed from the standard library.
# speech_recognition imports aifc at load time; we only use Microphone + Google,
# so AIFF file I/O is never used. This stub allows the import to succeed.

class Error(Exception):
    pass

def open(*args, **kwargs):
    raise NotImplementedError("aifc was removed in Python 3.13; use WAV or microphone input only.")
