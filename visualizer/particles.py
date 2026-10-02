import math
from pathlib import Path
import numpy as np
from PIL import Image
from .config import ASSET_DIR
from .image_utils import alpha_blend_bgra, tint_image

# 全屏粒子动画
class ParticleField:
    period = 32.

    def __init__(self, width, height, color=None):
        self.w, self.h = width, height
        scale = min(width/1920, height/1080)
        rng = np.random.default_rng(641)
        self.sprites = []
        for k in range(100):
            radius = max(2, round((rng.uniform(1.2, 3.) if k < 75 else rng.uniform(9, 24))*scale))
            q = np.linspace(-2.8, 2.8, radius*6+1)
            dot = np.exp(-(q[:, None]**2+q[None, :]**2)*.65)
            sprite = np.empty((*dot.shape, 4), np.uint8)
            sprite[:, :, :3] = (176, 106, 214)
            sprite[:, :, 3] = (dot*rng.uniform(35, 110 if k < 75 else 45)).astype(np.uint8)
            if color is not None:
                sprite[:, :, :3] = tint_image(sprite[:, :, :3], color)
            self.sprites.append((rng.random(), rng.random(), rng.uniform(0, math.tau), sprite))

    def draw(self, out, t):
        cycle = (t % self.period)/self.period
        for px, py, phase, sprite in self.sprites:
            yp = (py-cycle) % 1
            xp = (px+.016*math.sin(cycle*math.tau+phase)) % 1
            visibility = min(1., yp/.035, (1-yp)/.035, xp/.025, (1-xp)/.025)
            opacity = visibility*(.7+.3*math.sin(cycle*math.tau+phase)**2)
            alpha_blend_bgra(out, sprite, round(xp*self.w-sprite.shape[1]/2),
                             round(yp*self.h-sprite.shape[0]/2), opacity)


def export_particle_frames(directory=None):
    directory = Path(directory) if directory else ASSET_DIR/'particle_frames'
    directory.mkdir(parents=True, exist_ok=True)
    particles = ParticleField(1920, 1080)
    for i in range(32):
        frame = np.zeros((1080, 1920, 3), np.uint8)
        particles.draw(frame, i*particles.period/32)
        Image.fromarray(frame[:, :, ::-1]).save(directory/f'particle_{i:03d}.png')
