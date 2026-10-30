# Складає 4 варіанти гачка в одне відео з номерами (кожен звучить двічі)
import subprocess
from PIL import Image, ImageDraw, ImageFont
texts = ["Ти Терези́?", "Ти — Терези?", "Ти, мабуть, Терези?", "А ти Терези?"]
F = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
big, small = ImageFont.truetype(F, 360), ImageFont.truetype(F, 60)
parts = []
for i, t in enumerate(texts, 1):
    im = Image.new("RGB", (720, 1280), (8, 12, 30)); d = ImageDraw.Draw(im)
    d.text((360, 520), str(i), font=big, fill=(255, 210, 120), anchor="mm")
    d.text((360, 820), t, font=small, fill="white", anchor="mm")
    im.save(f"card{i}.png")
    # 0,6 с тиші, голос, 0,8 с, голос, 1,2 с
    a = (f"[0:a]aresample=44100,asplit=2[x][y];aevalsrc=0:d=0.6:s=44100[s1];aevalsrc=0:d=0.8:s=44100[s2];"
         f"aevalsrc=0:d=1.2:s=44100[s3];[s1][x][s2][y][s3]concat=n=5:v=0:a=1[a]")
    out = f"part{i}.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"v{i}.mp3", "-loop", "1", "-framerate", "30", "-i", f"card{i}.png",
                    "-filter_complex", a, "-map", "1:v", "-map", "[a]", "-shortest", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-c:a", "aac", "-b:a", "160k", out], check=True)
    parts.append(out)
open("list.txt", "w").write("".join(f"file '{p}'\n" for p in parts))
subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", "list.txt", "-c", "copy",
                "../../../../zodiac_lib_hooks.mp4"], check=True)
