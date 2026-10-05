import math, os, random, subprocess, sys
from multiprocessing import Pool
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance, ImageOps
import render as R

W, H, FPS, DUR = 1080, 1920, 30, R.DUR
S = 2                       # supersampling for the card layer
CW, CH = 960, 1200          # card size (1x)
CX, CY = 60, 150            # card position on the frame
BG = (224, 221, 216)
CARD = (245, 243, 239)
INK = (22, 22, 22)
OR = (255, 122, 26)
GRAY = (150, 146, 140)
PHOTOS = os.environ.get("PHOTOS", "/home/user/Recordly/reels/fotos")

def F(name, size):
    return ImageFont.truetype(f"fonts/{name}.woff", int(size * S))
from PIL import ImageFont
MALI = "mali-latin-600-normal"
MALIB = "mali-latin-700-normal"
FRED = "fredoka-latin-500-normal"
FREDB = "fredoka-latin-600-normal"
T = R.T
T_UMA = max(x["s"] for x in R.words if x["t"] == "Uma")

# ---------------- easing ----------------
def clamp(x): return max(0.0, min(1.0, x))
def ease_out(x): x = clamp(x); return 1 - (1 - x) ** 3
def ease_io(x): x = clamp(x); return 4 * x ** 3 if x < .5 else 1 - (-2 * x + 2) ** 3 / 2
def back(x):
    x = clamp(x); c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (x - 1) ** 3 + c1 * (x - 1) ** 2

# ---------------- wobbly drawing ----------------
class Ctx:
    def __init__(self, img, t, boil):
        self.img, self.d, self.t, self.boil = img, ImageDraw.Draw(img), t, boil

def subdiv(pts, step=14):
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        n = max(1, int(math.hypot(x1 - x0, y1 - y0) / step))
        out += [(x0 + (x1 - x0) * k / n, y0 + (y1 - y0) * k / n) for k in range(n)]
    out.append(pts[-1])
    return out

def wline(c, pts, width=5, color=INK, prog=1.0, seed=0, amp=1.6):
    if prog <= 0 or len(pts) < 2:
        return
    p = subdiv(pts)
    r = random.Random(seed * 131 + c.boil)
    p = [(x + r.uniform(-amp, amp), y + r.uniform(-amp, amp)) for x, y in p]
    n = max(2, int(len(p) * clamp(prog)))
    q = [(x * S, y * S) for x, y in p[:n]]
    c.d.line(q, fill=color, width=int(width * S), joint="curve")
    rr = width * S / 2
    for x, y in (q[0], q[-1]):
        c.d.ellipse([x - rr, y - rr, x + rr, y + rr], fill=color)

def ell_pts(cx, cy, rx, ry, a0=0, a1=2 * math.pi, n=48):
    return [(cx + rx * math.cos(a0 + (a1 - a0) * k / n), cy + ry * math.sin(a0 + (a1 - a0) * k / n)) for k in range(n + 1)]

def wellipse(c, cx, cy, rx, ry, width=5, color=INK, prog=1, seed=0, fill=None):
    if fill and prog >= 1:
        c.d.ellipse([(cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S], fill=fill)
    wline(c, ell_pts(cx, cy, rx, ry, -1.6, -1.6 + 2 * math.pi * 1.04), width, color, prog, seed)

def wrect(c, x0, y0, x1, y1, r=18, width=4, color=INK, prog=1, seed=0):
    pts = []
    for (cx, cy, a) in ((x1 - r, y0 + r, -math.pi / 2), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, math.pi / 2), (x0 + r, y0 + r, math.pi)):
        pts += ell_pts(cx, cy, r, r, a, a + math.pi / 2, 6)
    pts.append(pts[0])
    wline(c, pts, width, color, prog, seed, amp=1.2)

def curve(p0, p1, bend=0.25, n=24):
    (x0, y0), (x1, y1) = p0, p1
    cx, cy = (x0 + x1) / 2 - (y1 - y0) * bend, (y0 + y1) / 2 + (x1 - x0) * bend
    return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1, (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1)
            for t in [k / n for k in range(n + 1)]]

