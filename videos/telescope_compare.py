import sys, numpy as np
from PIL import Image, ImageFilter, ImageDraw, ImageFont
D=sys.argv[1]
def bbox(im,th=40):
    a=np.asarray(im.convert('L'))>th
    ys=np.where(a.any(1))[0]; xs=np.where(a.any(0))[0]
    return xs[0],ys[0],xs[-1]+1,ys[-1]+1
jup=Image.open(D+'/dl/jup1.png').convert('RGB'); jup=jup.crop(bbox(jup))
sat=Image.open(D+'/dl/PIA05982.jpg').convert('RGB'); sat=sat.crop(bbox(sat,30))
def pad(im,f=0.12):
    w,h=im.size;p=round(w*f);n=Image.new('RGB',(w+2*p,h+2*p));n.paste(im,(p,p));return n,(w+2*p)/w
jup,fj=pad(jup);sat,fs=pad(sat)
print(jup.size, sat.size)
# arcsec widths: Jupiter ~45.5" (opposition Jan 2027); Saturn rings ~42" (2026)
TARGETS={'jup':(jup,45.5*fj),'sat':(sat,42.0*fs)}
# (name, arcsec/px, effective FWHM arcsec after stacking, sharpen)
SCOPES=[('s50',2.39,4.5,False),('mak',0.20,1.3,True),('sct',0.147,0.85,True)]
rng=np.random.default_rng(1)
def sim(img,width_as,scale,fwhm,sharp):
    W=img.size[0]; src_as_per_px=width_as/W
    sig=fwhm/2.355/src_as_per_px
    b=img.filter(ImageFilter.GaussianBlur(sig))
    tw=max(2,round(width_as/scale)); th=max(2,round(img.size[1]*tw/W))
    s=b.resize((tw,th),Image.LANCZOS)
    a=np.asarray(s).astype(float); a+=rng.normal(0,3,a.shape); s=Image.fromarray(np.clip(a,0,255).astype('uint8'))
    if sharp: s=s.filter(ImageFilter.UnsharpMask(radius=max(1,tw/120),percent=80,threshold=1))
    return s
CW,CH=380,300
F=lambda w,s: ImageFont.truetype(f'/usr/share/fonts/opentype/inter/Inter-{w}.otf',s)
cols=[('Seestar S50','50 мм · смарт-телескоп'),('Максутов 127 мм','+ планетна камера'),('Шмідт-Кассегрен 8″','203 мм + планетна камера'),('Hubble (NASA)','для порівняння')]
M=40; TOP=150; LW=0
Wc=M*2+4*CW+3*20; Hc=TOP+80+2*(CH+70)+110
can=Image.new('RGB',(Wc,Hc),(8,10,18)); d=ImageDraw.Draw(can)
d.text((M,36),'Юпітер і Сатурн у різних телескопах',font=F('Bold',44),fill=(255,255,255))
d.text((M,94),'Симуляція за знімками Hubble: розмір у пікселях і різкість — як після складання відео в добру ніч',font=F('Regular',22),fill=(170,180,200))
for i,(t,s) in enumerate(cols):
    x=M+i*(CW+20)
    d.text((x,TOP),t,font=F('SemiBold',26),fill=(255,215,120) if i==0 else (255,255,255))
    d.text((x,TOP+34),s,font=F('Regular',19),fill=(160,170,190))
for r,key in enumerate(['jup','sat']):
    img,was=TARGETS[key]; y=TOP+80+r*(CH+70)
    for i in range(4):
        x=M+i*(CW+20)
        d.rectangle([x,y,x+CW,y+CH],fill=(0,0,0))
        if i<3:
            n,sc,fw,sh=SCOPES[i]; s=sim(img,was,sc,fw,sh); native=s.size
        else:
            s=img; native=None
        k=min((CW-30)/s.size[0],(CH-30)/s.size[1]); big=s.resize((round(s.size[0]*k),round(s.size[1]*k)),Image.BICUBIC)
        can.paste(big,(x+(CW-big.size[0])//2,y+(CH-big.size[1])//2))
        if native:
            d.text((x+10,y+CH-28),f'≈ {round(native[0]/(fj if key=="jup" else fs))} пікс. на кадрі' + ('  (збільшено ×%d)'%round(k) if k>1.5 else ''),font=F('Regular',17),fill=(150,160,180))
        if i==0:
            # real-size inset
            d.text((x+10,y+8),'справжній розмір:',font=F('Regular',16),fill=(150,160,180))
            can.paste(s,(x+160,y+12))
    d.text((M,y+CH+12),('Юпітер (≈46″, протистояння січня 2027)' if key=='jup' else 'Сатурн (кільця ≈42″; у 2026–27 вони вузькі — майже ребром)'),font=F('Regular',19),fill=(200,205,220))
fy=Hc-95
d.text((M,fy),'S50: видно диск, 2 смуги й кільця — без Великої червоної плями. Планетний телескоп: смуги, пляма, щілина Кассіні.',font=F('Regular',21),fill=(230,232,240))
d.text((M,fy+34),'Туманностей і галактик це не стосується: там S50 сильний. Оригінали: NASA/ESA Hubble · Небозвід',font=F('Regular',19),fill=(140,150,170))
can.save(sys.argv[2],quality=92)
