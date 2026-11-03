"""Solver 2D cuasiestático de volúmenes finitos (malla no uniforme) para secciones microstrip
multiconductor. Devuelve la matriz C de Maxwell (con dieléctricos) y la matriz L (a partir de C en vacío).
Geometría: plano de referencia en y=0, caja conectada a masa. Unidades de entrada: mm; salida: SI."""
import numpy as np, scipy.sparse as sp, scipy.sparse.linalg as spla
EPS0=8.8541878128e-12; MU0=4e-7*np.pi; C0=299792458.0
def grid_axis(breaks, hmin, hmax, ratio=1.15, lo=None, hi=None):
    """Build a 1D non-uniform grid refined near break points."""
    breaks=sorted(set([round(b,9) for b in breaks]))
    pts=set(breaks)
    for i in range(len(breaks)-1):
        a,b=breaks[i],breaks[i+1]; L=b-a
        # grade from both ends
        xs=[a]; hcur=hmin
        left=[a]; right=[b]
        while True:
            # symmetric grading
            if right[-1]-left[-1] <= 2*hcur: break
            left.append(left[-1]+hcur); right.append(right[-1]-hcur)
            hcur=min(hcur*ratio,hmax)
        seg=left+right[::-1]
        if right[-1]-left[-1]>hcur*1.0001:
            seg.insert(len(left),(left[-1]+right[-1])/2)
        pts.update(seg)
    return np.array(sorted(pts))
class Section:
    def __init__(self): self.rects=[]   # (x0,x1,y0,y1, kind, value) kind='diel'(er) or 'cond'(index)
    def diel(self,x0,x1,y0,y1,er): self.rects.append((x0,x1,y0,y1,'diel',er))
    def cond(self,x0,x1,y0,y1,idx): self.rects.append((x0,x1,y0,y1,'cond',idx))
def solve(sec, boxw, boxh, ncond, hmin=0.002, hmax=0.05, ratio=1.12):
    xb=[-boxw/2,boxw/2]; yb=[0,boxh]
    for r in sec.rects: xb+= [r[0],r[1]]; yb+=[r[2],r[3]]
    x=grid_axis([b for b in xb if -boxw/2<=b<=boxw/2],hmin,hmax,ratio)
    y=grid_axis([b for b in yb if 0<=b<=boxh],hmin,hmax,ratio)
    nx,ny=len(x),len(y)
    xc=(x[:-1]+x[1:])/2; yc=(y[:-1]+y[1:])/2
    # cell permittivity (cells between nodes), default air
    er=np.ones((nx-1,ny-1))
    for (x0,x1,y0,y1,k,v) in sec.rects:
        if k=='diel':
            mx=(xc>x0)&(xc<x1); my=(yc>y0)&(yc<y1)
            er[np.ix_(mx,my)]=v
    # conductor node map
    cidx=-np.ones((nx,ny),dtype=int)
    for (x0,x1,y0,y1,k,v) in sec.rects:
        if k=='cond':
            mx=(x>=x0-1e-12)&(x<=x1+1e-12); my=(y>=y0-1e-12)&(y<=y1+1e-12)
            cidx[np.ix_(mx,my)]=v
    # boundary: ground (index 0 reserved = ground) -> use -2 for ground
    gnd=np.zeros((nx,ny),bool); gnd[0,:]=gnd[-1,:]=True; gnd[:,0]=gnd[:,-1]=True
    def build(erc):
        # finite volume: conductance between node (i,j) and (i+1,j): eps_face * (dual height)/dx
        dx=np.diff(x); dy=np.diff(y)
        # horizontal links (i,j)-(i+1,j): face spans half cells above and below in y
        # eps average weighted by dy of adjacent cells
        Gx=np.zeros((nx-1,ny))
        for j in range(ny):
            acc=np.zeros(nx-1)
            if j>0: acc+=erc[:,j-1]*dy[j-1]/2
            if j<ny-1: acc+=erc[:,j]*dy[j]/2
            Gx[:,j]=acc/dx
        Gy=np.zeros((nx,ny-1))
        for i in range(nx):
            acc=np.zeros(ny-1)
            if i>0: acc+=erc[i-1,:]*dx[i-1]/2
            if i<nx-1: acc+=erc[i,:]*dx[i]/2
            Gy[i,:]=acc/dy
        return Gx,Gy
    def capmatrix(erc):
        Gx,Gy=build(erc)
        N=nx*ny; idx=lambda i,j: i*ny+j
        fixed=gnd|(cidx>=0)
        free=~fixed
        fid=-np.ones((nx,ny),dtype=int); fid[free]=np.arange(free.sum())
        rows=[];cols=[];vals=[]
        diag=np.zeros(free.sum())
        # assemble
        I,J=np.nonzero(free)
        # build links list
        links=[]
        ii,jj=np.meshgrid(np.arange(nx-1),np.arange(ny),indexing='ij'); links.append((ii.ravel(),jj.ravel(),ii.ravel()+1,jj.ravel(),Gx.ravel()))
        ii,jj=np.meshgrid(np.arange(nx),np.arange(ny-1),indexing='ij'); links.append((ii.ravel(),jj.ravel(),ii.ravel(),jj.ravel()+1,Gy.ravel()))
        A_r=[];A_c=[];A_v=[]; 
        B=np.zeros((free.sum(),ncond))
        Q_link=[]  # for charge computation
        for (i1,j1,i2,j2,g) in links:
            f1=fid[i1,j1]; f2=fid[i2,j2]
            c1=cidx[i1,j1]; c2=cidx[i2,j2]
            m=(f1>=0)
            np.add.at(diag,f1[m],g[m])
            m2=(f2>=0)
            np.add.at(diag,f2[m2],g[m2])
            mm=(f1>=0)&(f2>=0)
            A_r+= [f1[mm],f2[mm]]; A_c+=[f2[mm],f1[mm]]; A_v+=[-g[mm],-g[mm]]
            # free-conductor links -> rhs
            for k in range(ncond):
                m3=(f1>=0)&(c2==k); np.add.at(B[:,k],f1[m3],g[m3])
                m4=(f2>=0)&(c1==k); np.add.at(B[:,k],f2[m4],g[m4])
            Q_link.append((i1,j1,i2,j2,g))
        A=sp.coo_matrix((np.concatenate(A_v+[diag]),(np.concatenate(A_r+[np.arange(len(diag))]),np.concatenate(A_c+[np.arange(len(diag))]))),shape=(len(diag),len(diag))).tocsc()
        lu=spla.splu(A)
        C=np.zeros((ncond,ncond))
        for k in range(ncond):
            vfree=lu.solve(B[:,k])
            V=np.zeros((nx,ny)); V[free]=vfree; V[cidx==k]=1.0
            # charge on conductor m: sum over links from conductor m nodes to non-m nodes of g*(Vm - Vother)
            for m in range(ncond):
                q=0.0
                for (i1,j1,i2,j2,g) in Q_link:
                    a=(cidx[i1,j1]==m)&(cidx[i2,j2]!=m); q+=np.sum(g[a]*(V[i1,j1][a]-V[i2,j2][a]))
                    b=(cidx[i2,j2]==m)&(cidx[i1,j1]!=m); q+=np.sum(g[b]*(V[i2,j2][b]-V[i1,j1][b]))
                C[m,k]=q*EPS0   # per metre (2D, dimensionless geometry ratio)
        return C
    C=capmatrix(er)
    Cv=capmatrix(np.ones_like(er))
    L=MU0*EPS0*np.linalg.inv(Cv)
    return dict(C=C,Cv=Cv,L=L,nx=nx,ny=ny)