def arrow(c, p0, p1, bend=0.25, width=5, color=OR, prog=1, seed=0):
    pts = curve(p0, p1, bend)
    wline(c, pts, width, color, prog / 0.8, seed)
    if prog > 0.8:
        hp = (prog - 0.8) / 0.2
        (xa, ya), (xb, yb) = pts[-3], pts[-1]
        a = math.atan2(yb - ya, xb - xa)
        for da in (2.5, -2.5):
            wline(c, [(xb, yb), (xb + 26 * hp * math.cos(a + da), yb + 26 * hp * math.sin(a + da))], width, color, 1, seed + 7)

def squiggle(c, x0, x1, y, width=5, color=OR, prog=1, seed=0):
    pts = [(x0 + (x1 - x0) * k / 40, y + 7 * math.sin(k * 0.9)) for k in range(41)]
    wline(c, pts, width, color, prog, seed, amp=0.6)

def text(c, x, y, s, font, size, color=INK, prog=1.0, anchor="la"):
    """typewriter reveal"""
    if prog <= 0:
        return
    n = max(1, int(round(len(s) * clamp(prog))))
    f = F(font, size)
    if anchor == "ma":
        w = c.d.textlength(s, font=f)
        c.d.text((x * S - w / 2, y * S), s[:n], font=f, fill=color)
    else:
        c.d.text((x * S, y * S), s[:n], font=f, fill=color)

def tlen(s, font, size):
    return ImageDraw.Draw(Image.new("L", (1, 1))).textlength(s, font=F(font, size)) / S

def pill(c, title, prog, seed=0, y=40):
    """outlined title box like the reference"""
    wrect(c, 70, y, CW - 70, y + 74, 14, 4, INK, ease_out(prog * 1.6), seed)
    text(c, CW / 2, y + 12, title, MALI, 44, INK, (prog - 0.25) * 1.8, "ma")

def bullet(c, x, y, s=1.0):
    for k in range(3):
        a = k * 2.1 + 0.4
        c.d.ellipse([(x + 7 * math.cos(a) - 7) * S, (y + 7 * math.sin(a) - 7) * S, (x + 7 * math.cos(a) + 7) * S, (y + 7 * math.sin(a) + 7) * S], fill=OR)

def paste(c, im, x, y, prog=1.0, rot=0.0):
    """paste an RGBA (1x coordinates, image already at S scale) with pop"""
    if prog <= 0:
        return
    sc = 0.6 + 0.4 * back(prog)
    if abs(sc - 1) > 1e-3 or rot:
        im = im.resize((max(1, int(im.width * sc)), max(1, int(im.height * sc))), Image.BILINEAR)
        if rot:
            im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    a = clamp(prog * 3)
    if a < 1:
        im = im.copy(); im.putalpha(im.split()[3].point(lambda v: int(v * a)))
    cx, cy = (x * S), (y * S)
    c.img.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

# ---------------- photos ----------------
def colorize(img):
    img = img.convert("RGB")
    img = ImageEnhance.Color(img).enhance(0.8)
    return img.convert("RGBA")
R.photoize = lambda img, sepia=True: colorize(img)

def photo(key, w, h, fallback, circle=False):
    p = None
    for ext in ("jpg", "jpeg", "png", "webp"):
        fp = os.path.join(PHOTOS, f"{key}.{ext}")
        if os.path.exists(fp):
            p = Image.open(fp).convert("RGBA"); break
    if p is None:
        p = fallback()
    p = ImageOps.fit(p, (w * S, h * S), Image.LANCZOS)
    if circle:
        m = Image.new("L", p.size, 0); ImageDraw.Draw(m).ellipse([0, 0, p.width, p.height], fill=255)
        p.putalpha(m)
    else:
        m = Image.new("L", p.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, p.width, p.height], 18 * S, fill=255)
        p.putalpha(m)
    return p

