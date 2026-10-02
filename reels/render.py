import json, math, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps, ImageChops

W, H, FPS = 1080, 1920, 30
AUDIO = "/root/.claude/uploads/b143ab22-cb1b-5ce4-a67e-87e92c950f7a/7d2ecf93-reels-gurgel.mp3"
DUR = 60.34
INK = (24, 22, 20)
ORANGE = (232, 86, 42)
YELLOW = (244, 196, 48)
GREEN = (46, 125, 80)
BLUE = (52, 98, 168)
PAPER = (239, 235, 227)
CREAM = (250, 246, 236)

def F(name, size):
    return ImageFont.truetype(f"fonts/{name}.woff", size)
MARK = "permanent-marker-latin-400-normal"
TYPE = "special-elite-latin-400-normal"
HAND = "caveat-latin-700-normal"
ANTON = "anton-latin-400-normal"

# ---------- words ----------
words = json.load(open("fixed.json"))
fixes = {"bugs": "bugues"}
out = []
for i, x in enumerate(words):
    t = fixes.get(x["t"], x["t"])
    if t == "o" and i + 1 < len(words) and words[i + 1]["t"] == "país":
        t = "ao"
    if t == "fornecia":
        t = "tinha"
    if t == "com" and out and out[-1]["t"] == "tinha":
        out[-1]["e"] = x["e"]; continue
    out.append(dict(t=t, s=x["s"], e=x["e"]))
words = out

def T(word, n=1):
    c = 0
    for x in words:
        if x["t"].strip(",.:").lower() == word.lower():
            c += 1
            if c == n:
                return x["s"]
    raise KeyError(word)

# caption chunks: max 4 words, break on punctuation / pauses
chunks, cur = [], []
for i, x in enumerate(words):
    cur.append(x)
    nxt = words[i + 1] if i + 1 < len(words) else None
    brk = (len(cur) >= 4 or x["t"][-1] in ",.:" or nxt is None
           or nxt["s"] - x["e"] > 0.35 or nxt["t"][0].isupper() and len(cur) >= 2)
    if brk:
        chunks.append(cur); cur = []
for i, c in enumerate(chunks):
    c_end = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else DUR
    for x in c:
        x["chunk_end"] = c_end

# ---------- helpers ----------
rng = random.Random(7)

