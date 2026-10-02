import math
import cv2
import numpy as np
from .config import ASSET_DIR, DEFAULT_RPM, DEFAULT_FPS
from .image_utils import (parse_color, tint_image, cover_fit, clean_asset, load_bgr,
                          cover_crop_image, screen_blend_bgr, alpha_blend_bgra, rotate_bgra)
from .spectrum import BarSpectrum
from .particles import ParticleField

# 场景合成
class Scene:
    def __init__(self, image_path, width, height, rpm=DEFAULT_RPM, fps=DEFAULT_FPS, background_color=None, spectrum_color=None):
        background_color=parse_color(background_color)
        self.spectrum = BarSpectrum(color=parse_color(spectrum_color))
        self.dt = 1/fps
        self.w, self.h, self.rpm = width, height, rpm
        self.s = min(width/1920, height/1080)
        self.d = d = round(min(height*.665, width*.37))
        self.x = round(width*.798-d/2)
        self.floor_y = round(height*.80)
        self.y = self.floor_y-d+1
        self.wave = (round(width*.028), round(height*.30),
            self.x-round(width*.065), round(height*.395))
        bg = cover_fit(clean_asset('background.png'), (width, height))
        bg = cv2.GaussianBlur(bg, (0, 0), max(.5, self.s*2.0))
        self.base = np.clip(bg.astype(np.float32)*.27+np.array([5, 5, 6]), 0, 255).astype(np.uint8)
        floor = clean_asset('floor_reflection.png')
        floor = floor[round(floor.shape[0]*.42):]
        fh = height-self.floor_y
        floor = cover_fit(floor, (width, fh))
        fade = np.linspace(.0, .22, fh)[:, None, None]
        screen_blend_bgr(self.base[self.floor_y:], floor*fade, 1.)
        self.ambient = cover_fit(clean_asset('ambient_light.png'), (width, height))
        gy, gx = np.mgrid[:height, :width].astype(np.float32)
        vignette = 1-.20*np.clip(((gx-width*.5)/(width*.65))**2 + ((gy-height*.48)/(height*.8))**2, 0, 1)
        self.base = (self.base*vignette[:, :, None]).astype(np.uint8)
        preset = load_bgr(ASSET_DIR/'vinyl_preset.png')
        yy, xx = np.mgrid[:d, :d].astype(np.float32)
        u, v = (xx-(d-1)/2)/((d-3)/2), (yy-(d-1)/2)/((d-3)/2)
        radius = np.sqrt(u*u+v*v)
        sw, sh = preset.shape[1]/1024, preset.shape[0]/1024
        mx, my = (513+u*486)*sw, (522+v*505)*sh
        disc = cv2.remap(preset, mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_CONSTANT)
        disc = disc.astype(np.float32)*.84
        highlight = np.clip((disc.max(axis=2)-125)/80, 0, 1)[:, :, None]
        disc *= 1-highlight*np.array([.12, .38, .04])
        disc = np.clip(disc, 0, 255).astype(np.uint8)
        mask = np.clip((1-radius)*(d/2), 0, 1)
        self.disc = np.dstack([disc, (mask*255).astype(np.uint8)])
        ld = round(d*.566)
        label_rgb = cover_crop_image(image_path, (ld, ld))
        ly, lx = np.mgrid[:ld, :ld].astype(np.float32)
        lr = np.sqrt((lx-(ld-1)/2)**2+(ly-(ld-1)/2)**2)
        lm = np.clip((ld-2)/2-lr, 0, 1)
        self.label = np.dstack([label_rgb, (lm*255).astype(np.uint8)])
        self.label_xy = (d-ld)//2
        rim = np.exp(-((radius-.991)/.008)**2)
        theta = np.arctan2(v, u)
        arc = np.exp(-(np.sin(theta+.72)/.16)**2)
        glow = (rim*arc*160)[:, :, None]*np.array([.73, .22, 1.])
        self.rim = cv2.GaussianBlur(glow.astype(np.float32), (0, 0), max(.8, 3*self.s))
        self.rim += glow*.35
        self.particles = ParticleField(width, height, background_color)
        ramp = np.clip((np.arange(height)/height-.79)/.19, 0, 1)
        ramp = ramp*ramp*(3-2*ramp)
        self.subtitle_fade = (1-ramp*.66).astype(np.float32)[:, None, None]
        self.fade_start = int(height*.79)
        if background_color is not None:
            self.base=tint_image(self.base,background_color)
            self.ambient=tint_image(self.ambient,background_color)
            self.disc[:,:,:3]=tint_image(self.disc[:,:,:3],background_color)
            self.rim=tint_image(np.clip(self.rim,0,255).astype(np.uint8),background_color)
        self.ambient_delta = (np.float32(255.)-self.base.astype(np.float32)) * (self.ambient.astype(np.float32)/255.)
        self.base_float = self.base.astype(np.float32)
        self.ref_height = max(1, round(self.d*.32))
        rows = np.arange(self.ref_height, dtype=np.float32)
        self.ref_fade = (.31*np.exp(-rows/(self.ref_height*.36))*(1-rows/self.ref_height))[:, None]
        self.shadow = np.zeros((max(8, round(28*self.s)), self.d, 4), np.uint8)
        cv2.ellipse(self.shadow, (self.d//2, self.shadow.shape[0]//2),
            (round(self.d*.29), max(2, self.shadow.shape[0]//4)), 0, 0, 360, (0, 0, 0, 100), -1, cv2.LINE_AA)
        self.shadow = cv2.GaussianBlur(self.shadow, (0, 0), max(1., 4*self.s))
        rgb = self.disc[:, :, :3].copy()
        screen_blend_bgr(rgb, self.rim, .65)
        self.disc[:, :, :3] = rgb


    def frame(self, t, values):
        strength = np.float32(.025+.008*math.sin(t*.32))
        out = (self.base_float+self.ambient_delta*strength).astype(np.uint8)
        self.particles.draw(out, t)
        self.spectrum.draw(out, values, self.wave, self.dt)
        vinyl = self.disc.copy()
        rot = rotate_bgra(self.label, t*self.rpm*6)
        rgb = vinyl[:, :, :3].copy()
        alpha_blend_bgra(rgb, rot, self.label_xy, self.label_xy)
        vinyl[:, :, :3] = rgb
        ref = cv2.resize(cv2.flip(vinyl, 0), (self.d, self.ref_height), interpolation=cv2.INTER_AREA)
        ref[:, :, 3] = (ref[:, :, 3]*self.ref_fade).astype(np.uint8)
        ref = cv2.GaussianBlur(ref, (0, 0), max(.7, self.s*1.8))
        alpha_blend_bgra(out, ref, self.x, self.floor_y)
        alpha_blend_bgra(out, self.shadow, self.x, self.floor_y-self.shadow.shape[0]//2)
        alpha_blend_bgra(out, vinyl, self.x, self.y)
        out[self.fade_start:] = (out[self.fade_start:]*self.subtitle_fade[self.fade_start:]).astype(np.uint8)
        return out
