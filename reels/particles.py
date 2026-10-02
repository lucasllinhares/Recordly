import math, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import render as R  # reuse words, chunks, T(), fonts, drawing helpers

W, H, FPS, DUR = 1080, 1920, 30, R.DUR
N = 15000
CY = 820  # vertical centre of the illustration area
rng = np.random.default_rng(3)
F = R.F

# ---------- shape builders (white on black masks) ----------
def canvas():
    m = Image.new("L", (W, H), 0)
    return m, ImageDraw.Draw(m)

def txt(text, size, font=R.ANTON, y=CY, m=None, d=None):
    if m is None:
        m, d = canvas()
    f = F(font, size)
    lines = text.split("\n")
    lh = size * 1.05
    y0 = y - lh * len(lines) / 2
    for i, l in enumerate(lines):
        w = d.textlength(l, font=f)
        d.text(((W - w) / 2, y0 + i * lh), l, font=f, fill=255)
    return m

def car(label=None):
    m, d = canvas()
    s = 4.2; x = (W - 196 * s) / 2; y = CY - 60 * s
    P = lambda pts: [(x + a * s, y + b * s) for a, b in pts]
    body = P([(0, 60), (4, 34), (70, 8), (150, 2), (190, 22), (196, 60)])
    d.line(body + [body[0]], fill=255, width=14, joint="curve")
    d.polygon(P([(78, 12), (146, 6), (176, 24), (88, 30)]), fill=150)
    d.line(P([(8, 44), (190, 44)]), fill=255, width=8)
    for cx in (40, 156):
        for r, wd in ((22, 14), (8, 0)):
            box = [x + cx * s - r * s, y + 60 * s - r * s, x + cx * s + r * s, y + 60 * s + r * s]
            d.ellipse(box, outline=255, width=wd) if wd else d.ellipse(box, fill=255)
    if label:
        txt(label, 120, y=CY + 330, m=m, d=d)
    return m

def bolt(m, d, cx, cy, s):
    pts = [(.1, -1), (-.55, .1), (-.05, .1), (-.2, 1), (.55, -.15), (.05, -.15), (.3, -1)]
    d.polygon([(cx + a * s, cy + b * s) for a, b in pts], fill=255)

def battery(text=None):
    m, d = canvas()
    d.rounded_rectangle([200, CY - 190, 820, CY + 190], 50, outline=255, width=22)
    d.rectangle([820, CY - 70, 880, CY + 70], fill=255)
    bolt(m, d, 510, CY, 150)
    if text:
        txt(text, 130, y=CY + 330, m=m, d=d)
    return m

def person():
    m, d = canvas()
    d.ellipse([400, CY - 380, 680, CY - 100], outline=255, width=18)
    d.chord([250, CY - 40, 830, CY + 520], 180, 360, outline=255, width=18)
    d.line([(250, CY + 240), (830, CY + 240)], fill=255, width=18)
    return m

def pump():
    m, d = canvas()
    d.rounded_rectangle([330, CY - 340, 650, CY + 300], 40, outline=255, width=20)
    d.rectangle([380, CY - 270, 600, CY - 110], outline=255, width=14)
    d.line([(650, CY - 200), (760, CY - 180), (780, CY + 60), (720, CY + 140)], fill=255, width=18)
    d.rectangle([690, CY + 120, 740, CY + 200], fill=255)
    d.rectangle([290, CY + 300, 690, CY + 340], fill=255)
    # cross
    d.line([(220, CY - 420), (860, CY + 420)], fill=255, width=26)
    d.line([(860, CY - 420), (220, CY + 420)], fill=255, width=26)
    return m

def timeline():
    m, d = canvas()
    txt("1974", 150, y=CY - 160, m=m, d=d)
    d.line([(540, CY - 40), (540, CY + 200)], fill=255, width=14)
    d.polygon([(500, CY + 190), (580, CY + 190), (540, CY + 250)], fill=255)
    txt("2020", 150, y=CY + 380, m=m, d=d)
    return m

def tag():
    m, d = canvas()
    w, h = 720, 400; x, y = (W - w) / 2, CY - h / 2
    pts = [(x, y + h / 2), (x + 140, y), (x + w, y), (x + w, y + h), (x + 140, y + h), (x, y + h / 2)]
    d.line(pts, fill=255, width=20, joint="curve")
    d.ellipse([x + 70, y + h / 2 - 30, x + 130, y + h / 2 + 30], outline=255, width=12)
    f = F(R.ANTON, 230)
    d.text((x + 230, y + 50), "$$$", font=f, fill=255)
    return m

