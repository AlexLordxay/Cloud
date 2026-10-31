# Finishes the finale and joins it to the cartoon: the frames (720×1280) brought up to the cartoon's 1080×1920, the
# question over the black sky above his helmet once his head has sunk, the sound (sound.py), then the cartoon
# (videos/stick_story.mp4) and the finale cut together, hard (white paper to the black of space).
#   python3 scenes/moon_final/post.py   ->  videos/moon_final.mp4 (the finale alone), videos/stick_story_final.mp4
import os, subprocess
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.abspath(os.path.join(HERE, '../..'))
WORK = os.path.join(TOOLS, 'work', 'moon_final')
VIDEOS = os.path.abspath(os.path.join(TOOLS, '..'))
FF = __import__('imageio_ffmpeg').get_ffmpeg_exe()
W, H, FPS = 1080, 1920, 30
TITLE = ['Що з цією планетою', 'не так?']
T_IN, FADE = 10.2, 0.7                      # the question comes in after the head has sunk (8.2–9.8 s)


def title_layer():
    """The question, white, centred in the black sky above the helmet."""
    font = ImageFont.truetype(os.path.join(TOOLS, 'fonts', 'Unbounded.ttf'), 66)
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    y = 210
    for line in TITLE:
        w = d.textlength(line, font=font)
        d.text(((W - w) / 2, y), line, font=font, fill=(255, 255, 255, 255))
        y += 92
    return lay


def main():
    src = os.path.join(WORK, 'frames'); out = os.path.join(WORK, 'out'); os.makedirs(out, exist_ok=True)
    frames = sorted(f for f in os.listdir(src) if f.endswith('.jpg'))
    lay = title_layer()
    for i, f in enumerate(frames):
        im = Image.open(os.path.join(src, f)).convert('RGB').resize((W, H), Image.LANCZOS)
        k = min(1.0, max(0.0, (i / FPS - T_IN) / FADE))
        if k > 0:
            l = lay.copy(); l.putalpha(l.getchannel('A').point(lambda a: int(a * k * k * (3 - 2 * k))))
            im = Image.alpha_composite(im.convert('RGBA'), l).convert('RGB')
        im.save(os.path.join(out, f), quality=95)
    n = len(frames)
    fin = os.path.join(VIDEOS, 'moon_final.mp4')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(out, 'f_%05d.jpg'),
                    '-i', os.path.join(WORK, 'audio.wav'), '-map', '0:v', '-map', '1:a', '-t', f'{n / FPS:.3f}',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
                    '-c:a', 'aac', '-b:a', '160k', '-ar', '44100', '-movflags', '+faststart', fin], check=True)
    print('written', fin)
    full = os.path.join(VIDEOS, 'stick_story_final.mp4')
    subprocess.run([FF, '-y', '-loglevel', 'error', '-i', os.path.join(VIDEOS, 'stick_story.mp4'), '-i', fin, '-filter_complex',
                    '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]', '-map', '[v]', '-map', '[a]',
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '160k',
                    '-movflags', '+faststart', full], check=True)
    print('written', full)


if __name__ == '__main__':
    main()
