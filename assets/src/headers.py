import math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path("/tmp/assets_gen")
HERE.mkdir(parents=True, exist_ok=True)
FONTS = Path("/tmp/fonts")
OUT = Path("/tmp/parrel17/assets")
OUT.mkdir(parents=True, exist_ok=True)

SCALE = 2

# Palette: Void, Deep Cyan/Navy, Cyber Blue, Ice Blue, Platinum Bone
# (10, 10, 10) matching #0A0A0A minimalist luxury void
PALETTE = np.array([
    (13, 17, 23),    # 0: Void #0d1117 (GitHub dark bg match)
    (12, 74, 110),   # 1: Deep Sky #0c4a6e
    (2, 132, 199),   # 2: Cyber Blue #0284c7
    (56, 189, 248),  # 3: Ice Cyan #38bdf8
    (240, 246, 252)  # 4: Platinum Bone #f0f6fc
], dtype=np.uint8)
LEVELS = len(PALETTE)

def bayer(n):
    m = np.array([[0]])
    while m.shape[0] < n:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return (m + 0.5) / (n * n)

B8 = bayer(8)

def dither(field, ox=0, oy=0):
    h, w = field.shape
    t = np.roll(np.roll(np.tile(B8, (h // 8 + 1, w // 8 + 1))[:h, :w], oy, 0), ox, 1)
    v = np.clip(field, 0, 1) * (LEVELS - 1)
    base = np.floor(v)
    idx = base + (v - base > t)
    return np.clip(idx, 0, LEVELS - 1).astype(np.uint8)

def to_image(idx):
    im = Image.fromarray(idx, "P")
    im.putpalette([c for rgb in PALETTE for c in rgb])
    w, h = im.size
    return im.resize((w * SCALE, h * SCALE), Image.NEAREST)

def text_mask(text, font, size, pad=4):
    f = ImageFont.truetype(str(FONTS / font), size)
    l, t, r, b = f.getbbox(text)
    im = Image.new("L", (r - l + pad * 2, b - t + pad * 2), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=255)
    return np.asarray(im, dtype=np.float32) / 255.0

# Generate Headers
def header(num, label, name):
    W, H = 450, 22
    f_reg = ImageFont.truetype(str(FONTS / "Silkscreen-Regular.ttf"), 8)
    f_bold = ImageFont.truetype(str(FONTS / "Silkscreen-Bold.ttf"), 8)
    
    num_m = text_mask(num, "Silkscreen-Regular.ttf", 8)
    lab_m = text_mask(label, "Silkscreen-Bold.ttf", 8)
    slash_m = text_mask("/", "Silkscreen-Regular.ttf", 8)
    
    idx = np.zeros((H, W), np.uint8)
    y = (H - lab_m.shape[0]) // 2
    x = 0
    
    idx[y : y + num_m.shape[0], x : x + num_m.shape[1]][num_m > 0.5] = 2
    x += num_m.shape[1] + 6
    
    idx[y : y + slash_m.shape[0], x : x + slash_m.shape[1]][slash_m > 0.5] = 2
    x += slash_m.shape[1] + 6
    
    idx[y : y + lab_m.shape[0], x : x + lab_m.shape[1]][lab_m > 0.5] = 3
    x += lab_m.shape[1] + 10
    
    # Dithered rule fading out to the right
    ry = y + lab_m.shape[0] // 2 - 1
    xs = np.arange(W - x, dtype=np.float32)
    fade = np.clip(1.0 - xs / (W - x), 0, 1) ** 0.8 * 0.95
    rule = dither(np.tile(fade, (3, 1)))
    idx[ry : ry + 3, x:] = rule
    
    im = to_image(idx)
    im.save(OUT / name, optimize=True)
    print(f"Generated header: {name}")

header("01", "ABOUT", "h-about.png")
header("02", "ACTIVITY", "h-activity.png")
