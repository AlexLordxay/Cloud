import sys, json, re, os, subprocess, urllib.request, urllib.parse, html
UA="NebozvidVideoBot/1.0 (educational video)"
API="https://commons.wikimedia.org/w/api.php"
A="/home/user/cloud/videos/tools/work/earth_history/assets"
M="/home/user/cloud/videos/tools/scenes/earth_history/assets.json"
def api(**p):
    p["format"]="json"
    import time
    for k in range(6):
        try:
            r=urllib.request.Request(API+"?"+urllib.parse.urlencode(p),headers={"User-Agent":UA})
            return json.load(urllib.request.urlopen(r,timeout=60))
        except urllib.error.HTTPError as e:
            if e.code!=429: raise
            time.sleep(10*(k+1))
    raise SystemExit("429 persistent")
def strip(s): return html.unescape(re.sub("<[^>]+>","",s or "")).strip()
def info(titles):
    d=api(action="query",titles="|".join(titles),prop="imageinfo",iiprop="url|size|mime|extmetadata",iiurlwidth=2560)
    out=[]
    for pg in d["query"]["pages"].values():
        ii=(pg.get("imageinfo") or [None])[0]
        if not ii: continue
        e=ii["extmetadata"]
        out.append(dict(title=pg["title"],url=ii["url"],thumb=ii.get("thumburl"),w=ii["width"],h=ii["height"],mime=ii["mime"],
          lic=strip(e.get("LicenseShortName",{}).get("value")),licurl=strip(e.get("LicenseUrl",{}).get("value")),
          artist=strip(e.get("Artist",{}).get("value")),credit=strip(e.get("Credit",{}).get("value"))[:80],dur=ii.get("duration")))
    return out
def search(q,n=12,filt=None):
    d=api(action="query",list="search",srnamespace=6,srsearch=q,srlimit=n)
    ts=[x["title"] for x in d["query"]["search"]]
    if not ts: return
    for i in info(ts):
        print(f'{i["title"]} | {i["w"]}x{i["h"]} {i["mime"].split("/")[1]} | {i["lic"]} | {i["artist"][:40]}')
def get(id,short,title,note=""):
    i=info([title])[0]
    lic=i["lic"]
    if re.search(r"NC|ND",lic) : print("BAD LICENSE",lic); return
    vid=i["mime"].startswith("video") or i["mime"]=="application/ogg"
    ext=os.path.splitext(i["url"].split("?")[0])[1].lower()
    if vid:
        fn=f"{id}_{short}{ext}"; url=i["url"]
    else:
        big=i["w"]>2560 and i["thumb"]
        url=i["thumb"] if big else i["url"]
        ext=".jpg" if (big or ext in(".jpg",".jpeg")) else ext
        fn=f"{id}_{short}{ext}"
    path=os.path.join(A,fn)
    import time
    for k in range(8):
        subprocess.run(["curl","-sSL","-A",UA,"-o",path,url])
        if os.path.getsize(path)>20000 and open(path,"rb").read(5)!=b"<!DOC": break
        time.sleep(15*(k+1))
    else: raise SystemExit("download failed")
    if vid:
        mp4=os.path.join(A,f"{id}_{short}_1080.mp4")
        dur=float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",path]).decode().strip() or 0)
        ss=max(0,(dur-15)/2) if dur>15 else 0
        subprocess.run(["ffmpeg","-y","-v","error","-ss",str(ss),"-i",path,"-t","15","-an","-vf","scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,fps=30","-c:v","libx264","-crf","20","-pix_fmt","yuv420p",mp4],check=True)
        w,h,du=i["w"],i["h"],round(dur,1)
    else:
        from PIL import Image
        im=Image.open(path); w,h=im.size; du=None
        if ext!=".jpg": pass
    man=json.load(open(M)) if os.path.exists(M) else []
    man=[m for m in man if not(m["id"]==id and m["file"]==fn)]
    man.append(dict(id=id,file=fn,kind="video" if vid else "photo",width=w,height=h,duration=du,title=i["title"].replace("File:",""),author=i["artist"],license=lic,license_url=i["licurl"],source_url="https://commons.wikimedia.org/wiki/"+urllib.parse.quote(i["title"].replace(" ","_")),note=note+(" | 1080 mp4: "+f"{id}_{short}_1080.mp4" if vid else "")))
    json.dump(man,open(M,"w"),ensure_ascii=False,indent=1)
    print("OK",fn,w,h,lic)
if __name__=="__main__":
    c=sys.argv[1]
    if c=="s": search(sys.argv[2],int(sys.argv[3]) if len(sys.argv)>3 else 12)
    else: get(*sys.argv[2:])
