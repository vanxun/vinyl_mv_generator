import os
import math
import subprocess
import tempfile
from pathlib import Path
from .config import FLAGS
from .image_utils import find_ffmpeg
from .audio import audio_duration, read_audio_mono, build_spectrum
from .scene import Scene

# 视频导出
def validate_parameters(width, height, fps, rpm):
    if width < 640 or height < 360 or width % 2 or height % 2:
        raise ValueError('宽高须为偶数，至少 640 × 360。')
    if not 1.3 <= width/height <= 2.5:
        raise ValueError('此预设适用于横屏，宽高比请在 1.3～2.5 之间。')
    if not 1 <= fps <= 120 or not math.isfinite(rpm) or not 0 <= rpm <= 30:
        raise ValueError('FPS 应为 1～120，转速应为 0～30 RPM。')

def render_video(image_path, audio_path, output_path, width=1920, height=1080,
                 fps=30, rpm=2.5, progress=None, status=None, start=0., duration=None, background_color=None, spectrum_color=None):
    validate_parameters(width, height, fps, rpm)
    output_path = Path(output_path).resolve()
    if output_path in (Path(image_path).resolve(), Path(audio_path).resolve()):
        raise ValueError('输出路径不能覆盖输入文件。')
    ffmpeg, ffprobe = find_ffmpeg('ffmpeg'), find_ffmpeg('ffprobe')
    if not ffmpeg or not ffprobe:
        raise RuntimeError('找不到 FFmpeg/FFprobe，请放入 PATH 或脚本旁 ffmpeg/bin。')
    if status: status('正在加载素材并校准布局……')
    scene = Scene(image_path, width, height, rpm, fps, background_color, spectrum_color)
    available = audio_duration(audio_path, ffprobe)-start
    if start < 0 or available <= 0:
        raise ValueError('预览起点超出音频范围。')
    duration = available if duration is None else min(duration, available)
    if not math.isfinite(duration) or duration <= 0:
        raise ValueError('音频时长无效。')
    if status: status('正在分析音频频谱……')
    y, sr = read_audio_mono(audio_path, ffmpeg, start=start, duration=duration)
    spectrum = build_spectrum(y, sr, fps, duration)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=output_path.stem+'.', suffix='.partial.mp4', dir=output_path.parent)
    os.close(fd)
    cmd = [ffmpeg, '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo',
        '-pix_fmt', 'bgr24', '-s', f'{width}x{height}', '-r', str(fps), '-i', '-',
        '-ss', str(start), '-i', str(audio_path), '-map', '0:v:0', '-map', '1:a:0',
        '-t', str(duration), '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
        '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', temporary]
    enc = None
    try:
        with tempfile.TemporaryFile() as errors:
            enc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                stderr=errors, creationflags=FLAGS)
            try:
                for i, values in enumerate(spectrum):
                    frame = scene.frame(i/fps, values)
                    enc.stdin.write(frame.tobytes())
                    if i % max(1, fps//4) == 0 or i == len(spectrum)-1:
                        if progress: progress(100*(i+1)/len(spectrum))
                        if status: status(f'正在渲染：{i+1}/{len(spectrum)} 帧')
                enc.stdin.close()
            except BrokenPipeError:
                enc.stdin.close()
            rc = enc.wait()
            errors.seek(0)
            detail = errors.read().decode('utf-8', errors='replace')
            if rc:
                raise RuntimeError('视频编码失败：\n'+detail[-3000:])
        os.replace(temporary, output_path)
    finally:
        if enc is not None and enc.poll() is None:
            enc.terminate()
            enc.wait()
        if os.path.exists(temporary):
            os.unlink(temporary)
    if progress: progress(100)
    if status: status('完成')