def buggy():
    m, d = canvas()
    s = 4.2; x = (W - 200 * s) / 2; y = CY - 50 * s
    P = lambda pts: [(x + a * s, y + b * s) for a, b in pts]
    d.line(P([(10, 50), (30, 30), (150, 28), (190, 46), (180, 62), (20, 64), (10, 50)]), fill=255, width=14, joint="curve")
    d.line(P([(70, 30), (80, -14), (120, -14), (128, 28)]), fill=255, width=14)
    for cx, r in ((42, 26), (160, 30)):
        d.ellipse([x + (cx - r) * s, y + (64 - r) * s, x + (cx + r) * s, y + (64 + r) * s], outline=255, width=16)
        d.ellipse([x + (cx - 7) * s, y + 57 * s, x + (cx + 7) * s, y + 71 * s], fill=255)
    txt("FIBRA DE VIDRO", 100, y=CY + 420, m=m, d=d)
    return m

def beach():
    m, d = canvas()
    d.ellipse([640, CY - 420, 860, CY - 200], outline=255, width=16)
    for k in range(12):
        a = k * math.pi / 6
        d.line([(750 + 140 * math.cos(a), CY - 310 + 140 * math.sin(a)), (750 + 190 * math.cos(a), CY - 310 + 190 * math.sin(a))], fill=255, width=10)
    d.line([(300, CY + 300), (340, CY - 250)], fill=255, width=18)
    for a in np.linspace(0.3, 2.9, 5):
        pts = [(340 + 220 * t * math.cos(a + math.pi), CY - 250 - 220 * t * math.sin(a) + 120 * t * t) for t in np.linspace(0, 1, 12)]
        d.line(pts, fill=255, width=14, joint="curve")
    for k in range(3):
        y = CY + 340 + k * 70
        d.line([(120 + i * 12, y + 22 * math.sin(i / 3)) for i in range(70)], fill=255, width=10, joint="curve")
    return m

def gauge():
    m, d = canvas()
    d.arc([190, CY - 350, 890, CY + 350], 180, 360, fill=255, width=22)
    for k in range(11):
        a = math.pi + k * math.pi / 10
        d.line([(540 + 300 * math.cos(a), CY + 300 * math.sin(a)), (540 + 340 * math.cos(a), CY + 340 * math.sin(a))], fill=255, width=12)
    d.line([(540, CY), (540 + 280 * math.cos(-0.5), CY + 280 * math.sin(-0.5))], fill=255, width=18)
    d.ellipse([505, CY - 35, 575, CY + 35], fill=255)
    txt("POTÊNCIA + DESIGN", 100, y=CY + 230, m=m, d=d)
    return m

def bulb():
    m, d = canvas()
    d.ellipse([330, CY - 450, 750, CY - 30], outline=255, width=20)
    d.rectangle([440, CY - 20, 640, CY + 140], outline=255, width=18)
    for k in range(3):
        d.line([(440, CY + 20 + k * 40), (640, CY + 20 + k * 40)], fill=255, width=10)
    bolt(m, d, 540, CY - 240, 120)
    for k in range(7):
        a = math.pi + k * math.pi / 6
        d.line([(540 + 260 * math.cos(a), CY - 240 + 260 * math.sin(a)), (540 + 330 * math.cos(a), CY - 240 + 330 * math.sin(a))], fill=255, width=12)
    txt("LOUCURA?", 140, y=CY + 330, m=m, d=d)
    return m

def dam():
    m, d = canvas()
    d.polygon([(120, CY - 120), (960, CY - 200), (960, CY + 120), (120, CY + 220)], outline=255, width=16)
    for k in range(10):
        x = 180 + k * 80
        d.line([(x, CY - 120 - k * 8 + 10), (x, CY + 200 - k * 10)], fill=255, width=8)
    for k in range(3):
        y = CY - 330 + k * 50
        d.line([(120 + i * 12, y + 16 * math.sin(i / 3)) for i in range(70)], fill=255, width=8, joint="curve")
    for cx in (300, 760):
        d.line([(cx, CY - 160), (cx, CY - 470)], fill=255, width=12)
        d.line([(cx - 90, CY - 450), (cx + 200, CY - 450)], fill=255, width=12)
    txt("USINA DE ITAIPU", 100, y=CY + 400, m=m, d=d)
    return m

