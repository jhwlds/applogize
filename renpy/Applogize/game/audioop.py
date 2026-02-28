# Pure Python fallback for audioop (removed in Python 3.13).
# Implements only the subset used by speech_recognition: rms, add, bias, ratecv, lin2lin, tomono, byteswap, error.

import struct

class error(Exception):
    pass

def _unpack(width, data):
    """Yield signed samples from bytes; width 1,2,3,4."""
    n = len(data) // width
    if width == 1:
        for i in range(n):
            b = data[i]
            yield b - 128 if b & 128 else b
    elif width == 2:
        for i in range(n):
            yield struct.unpack_from("<h", data, i * 2)[0]
    elif width == 3:
        for i in range(n):
            b = data[i * 3 : i * 3 + 3] + b"\x00"
            yield struct.unpack_from("<i", b)[0] >> 8
    else:  # 4
        for i in range(n):
            yield struct.unpack_from("<i", data, i * 4)[0]

def _pack(width, samples):
    """Pack signed samples to bytes."""
    if width == 1:
        return bytes((s + 128) & 0xFF for s in samples)
    elif width == 2:
        return struct.pack("<" + "h" * len(samples), *samples)
    elif width == 3:
        out = []
        for s in samples:
            s = max(-0x800000, min(0x7FFFFF, s))
            out.append(struct.pack("<i", s << 8)[:3])
        return b"".join(out)
    else:
        return struct.pack("<" + "i" * len(samples), *samples)

def rms(buffer, width):
    if width not in (1, 2, 3, 4) or len(buffer) % width != 0:
        raise error("rms: bad args")
    if len(buffer) == 0:
        return 0
    samples = list(_unpack(width, buffer))
    s = sum(s * s for s in samples)
    return int((s / len(samples)) ** 0.5)

def add(buffer1, buffer2, width):
    if width not in (1, 2, 3, 4) or len(buffer1) != len(buffer2) or len(buffer1) % width != 0:
        raise error("add: bad args")
    s1 = list(_unpack(width, buffer1))
    s2 = list(_unpack(width, buffer2))
    out = []
    for a, b in zip(s1, s2):
        out.append(max(-0x80000000, min(0x7FFFFFFF, a + b)))
    return _pack(width, out)

def bias(buffer, width, bias_val):
    if width not in (1, 2, 3, 4) or len(buffer) % width != 0:
        raise error("bias: bad args")
    samples = [s + bias_val for s in _unpack(width, buffer)]
    return _pack(width, samples)

def ratecv(buffer, width, nchannels, inrate, outrate, state):
    if width not in (1, 2, 3, 4) or nchannels < 1 or inrate <= 0 or outrate <= 0:
        raise error("ratecv: bad args")
    if state is None:
        state = (0, 0)
    # Simple linear interpolation resample: consume inrate, produce outrate
    d = len(buffer) // (width * nchannels)
    if d == 0:
        return buffer, state
    # Approximate: out_samples = d * outrate / inrate
    out_d = int(d * outrate / inrate)
    if out_d == 0:
        return b"", state
    samples = list(_unpack(width, buffer))
    frame_len = nchannels
    in_frames = [samples[i:i + frame_len] for i in range(0, len(samples), frame_len)]
    out_frames = []
    for i in range(out_d):
        src_i = i * inrate / outrate
        i0 = int(src_i) % len(in_frames)
        i1 = (i0 + 1) % len(in_frames)
        t = src_i - int(src_i)
        f = [int(in_frames[i0][c] * (1 - t) + in_frames[i1][c] * t) for c in range(frame_len)]
        out_frames.extend(f)
    return _pack(width, out_frames), state

def lin2lin(buffer, width, newwidth):
    if width not in (1, 2, 3, 4) or newwidth not in (1, 2, 3, 4) or len(buffer) % width != 0:
        raise error("lin2lin: bad args")
    samples = list(_unpack(width, buffer))
    return _pack(newwidth, samples)

def tomono(buffer, width, fac1, fac2):
    if width not in (1, 2, 3, 4) or len(buffer) % (2 * width) != 0:
        raise error("tomono: bad args")
    samples = list(_unpack(width, buffer))
    mono = []
    for i in range(0, len(samples), 2):
        m = int(samples[i] * fac1 + samples[i + 1] * fac2)
        mono.append(max(-0x80000000, min(0x7FFFFFFF, m)))
    return _pack(width, mono)

def byteswap(buffer, width):
    if width not in (1, 2, 3, 4) or len(buffer) % width != 0:
        raise error("byteswap: bad args")
    if width == 1:
        return buffer
    out = []
    for i in range(0, len(buffer), width):
        out.append(buffer[i : i + width][::-1])
    return b"".join(out)