def framed(c, im, x, y, prog, seed, circle=False):
    """photo with sketchy double border (like the reference)"""
    w, h = im.width / S, im.height / S
    paste(c, im, x, y, prog)
    if prog > 0.4:
        bp = (prog - 0.4) / 0.6
        if circle:
            wellipse(c, x, y, w / 2 + 4, h / 2 + 4, 5, INK, bp, seed)
            wellipse(c, x + 3, y + 2, w / 2 + 9, h / 2 + 7, 3, INK, bp, seed + 1)
        else:
            wrect(c, x - w / 2 - 4, y - h / 2 - 4, x + w / 2 + 4, y + h / 2 + 4, 20, 5, INK, bp, seed)
            wrect(c, x - w / 2 - 9, y - h / 2 - 2, x + w / 2 + 7, y + h / 2 + 8, 22, 3, INK, bp, seed + 1)

def portrait():
    img = Image.new("RGBA", (400, 400), (205, 200, 192, 255))
    d = ImageDraw.Draw(img)
    d.ellipse([130, 70, 270, 230], fill=(120, 100, 85))
    d.chord([60, 220, 340, 520], 180, 360, fill=(60, 60, 70))
    d.rectangle([168, 200, 232, 250], fill=(120, 100, 85))
    d.arc([150, 150, 250, 210], 20, 160, fill=(40, 30, 25), width=8)
    return img

