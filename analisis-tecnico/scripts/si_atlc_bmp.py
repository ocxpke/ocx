"""Genera BMP de 24 bits para atlc: (par) microstrip sobre el apilado JLC04161H-2116.
Sección: plano GND (In1) / preimpregnado h, er / pistas t / máscara conforme / aire, en caja a masa."""
import struct, sys, numpy as np
GREEN=(0,255,0); RED=(255,0,0); BLUE=(0,0,255); WHITE=(255,255,255)
PREPREG=(0xAC,0x82,0xAC); MASK=(0x8C,0x1C,0x01)
def write_bmp(fn, img):
    H,W,_=img.shape
    row=W*3; pad=(4-row%4)%4
    data=bytearray()
    for y in range(H-1,-1,-1):
        r=img[y,:,::-1].astype(np.uint8).tobytes()  # BGR
        data+=r+b'\x00'*pad
    hdr=b'BM'+struct.pack('<IHHI',54+len(data),0,0,54)
    dib=struct.pack('<IiiHHIIiiII',40,W,H,1,24,0,len(data),2835,2835,0,0)
    open(fn,'wb').write(hdr+dib+data)
def make(fn, w, s, h, t, mask, p, nlines=2, pol=(1,-1), boxw=3.0, boxh=2.0, trap=0.0, extra=None):
    """dimensions in mm, p = pixel size (mm). nlines=1 -> single line. trap = reduction of top width (mm, total)."""
    W=int(round(boxw/p)); H=int(round(boxh/p))
    hp=int(round(h/p)); tp=int(round(t/p)); mp=int(round(mask/p)); wp=int(round(w/p)); sp=int(round(s/p))
    img=np.zeros((H,W,3),dtype=np.uint8); img[:]=WHITE
    gnd_th=max(2,int(round(0.0152/p)))
    # y index: 0 at top of image. ground plane at bottom
    yb=H-1-gnd_th   # last dielectric row index (just above plane)
    img[H-gnd_th-1:,:]=GREEN
    y_sub_top=H-gnd_th-1-hp  # first row of prepreg
    img[y_sub_top:H-gnd_th-1,:]=PREPREG
    # traces
    if nlines==1: xs=[W//2-wp//2]
    else:
        tot=2*wp+sp; x0=W//2-tot//2; xs=[x0, x0+wp+sp]
    cols=[RED if pp>0 else BLUE for pp in pol[:nlines]]
    ytr_top=y_sub_top-tp
    # solder mask: conformal mp thick over substrate and around traces
    if mp>0:
        img[y_sub_top-mp:y_sub_top,:]=MASK
        for x in xs:
            img[ytr_top-mp:y_sub_top, max(0,x-mp):x+wp+mp]=MASK
    trp=int(round(trap/p/2))
    for x,c in zip(xs,cols):
        for k in range(tp):
            # linear trapezoid: bottom row full width, top row reduced by trp each side
            red=int(round(trp*(tp-1-k)/(max(tp-1,1)))) if False else int(round(trp*(1-(k/(max(tp-1,1))))))
            yy=ytr_top+k
            # k=0 top row -> reduction trp ; k=tp-1 bottom row -> 0
            r=int(round(trp*(tp-1-k)/max(tp-1,1)))
            img[yy, x+r:x+wp-r]=c
    # grounded box
    img[0:2,:]=GREEN; img[:,0:2]=GREEN; img[:,W-2:]=GREEN
    write_bmp(fn,img)
    return dict(W=W,H=H,hp=hp,tp=tp,wp=wp,sp=sp,mp=mp, h_eff=hp*p, w_eff=wp*p, s_eff=sp*p, t_eff=tp*p, mask_eff=mp*p)
if __name__=='__main__':
    import json
    args=json.loads(sys.argv[1])
    print(make(**args))