def shadow(img, off=(10, 14), blur=14, alpha=90):
    pad = 40
    base = Image.new("RGBA", (img.width + pad * 2, img.height + pad * 2), (0, 0, 0, 0))
    a = img.split()[3].point(lambda v: v * alpha // 255)
    sh = Image.new("RGBA", img.size, (40, 30, 20, 0)); sh.putalpha(a)
    base.alpha_composite(sh, (pad + off[0], pad + off[1]))
    base = base.filter(ImageFilter.GaussianBlur(blur))
    base.alpha_composite(img, (pad, pad))
    return base

def torn_mask(w, h, edges="tblr", amp=10, seed=0):
    r = random.Random(seed)
    pts = []
    def jag(a, b, n, side):
        res = []
        for k in range(n + 1):
            t = k / n
            x = a[0] + (b[0] - a[0]) * t; y = a[1] + (b[1] - a[1]) * t
            d = r.uniform(0, amp) if side in edges else 0
            if side == "t": y += d
            if side == "b": y -= d
            if side == "l": x += d
            if side == "r": x -= d
            res.append((x, y))
        return res
    pts += jag((0, 0), (w, 0), w // 14, "t")
    pts += jag((w, 0), (w, h), h // 14, "r")
    pts += jag((w, h), (0, h), w // 14, "b")
    pts += jag((0, h), (0, 0), h // 14, "l")
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).polygon(pts, fill=255)
    return m

def noise_layer(w, h, strength=18, seed=1):
    r = random.Random(seed)
    small = Image.new("L", (w // 3, h // 3))
    small.putdata([128 + r.randint(-strength, strength) for _ in range(small.width * small.height)])
    return small.resize((w, h))

def paper(w, h, color=CREAM, grid=False, lines=False, edges="tblr", seed=0):
    img = Image.new("RGBA", (w, h), color + (255,))
    d = ImageDraw.Draw(img)
    if grid:
        for x in range(0, w, 34): d.line([(x, 0), (x, h)], fill=(170, 190, 200, 120), width=2)
        for y in range(0, h, 34): d.line([(0, y), (w, y)], fill=(170, 190, 200, 120), width=2)
    if lines:
        for y in range(90, h, 62): d.line([(0, y), (w, y)], fill=(150, 175, 205, 160), width=2)
        d.line([(80, 0), (80, h)], fill=(220, 120, 120, 170), width=3)
    n = noise_layer(w, h, 10, seed)
    img = Image.composite(ImageChops.multiply(img.convert("RGB"), Image.merge("RGB", [n.point(lambda v: min(255, v + 127))] * 3)).convert("RGBA"), img, Image.new("L", (w, h), 255))
    img.putalpha(torn_mask(w, h, edges, 12, seed))
    return img

def tape(w=220, h=64, seed=0):
    img = Image.new("RGBA", (w, h), (232, 222, 196, 185))
    m = torn_mask(w, h, "lr", 10, seed)
    m = ImageChops.multiply(m, Image.new("L", (w, h), 200))
    img.putalpha(m)
    return img

def photoize(img, sepia=True):
    g = ImageOps.grayscale(img.convert("RGB"))
    g = ImageOps.autocontrast(g, cutoff=1)
    if sepia:
        g = ImageOps.colorize(g, (30, 26, 22), (238, 228, 210))
    else:
        g = g.convert("RGB")
    n = noise_layer(img.width, img.height, 26, 3).convert("RGB")
    g = ImageChops.overlay(g, n)
    # vignette
    v = Image.new("L", img.size, 0)
    ImageDraw.Draw(v).ellipse([-img.width * .2, -img.height * .2, img.width * 1.2, img.height * 1.2], fill=255)
    v = v.filter(ImageFilter.GaussianBlur(80))
    g = Image.composite(g, Image.new("RGB", img.size, (60, 50, 40)), v)
    return g.convert("RGBA")

def polaroid(content, caption=None, tape_on=True, seed=0):
    m = 26
    w, h = content.width + m * 2, content.height + m + 110
    img = Image.new("RGBA", (w, h), (252, 251, 247, 255))
    img.alpha_composite(content, (m, m))
    d = ImageDraw.Draw(img)
    if caption:
        f = F(HAND, 62)
        tw = d.textlength(caption, font=f)
        d.text(((w - tw) / 2, content.height + m + 18), caption, font=f, fill=INK)
    if tape_on:
        t = tape(240, 66, seed).rotate(rng.uniform(-8, 8), expand=True, resample=Image.BICUBIC)
        big = Image.new("RGBA", (w, h + 40), (0, 0, 0, 0))
        big.alpha_composite(img, (0, 40))
        big.alpha_composite(t, ((w - t.width) // 2, 0))
        img = big
    return img

def text_img(text, font, color=INK, pad=0, bg=None, stroke=0):
    d0 = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    lines = text.split("\n")
    bbs = [d0.textbbox((0, 0), l, font=font, stroke_width=stroke) for l in lines]
    lh = max(b[3] for b in bbs) + 8
    w = max(b[2] for b in bbs) + pad * 2
    h = lh * len(lines) + pad * 2
    img = Image.new("RGBA", (int(w), int(h)), bg + (255,) if bg else (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lines):
        d.text((pad, pad + i * lh), l, font=font, fill=color, stroke_width=stroke, stroke_fill=color)
    return img

def label(text, font, fg=INK, bg=CREAM, pad=22, seed=0):
    t = text_img(text, font, fg)
    p = paper(t.width + pad * 2, t.height + pad * 2, bg, edges="lr", seed=seed)
    p.alpha_composite(t, (pad, pad - 6))
    return p

def stamp(text, size=170, color=ORANGE):
    f = F(ANTON, size)
    t = text_img(text, f, color)
    w, h = t.width + 80, t.height + 60
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([6, 6, w - 6, h - 6], 18, outline=color + (255,), width=12)
    img.alpha_composite(t, (40, 18))
    # worn ink
    n = noise_layer(w, h, 90, 9).point(lambda v: 255 if v > 110 else 0)
    a = ImageChops.multiply(img.split()[3], n)
    img.putalpha(a)
    return img

# ---------- illustrations (drawn on a scene then turned into "old photos") ----------
def scene_canvas(w, h, sky=(200, 205, 210), ground=(150, 140, 120), horizon=0.62):
    img = Image.new("RGBA", (w, h), sky + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([0, int(h * horizon), w, h], fill=ground)
    return img, d

def draw_itaipu(d, x, y, s, fill=(235, 232, 225)):
    P = lambda pts: [(x + px * s, y + py * s) for px, py in pts]
    body = P([(0, 60), (4, 34), (70, 8), (150, 2), (190, 22), (196, 60), (0, 60)])
    d.polygon(body, fill=fill, outline=INK)
    d.line(body, fill=INK, width=max(3, int(s * 2.4)), joint="curve")
    d.polygon(P([(78, 12), (146, 6), (176, 24), (88, 30)]), fill=(70, 80, 90))
    d.line(P([(8, 44), (190, 44)]), fill=INK, width=max(2, int(s * 1.4)))
    for cx in (40, 156):
        r = 20 * s
        d.ellipse([x + cx * s - r, y + 60 * s - r, x + cx * s + r, y + 60 * s + r], fill=(30, 30, 30))
        r2 = 8 * s
        d.ellipse([x + cx * s - r2, y + 60 * s - r2, x + cx * s + r2, y + 60 * s + r2], fill=(170, 170, 170))

def draw_buggy(d, x, y, s):
    P = lambda pts: [(x + px * s, y + py * s) for px, py in pts]
    d.polygon(P([(10, 50), (30, 30), (150, 28), (190, 46), (180, 62), (20, 64)]), fill=(225, 120, 70), outline=INK)
    d.line(P([(70, 30), (80, -10), (120, -10), (128, 28)]), fill=INK, width=int(5 * s))
    d.line(P([(40, 30), (60, 8)]), fill=INK, width=int(4 * s))
    for cx, r in ((42, 26), (160, 30)):
        d.ellipse([x + (cx - r) * s, y + (64 - r) * s, x + (cx + r) * s, y + (64 + r) * s], fill=(25, 25, 25))
        d.ellipse([x + (cx - 9) * s, y + 55 * s, x + (cx + 9) * s, y + 73 * s], fill=(160, 160, 160))

def photo_car(w=640, h=480):
    img, d = scene_canvas(w, h, (205, 210, 215), (120, 115, 105), 0.66)
    for i in range(6):  # buildings
        bx = i * 120 - 20; bh = 120 + (i * 53) % 140
        d.rectangle([bx, h * 0.66 - bh, bx + 100, h * 0.66], fill=(165 + i * 5, 165, 160))
    draw_itaipu(d, 80, 210, 2.5)
    return photoize(img)

def photo_buggy(w=640, h=460):
    img, d = scene_canvas(w, h, (215, 220, 225), (230, 215, 180), 0.58)
    d.rectangle([0, int(h * .5), w, int(h * .58)], fill=(110, 130, 150))  # sea
    d.ellipse([w - 170, 40, w - 70, 140], fill=(250, 250, 240))
    for px in (60, 520):
        d.line([(px, h * .6), (px + 20, 90)], fill=(80, 60, 40), width=12)
        for a in range(5):
            ang = a * 1.25
            d.line([(px + 20, 90), (px + 20 + 90 * math.cos(ang), 90 + 50 * math.sin(ang) - 10)], fill=(60, 90, 50), width=14)
    draw_buggy(d, 120, 250, 2.2)
    return photoize(img)

def photo_dam(w=640, h=460):
    img, d = scene_canvas(w, h, (210, 215, 220), (120, 130, 110), 0.8)
    d.polygon([(0, 150), (w, 120), (w, 200), (0, 230)], fill=(110, 130, 150))
    d.polygon([(0, 210), (w, 180), (w, 330), (0, 370)], fill=(185, 182, 175), outline=INK)
    for k in range(14):
        xx = 20 + k * 46
        d.line([(xx, 205 - k * 2.2), (xx, 360 - k * 3)], fill=(140, 138, 130), width=6)
    d.rectangle([0, 370, w, h], fill=(100, 120, 140))
    # cranes = "under construction"
    for cx in (140, 470):
        d.line([(cx, 210), (cx, 40)], fill=INK, width=8)
        d.line([(cx - 60, 50), (cx + 140, 50)], fill=INK, width=8)
        d.line([(cx + 120, 50), (cx + 120, 110)], fill=INK, width=3)
    return photoize(img)

def photo_pump(w=520, h=520):
    img, d = scene_canvas(w, h, (210, 212, 214), (140, 135, 125), 0.82)
    d.rounded_rectangle([150, 110, 340, 430], 20, fill=(200, 60, 50), outline=INK, width=8)
    d.rectangle([180, 150, 310, 240], fill=(240, 240, 230), outline=INK, width=6)
    d.text((196, 166), "GAS", font=F(ANTON, 54), fill=INK)
    d.line([(340, 200), (400, 210), (410, 330), (380, 380)], fill=INK, width=12)
    d.rectangle([360, 370, 400, 420], fill=INK)
    d.rectangle([130, 430, 360, 460], fill=(80, 80, 80))
    return photoize(img)

def icon_battery(w=340, h=200, text="320 kg"):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 20, w - 40, h - 10], 22, fill=GREEN, outline=INK, width=9)
    d.rectangle([w - 40, h / 2 - 30, w - 12, h / 2 + 30], fill=INK)
    d.polygon([(110, 40), (70, 110), (115, 110), (95, 170), (160, 90), (115, 90), (140, 40)], fill=YELLOW, outline=INK)
    if text:
        d.text((170, 70), text, font=F(MARK, 52), fill=CREAM)
    return img

def icon_tag(w=420, h=240, text="$$$"):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon([(0, h / 2), (80, 6), (w - 6, 6), (w - 6, h - 6), (80, h - 6)], fill=YELLOW, outline=INK)
    d.line([(0, h / 2), (80, 6), (w - 6, 6), (w - 6, h - 6), (80, h - 6), (0, h / 2)], fill=INK, width=8)
    d.ellipse([50, h / 2 - 18, 86, h / 2 + 18], fill=PAPER, outline=INK, width=6)
    d.text((120, 40), text, font=F(ANTON, 130), fill=INK)
    return img

def map_paper(w=900, h=760):
    img = paper(w, h, (236, 232, 220), seed=5)
    d = ImageDraw.Draw(img)
    r = random.Random(3)
    for k in range(9):
        y = 40 + k * 85 + r.randint(-10, 10)
        d.line([(20, y), (w - 20, y + r.randint(-40, 40))], fill=(200, 190, 170), width=14)
    for k in range(8):
        x = 40 + k * 115 + r.randint(-10, 10)
        d.line([(x, 20), (x + r.randint(-40, 40), h - 20)], fill=(200, 190, 170), width=14)
    d.polygon([(520, 380), (700, 340), (760, 520), (560, 560)], fill=(170, 200, 160))
    d.ellipse([140, 470, 300, 600], fill=(160, 190, 215))
    return img

def pin(size=110, color=ORANGE):
    img = Image.new("RGBA", (size, int(size * 1.4)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size
    d.ellipse([6, 6, s - 6, s - 6], fill=color, outline=INK, width=6)
    d.polygon([(s * .18, s * .7), (s / 2, s * 1.36), (s * .82, s * .7)], fill=color, outline=INK)
    d.ellipse([6, 6, s - 6, s - 6], fill=color)
    d.line([(s * .18, s * .72), (s / 2, s * 1.36), (s * .82, s * .72)], fill=INK, width=6)
    d.polygon([(s * .52, s * .2), (s * .34, s * .52), (s * .5, s * .52), (s * .44, s * .8), (s * .66, s * .44), (s * .5, s * .44), (s * .58, s * .2)], fill=YELLOW)
    return img

# ---------- sticker / stroke system ----------
class Sticker:
    def __init__(self, img, x, y, t0, rot=0.0, t1=None, pop=0.28, shadow_on=True, slide=None):
        self.img = shadow(img) if shadow_on else img
        self.x, self.y, self.t0, self.t1, self.rot, self.pop, self.slide = x, y, t0, t1, rot, pop, slide

class Stroke:
    """hand drawn line that draws itself"""
    def __init__(self, pts, t0, dur=0.45, color=ORANGE, width=12, head=False, t1=None):
        self.pts, self.t0, self.dur, self.color, self.width, self.head, self.t1 = pts, t0, dur, color, width, head, t1

def curve(p0, p1, bend=0.25, n=40):
    (x0, y0), (x1, y1) = p0, p1
    mx, my = (x0 + x1) / 2, (y0 + y1) / 2
    nx, ny = -(y1 - y0) * bend, (x1 - x0) * bend
    cx, cy = mx + nx, my + ny
    return [((1 - t) ** 2 * x0 + 2 * (1 - t) * t * cx + t * t * x1,
             (1 - t) ** 2 * y0 + 2 * (1 - t) * t * cy + t * t * y1) for t in [i / n for i in range(n + 1)]]

def circle_pts(cx, cy, rx, ry, n=60):
    return [(cx + rx * math.cos(a) * (1 + 0.04 * math.sin(a * 3)), cy + ry * math.sin(a))
            for a in [-1.9 + i / n * 2 * math.pi * 1.1 for i in range(n + 1)]]

def ease_back(t):
    c1, c3 = 1.70158, 2.70158
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

# ---------- background ----------
def make_bg(seed):
    r = random.Random(seed)
    bg = Image.new("RGBA", (W, H), PAPER + (255,))
    n = noise_layer(W, H, 8, seed).convert("RGB")
    bg = ImageChops.overlay(bg.convert("RGB"), n).convert("RGBA")
    g = paper(760, 900, (226, 220, 205), grid=True, seed=seed + 1).rotate(r.uniform(-6, 6), expand=True, resample=Image.BICUBIC)
    bg.alpha_composite(shadow(g, blur=10, alpha=50), (r.randint(-260, -120), r.randint(260, 600)))
    l = paper(560, 700, (233, 228, 214), lines=True, seed=seed + 2).rotate(r.uniform(-8, 8), expand=True, resample=Image.BICUBIC)
    bg.alpha_composite(shadow(l, blur=10, alpha=50), (r.randint(620, 760), r.randint(900, 1250)))
    # faded typewriter scraps (like refs)
    f = F(TYPE, 34)
    d = ImageDraw.Draw(bg)
    for k in range(3):
        d.text((r.randint(30, 700), r.randint(80, 1800)), r.choice(["anos 70 · são paulo", "nº 0150 — protótipo", "km/h  ·  volts  ·  amperes", "arquivo pessoal"]), font=f, fill=(150, 140, 125))
    return bg

# ---------- scenes ----------
SC = []
def scene(t0, t1, items, bg_seed):
    SC.append(dict(t0=t0, t1=t1, items=items, bg=make_bg(bg_seed)))

TM = F(MARK, 112)
TM2 = F(MARK, 84)
HD = F(HAND, 74)
HDs = F(HAND, 60)

# S1 hook
t_end1 = T("em")  # "em 1974"
car = polaroid(photo_car(560, 400), "1974 · brasil", seed=1)
scene(0, t_end1, [
    Sticker(text_img("O BRASIL TEVE\nUM CARRO", TM, INK), 70, 120, T("O"), rot=-2),
    Sticker(label("ELÉTRICO ⚡".replace("⚡", "!"), F(ANTON, 110), INK, YELLOW, seed=3), 80, 380, T("elétrico"), rot=3),
    Sticker(car, 340, 540, T("carro"), rot=-4),
    Sticker(label("50 ANOS\nANTES", F(ANTON, 120), CREAM, ORANGE, seed=4), 640, 1000, T("50"), rot=6),
    Stroke(curve((660, 1000), (560, 900), 0.3), T("antes"), color=INK, width=9, head=True),
    Sticker(text_img("& quase ninguém\nsabe disso...", HD, INK), 80, 1110, T("quase"), rot=-3, shadow_on=False),
], 11)

# S2 1974
t_end2 = T("em", 3)  # "em uma época"
scene(t_end1, t_end2, [
    Sticker(stamp("1974", 230), 160, 140, T("1974"), rot=-7),
    Sticker(label("um engenheiro\npaulista...", F(HAND, 84), INK, CREAM, seed=6), 520, 520, T("engenheiro"), rot=4),
    Sticker(polaroid(photo_car(560, 420), "o protótipo", seed=2), 90, 760, T("apresentou"), rot=3),
    Sticker(icon_battery(420, 240, "100%"), 600, 1030, T("bateria"), rot=-6),
    Stroke(curve((540, 860), (700, 1000), -0.3), T("movido"), color=ORANGE, width=11, head=True),
    Sticker(text_img("SÓ A BATERIA", TM2, INK), 80, 1290, T("só"), rot=-2, shadow_on=False),
], 21)

# S3 gasoline era
t_end3 = T("mas")
scene(t_end2, t_end3, [
    Sticker(text_img("NUMA ÉPOCA\nMOVIDA A\nGASOLINA", TM, INK), 70, 110, T("época"), rot=-2),
    Sticker(polaroid(photo_pump(400, 400), "posto, 1974", seed=3), 640, 470, T("ninguém"), rot=6),
    Stroke([(690, 570), (1030, 930)], T("abandonar"), 0.3, (200, 40, 30), 16),
    Stroke([(1030, 570), (690, 930)], T("abandonar") + 0.3, 0.3, (200, 40, 30), 16),
    Sticker(label("décadas antes da\neletrificação virar pauta", F(HAND, 70), INK, CREAM, seed=7), 70, 1000, T("décadas"), rot=-3),
    Sticker(label("1974", F(ANTON, 90), CREAM, INK, seed=8), 90, 1230, T("eletrificação"), rot=-4),
    Stroke(curve((330, 1300), (700, 1300), -0.12), T("eletrificação") + .2, 0.5, ORANGE, 11, head=True),
    Sticker(label("2020", F(ANTON, 90), INK, YELLOW, seed=9), 720, 1220, T("salão"), rot=5),
], 31)

# S4 price
t_end4 = T("Veja")
scene(t_end3, t_end4, [
    Sticker(text_img("CHEGAR\nPRIMEIRO...", F(MARK, 130), INK), 80, 170, T("chegar"), rot=-3),
    Stroke(curve((90, 520), (720, 500), 0.05), T("primeiro"), 0.4, ORANGE, 14),
    Sticker(icon_tag(560, 300, "$$$"), 300, 700, T("custou"), rot=-10),
    Sticker(label("custou MUITO caro", F(MARK, 80), CREAM, ORANGE, seed=10), 160, 1100, T("muito"), rot=3),
], 41)

# S5 about Gurgel (ID card like the reference)
t_end5 = T("Quando")
card = paper(940, 560, CREAM, seed=12)
scene(t_end4, t_end5, [
    Sticker(text_img("QUEM ERA ELE:", F(MARK, 120), INK), 70, 110, T("Veja"), rot=-2),
    Sticker(card, 70, 300, T("João"), rot=1),
    Sticker(text_img("Nome: João", HD, INK), 120, 340, T("João"), shadow_on=False, pop=0.15),
    Sticker(text_img("Sobrenome: Gurgel", HD, INK), 120, 430, T("Gurgel"), shadow_on=False, pop=0.15),
    Sticker(text_img("Fama: bugues de\nfibra de vidro", HD, INK), 120, 520, T("construindo"), shadow_on=False, pop=0.15),
    Sticker(text_img("Público: elite\npaulista, anos 70", HD, INK), 120, 700, T("elite"), shadow_on=False, pop=0.15),
    Sticker(polaroid(photo_buggy(480, 320), "bugue de praia", seed=4), 470, 900, T("Aqueles"), rot=5),
    Sticker(text_img("eu :)", F(MARK, 70), INK), 110, 1010, T("carrinhos"), rot=-8, shadow_on=False),
    Stroke(curve((200, 1110), (470, 1130), -0.3), T("carrinhos") + .2, 0.4, INK, 8, head=True),
    Sticker(label("uma febre!", F(MARK, 76), CREAM, ORANGE, seed=13), 80, 1220, T("febre"), rot=-5),
], 51)

# S6 crazy idea
t_end6 = T("Foi")
scene(t_end5, t_end6, [
    Sticker(label("o mercado:\npotência + design", F(HAND, 80), INK, CREAM, seed=14), 80, 160, T("mercado"), rot=-4),
    Sticker(text_img("VS", F(ANTON, 160), ORANGE), 440, 560, T("ele"), rot=0, shadow_on=False),
    Sticker(label("gurgel:\num carro elétrico", F(HAND, 80), CREAM, INK, seed=15), 420, 800, T("apostou"), rot=4),
    Sticker(text_img("LOUCURA?", F(MARK, 150), INK), 150, 1130, T("loucura"), rot=-4, shadow_on=False),
    Stroke(circle_pts(500, 1220, 430, 130), T("loucura") + .15, 0.55, ORANGE, 12),
], 61)

# S7 Itaipu E150
t_end7 = T("O", 2) if False else T("motor")
scene(t_end6, t_end7, [
    Sticker(text_img("ITAIPU", F(ANTON, 230), INK), 70, 90, T("Itaipu"), rot=-2),
    Sticker(label("E150", F(ANTON, 150), CREAM, ORANGE, seed=16), 690, 170, T("E150"), rot=8),
    Sticker(polaroid(photo_car(520, 360), "itaipu e150", seed=5), 60, 420, T("E150") + .1, rot=-4),
    Sticker(polaroid(photo_dam(460, 400), "usina de itaipu", seed=6), 520, 800, T("homenagem"), rot=5),
    Sticker(label("ainda em construção!", F(HAND, 66), INK, YELLOW, seed=17), 70, 1250, T("construída"), rot=-3),
    Stroke(curve((560, 1250), (600, 1220), 0.3), T("construída") + .2, 0.4, INK, 8, head=True),
], 71)

# S8 specs
t_end8 = T("Gurgel", 2)
sheet = paper(900, 760, CREAM, lines=True, seed=18)
scene(t_end7, t_end8, [
    Sticker(text_img("FICHA TÉCNICA:", F(MARK, 112), INK), 70, 110, T("motor"), rot=-2),
    Sticker(sheet, 90, 290, T("motor"), rot=1),
    Sticker(text_img("motor: ~4 cv", F(HAND, 96), INK), 200, 370, T("cavalos"), shadow_on=False, pop=.15),
    Sticker(text_img("bateria: 320 kg", F(HAND, 96), INK), 200, 560, T("320"), shadow_on=False, pop=.15),
    Stroke(circle_pts(560, 610, 150, 60), T("quilos") + .1, 0.45, ORANGE, 9),
    Sticker(text_img("autonomia: 120 km\npor carga", F(HAND, 96), INK), 200, 750, T("120"), shadow_on=False, pop=.15),
    Sticker(icon_battery(380, 220, "320kg"), 630, 960, T("bateria", 2), rot=-8),
    Sticker(label("e não parava por aí...", F(MARK, 64), CREAM, INK, seed=19), 80, 1180, T("projeto"), rot=-3),
], 81)

# S9 charging network
mp = map_paper()
pins = [(250, 490), (520, 430), (760, 590), (380, 710), (640, 830), (300, 950), (820, 970)]
p_times = [T("rede"), T("pública"), T("pública") + .3, T("recargas"), T("espalhadas"), T("espalhadas") + .3, T("cidade")]
items9 = [
    Sticker(text_img("REDE PÚBLICA\nDE RECARGA", F(MARK, 112), INK), 70, 90, T("Gurgel", 2), rot=-2),
    Sticker(mp, 70, 400, T("imaginava"), rot=2),
]
for (px, py), tp in zip(pins, p_times):
    items9.append(Sticker(pin(110), px, py, tp, rot=0))
items9.append(Sticker(label("em 1974!", F(MARK, 80), CREAM, ORANGE, seed=20), 620, 1210, T("Uma"), rot=6))
items9.append(Sticker(text_img("continua...", HD, INK), 120, 1250, T("Brasil", 3) if False else T("só", 2), rot=-3, shadow_on=False))
scene(t_end8, DUR + 1, items9, 91)

# ---------- caption ----------
CAPF = F(MARK, 74)
def draw_caption(frame, t):
    act = None
    for i, c in enumerate(chunks):
        if c[0]["s"] - 0.05 <= t < c[-1]["chunk_end"]:
            act = c
    if not act:
        return
    toks = [x["t"].upper() for x in act]
    d0 = ImageDraw.Draw(frame)
    space = d0.textlength(" ", font=CAPF)
    widths = [d0.textlength(s, font=CAPF) for s in toks]
    # wrap into max 2 lines of 880px
    lines, cur, cw = [], [], 0
    for k, wdt in enumerate(widths):
        if cur and cw + space + wdt > 880:
            lines.append(cur); cur, cw = [], 0
        cw += (space if cur else 0) + wdt; cur.append(k)
    lines.append(cur)
    lh = 96
    top = 1500 - lh * len(lines) // 2
    maxw = max(sum(widths[k] for k in l) + space * (len(l) - 1) for l in lines)
    strip = paper(int(maxw + 70), lh * len(lines) + 40, CREAM, edges="lr", seed=len(act[0]["t"]))
    frame.alpha_composite(shadow(strip, (6, 8), 8, 70), (int((W - strip.width) / 2) - 40, top - 20 - 40))
    for li, l in enumerate(lines):
        lw = sum(widths[k] for k in l) + space * (len(l) - 1)
        x = (W - lw) / 2
        for k in l:
            x0 = act[k]
            on = x0["s"] <= t
            col = ORANGE if (x0["s"] <= t < (act[k + 1]["s"] if k + 1 < len(act) else x0["chunk_end"])) else (INK if on else (150, 145, 135))
            d0.text((x, top + li * lh), toks[k], font=CAPF, fill=col)
            x += widths[k] + space

# ---------- render ----------
def render_stroke(frame, s, t):
    if t < s.t0:
        return
    p = min(1, (t - s.t0) / s.dur)
    n = max(2, int(len(s.pts) * p))
    pts = s.pts[:n]
    d = ImageDraw.Draw(frame)
    d.line(pts, fill=s.color, width=s.width, joint="curve")
    for q in (pts[0], pts[-1]):
        r = s.width / 2
        d.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=s.color)
    if s.head and p >= 1:
        (x0, y0), (x1, y1) = s.pts[-4], s.pts[-1]
        a = math.atan2(y1 - y0, x1 - x0)
        for da in (2.6, -2.6):
            d.line([(x1, y1), (x1 + 46 * math.cos(a + da), y1 + 46 * math.sin(a + da))], fill=s.color, width=s.width)

def render(t, f):
    sc = [s for s in SC if s["t0"] <= t < s["t1"]][-1]
    frame = sc["bg"].copy()
    step = f // 3  # stop-motion jitter at 10fps
    for idx, it in enumerate(sc["items"]):
        if isinstance(it, Stroke):
            render_stroke(frame, it, t); continue
        if t < it.t0:
            continue
        r = random.Random(step * 97 + idx)
        p = min(1, (t - it.t0) / it.pop)
        sc_ = 0.55 + 0.45 * ease_back(p) if p < 1 else 1
        rot = it.rot + r.uniform(-0.6, 0.6)
        img = it.img
        if sc_ != 1:
            img = img.resize((max(1, int(img.width * sc_)), max(1, int(img.height * sc_))), Image.BILINEAR)
        img = img.rotate(rot, expand=True, resample=Image.BILINEAR)
        cx = it.x + it.img.width / 2 - 40 + r.uniform(-2, 2)
        cy = it.y + it.img.height / 2 - 40 + r.uniform(-2, 2)
        a = min(1, p * 3)
        if a < 1:
            img = img.copy(); img.putalpha(img.split()[3].point(lambda v: int(v * a)))
        frame.alpha_composite(img, (int(cx - img.width / 2), int(cy - img.height / 2)))
    # scene-change flash of paper
    if t - sc["t0"] < 0.08 and sc["t0"] > 0:
        frame = Image.blend(frame, Image.new("RGBA", (W, H), (255, 252, 245, 255)), 0.5)
    draw_caption(frame, t)
    return frame.convert("RGB")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for tt in map(float, sys.argv[2:]):
            render(tt, int(tt * FPS)).save(f"prev_{tt:05.1f}.jpg", quality=80)
        sys.exit()
    nf = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", AUDIO,
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", "reels_gurgel.mp4"], stdin=subprocess.PIPE)
    for f in range(nf):
        ff.stdin.write(render(f / FPS, f).tobytes())
        if f % 150 == 0:
            print(f, flush=True)
    ff.stdin.close(); ff.wait()