# ---------------- stick figure ----------------
def figure(c, x, y, s=1.0, pose="walk", mood="smile", t=0.0, seed=0, prog=1.0):
    """doodle character: round head, black body, thin limbs. (x,y)=feet centre"""
    if prog <= 0:
        return
    k = ease_out(prog)
    y += (1 - k) * 60
    bob = 4 * math.sin(t * 6) if pose == "walk" else 3 * math.sin(t * 3)
    hip = (x, y - 150 * s + bob)
    sh = (x, y - 270 * s + bob)
    head = (x + 4 * s, y - 335 * s + bob)
    # legs
    if pose == "walk":
        sw = math.sin(t * 6) * 0.45
        legs = [(sw, 0), (-sw, 0)]
    elif pose == "sit":
        legs = None
    else:
        legs = [(0.18, 0), (-0.18, 0)]
    if legs:
        for i, (a, _) in enumerate(legs):
            foot = (hip[0] + math.sin(a) * 150 * s, hip[1] + math.cos(a) * 150 * s)
            knee = ((hip[0] + foot[0]) / 2 + 10 * s, (hip[1] + foot[1]) / 2)
            wline(c, [hip, knee, foot, (foot[0] + 28 * s, foot[1] + 2)], 5 * s + 1, INK, 1, seed + i)
    else:  # sitting hugging knees
        wline(c, [hip, (x + 80 * s, y - 210 * s), (x + 70 * s, y - 40 * s), (x + 110 * s, y - 36 * s)], 5 * s + 1, INK, 1, seed + 3)
    # torso (black, slightly irregular)
    tw = 46 * s
    body = [(sh[0] - tw, sh[1] + 10 * s), (sh[0] + tw, sh[1] + 10 * s), (hip[0] + tw * 1.05, hip[1]), (hip[0] - tw * 1.05, hip[1])]
    c.d.polygon([(px * S, py * S) for px, py in body], fill=INK)
    c.d.ellipse([(sh[0] - tw) * S, (sh[1] - 4 * s) * S, (sh[0] + tw) * S, (sh[1] + 40 * s) * S], fill=INK)
    # arms
    L = 120 * s
    w = t * 5
    sw = 0.3 * math.sin(t * 6)
    wv = 0.25 * math.sin(t * 7)
    hp = math.pi / 2
    arms = {
        "walk": [(hp + 0.35 + sw, hp + 0.1), (hp - 0.35 - sw, hp - 0.1)],
        "think": [(hp + 0.3, hp), (0, 0)],
        "confused": [(-2.3 + wv, -1.9 + wv), (-0.85 - wv, -1.25 - wv)],
        "cheer": [(hp + 0.3, hp + 0.1), (-0.9 + wv, -1.5 + wv)],
        "point": [(hp + 0.3, hp + 0.1), (-0.15, -0.3)],
        "sit": [(0, 0), (0, 0)],
    }[pose]
    for i, (u, l) in enumerate(arms):
        side = -1 if i == 0 else 1
        s0 = (sh[0] + side * tw * 0.85, sh[1] + 22 * s)
        elbow = (s0[0] + math.cos(u) * L * 0.55, s0[1] + math.sin(u) * L * 0.55)
        hand = (elbow[0] + math.cos(l) * L * 0.5, elbow[1] + math.sin(l) * L * 0.5)
        if pose == "think" and side > 0:
            hand = (head[0] + 10 * s, head[1] + 62 * s)
            elbow = (sh[0] + 70 * s, sh[1] + 70 * s)
        if pose == "sit":
            hand = (x + 90 * s, y - 120 * s + i * 20 * s)
            elbow = (s0[0] + 40 * s, s0[1] + 60 * s)
        wline(c, [s0, elbow, hand], 5 * s + 1, INK, 1, seed + 10 + i)
        hs = 9 * s
        c.d.ellipse([(hand[0] - hs) * S, (hand[1] - hs) * S, (hand[0] + hs) * S, (hand[1] + hs) * S], outline=INK, width=int(4 * s * S))
    # head
    hr = 62 * s
    c.d.ellipse([(head[0] - hr) * S, (head[1] - hr) * S, (head[0] + hr) * S, (head[1] + hr) * S], fill=CARD)
    wellipse(c, head[0], head[1], hr, hr * 1.02, 5 * s + 1, INK, 1, seed + 20)
    ex = head[0] + 4 * s
    blink = (int(t * 10) % 37) == 0
    for dx in (-20, 20):
        if blink:
            wline(c, [(ex + dx * s - 6 * s, head[1] - 8 * s), (ex + dx * s + 6 * s, head[1] - 8 * s)], 4 * s, INK, 1, seed)
        elif mood == "shock":
            wellipse(c, ex + dx * s, head[1] - 10 * s, 11 * s, 11 * s, 3 * s, INK, 1, seed + 30)
            c.d.ellipse([(ex + dx * s - 4 * s) * S, (head[1] - 14 * s) * S, (ex + dx * s + 4 * s) * S, (head[1] - 6 * s) * S], fill=INK)
        else:
            c.d.ellipse([(ex + dx * s - 6 * s) * S, (head[1] - 16 * s) * S, (ex + dx * s + 6 * s) * S, (head[1] - 2 * s) * S], fill=INK)
    my = head[1] + 22 * s
    if mood == "smile":
        wline(c, ell_pts(ex, my - 10 * s, 22 * s, 14 * s, 0.4, math.pi - 0.4, 10), 4 * s + 1, INK, 1, seed + 40)
    elif mood == "shock":
        wellipse(c, ex, my + 4 * s, 10 * s, 13 * s, 4 * s, INK, 1, seed + 41, fill=INK)
    elif mood == "sad":
        wline(c, ell_pts(ex, my + 12 * s, 18 * s, 10 * s, math.pi + 0.5, 2 * math.pi - 0.5, 10), 4 * s + 1, INK, 1, seed + 42)
    else:  # meh / thinking
        wline(c, [(ex - 16 * s, my + 2 * s), (ex + 16 * s, my - 4 * s)], 4 * s + 1, INK, 1, seed + 43)
    if mood in ("shock", "sad"):  # sweat drop
        dx, dy = head[0] + 48 * s, head[1] - 40 * s + 6 * math.sin(t * 4)
        c.d.polygon([((dx) * S, (dy - 14 * s) * S), ((dx - 7 * s) * S, (dy) * S), ((dx + 7 * s) * S, (dy) * S)], fill=(90, 160, 230))
        c.d.ellipse([(dx - 7 * s) * S, (dy - 6 * s) * S, (dx + 7 * s) * S, (dy + 8 * s) * S], fill=(90, 160, 230))

# ---------------- scenes ----------------
def at(t, t0, dur=0.5):
    return clamp((t - t0) / dur)

PH = {}
def ph(key, w, h, fb, circle=False):
    k = (key, w, h, circle)
    if k not in PH:
        PH[k] = photo(key, w, h, fb, circle)
    return PH[k]

