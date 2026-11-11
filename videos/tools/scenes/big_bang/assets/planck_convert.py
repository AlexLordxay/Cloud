# Regenerates planck_cmb_equirect.npy (8192x4096, float32, uK) + preview from the Planck 2018 (PR3) SMICA-nosz map.
# Download first: https://irsa.ipac.caltech.edu/data/Planck/release_3/all-sky-maps/maps/component-maps/cmb/COM_CMB_IQU-smica-nosz_2048_R3.00_full.fits -> smica_nosz_2048.fits (384 MB, gitignored)
# Uses column I_STOKES_INP (inpainted Galactic plane; values already in uK although header says K_CMB). Needs: pip install healpy astropy pillow
import numpy as np, healpy as hp
from astropy.io import fits
from PIL import Image
OUT='./'  # run from this dir
h=fits.open('smica_nosz_2048.fits',memmap=True)
m=np.array(h[1].data['I_STOKES_INP'],dtype=np.float32)
print(m.shape, np.isnan(m).sum(), (m<-1e20).sum(), np.nanmin(m), np.nanmax(m))
m=hp.reorder(m,n2r=True)
bad=(m<-1e20)|~np.isfinite(m)
print('bad',bad.sum())
if bad.any():
    m[bad]=0
    sm=hp.smoothing(m,fwhm=np.radians(1.0)); m=np.where(bad,sm,m).astype(np.float32)
pass  # INP column is already in uK despite header K_CMB label
print('rms uK',m.std(), m.min(), m.max())
W,H=8192,4096
out=np.empty((H,W),np.float32)
lon=(np.arange(W)+0.5)/W*360.0
for j0 in range(0,H,256):
    j=np.arange(j0,min(H,j0+256))
    lat=90-(j+0.5)/H*180
    L,B=np.meshgrid(lon,lat)
    out[j0:j0+len(j)]=hp.get_interp_val(m,L.ravel(),B.ravel(),nest=False,lonlat=True).reshape(L.shape)
np.save(OUT+'planck_cmb_equirect.npy',out)
print(out.shape,out.dtype,out.min(),out.max(),out.std())
pts=np.array([[0,0,255],[0,112,255],[0,221,255],[255,237,217],[255,180,0],[255,75,0],[100,0,0]],float)
x=np.clip((out+300)/600,0,1)*(len(pts)-1)
i=np.minimum(x.astype(int),len(pts)-2); f=(x-i)[...,None]
rgb=pts[i]*(1-f)+pts[i+1]*f
Image.fromarray(rgb.astype(np.uint8)).save(OUT+'planck_cmb_preview.jpg',quality=92)