def citymap():
    m, d = canvas()
    for k in range(7):
        y = CY - 420 + k * 140
        d.line([(110, y), (970, y + (k % 3 - 1) * 30)], fill=110, width=6)
        x = 150 + k * 130
        d.line([(x, CY - 460), (x + (k % 3 - 1) * 30, CY + 460)], fill=110, width=6)
    for px, py in [(260, CY - 300), (560, CY - 360), (800, CY - 180), (380, CY - 20), (680, CY + 120), (300, CY + 300), (820, CY + 330)]:
        d.ellipse([px - 45, py - 105, px + 45, py - 15], outline=255, width=12)
        d.polygon([(px - 38, py - 45), (px, py + 20), (px + 38, py - 45)], fill=255)
        bolt(m, d, px, py - 60, 28)
    return m

def brazil():
    m, d = canvas()
    # rough Brazil silhouette
    pts = [(.42, .02), (.55, .0), (.62, .08), (.78, .12), (.98, .3), (.92, .45), (.82, .6), (.75, .72), (.62, .8),
           (.5, .98), (.42, .9), (.44, .78), (.36, .7), (.3, .58), (.15, .5), (.02, .38), (.05, .25), (.2, .2), (.3, .1)]
    s = 760; x, y = (W - s) / 2, CY - s / 2
    d.polygon([(x + a * s, y + b * s) for a, b in pts], outline=255, width=18)
    bolt(m, d, x + .6 * s, y + .45 * s, 120)
    return m

T = R.T
SHAPES = [
    (0.0, lambda: brazil()),
    (T("carro"), lambda: car("ELÉTRICO")),
    (T("50"), lambda: txt("50\nANOS", 300)),
    (T("quase"), lambda: txt("?", 700)),
    (T("1974"), lambda: txt("1974", 330)),
    (T("engenheiro"), person),
    (T("bateria"), lambda: battery("SÓ BATERIA")),
    (T("época"), pump),
    (T("décadas"), timeline),
    (T("salão"), lambda: car("SALÃO DO AUTOMÓVEL".replace("SALÃO DO AUTOMÓVEL", "SALÃO"))),
    (T("chegar"), lambda: txt("1º", 640)),
    (T("custou"), tag),
    (T("João"), lambda: txt("JOÃO\nGURGEL", 270)),
    (T("bugues"), buggy),
    (T("praia"), beach),
    (T("febre"), lambda: txt("ANOS\n70", 330)),
    (T("mercado", 2), gauge),
    (T("ideia"), bulb),
    (T("Itaipu"), lambda: txt("ITAIPU\nE150", 290)),
    (T("homenagem"), dam),
    (T("motor"), lambda: txt("4\nCAVALOS", 260)),
    (T("320"), lambda: battery("320 KG")),
    (T("120"), lambda: txt("120 KM\nPOR CARGA", 190)),
    (T("projeto"), car),
    (T("rede"), citymap),
    (max(x["s"] for x in R.words if x["t"]=="Uma"), lambda: brazil()),
]

def sample(mask):
    a = np.asarray(mask, dtype=np.float32) / 255.0
    edge = np.asarray(mask.filter(ImageFilter.FIND_EDGES), dtype=np.float32) / 255.0
    w = (a * 0.7 + edge * 2.0).ravel()
    idx = rng.choice(w.size, size=N, p=w / w.sum())
    ys, xs = np.divmod(idx, W)
    pts = np.stack([xs, ys], 1).astype(np.float32) + rng.uniform(-1.5, 1.5, (N, 2)).astype(np.float32)
    # order by angle around centre so morphs swirl coherently
    c = pts.mean(0)
    order = np.argsort(np.arctan2(pts[:, 1] - c[1], pts[:, 0] - c[0]))
    return pts[order]

print("sampling shapes", flush=True)
TARGETS = sorted([(t, sample(fn())) for t, fn in SHAPES], key=lambda x: x[0])

# per-particle randomness
phase = rng.uniform(0, 2 * math.pi, N).astype(np.float32)
speed = rng.uniform(0.6, 1.6, N).astype(np.float32)
delay = rng.uniform(0, 0.2, N).astype(np.float32)
bright = rng.uniform(0.6, 1.0, N).astype(np.float32)
start = np.stack([rng.uniform(0, W, N), rng.uniform(0, H, N)], 1).astype(np.float32)
DUST = np.stack([rng.uniform(0, W, 260), rng.uniform(0, H, 260)], 1).astype(np.float32)
TRANS = 0.8

def ease(x):
    return np.where(x < .5, 4 * x ** 3, 1 - (-2 * x + 2) ** 3 / 2)

