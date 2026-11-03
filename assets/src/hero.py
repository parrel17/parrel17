import math
import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path("/tmp/assets_gen")
FONTS = Path("/tmp/fonts")
OUT = Path("/tmp/parrel17/assets/hero.gif")

W, H = 450, 150          # internal resolution
SCALE = 2                # output is 900x300
FRAMES = 40
FRAME_MS = 80

STATEMENTS = [
    "building distributed systems & autonomous fleets.",
    "architecting low-latency backends with zero slop.",
    "coding obsessively, engineering with joy.",
]

# Palette: void, deep cyan, cyber blue, ice cyan, platinum bone
PALETTE = np.array(
    [
        (13, 17, 23),
        (12, 74, 110),
        (2, 132, 199),
        (56, 189, 248),
        (240, 246, 252),
    ],
    dtype=np.uint8,
)
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

def text_mask(text, font, size, pad=4):
    f = ImageFont.truetype(str(FONTS / font), size)
    l, t, r, b = f.getbbox(text)
    im = Image.new("L", (r - l + pad * 2, b - t + pad * 2), 0)
    ImageDraw.Draw(im).text((pad - l, pad - t), text, font=f, fill=255)
    return np.asarray(im, dtype=np.float32) / 255.0

def paste(dst, src, x, y):
    h, w = src.shape
    dst[y : y + h, x : x + w] = np.maximum(dst[y : y + h, x : x + w], src)

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# Load avatar portrait
avatar_path = Path("/tmp/avatar.png")
avatar = Image.open(avatar_path).convert("L")
aw, ah = avatar.size
PW = 145
avatar = avatar.resize((PW, int(PW * ah / aw)), Image.LANCZOS)
g = np.asarray(avatar, dtype=np.float32) / 255.0
g = g[:H, :]
# Contrast boost
g = np.clip((g - 0.10) / 0.82, 0, 1) ** 1.15
PX = W - PW - 6
portrait = np.zeros((H, W), np.float32)
portrait[: g.shape[0], PX : PX + PW] = g * 0.98

# Feather portrait's left edge and bottom
fx = np.clip((xx - PX) / 40.0, 0, 1)
fy = np.clip((H - 2 - yy) / 24.0, 0, 1)
portrait *= fx * fy
FACE_X, FACE_Y = PX + 72, 60
dv = np.sqrt(((xx - FACE_X) / 90.0) ** 2 + ((yy - FACE_Y) / 75.0) ** 2)
portrait *= np.clip(1.15 - 0.75 * dv ** 2, 0.25, 1.0)

# Title & copy
title = text_mask("farrel", "PirataOne-Regular.ttf", 68)
PIXEL = ImageFont.truetype(str(FONTS / "Silkscreen-Regular.ttf"), 8)
PIXEL_TOP = PIXEL.getbbox("> AG")[1]

def pixel_row(text):
    l, t, r, b = PIXEL.getbbox(text)
    w = r - l + 2
    im = Image.new("L", (w, 8), 0)
    ImageDraw.Draw(im).text((-l, -PIXEL_TOP), text, font=PIXEL, fill=255)
    return np.asarray(im, dtype=np.float32) / 255.0

DIAMOND = np.array(
    [
        [0, 0, 1, 0, 0],
        [0, 1, 1, 1, 0],
        [1, 1, 1, 1, 1],
        [0, 1, 1, 1, 0],
        [0, 0, 1, 0, 0],
    ],
    np.float32,
)

TX, TY = 20, 12
title_layer = np.zeros((H, W), np.float32)
paste(title_layer, title, TX, TY)
title_grad = np.clip(1.0 - (yy - TY) / (title.shape[0] * 1.05), 0.42, 1.0)

copy_layer = np.zeros((H, W), np.float32)
mark_layer = np.zeros((H, W), np.float32)
tag_y = TY + title.shape[0] + 4
role_a, role_b = pixel_row("SYSTEMS ARCHITECT"), pixel_row("AI FLEET")
x = TX + 4
paste(copy_layer, role_a, x, tag_y)
x += np.nonzero(role_a.max(axis=0) > 0.5)[0][-1] + 8
paste(mark_layer, DIAMOND, x, tag_y + 1)
paste(copy_layer, role_b, x + DIAMOND.shape[1] + 7, tag_y)

prompt_y = tag_y + 18
ROW_STEP = 13
gt = pixel_row(">")
gt_w = int(PIXEL.getlength("> "))
for i, line in enumerate(STATEMENTS):
    y = prompt_y + i * ROW_STEP
    paste(mark_layer, gt, TX + 4, y)
    paste(copy_layer, pixel_row(line), TX + 4 + gt_w, y)

ink = np.nonzero(title.max(axis=0) > 0.5)[0]
rule = np.zeros((H, W), np.float32)
rule[tag_y - 6, TX + ink[0] : TX + ink[-1] + 1] = 1.0

# Render frames
frames = []
for f in range(FRAMES):
    p = f / FRAMES
    pulse = 0.5 + 0.5 * math.sin(2 * math.pi * p)

    # Breathing cyber glow behind portrait
    cx, cy = PX + PW * 0.55, H * 0.42
    d = np.sqrt(((xx - cx) / 150.0) ** 2 + ((yy - cy) / 95.0) ** 2)
    glow = np.clip(1.0 - d, 0, 1) ** 1.6 * (0.30 + 0.10 * pulse)
    field = glow.copy()

    # Portrait with glitch scan band
    band_y = int((p * (H + 40)) - 20)
    por = portrait.copy()
    band = (yy >= band_y) & (yy < band_y + 7) & (xx >= PX + 20)
    if band.any():
        rows = np.unique(yy[band].astype(int))
        for r in rows:
            if 0 <= r < H:
                shift = int(5 * math.sin(r * 1.7 + f))
                seg = por[r, PX:]
                por[r, PX:] = np.roll(seg, shift) * 1.25 + 0.08
    por *= 0.92 + 0.10 * pulse
    field = np.maximum(field, por)

    # Diagonal light sweep across title
    sweep_x = -60 + p * (title.shape[1] + 260)
    sweep = np.exp(-(((xx - TX) + (yy - TY) * 0.6 - sweep_x) / 14.0) ** 2) * 0.55
    field = np.maximum(field, title_layer * np.clip(title_grad + sweep, 0, 1))
    field = np.maximum(field, rule * 0.45)
    field = np.where(copy_layer > 0.5, 0.80, field)
    field = np.where(mark_layer > 0.5, 0.50, field)

    idx = dither(field)
    if band.any():
        alt = dither(field, ox=f % 8, oy=(f * 3) % 8)
        idx = np.where(band, alt, idx)

    rgb = PALETTE[idx]
    im = Image.fromarray(rgb, "RGB").resize((W * SCALE, H * SCALE), Image.NEAREST)
    frames.append(im)

pal_img = Image.new("P", (1, 1))
pal_img.putpalette(PALETTE.flatten().tolist() + [0] * (768 - PALETTE.size))
q = [fr.quantize(palette=pal_img, dither=Image.Dither.NONE) for fr in frames]
OUT.parent.mkdir(parents=True, exist_ok=True)
q[0].save(
    OUT,
    save_all=True,
    append_images=q[1:],
    duration=FRAME_MS,
    loop=0,
    optimize=True,
    disposal=1,
)
print(f"Hero generated: {OUT} ({OUT.stat().st_size // 1024} KB)")
