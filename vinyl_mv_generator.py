import sys
from visualizer.image_utils import parse_color
from visualizer.particles import export_particle_frames
from visualizer.renderer import render_video

if __name__ == '__main__':
    if '--export-particles' in sys.argv:
        export_particle_frames()
    elif '--render' in sys.argv:
        import argparse
        parser=argparse.ArgumentParser(description='音频可视化生成器')
        parser.add_argument('--render',action='store_true')
        parser.add_argument('--image',required=True)
        parser.add_argument('--audio',required=True)
        parser.add_argument('--output',required=True)
        parser.add_argument('--width',type=int,default=1920)
        parser.add_argument('--height',type=int,default=1080)
        parser.add_argument('--fps',type=int,default=30)
        parser.add_argument('--rpm',type=float,default=2.5)
        parser.add_argument('--start',type=float,default=0.)
        parser.add_argument('--duration',type=float)
        parser.add_argument('--background-color',type=parse_color)
        parser.add_argument('--spectrum-color',type=parse_color)
        a=parser.parse_args()
        render_video(a.image,a.audio,a.output,a.width,a.height,a.fps,a.rpm,
                     status=lambda s:print(s,flush=True),start=a.start,duration=a.duration,
                     background_color=a.background_color,spectrum_color=a.spectrum_color)
    else:
        from visualizer.gui import App
        App().mainloop()
