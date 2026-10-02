import subprocess
import os
from pathlib import Path

# 配置
APP_DIR = Path(__file__).resolve().parent.parent
ASSET_DIR = APP_DIR / 'assets'
DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS, DEFAULT_RPM = 1920, 1080, 30, 2.5
FLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

