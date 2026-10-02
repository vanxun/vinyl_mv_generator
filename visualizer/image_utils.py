import shutil
import cv2
import numpy as np
from PIL import Image, ImageOps
from .config import APP_DIR, ASSET_DIR

# 文件与图像处理
def find_ffmpeg(name):
    return shutil.which(name) or next((str(p) for p in
        [APP_DIR / (name + '.exe'), APP_DIR / 'ffmpeg' / 'bin' / (name + '.exe')]
        if p.exists()), None)

def load_bgr(path, size=None):
    with Image.open(path) as src:
        im = np.array(ImageOps.exif_transpose(src).convert('RGB'))[:, :, ::-1].copy()
    return cv2.resize(im, size, interpolation=cv2.INTER_AREA) if size else im

def cover_fit(im, size):
    w, h = size
    ih, iw = im.shape[:2]
    s = max(w / iw, h / ih)
    nw, nh = max(w, round(iw*s)), max(h, round(ih*s))
    im = cv2.resize(im, (nw, nh), interpolation=cv2.INTER_AREA if s < 1 else cv2.INTER_CUBIC)
    x, y = (nw-w)//2, (nh-h)//2
    return im[y:y+h, x:x+w].copy()

def cover_crop_image(path, size):
    return cover_fit(load_bgr(path), size)

def clean_asset(name):
    im = load_bgr(ASSET_DIR / name)
    py, px = max(2, round(im.shape[0]*.014)), max(2, round(im.shape[1]*.009))
    return im[py:-py, px:-px].copy()

def screen_blend_bgr(dst, src, strength=1.):
    d = dst.astype(np.float32)
    light = np.asarray(src, dtype=np.float32) * np.float32(strength / 255.)
    d += (np.float32(255.) - d) * light
    dst[:] = np.clip(d, 0, 255).astype(np.uint8)


def alpha_blend_bgra(dst, fg, x, y, opacity=1.):
    x, y = int(x), int(y)
    h, w = fg.shape[:2]
    H, W = dst.shape[:2]
    l, t, r, b = max(x, 0), max(y, 0), min(x+w, W), min(y+h, H)
    if r <= l or b <= t:
        return
    p = fg[t-y:b-y, l-x:r-x]
    a = p[:, :, 3:4].astype(np.float32) * (opacity/255.)
    dst[t:b, l:r] = np.clip(p[:, :, :3]*a + dst[t:b, l:r]*(1-a), 0, 255).astype(np.uint8)

def rotate_bgra(im, angle):
    h, w = im.shape[:2]
    mat = cv2.getRotationMatrix2D(((w-1)/2, (h-1)/2), -angle, 1.)
    return cv2.warpAffine(im, mat, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)

# 颜色设置
def parse_color(value):
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if text.startswith('#'):
            text = text[1:]
        if len(text) == 6 and all(c in '0123456789abcdefABCDEF' for c in text):
            return tuple(int(text[i:i+2], 16) for i in (0, 2, 4))
        text = text.lower().removeprefix('rgb').strip(' ()').replace('，', ',')
        parts = text.split(',') if ',' in text else text.split()
        if len(parts) != 3 or not all(p.strip().isdigit() for p in parts):
            raise ValueError('颜色请输入 #RRGGBB 或 R,G,B（0～255）。')
        value = tuple(int(p.strip()) for p in parts)
    if len(value) != 3 or any(not isinstance(v, (int, np.integer)) or not 0 <= v <= 255 for v in value):
        raise ValueError('RGB 必须是三个 0～255 的整数。')
    return tuple(int(v) for v in value)

def tint_image(image, color):
    if color is None:
        return image
    level = image.max(axis=2).astype(np.float32)[:, :, None] / 255.
    return (level*np.array(color[::-1], np.float32)).astype(np.uint8)