def s_cover(c, t):  # 0 – em 1974
    figure(c, 230, 860, 1.25, "walk", "smile", t, 1, at(t, 0, .6))
    # giant plug carried by the figure
    if t > 0.3:
        p = ease_out(at(t, .3, .6))
        wline(c, [(110, 760), (360, 360)], 26, INK, p, 2)
        wline(c, [(110, 760), (360, 360)], 16, CARD, p, 2, amp=0)
        if p >= 1:
            for dx in (-16, 16):
                wline(c, [(372 + dx, 340), (395 + dx, 300)], 9, INK, 1, 3)
            c.d.ellipse([(345) * S, (338) * S, (385) * S, (378) * S], fill=OR)
    c.d.ellipse([110 * S, 840 * S, 380 * S, 890 * S], fill=(228, 225, 220))
    text(c, 470, 150, "O Brasil", MALIB, 92, INK, at(t, T("O"), .4))
    text(c, 470, 260, "teve um", MALIB, 92, INK, at(t, T("teve"), .4))
    text(c, 470, 370, "carro", MALIB, 92, INK, at(t, T("carro"), .3))
    text(c, 470, 480, "elétrico", MALIB, 92, INK, at(t, T("elétrico"), .4))
    squiggle(c, 480, 820, 600, 7, OR, at(t, T("elétrico") + .3, .5), 4)
    text(c, 470, 640, "nacional", MALIB, 92, INK, at(t, T("nacional"), .4))
    if t > T("50"):
        bullet(c, 490, 820); text(c, 520, 792, "50 anos antes", FRED, 42, INK, at(t, T("50"), .5))
    if t > T("quase"):
        bullet(c, 490, 900); text(c, 520, 872, "quase ninguém sabe", FRED, 42, INK, at(t, T("quase"), .6))
    if t > T("o", 3) if False else t > T("aconteceu"):
        text(c, 140, 1000, "o que aconteceu?", MALI, 64, OR, at(t, T("aconteceu"), .5))
        arrow(c, (600, 1060), (720, 960), -0.3, 5, OR, at(t, T("aconteceu") + .3, .5), 8)

def s_1974(c, t):
    pill(c, "O que aconteceu em 1974", at(t, T("1974") - .3, .6), 11)
    framed(c, ph("itaipu", 780, 470, lambda: R.photo_car(780, 470)), CW / 2, 420, at(t, T("1974"), .6), 12)
    text(c, 100, 720, "1974", MALIB, 120, OR, at(t, T("1974"), .3))
    text(c, 100, 870, "um engenheiro paulista", FRED, 46, INK, at(t, T("engenheiro"), .6))
    text(c, 100, 940, "apresentou ao país um carro", FRED, 46, INK, at(t, T("apresentou"), .8))
    text(c, 100, 1010, "movido só a bateria", FRED, 46, INK, at(t, T("movido"), .6))
    squiggle(c, 100, 560, 1085, 6, OR, at(t, T("bateria"), .5), 13)
    figure(c, 850, 1150, .7, "point", "smile", t, 14, at(t, T("apresentou"), .5))

def s_era(c, t):
    pill(c, "Por que isso importa", at(t, T("época") - .2, .6), 21)
    # staircase like "Developing our idea"
    p = at(t, T("época"), 1.2)
    steps = [(80, 760), (300, 760), (300, 620), (520, 620), (520, 480), (740, 480), (740, 340), (880, 340)]
    wline(c, steps, 5, INK, p, 22)
    labels = [("1974", "Itaipu", T("época") + .2, 190, 700), ("anos 90", "gasolina reina", T("abandonar"), 410, 560),
              ("hoje", "pauta obrigatória", T("eletrificação") if False else T("décadas") + .8, 630, 420)]
    for i, (a, b, tt, lx, ly) in enumerate(labels):
        q = at(t, tt, .5)
        if q > 0:
            wellipse(c, lx, ly, 22, 22, 4, INK, q, 23 + i)
            text(c, lx, ly - 14, str(i + 1), FREDB, 30, INK, q, "ma")
            text(c, lx - 90, ly - 120, a, MALIB, 46, OR if i == 2 else INK, q)
            text(c, lx - 90, ly - 70, b, FRED, 36, INK, q)
            arrow(c, (lx + 40, ly + 10), (lx + 100, ly - 50), .3, 5, OR, at(t, tt + .3, .4), 26 + i)
    figure(c, 230, 1150, .85, "confused", "shock", t, 27, at(t, T("ninguém"), .5))
    text(c, 430, 900, "ninguém cogitava", MALI, 50, INK, at(t, T("ninguém"), .6))
    text(c, 430, 965, "largar a gasolina", MALI, 50, INK, at(t, T("abandonar"), .6))
    text(c, 430, 1060, "salões do mundo todo", FRED, 40, GRAY, at(t, T("salão"), .6))

