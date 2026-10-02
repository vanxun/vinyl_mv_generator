import cv2
import numpy as np
from .image_utils import screen_blend_bgr

# 细柱频谱
class BarSpectrum:
    def __init__(self, bins=72, color=None):
        self.colors=[(166,48,238),(223,150,249),(250,221,255),(245,199,255)]
        if color is not None:
            bgr=np.array(color[::-1],np.float32)
            self.colors=[tuple(int(round(v)) for v in bgr*(1-mix)+bgr.max()*mix) for mix in (0.,.5,.85,.7)]
        self.peaks=np.zeros(bins)
        self.hold=np.zeros(bins)
        self.velocity=np.zeros(bins)

    def draw(self,frame,values,rect,dt):
        x,y,w,h=rect
        scale=frame.shape[0]/1080
        roi=frame[y:y+h,x:x+w]
        baseline=int(h*.60)
        amplitude=h*.64
        v=values.copy()
        layer=np.zeros_like(roi)
        core=np.zeros_like(roi)
        pad=max(6,round(20*scale))
        xs=np.linspace(pad,w-pad-1,len(v))
        new=v>=self.peaks
        self.peaks[new]=v[new]
        self.hold[new]=.13
        self.velocity[new]=0
        self.hold[~new]-=dt
        falling=(~new)&(self.hold<=0)
        self.velocity[falling]+=3.8*dt
        self.peaks[falling]=np.maximum(v[falling],self.peaks[falling]-self.velocity[falling]*dt)
        bw=max(1,round(5*scale))
        cap=max(1,round(2*scale))
        for j,xx in enumerate(xs):
            xx=round(xx)
            top=baseline-round(v[j]*amplitude)
            if baseline-top>1:
                cv2.rectangle(layer,(xx-bw//2,top),(xx+bw//2,baseline),self.colors[0],-1)
                cv2.line(core,(xx,top),(xx,baseline),self.colors[1],1,cv2.LINE_AA)
                cv2.line(core,(xx-cap,top),(xx+cap,top),self.colors[2],1,cv2.LINE_AA)
            peak=baseline-round(self.peaks[j]*amplitude)-max(1,round(4*scale))
            if self.peaks[j]>.015:
                cv2.line(core,(xx-cap,peak),(xx+cap,peak),self.colors[3],1,cv2.LINE_AA)
        screen_blend_bgr(roi,cv2.GaussianBlur(layer,(0,0),max(.6,3.2*scale)),.9)
        screen_blend_bgr(roi,cv2.GaussianBlur(layer,(0,0),max(.4,scale)),.5)
        screen_blend_bgr(roi,layer,.7)
        screen_blend_bgr(roi,core,1.)
        refl_y=baseline+round(h*.22)
        refl=cv2.resize(cv2.flip(cv2.add(layer,core),0),(w,round(h*.42)))
        start=refl_y-round((h-1-baseline)*.42)
        rh=min(refl.shape[0],h-start)
        refl=cv2.GaussianBlur(refl,(0,0),max(.6,2.1*scale))
        fade=np.exp(-np.maximum(0,np.arange(rh)+start-refl_y)/(h*.10))[:,None,None]
        screen_blend_bgr(roi[start:start+rh],refl[:rh]*fade,.17)
