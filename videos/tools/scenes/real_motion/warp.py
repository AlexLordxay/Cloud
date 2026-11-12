# The picture, captions and music were laid out for the first recording (voice.mp3, video 56 s). The one-take
# re-recording (voice_v2.mp3, 12.11) is ~3 s longer, so the video runs on a new clock: KEYS pair each phrase's start on the
# new timeline with its start on the old one; old(t) maps new video time to the old layout, new(t) the other way.
KEYS = [(0.0, 0.0), (0.15, 0.15), (2.85, 3.0), (4.95, 5.05), (9.15, 9.1), (11.95, 11.95), (15.35, 15.0), (19.7, 19.85),
        (23.0, 22.05), (28.15, 27.2), (30.9, 30.4), (34.7, 33.85), (36.5, 35.55), (41.15, 39.9), (44.25, 42.9),
        (46.75, 44.85), (51.45, 49.35), (54.8, 52.4), (58.4, 56.0)]

def _map(t, src, dst):
    if t <= src[0]: return dst[0] + (t - src[0])
    for (a0, a1), (b0, b1) in zip(zip(src, src[1:]), zip(dst, dst[1:])):
        if t <= a1: return b0 + (t - a0) * (b1 - b0) / (a1 - a0)
    return dst[-1] + (t - src[-1])

def old(t): return _map(t, [k[0] for k in KEYS], [k[1] for k in KEYS])
def new(t): return _map(t, [k[1] for k in KEYS], [k[0] for k in KEYS])
