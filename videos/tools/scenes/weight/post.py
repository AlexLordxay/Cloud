# Finishes «Скільки ти важиш на інших планетах?»: the frames (render.js, 720×1280) brought up to 1080×1920 with the
# titles over the sky — the world's name, the kilograms rolling from the last world's number to this one's (as the
# scale's own display does), a line with the twist — the source of the Moon's relief, the scale's beep as each number
# settles, the voice (sped up 1.07) over the music (music.js), ducked under it, at -14 LUFS.
#   python3 scenes/weight/post.py         ->  videos/weight.mp4
#   python3 scenes/weight/post.py sound   ->  the same, the titled frames (work/weight/out) kept: only the sound redone
# The voice: scenes/weight/voice_all.mp3 — the take with «Причепи крила — і полетиш» (the model stressed «крилА», and with
# stress marks read «прічіпі кріла») replaced by «Тут можна літати, як птах» (fix_bird.mp3) at 51.68 s; or voice.mp3.
import os, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.io import wavfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
WORK = os.path.join(TOOLS, 'work', 'weight')
VIDEOS = os.path.abspath(os.path.join(TOOLS, '..'))
FF = __import__('imageio_ffmpeg').get_ffmpeg_exe()
W, H, FPS, DUR = 1080, 1920, 30, 72.3
FONT = os.path.join(TOOLS, 'fonts', 'Unbounded.ttf')
FONT2 = os.path.join(TOOLS, 'fonts', 'Commissioner.ttf')

# (start, end, name, kg, [(from, to, line)]) — the same shots as render.js; kg None: no scale
SHOTS = [
    (0.0, 14.41, 'МІСЯЦЬ', 11.6, [(0.4, 6.5, 'як дворічна дитина'), (6.6, 10.3, 'маса та сама — тягне слабше'), (10.4, 14.41, 'стрибок у 6 разів вищий')]),
    (14.41, 17.44, 'МЕРКУРІЙ', 26.4, []),
    (17.44, 20.67, 'МАРС', 26.6, [(17.6, 20.67, 'як першокласник')]),
    (20.67, 27.54, 'ВЕНЕРА', 63.3, [(21.0, 24.0, 'майже як удома'), (24.0, 27.54, 'але тиск — як на глибині 900 м')]),
    (27.54, 32.69, 'ЮПІТЕР', 177, [(28.0, 32.69, 'ніби ще два мішки цементу')]),
    (32.69, 43.25, 'САТУРН', 74.5, [(33.0, 37.4, 'майже як на Землі'), (37.4, 43.25, 'хоча він у 95 разів масивніший')]),
    (43.25, 50.64, 'ТИТАН', 9.7, [(43.6, 47.2, 'супутник Сатурна'), (47.2, 50.64, 'густе повітря: можна літати, як птах')]),
    (50.64, 54.34, 'ПЛУТОН', 4.4, [(51.0, 54.34, 'як кіт')]),
    (54.34, 57.91, 'СОНЦЕ', 1950, [(54.8, 57.91, 'як легковик')]),
    (57.91, 66.12, 'НЕЙТРОННА ЗІРКА', 9e12, [(58.4, 60.8, 'мільярди тонн'), (60.8, 66.12, 'чайна ложка її речовини важча\nза всіх людей на Землі разом')]),
    (66.12, DUR, 'А ТИ?', None, [(66.3, DUR, 'твоя вага × 0,38 = вага на Марсі\nпиши в коментарях')]),
]
CREDIT = (0.0, 14.41, 'Рельєф Місяця — NASA LRO (LOLA, LROC) · художня візуалізація')


def fmt(kg):
    if kg >= 1e4:                                     # tonnes, grouped by thousands
        return '{:,}'.format(int(round(kg / 1000))).replace(',', ' ') + ' т'
    if kg >= 1000:
        return '{:,}'.format(int(round(kg))).replace(',', ' ') + ' кг'
    return ('%.1f' % kg).replace('.', ',') + ' кг' if kg < 100 else '%d кг' % round(kg)


def value(i, lt):
    """The number at shot-time lt: rolling from the last world's to this one's over ~1 s (the scale's display does the
    same); to the neutron star it rolls on a log scale, faster and faster through the digits."""
    kg = SHOTS[i][3]
    prev = next((s[3] for s in reversed(SHOTS[:i]) if s[3]), 70.0)
    roll = 1.1 if kg < 1e6 else 2.2
    u = min(1.0, max(0.0, (lt - 0.15) / roll)); e = u * u * (3 - 2 * u)
    if kg > 1e6: return prev * (kg / prev) ** (u ** 1.6)
    return prev + (kg - prev) * e