def s_price(c, t):
    wrect(c, 70, 160, CW - 70, 900, 20, 5, INK, at(t, T("mas") - .1, .7), 31)
    text(c, 130, 260, "“Chegar primeiro", MALIB, 76, INK, at(t, T("chegar"), .5))
    text(c, 130, 370, "custou um preço", MALIB, 76, INK, at(t, T("custou"), .5))
    text(c, 130, 480, "muito alto.”", MALIB, 76, INK, at(t, T("muito"), .4))
    squiggle(c, 130, 600, 580, 6, OR, at(t, T("alto"), .5), 32)
    text(c, 130, 650, "a história do Itaipu", FRED, 40, GRAY, at(t, T("alto"), .5))
    figure(c, 760, 1100, 1.0, "think", "meh", t, 33, at(t, T("mas"), .5))

def s_gurgel(c, t):
    text(c, 80, 120, "João Gurgel", MALIB, 78, INK, at(t, T("João"), .6))
    squiggle(c, 80, 520, 225, 7, OR, at(t, T("Gurgel") + .2, .5), 41)
    framed(c, ph("gurgel", 300, 300, portrait, True), 790, 200, at(t, T("Veja"), .6), 42, True)
    bullet(c, 100, 330); text(c, 130, 302, "já tinha nome no mercado", FRED, 40, INK, at(t, T("já"), .6))
    bullet(c, 100, 400); text(c, 130, 372, "bugues de fibra de vidro", FRED, 40, INK, at(t, T("bugues"), .6))
    framed(c, ph("bugue", 820, 440, lambda: R.photo_buggy(820, 440)), CW / 2, 720, at(t, T("Aqueles"), .6), 43)
    text(c, 80, 1000, "febre na elite", MALIB, 64, INK, at(t, T("febre"), .5))
    text(c, 80, 1080, "paulista dos anos 70", MALIB, 64, OR, at(t, T("paulista"), .5))
    arrow(c, (740, 1120), (820, 980), .3, 5, OR, at(t, T("anos", 2) if False else T("70"), .5), 44)

def s_market(c, t):
    pill(c, "Enquanto isso, o mercado...", at(t, T("Quando") - .2, .6), 51)
    figure(c, CW / 2, 820, 1.1, "confused", "shock", t, 52, at(t, T("Quando"), .5))
    text(c, 80, 260, "brigava por", FRED, 42, INK, at(t, T("brigava"), .5))
    text(c, 80, 310, "potência", MALIB, 60, INK, at(t, T("potência"), .4))
    arrow(c, (260, 400), (360, 470), -.3, 5, OR, at(t, T("potência") + .2, .4), 53)
    text(c, 680, 260, "e por", FRED, 42, INK, at(t, T("design"), .4))
    text(c, 680, 310, "design", MALIB, 60, INK, at(t, T("design"), .4))
    arrow(c, (700, 400), (600, 470), .3, 5, OR, at(t, T("design") + .2, .4), 54)
    text(c, 80, 900, "Gurgel apostou", FRED, 46, INK, at(t, T("apostou"), .5))
    text(c, 80, 960, "numa ideia", FRED, 46, INK, at(t, T("numa"), .4))
    text(c, 470, 910, "loucura?", MALIB, 88, OR, at(t, T("loucura"), .4))
    wellipse(c, 640, 965, 200, 85, 5, INK, at(t, T("loucura") + .3, .6), 55)
    text(c, 80, 1060, "para o Brasil daquele momento", FRED, 40, GRAY, at(t, T("daquele"), .6))

