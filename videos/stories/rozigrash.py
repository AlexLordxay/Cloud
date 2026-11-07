from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
import numpy as np, math
W,H=1080,1920
sky=Image.open('data/sky/eso0932a.jpg').convert('RGB')
# central galaxy region, vertical crop, rotate so the band is diagonal
c=sky.crop((1800,0,4200,3000)).rotate(-28,resample=Image.BICUBIC,expand=False)
cw,ch=c.size
s=max(W/cw,H/ch)*1.9
c=c.resize((int(cw*s),int(ch*s)),Image.LANCZOS)
x0=(c.width-W)//2; y0=(c.height-H)//2
bg=c.crop((x0,y0,x0+W,y0+H))
bg=ImageEnhance.Brightness(bg).enhance(0.85)
a=np.asarray(bg).astype(np.float32)/255
yy=np.linspace(0,1,H)[:,None,None]
# darken top (title) and lower area (sticker) slightly
shade=1-0.55*np.exp(-((yy-0.17)/0.16)**2)-0.35*np.exp(-((yy-0.80)/0.15)**2)
a*=shade
a=np.clip(a,0,1)
img=Image.fromarray((a*255).astype(np.uint8))

# falling star: streak from upper right to point P with glow + flare
glow=Image.new('RGB',(W,H),0); g=ImageDraw.Draw(glow)
P=(330,1130); L=620; ang=math.radians(205)
dx,dy=math.cos(ang),-math.sin(ang)  # direction from head back to tail
N=160
for i in range(N):
    t=i/N
    x=P[0]-dx*L*t*-1; y=P[1]-dy*L*t*-1
for i in range(N,0,-1):
    t=i/N
    x=P[0]+ (900-P[0])*t; y=P[1]+(420-P[1])*t
    r=1+9*(1-t)
    v=int(255*(1-t)**1.6)
    g.ellipse((x-r,y-r,x+r,y+r),fill=(int(v*0.85),int(v*0.92),v))
glow1=glow.filter(ImageFilter.GaussianBlur(14))
glow2=glow.filter(ImageFilter.GaussianBlur(3))
fl=Image.new('RGB',(W,H),0); f=ImageDraw.Draw(fl)
for r,v in [(110,40),(60,90),(30,170),(14,255)]:
    f.ellipse((P[0]-r,P[1]-r,P[0]+r,P[1]+r),fill=(v,int(v*0.95),int(v*0.85)))
fl=fl.filter(ImageFilter.GaussianBlur(18))
sp=Image.new('RGB',(W,H),0); s2=ImageDraw.Draw(sp)
for (ax,ay,bx,by,wd) in [(P[0]-170,P[1],P[0]+170,P[1],3),(P[0],P[1]-170,P[0],P[1]+170,3)]:
    s2.line((ax,ay,bx,by),fill=(255,240,220),width=wd)
sp=sp.filter(ImageFilter.GaussianBlur(2.5))
A=np.asarray(img).astype(np.float32)
for layer,k in [(glow1,1.3),(glow2,1.0),(fl,1.2),(sp,0.9)]:
    A=255-(255-A)*(1-np.asarray(layer).astype(np.float32)/255*k).clip(0,1)
img=Image.fromarray(A.clip(0,255).astype(np.uint8))

d=ImageDraw.Draw(img)
U=lambda s:ImageFont.truetype('fonts/Unbounded.ttf',s)
C=lambda s:ImageFont.truetype('fonts/Commissioner.ttf',s)
def ctext(y,t,font,fill=(255,255,255)):
    w=d.textlength(t,font=font); 
    d.text(((W-w)/2+3,y+3),t,font=font,fill=(0,0,0))
    d.text(((W-w)/2,y),t,font=font,fill=fill,stroke_width=1 if font.size<80 and 'Commissioner' in font.path else 0,stroke_fill=fill)
gold=(255,214,140)
ctext(170,"🎁".replace("🎁",""),U(10))
ctext(165,"РОЗІГРАШ",U(92),gold)
ctext(285,"відео про ваше небо",U(52))
ctext(420,"Яким був космос",C(56))
ctext(490,"у мить вашого народження?",C(56))
ctext(1300,"Напишіть дату, місто",C(50))
ctext(1365,"і свою історію 👇".replace(" 👇",""),C(50))
d.polygon([(W/2-22,1440),(W/2+22,1440),(W/2,1472)],fill=gold)
# space for sticker ~1500-1720
ctext(1745,"Обираємо в неділю, 15 листопада",C(44),gold)
ctext(1825,"НЕБОЗВІД",U(34),(200,210,235))
img.save('/home/user/Cloud/videos/stories/rozigrash.png')