def text_layer(lines, font, size, y, spacing=1.12, alpha=255):
    """Centred lines with a soft dark halo (readable over a bright sky), as an RGBA layer."""
    f = ImageFont.truetype(font, size)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    sh = Image.new('L', (W, H), 0); ds = ImageDraw.Draw(sh)
    for k, line in enumerate(lines):
        w = d.textlength(line, font=f); x = (W - w) / 2; yy = y + k * size * spacing
        d.text((x, yy), line, font=f, fill=(255, 255, 255, alpha)); ds.text((x, yy), line, font=f, stroke_width=max(2, size // 14), fill=210)
    halo = sh.filter(ImageFilter.GaussianBlur(size * 0.18))
    base = Image.new('RGBA', (W, H), (0, 0, 0, 0)); base.putalpha(halo)
    return Image.alpha_composite(base, lay)


def fade(lay, k):
    if k >= 1: return lay
    l = lay.copy(); l.putalpha(l.getchannel('A').point(lambda a: int(a * k))); return l


def frames():
    src = os.path.join(WORK, 'frames'); out = os.path.join(WORK, 'out'); os.makedirs(out, exist_ok=True)
    n = int(round(DUR * FPS))
    names = [text_layer([s[2]], FONT, 54, 190, alpha=235) for s in SHOTS]
    subs = {(i, j): text_layer(line[2].split('\n'), FONT, 40, 462, spacing=1.3) for i, s in enumerate(SHOTS) for j, line in enumerate(s[4])}
    credit = text_layer([CREDIT[2]], FONT2, 26, 1575, alpha=200)
    # over a bright sky (Mars, Venus, the gas giants, Titan, the Sun) a soft shade at the top keeps the titles readable
    shade = Image.new('RGBA', (W, H), (0, 0, 0, 0)); sa = np.zeros((H, W), np.uint8)
    sa[:760] = (np.clip(1 - np.arange(760) / 760.0, 0, 1) ** 1.6 * 120)[:, None].astype(np.uint8); shade.putalpha(Image.fromarray(sa))
    BRIGHT = {'МАРС', 'ВЕНЕРА', 'ЮПІТЕР', 'САТУРН', 'ТИТАН', 'СОНЦЕ', 'А ТИ?'}
    cache = {}
    for f in range(n):
        t = f / FPS
        i = next(k for k, s in enumerate(SHOTS) if s[0] <= t < s[1] or k == len(SHOTS) - 1)
        s = SHOTS[i]; lt = t - s[0]
        im = Image.open(os.path.join(src, f'f_{f:05d}.jpg')).convert('RGB').resize((W, H), Image.LANCZOS).convert('RGBA')
        k = min(1.0, lt / 0.25)                        # each title comes in over a quarter second
        if s[2] in BRIGHT: im = Image.alpha_composite(im, shade)
        im = Image.alpha_composite(im, fade(names[i], k))
        if s[3]:
            txt = fmt(value(i, lt))
            if txt not in cache: cache[txt] = text_layer([txt], FONT, 132 if len(txt) < 10 else 96, 268)
            im = Image.alpha_composite(im, fade(cache[txt], k))
        for j, (a, b, _) in enumerate(s[4]):
            if a <= t < b:
                kk = min(1.0, (t - a) / 0.3, (b - t) / 0.2 if b < s[1] - 0.05 else 1.0)
                im = Image.alpha_composite(im, fade(subs[(i, j)], kk))
        if CREDIT[0] <= t < CREDIT[1]: im = Image.alpha_composite(im, credit)
        im.convert('RGB').save(os.path.join(out, f'f_{f:05d}.jpg'), quality=94)
        if f % 300 == 0: print('titles', f, '/', n, flush=True)


def beeps():
    """The scale's beep as each number settles: two short soft tones."""
    sr = 44100; y = np.zeros(int(DUR * sr) + sr, np.float32)
    for i, s in enumerate(SHOTS):
        if not s[3] or s[3] > 1e6: continue
        t = s[0] + 0.15 + 1.1 + 0.05
        for k, fq in enumerate((1568.0, 2093.0)):
            n = int(0.07 * sr); env = np.sin(np.pi * np.arange(n) / n) ** 2; a = int((t + k * 0.09) * sr)
            y[a:a + n] += (np.sin(2 * np.pi * fq * np.arange(n) / sr) * env * 0.12).astype(np.float32)
    wavfile.write(os.path.join(WORK, 'beeps.wav'), sr, (np.stack([y, y], 1) * 32767).astype(np.int16))


def voice():
    src = os.path.join(HERE, 'voice_all.mp3') if os.path.exists(os.path.join(HERE, 'voice_all.mp3')) else os.path.join(HERE, 'voice.mp3')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', src, '-af', 'atempo=1.07,apad=pad_dur=0.8', '-ar', '44100', '-ac', '2',
                    os.path.join(WORK, 'voice.wav')], check=True)


def encode():
    out = os.path.join(VIDEOS, 'weight.mp4')
    mix = ('[1:a]volume=0.55[m];[0:a]asplit=2[v][sc];[m][sc]sidechaincompress=threshold=0.04:ratio=4:attack=60:release=700[md];'
           '[md][v][2:a]amix=inputs=3:normalize=0,volume=1.15,loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st=%.2f:d=1.0[a]' % (DUR - 1.0))
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', os.path.join(WORK, 'voice.wav'), '-i', os.path.join(WORK, 'music.wav'),
                    '-i', os.path.join(WORK, 'beeps.wav'), '-framerate', str(FPS), '-i', os.path.join(WORK, 'out', 'f_%05d.jpg'),
                    '-filter_complex', mix, '-map', '3:v', '-map', '[a]', '-t', f'{DUR:.2f}',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                    '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-movflags', '+faststart', out], check=True)
    print('written', out)


if __name__ == '__main__':
    import sys
    voice(); beeps()
    if 'sound' not in sys.argv[1:]: frames()
    encode()