def s_itaipu(c, t):
    pill(c, "Itaipu E150", at(t, T("Foi") - .1, .6), 61)
    framed(c, ph("itaipu", 820, 440, lambda: R.photo_car(820, 440)), CW / 2, 400, at(t, T("Itaipu"), .6), 62)
    text(c, 80, 670, "batizado em homenagem", FRED, 48, INK, at(t, T("Batizado"), .7))
    text(c, 80, 730, "à usina de Itaipu", MALIB, 58, OR, at(t, T("usina"), .5))
    framed(c, ph("usina", 470, 300, lambda: R.photo_dam(470, 400)), 640, 990, at(t, T("usina"), .6), 63)
    text(c, 70, 900, "que ainda", FRED, 44, INK, at(t, T("ainda"), .4))
    text(c, 70, 955, "estava sendo", FRED, 44, INK, at(t, T("estava"), .4))
    text(c, 70, 1010, "construída", MALIB, 54, INK, at(t, T("construída"), .4))
    arrow(c, (250, 1100), (380, 1060), .3, 5, OR, at(t, T("construída") + .2, .4), 64)

def s_specs(c, t):
    pill(c, "O que ele tinha", at(t, T("motor") - .1, .6), 71)
    data = [(170, 620, 90, "4 cv", "motor", T("cavalos"), False),
            (450, 560, 135, "320 kg", "bateria", T("320"), False),
            (760, 470, 175, "120 km", "por carga", T("120"), True)]
    for i, (x, y, r, big, small, tt, hi) in enumerate(data):
        q = at(t, tt - .2, .5)
        if q <= 0:
            continue
        rr = r * (0.6 + 0.4 * back(q))
        if hi:
            c.d.ellipse([(x - rr) * S, (y - rr) * S, (x + rr) * S, (y + rr) * S], fill=OR)
        wellipse(c, x, y, rr, rr, 5, INK, q, 72 + i)
        fs = 40 if r < 100 else (52 if r < 150 else 64)
        text(c, x, y - fs * .7, big, FREDB, fs, INK, q, "ma")
        text(c, x, y + r + 20, small, FRED, 36, INK, q, "ma")
    arrow(c, (560, 300), (660, 330), -.3, 5, OR, at(t, T("autonomia"), .5), 75)
    text(c, 360, 250, "autonomia", MALI, 42, INK, at(t, T("autonomia"), .5))
    figure(c, 180, 1150, .8, "cheer", "smile", t, 76, at(t, T("motor"), .5))
    text(c, 380, 900, "e o projeto", MALIB, 60, INK, at(t, T("projeto"), .4))
    text(c, 380, 975, "não parava", MALIB, 60, INK, at(t, T("parava"), .4))
    text(c, 380, 1050, "no carro...", MALIB, 60, OR, at(t, T("carro", 5) if False else T("parava") + .4, .4))

def s_network(c, t):
    pill(c, "O plano de Gurgel", at(t, T("Gurgel", 2) - .1, .6), 81)
    figure(c, 200, 760, 1.0, "cheer", "smile", t, 82, at(t, T("Gurgel", 2), .5))
    items = [("rede pública", T("rede")), ("de recarga", T("recargas")), ("espalhada pela cidade", T("espalhadas"))]
    for i, (s, tt) in enumerate(items):
        y = 260 + i * 150
        q = at(t, tt, .5)
        arrow(c, (400, y + 30), (460, y + 30), 0, 5, OR, q, 83 + i)
        text(c, 490, y, s, FRED, 48 if i < 2 else 36, INK, q)
        wline(c, [(400, y + 100), (900, y + 100)], 4, INK, q, 86 + i)
    text(c, 120, 900, "em 1974.", MALIB, 92, INK, at(t, T("Uma"), .4) if False else at(t, T_UMA - .4, .5))
    squiggle(c, 120, 520, 1010, 7, OR, at(t, T_UMA, .5), 88)
    text(c, 120, 1060, "uma ideia que o Brasil só...", FRED, 44, GRAY, at(t, T_UMA, 1.0))
    arrow(c, (760, 1100), (860, 1020), .3, 5, OR, at(t, T_UMA + .6, .5), 89)

