import sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONTS = Path("/tmp/fonts")
OUT = Path("/tmp/parrel17/assets/boot.gif")

W, H = 450, 144
SCALE = 2

# void, deep cyan, cyber blue, ice cyan, platinum bone
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
VOID, DEEP, CYBER, BRIGHT, BONE = range(5)
LEVELS = len(PALETTE)

LINES = [
    ("OK", "INITIALIZING SYSTEM", "FARREL.SYS"),
    ("OK", "ACTIVE FLEET", "9ROUTER / MOVIE / FINANCE"),
    ("OK", "CORE STACK", "PYTHON / TS / GO / SQLITE"),
    ("OK", "INFRASTRUCTURE", "SUMOPOD / WARP / NGINX"),
    ("OK", "OFF-DUTY", "FC PES / F1 / CINEMA / BARCA"),
    ("!!", "DIRECTIVE", "ZERO SLOP / RELENTLESS DEV"),
    ("..", "SYSTEM CHARGE", None),
]

def bayer(n):
    m = np.array([[0]])
    while m.shape[0] < n:
        m = np.block([[4 * m, 4 * m + 2], [4 * m + 3, 4 * m + 1]])
    return (m + 0.5) / (n * n)

B8 = bayer(8)

def dither(field):
    h, w = field.shape
    t = np.tile(B8, (h // 8 + 1, w // 8 + 1))[:h, :w]
    v = np.clip(field, 0, 1) * (LEVELS - 1)
    base = np.floor(v)
    return np.clip(base + (v - base > t), 0, LEVELS - 1).astype(np.uint8)

_fonts = {}

def text(idx, s, x, y, color, bold=False):
    name = "Silkscreen-Bold.ttf" if bold else "Silkscreen-Regular.ttf"
    f = _fonts.setdefault(name, ImageFont.truetype(str(FONTS / name), 8))
    l, t, r, b = f.getbbox(s)
    im = Image.new("L", (r - l, b - t), 0)
    ImageDraw.Draw(im).text((-l, -t), s, font=f, fill=255)
    m = np.asarray(im) > 127
    h, w = m.shape
    idx[y : y + h, x : x + w][m] = color
    return x + w

yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)

# Static panel: cyan corner glow, frame, title bar
glow = np.clip(1.0 - np.sqrt(((xx - W) / 260.0) ** 2 + (yy / 150.0) ** 2), 0, 1) ** 2 * 0.22
panel = dither(glow)
panel[0, :] = panel[-1, :] = CYBER
panel[:, 0] = panel[:, -1] = CYBER
bar = dither(np.tile(np.clip(1.0 - np.arange(W - 2) / (W * 0.9), 0, 1) * 0.5, (13, 1)))
panel[1:14, 1:-1] = bar
text(panel, "FARREL.SYS // NEXA.BOOT", 8, 4, BONE, bold=True)

LX, LY, STEP = 10, 24, 13
VALUE_X = W - 10
TAG_COLOR = {"OK": BRIGHT, "!!": BONE, "..": CYBER}

def draw_line(idx, i, chars=None):
    tag, label, value = LINES[i]
    y = LY + i * STEP
    text(idx, "[", LX, y, CYBER)
    probe = np.zeros_like(idx)
    tw = text(probe, tag, 0, 0, 1, bold=True)
    text(idx, tag, LX + 4 + (13 - tw) // 2, y, TAG_COLOR[tag], bold=True)
    text(idx, "]", LX + 19, y, CYBER)
    shown = label if chars is None else label[:chars]
    x = text(idx, shown, LX + 31, y, BONE)
    return x, y

def draw_value(idx, i, end_x):
    _, _, value = LINES[i]
    y = LY + i * STEP
    probe = np.zeros_like(idx)
    w = text(probe, value, 0, 0, 1) if value else 0
    vx = VALUE_X - w
    for dx in range(end_x + 6, vx - 6, 4):
        idx[y + 4, dx] = DEEP
    text(idx, value, vx, y, BRIGHT)

def draw_bar(idx, end_x, fill):
    y = LY + (len(LINES) - 1) * STEP
    x0, x1 = end_x + 10, VALUE_X - 34
    idx[y - 1, x0 - 1 : x1 + 1] = DEEP
    idx[y + 7, x0 - 1 : x1 + 1] = DEEP
    idx[y - 1 : y + 8, x0 - 1] = DEEP
    idx[y - 1 : y + 8, x1] = DEEP
    n = int((x1 - x0) * fill)
    if n > 0:
        ramp = np.linspace(0.35, 1.0, x1 - x0)[:n]
        idx[y : y + 7, x0 : x0 + n] = dither(np.tile(ramp, (7, 1)))
    text(idx, f"{int(fill * 100):>3d}%", VALUE_X - 26, y, BRIGHT)

PROMPT_Y = LY + len(LINES) * STEP + 2

frames, durations = [], []

def emit(idx, ms):
    frames.append(idx.copy())
    durations.append(ms)

# 1) Type each line, then drop its value in
for i in range(len(LINES)):
    label = LINES[i][1]
    for c in range(0, len(label) + 1, 4):
        idx = panel.copy()
        for j in range(i):
            ex, _ = draw_line(idx, j)
            if LINES[j][2] is not None:
                draw_value(idx, j, ex)
        draw_line(idx, i, chars=c)
        emit(idx, 45)
    if LINES[i][2] is not None:
        idx = panel.copy()
        for j in range(i + 1):
            ex, _ = draw_line(idx, j)
            draw_value(idx, j, ex)
        emit(idx, 160)

# 2) Charge progress bar
base = panel.copy()
last_end = 0
for j in range(len(LINES)):
    ex, _ = draw_line(base, j)
    if LINES[j][2] is not None:
        draw_value(base, j, ex)
    else:
        last_end = ex
for k in range(15):
    idx = base.copy()
    draw_bar(idx, last_end, min(0.88, k * 0.06))
    emit(idx, 70)

# 3) Blinking prompt
done = frames[-1].copy()
px = text(done, "> OPERATOR: FARREL (RELLZA)", LX, PROMPT_Y, BONE)
for k in range(8):
    idx = done.copy()
    if k % 2 == 0:
        idx[PROMPT_Y : PROMPT_Y + 7, px + 3 : px + 8] = BRIGHT
    emit(idx, 420)

pal = Image.new("P", (1, 1))
pal.putpalette(PALETTE.flatten().tolist() + [0] * (768 - PALETTE.size))
imgs = []
for idx in frames:
    im = Image.fromarray(idx, "P")
    im.putpalette(pal.getpalette())
    imgs.append(im.resize((W * SCALE, H * SCALE), Image.NEAREST))

OUT.parent.mkdir(parents=True, exist_ok=True)
imgs[0].save(
    OUT,
    save_all=True,
    append_images=imgs[1:],
    duration=durations,
    loop=0,
    optimize=True,
    disposal=1,
)
print(f"Boot generated: {OUT} ({OUT.stat().st_size // 1024} KB)")
