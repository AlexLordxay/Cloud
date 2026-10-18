# Reads a window out of a huge, uncompressed global GeoTIFF over HTTP, fetching only the bytes it needs (Range requests).
# USGS's Mars mosaics are 5–25 GB each; a patch round one volcano is a few tens of MB.
import io, threading, urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import tifffile

UA = 'nebozvid-video/1.0'


class RangeFile(io.RawIOBase):
    """A read-only file over HTTP: seek/read become Range requests (cached in 1 MB blocks)."""
    BLOCK = 1 << 20

    def __init__(self, url):
        self.pos, self.cache, self.lock = 0, {}, threading.Lock()
        # one tiny request finds the real address (USGS redirects to S3) and the file size
        r = urllib.request.urlopen(urllib.request.Request(url, headers={'Range': 'bytes=0-0', 'User-Agent': UA}), timeout=60)
        self.url, self.size = r.geturl(), int(r.headers['Content-Range'].split('/')[1])

    def get(self, a, b):
        """Bytes [a, b) straight from the server."""
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={a}-{b - 1}', 'User-Agent': UA})
        for attempt in range(5):
            try:
                return urllib.request.urlopen(req, timeout=120).read()
            except Exception:
                if attempt == 4: raise

    def block(self, i):
        with self.lock:
            if i in self.cache: return self.cache[i]
        d = self.get(i * self.BLOCK, min(self.size, (i + 1) * self.BLOCK))
        with self.lock: self.cache[i] = d
        return d

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos

    def readinto(self, b):
        n = min(len(b), self.size - self.pos)
        out, p = bytearray(), self.pos
        while len(out) < n:
            i = p // self.BLOCK; blk = self.block(i); o = p - i * self.BLOCK
            take = blk[o:o + n - len(out)]; out += take; p += len(take)
        b[:n] = out; self.pos += n
        return n


def layout(url):
    """Size, data type, planes and where each strip is, from the TIFF header."""
    f = RangeFile(url)
    with tifffile.TiffFile(io.BufferedReader(f, 1 << 20)) as t:
        pg = t.pages[0]
        info = dict(shape=pg.shape, dtype=np.dtype(pg.dtype).newbyteorder(t.byteorder), tiled=pg.is_tiled,
                    rows_per_strip=pg.rowsperstrip, compression=int(pg.compression), planar=int(pg.planarconfig),
                    offsets=np.array(pg.dataoffsets), counts=np.array(pg.databytecounts))
    return f, info


def window(url, row0, row1, col0, col1, workers=48):
    """Rows [row0, row1) and columns [col0, col1) of a striped, uncompressed image, as (rows, cols[, planes])."""
    f, L = layout(url)
    assert not L['tiled'] and L['compression'] == 1 and L['rows_per_strip'] == 1, L
    sep = L['planar'] == 2 and len(L['shape']) == 3            # planes stored one after another
    P = L['shape'][0] if sep else (L['shape'][2] if len(L['shape']) == 3 else 1)
    H, W = (L['shape'][1:] if sep else L['shape'][:2])
    it = L['dtype'].itemsize
    out = np.zeros((P, row1 - row0, col1 - col0), dtype=L['dtype'].newbyteorder('='))

    def one(job):
        p, r = job
        if sep:
            a = int(L['offsets'][p * H + r]) + col0 * it
            out[p, r - row0] = np.frombuffer(f.get(a, a + (col1 - col0) * it), dtype=L['dtype'])
        else:
            a = int(L['offsets'][r]) + col0 * it * P
            v = np.frombuffer(f.get(a, a + (col1 - col0) * it * P), dtype=L['dtype']).reshape(-1, P)
            out[:, r - row0] = v.T

    with ThreadPoolExecutor(workers) as ex: list(ex.map(one, [(p, r) for p in range(P if sep else 1) for r in range(row0, row1)]))
    return (out[0] if P == 1 else np.moveaxis(out, 0, -1)), (H, W)


def latlon_window(url, lat0, lat1, lon0, lon1):
    """A latitude/longitude box (degrees; longitudes -180…180) from a global simple-cylindrical mosaic."""
    f, L = layout(url)
    sep = L['planar'] == 2 and len(L['shape']) == 3
    H, W = (L['shape'][1:] if sep else L['shape'][:2])
    ppd = W / 360.0
    r0, r1 = int((90 - lat1) * ppd), int(np.ceil((90 - lat0) * ppd))
    c0, c1 = int((lon0 + 180) * ppd), int(np.ceil((lon1 + 180) * ppd))
    img, _ = window(url, r0, r1, c0, c1)
    # the exact box the pixels cover (for resampling onto a common grid)
    return img, (90 - r0 / ppd, 90 - r1 / ppd, c0 / ppd - 180, c1 / ppd - 180)
