# Mixes each organ sketch with its breathing and cuts them into one listening video (the app plays mp4, not mp3):
# three clips of ~16 s, each on its own card with a number and a line about the character.
#   node scenes/moonfall/sound_preview.js && python3 scenes/moonfall/breath.py && python3 scenes/moonfall/sound_preview.py
#   -> videos/moonfall_sound_preview.mp4   (and work/moonfall/mix_<variant>.wav)
import math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.io import wavfile
import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
WORK = os.path.join(TOOLS, 'work', 'moonfall')
OUT = os.path.abspath(os.path.join(TOOLS, '..', 'moonfall_sound_preview.mp4'))
FF = imageio_ffmpeg.get_ffmpeg_exe()
SR, W, H, FPS = 44100, 720, 1280, 15
GAP = 1.0

CARDS = {
    1: ('Годинник', 'Рівний пульс органа — як годинник,\nщо поволі прискорюється.\nДихання: від спокійного до частого,\nпотім затамував подих —\nі акорд світлішає.'),
    2: ('Хорал', 'Повільні акорди, що «дихають»,\nі самотня флейта зверху.\nДихання глибоке, неквапливе.\nБільше величі, ніж тривоги.'),
    3: ('Відлік', 'Тихий тик, що прискорюється,\nі акорд, що крок за кроком підіймається.\nДихання часте й уривчасте.\nНайтривожніший.'),
}


def font(file, size, wght):
    f = ImageFont.truetype(os.path.join(TOOLS, 'fonts', file), size)
    try:
        f.set_variation_by_axes([wght if a['name'] in (b'Weight', 'Weight') else a['default'] for a in f.get_variation_axes()])
    except Exception:
        pass
    return f


def load(name):
    sr, y = wavfile.read(os.path.join(WORK, name)); assert sr == SR
    return y.astype(np.float32) / 32768


def level_db(x, win=3 * SR):
    m = x.mean(axis=1) if x.ndim > 1 else x
    return max(20 * math.log10(math.sqrt((m[i:i + win] ** 2).mean()) + 1e-9) for i in range(0, len(m) - win, SR // 4))


def mix(v):
    music, breath = load(f'music_{v}.wav'), load(f'breath_{v}.wav')
    n = min(len(music), len(breath))
    music, breath = music[:n], breath[:n]
    music *= 10 ** ((-21 - level_db(music)) / 20)                # the loudest swell of the organ at -21 dBFS (3 s mean)
    breath *= 10 ** ((-27 - level_db(breath, SR)) / 20)          # breathing in front of the quiet organ, under the swell
    y = music + breath
    y *= 0.89 / max(0.89, np.abs(y).max())
    wavfile.write(os.path.join(WORK, f'mix_{v}.wav'), SR, (y * 32767).astype(np.int16))
    return y


def card(v):
    name, text = CARDS[v]
    im = Image.new('RGB', (W, H), (6, 8, 16))
    d = ImageDraw.Draw(im)
    for r in range(520, 0, -8):                                   # a soft glow behind the number
        a = int(26 * (1 - r / 520) ** 2)
        d.ellipse((W / 2 - r, 470 - r, W / 2 + r, 470 + r), fill=(6 + a, 8 + a, 16 + int(a * 1.5)))
    rng = np.random.default_rng(3)
    for _ in range(90):
        x, y, s = rng.integers(0, W), rng.integers(0, H), rng.random()
        d.ellipse((x, y, x + 1 + s * 1.6, y + 1 + s * 1.6), fill=(int(120 + 120 * s),) * 3)
    d.text((W / 2, 150), 'Місяць упав: звук', font=font('Commissioner.ttf', 30, 500), fill=(170, 180, 205), anchor='mm')
    d.text((W / 2, 470), str(v), font=font('Unbounded.ttf', 330, 600), fill=(247, 198, 107), anchor='mm')
    d.text((W / 2, 760), f'«{name}»', font=font('Unbounded.ttf', 62, 600), fill=(255, 255, 255), anchor='mm')
    d.multiline_text((W / 2, 860), text, font=font('Commissioner.ttf', 28, 500), fill=(205, 212, 230), anchor='ma', align='center', spacing=12)
    d.text((W / 2, 1210), 'орган + дихання космонавта · ~15 с', font=font('Commissioner.ttf', 24, 500), fill=(130, 140, 165), anchor='mm')
    return im


def main():
    mixes = [mix(v) for v in (1, 2, 3)]
    gap = np.zeros((int(GAP * SR), 2), np.float32)
    audio = np.concatenate([a for m in mixes for a in (m, gap)][:-1])
    wav = os.path.join(WORK, 'preview.wav')
    wavfile.write(wav, SR, (audio * 32767).astype(np.int16))
    dur = len(audio) / SR
    cards = {v: card(v) for v in (1, 2, 3)}
    spans, t = [], 0.0
    for v, m in zip((1, 2, 3), mixes):
        spans.append((v, t, t + len(m) / SR)); t += len(m) / SR + GAP
    p = subprocess.Popen([FF, '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                          '-i', wav, '-filter_complex', '[1:a]loudnorm=I=-16:TP=-1.5:LRA=11[a]', '-map', '0:v', '-map', '[a]',
                          '-c:v', 'libx264', '-preset', 'fast', '-crf', '24', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k', '-ar', '48000',
                          '-movflags', '+faststart', '-t', f'{dur:.2f}', OUT], stdin=subprocess.PIPE)
    for i in range(int(dur * FPS)):
        tt = i / FPS
        v, a, b = next(((v, a, b) for v, a, b in spans if a <= tt <= b + GAP), spans[-1])
        im = cards[v].copy()
        if a <= tt <= b:
            d = ImageDraw.Draw(im)
            k = (tt - a) / (b - a)
            d.rounded_rectangle((90, 1140, W - 90, 1146), radius=3, fill=(40, 46, 66))
            d.rounded_rectangle((90, 1140, 90 + (W - 180) * k, 1146), radius=3, fill=(247, 198, 107))
        p.stdin.write(im.tobytes())
    p.stdin.close(); p.wait()
    print('done:', OUT, f'{dur:.1f} s')


if __name__ == '__main__':
    main()