SCENES = [
    (0, s_cover), (T("em"), s_1974), (T("em", 3), s_era), (T("mas"), s_price), (T("Veja"), s_gurgel),
    (T("Quando"), s_market), (T("Foi"), s_itaipu), (T("motor"), s_specs), (T("Gurgel", 2), s_network),
]

# ---------------- frame ----------------
_card_mask = None
def card_layer(fn, t, boil):
    img = Image.new("RGBA", (CW * S, CH * S), CARD + (255,))
    c = Ctx(img, t, boil)
    fn(c, t)
    img = img.resize((CW, CH), Image.LANCZOS)
    global _card_mask
    if _card_mask is None:
        _card_mask = Image.new("L", (CW, CH), 0)
        ImageDraw.Draw(_card_mask).rounded_rectangle([0, 0, CW - 1, CH - 1], 34, fill=255)
    img.putalpha(_card_mask)
    return img

SHADOW = None
def shadow():
    global SHADOW
    if SHADOW is None:
        s = Image.new("RGBA", (CW + 120, CH + 120), (0, 0, 0, 0))
        ImageDraw.Draw(s).rounded_rectangle([60, 66, CW + 60, CH + 66], 34, fill=(0, 0, 0, 55))
        SHADOW = s.filter(ImageFilter.GaussianBlur(14))
    return SHADOW

CAP = None
def caption(frame, t):
    act = None
    for ch in R.chunks:
        if ch[0]["s"] - 0.05 <= t < ch[-1]["chunk_end"]:
            act = ch
    if not act:
        return
    f = ImageFont.truetype(f"fonts/{FREDB}.woff", 70)
    d = ImageDraw.Draw(frame)
    toks = [x["t"] for x in act]
    sp = d.textlength(" ", font=f)
    ws = [d.textlength(s, font=f) for s in toks]
    lines, cur, cw = [], [], 0
    for k, w in enumerate(ws):
        if cur and cw + sp + w > 920:
            lines.append(cur); cur, cw = [], 0
        cw += (sp if cur else 0) + w; cur.append(k)
    lines.append(cur)
    top = 1420
    for li, l in enumerate(lines):
        x = (W - sum(ws[k] for k in l) - sp * (len(l) - 1)) / 2
        y = top + li * 92
        for k in l:
            s0 = act[k]["s"]
            e0 = act[k + 1]["s"] if k + 1 < len(act) else act[k]["chunk_end"]
            on = s0 <= t < e0
            col = OR if on else (INK if s0 <= t else (165, 160, 152))
            d.text((x, y), toks[k], font=f, fill=col)
            if on:
                pts = [(x + ws[k] * j / 20, y + 92 + 5 * math.sin(j * 1.1 + t * 8)) for j in range(21)]
                d.line(pts, fill=OR, width=5, joint="curve")
            x += ws[k] + sp

def frame(fi):
    t = fi / FPS
    boil = fi // 4
    k = max(i for i, (t0, _) in enumerate(SCENES) if t0 <= t)
    t0, fn = SCENES[k]
    out = Image.new("RGBA", (W, H), BG + (255,))
    TR = 0.5
    p = ease_io((t - t0) / TR) if k > 0 else 1
    if p < 1:
        old = card_layer(SCENES[k - 1][1], t, boil)
        oy = CY - p * (CH + 200)
        out.alpha_composite(shadow(), (CX - 60, int(oy) - 60))
        out.alpha_composite(old, (CX, int(oy)))
    ny = CY + (1 - p) * (H - CY + 40)
    out.alpha_composite(shadow(), (CX - 60, int(ny) - 60))
    out.alpha_composite(card_layer(fn, t, boil), (CX, int(ny)))
    caption(out, t)
    return out.convert("RGB").tobytes()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for tt in map(float, sys.argv[2:]):
            Image.frombytes("RGB", (W, H), frame(int(tt * FPS))).save(f"dd_{tt:05.1f}.jpg", quality=85)
        sys.exit()
    nf = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", R.AUDIO,
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", "reels_gurgel_doodle.mp4"], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for i, b in enumerate(pool.imap(frame, range(nf), chunksize=8)):
            ff.stdin.write(b)
            if i % 300 == 0:
                print(i, flush=True)
    ff.stdin.close(); ff.wait()
