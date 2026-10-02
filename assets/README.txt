Vinyl MV preset assets

background.png          1920x1080  fixed cinematic background
floor_reflection.png    1920x740   reflective floor preset
vinyl_preset.png        1024x1024  vinyl appearance reference/preset
vinyl_groove.png        1024x1024  groove/highlight texture
vinyl_glow.png          1024x1024  magenta rim-light preset
ambient_light.png       1024x1024  ambient glow
vignette.png            1920x1080  vignette overlay
particles_overlay.png   1920x1080  static particle overlay
particle_frames/        32 frames  loopable particle sequence (960x540)

Recommended compositing:
- background/floor: normal blend
- vinyl_glow / particles: screen or additive blend
- particle_frames: 12-16 fps, loop continuously
- waveform: generate from audio in code; do not use a fixed image