def microstrip(ws, xs, h, t, mask=0.0, er=4.16, erm=3.8, boxw=3.0, boxh=2.0, gplane=0.0152, **kw):
    """ws: list of widths, xs: list of left x positions (mm). Returns solve() dict + derived."""
    s=Section()
    s.diel(-boxw/2,boxw/2,0,h,er)
    if mask>0:
        s.diel(-boxw/2,boxw/2,h,h+mask,erm)
        for w,x0 in zip(ws,xs): s.diel(x0-mask,x0+w+mask,h,h+t+mask,erm)
    for k,(w,x0) in enumerate(zip(ws,xs)): s.cond(x0,x0+w,h,h+t,k)
    r=solve(s,boxw,boxh,len(ws),**kw)
    return r
def modal_pair(r):
    C=r['C']; L=r['L']
    # symmetric pair: even/odd
    Le=L[0,0]+L[0,1]; Ce=C[0,0]+C[0,1]   # C[0,1] negative (Maxwell)
    Lo=L[0,0]-L[0,1]; Co=C[0,0]-C[0,1]
    Ze=np.sqrt(Le/Ce); Zo=np.sqrt(Lo/Co)
    ve=1/np.sqrt(Le*Ce); vo=1/np.sqrt(Lo*Co)
    return dict(Zeven=Ze,Zodd=Zo,Zdiff=2*Zo,Zcomm=Ze/2,ereff_e=(C0/ve)**2,ereff_o=(C0/vo)**2,
                kL=L[0,1]/L[0,0],kC=-C[0,1]/C[0,0])
def single(r):
    C=r['C'][0,0]; L=r['L'][0,0]
    return dict(Z0=np.sqrt(L/C), ereff=(C0*np.sqrt(L*C))**2, C=C, L=L)
if __name__=='__main__':
    import time
    t0=time.time()
    r=microstrip([0.2],[-0.1],0.1164,0.035,mask=0.015)
    print('SE mask', single(r), r['nx'],r['ny'], time.time()-t0)
    t0=time.time()
    r=microstrip([0.2,0.2],[-0.325,0.125],0.1164,0.035,mask=0.015)
    print('USB mask', modal_pair(r), r['nx'],r['ny'], time.time()-t0)
