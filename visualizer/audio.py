import math
import subprocess
import numpy as np
from .config import FLAGS

# 音频分析
def read_audio_mono(audio_path, ffmpeg, sr=44100, start=0., duration=None):
    cmd = [ffmpeg, '-v', 'error', '-ss', str(start), '-i', str(audio_path)]
    if duration is not None:
        cmd += ['-t', str(duration)]
    cmd += ['-vn', '-f', 'f32le', '-ac', '1', '-ar', str(sr), '-']
    p = subprocess.run(cmd, capture_output=True, creationflags=FLAGS)
    if p.returncode:
        raise RuntimeError(p.stderr.decode('utf-8', errors='replace')[-3000:])
    y = np.frombuffer(p.stdout, np.float32)
    if not len(y):
        raise RuntimeError('音频中没有有效采样。')
    return np.nan_to_num(y), sr

def audio_duration(audio_path, ffprobe):
    p = subprocess.run([ffprobe, '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', str(audio_path)],
        capture_output=True, text=True, creationflags=FLAGS)
    if p.returncode:
        raise RuntimeError('无法读取音频时长：' + p.stderr[-1000:])
    return float(p.stdout.strip())

def build_spectrum(y, sr, fps, duration, bins=72):
    n = max(1, math.ceil(duration*fps))
    fft_n = 4096
    win = np.hanning(fft_n).astype(np.float32)
    freq = np.fft.rfftfreq(fft_n, 1/sr)
    edges = np.geomspace(50., min(12000., sr*.47), bins+2)
    weights = np.zeros((bins, len(freq)), np.float32)
    for k in range(bins):
        weights[k] = np.maximum(0, np.minimum(
            (freq-edges[k])/(edges[k+1]-edges[k]),
            (edges[k+2]-freq)/(edges[k+2]-edges[k+1])))
        if weights[k].sum() == 0:
            weights[k, np.argmin(abs(freq-edges[k+1]))] = 1
        weights[k] /= weights[k].sum()
    raw = np.zeros((n, bins), np.float32)
    rms = np.zeros(n, np.float32)
    supports = [(np.flatnonzero(w), w[w > 0]) for w in weights]
    padded = np.pad(y, (fft_n//2, fft_n//2))
    for i in range(n):
        pos = round(i*sr/fps)
        chunk = padded[pos:pos+fft_n]
        if len(chunk) < fft_n:
            chunk = np.pad(chunk, (0, fft_n-len(chunk)))
        rms[i] = np.sqrt(np.mean(chunk*chunk))
        mag = abs(np.fft.rfft(chunk*win)) * (2/win.sum())
        for k, (idx, w) in enumerate(supports):
            raw[i, k] = np.sqrt(np.dot(mag[idx]**2, w))
    db = 20*np.log10(np.maximum(raw, 1e-9))
    active = db[raw > 1e-6]
    reference = max(-45., float(np.percentile(active, 99.6))) if len(active) else 0.
    v = np.maximum(0., (db-reference+46.)/46.) ** 2.2
    v = .9*np.tanh(v/1.05)
    v *= np.linspace(1., .92, bins)[None, :]
    gate = np.clip((20*np.log10(np.maximum(rms, 1e-9))+65.)/18., 0., 1.)
    v *= gate[:, None]
    prev = np.zeros(bins, np.float32)
    attack, release = math.exp(-1/(fps*.012)), math.exp(-1/(fps*.095))
    for i in range(n):
        a = np.where(v[i] > prev, attack, release)
        prev = a*prev + (1-a)*v[i]
        raw[i] = prev
    return raw