def positions(t):
    k = max(i for i, (ts, _) in enumerate(TARGETS) if ts <= t + 1e-6)
    tgt = TARGETS[k][1]
    prev = TARGETS[k - 1][1] if k > 0 else start
    p = np.clip((t - TARGETS[k][0] - delay) / TRANS, 0, 1)
    e = ease(p)[:, None]
    mid = np.sin(np.pi * p)[:, None]
    # swirl perpendicular to travel + some scatter
    dvec = tgt - prev
    perp = np.stack([-dvec[:, 1], dvec[:, 0]], 1) * 0.35
    scatter = np.stack([np.cos(phase * 3), np.sin(phase * 5)], 1) * 90
    pos = prev + dvec * e + (perp + scatter) * mid
    # idle shimmer
    pos += np.stack([np.sin(t * 1.7 * speed + phase), np.cos(t * 1.3 * speed + phase)], 1) * 2.2
    return pos, p

def draw_caption(img, t):
    act = None
    for c in R.chunks:
        if c[0]["s"] - 0.05 <= t < c[-1]["chunk_end"]:
            act = c
    if not act:
        return
    f = F(R.ANTON, 84)
    d = ImageDraw.Draw(img)
    toks = [x["t"].upper() for x in act]
    sp = d.textlength(" ", font=f)
    ws = [d.textlength(s, font=f) for s in toks]
    lines, cur, cw = [], [], 0
    for k, w in enumerate(ws):
        if cur and cw + sp + w > 900:
            lines.append(cur); cur, cw = [], 0
        cw += (sp if cur else 0) + w; cur.append(k)
    lines.append(cur)
    top = 1480 - 50 * len(lines)
    for li, l in enumerate(lines):
        x = (W - sum(ws[k] for k in l) - sp * (len(l) - 1)) / 2
        for k in l:
            s0 = act[k]["s"]
            e0 = act[k + 1]["s"] if k + 1 < len(act) else act[k]["chunk_end"]
            col = (255, 255, 255) if s0 <= t < e0 else ((170, 170, 170) if s0 <= t else (80, 80, 80))
            d.text((x, top + li * 100), toks[k], font=f, fill=col)
            x += ws[k] + sp

def frame(t):
    pos, p = positions(t)
    acc = np.zeros((H, W), np.float32)
    tw = bright * (0.75 + 0.25 * np.sin(t * 4 * speed + phase))
    # brighter while flying (streak feel)
    tw = tw * (1 + 0.6 * np.sin(np.pi * p))
    xi = pos[:, 0].astype(np.int32); yi = pos[:, 1].astype(np.int32)
    ok = (xi >= 1) & (xi < W - 2) & (yi >= 1) & (yi < H - 2)
    xi, yi, tw = xi[ok], yi[ok], tw[ok]
    for dx, dy, wgt in ((0, 0, 1.0), (1, 0, .6), (0, 1, .6), (1, 1, .4)):
        np.add.at(acc, (yi + dy, xi + dx), tw * wgt)
    # dust
    dp = (DUST + np.stack([np.sin(t * .2 + np.arange(260)), -t * 12 * np.ones(260)], 1)) % [W, H]
    np.add.at(acc, (dp[:, 1].astype(int), dp[:, 0].astype(int)), 0.35)
    core = np.clip(acc, 0, 1.4)
    img = Image.fromarray((np.clip(core, 0, 1) * 255).astype(np.uint8))
    glow = img.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(6)).resize((W, H), Image.BILINEAR)
    g = np.asarray(glow, np.float32) * 1.3 + np.asarray(img, np.float32)
    g = np.clip(g, 0, 255).astype(np.uint8)
    # very slight cool tint on glow
    rgb = np.stack([g, g, np.clip(g.astype(np.int16) + 8, 0, 255).astype(np.uint8)], -1)
    out = Image.fromarray(rgb, "RGB")
    draw_caption(out, t)
    return out

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        for tt in map(float, sys.argv[2:]):
            frame(tt).save(f"pp_{tt:05.1f}.jpg", quality=85)
        sys.exit()
    nf = int(DUR * FPS)
    ff = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", R.AUDIO,
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "18",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest",
                           "-movflags", "+faststart", "reels_gurgel_particulas.mp4"], stdin=subprocess.PIPE)
    for f in range(nf):
        ff.stdin.write(frame(f / FPS).tobytes())
        if f % 300 == 0:
            print(f, flush=True)
    ff.stdin.close(); ff.wait()
