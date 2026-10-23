# 生成 PWA / 主屏幕图标：橙底白"写"字圆角方块
import os
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'icons')
os.makedirs(OUT, exist_ok=True)

BG = (255, 122, 69, 255)      # 柿橙
FONT_CANDIDATES = [
    r'C:\Windows\Fonts\msyhbd.ttc',   # 微软雅黑 Bold
    r'C:\Windows\Fonts\msyh.ttc',
    r'C:\Windows\Fonts\simhei.ttf',
    r'C:\Windows\Fonts\simsun.ttc',
]

def rounded(size, radius):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=BG)
    return img, d

def make(size, radius_ratio, out_name, square_bg=False):
    if square_bg:
        img = Image.new('RGBA', (size, size), BG)
        d = ImageDraw.Draw(img)
    else:
        img, d = rounded(size, int(size * radius_ratio))
    ch = '写'
    font = None
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                font = ImageFont.truetype(p, int(size * 0.62))
                break
            except Exception:
                continue
    if font is None:
        font = ImageFont.load_default()
    bbox = d.textbbox((0, 0), ch, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((size - w) / 2 - bbox[0], (size - h) / 2 - bbox[1] - size * 0.01), ch,
           font=font, fill=(255, 255, 255, 255))
    img.save(os.path.join(OUT, out_name))
    print('generated', out_name, img.size)

# PWA 图标（带圆角，自带透明）
make(512, 0.22, 'icon-512.png')
make(192, 0.24, 'icon-192.png')
# apple-touch-icon：iOS 自己会切圆角，用满幅方形
make(180, 0, 'apple-touch-icon.png', square_bg=True)
print('done ->', OUT)
