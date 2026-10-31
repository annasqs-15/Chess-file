"""Anderssen-Dufresne plies 33-47, v5: top-down 2D 'Premiere-style' edit. Per-move speed graphs, scale/rotation keyframes,
adjustment-layer effects (RGB split, flash, vignette, grade), thick arrows, move-quality icons, seamless loop (pieces rewind to the start)."""
import sys, math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.interpolate import PchipInterpolator

WORK = os.path.dirname(os.path.abspath(__file__)) + "/"
sys.path.insert(0, WORK)
from minichess import Board, parse_moves, sq
from meaning import analyse

W, H, FPS = 1080, 1920, 60
RS = 2.0
BU, SQU, MU = 1000, 125, 60
SWU = BU + 2 * MU
BP, MP, SWP = int(BU * RS), int(MU * RS), int(SWU * RS)
PSU = 112
A0 = 2.4
CYN = (46, 205, 255)
AMB = (255, 170, 52)
RED = (232, 40, 48)
MAG = (255, 60, 190)
WHITE = (240, 242, 248)
BG1, BG2 = (30, 32, 40), (8, 8, 12)

HITS_A = [float(x) for x in np.load(WORK + "hits9_audio.npy")]
PLIES = list(range(33, 48))
T = {p: round((a - A0) * FPS) / FPS for p, a in zip(PLIES, HITS_A)}
REW0 = T[47] + 2.05          # pieces start rewinding to the opening position (loop)
REW1 = REW0 + 1.0
DUR = REW1 + 0.12
KS = {33: .7, 34: .35, 35: .5, 36: .3, 37: .35, 38: 1.0, 39: .8, 40: .45, 41: 1.0, 42: .45, 43: .6, 44: .3, 45: .7, 46: .35, 47: 1.3}
ACC = [(8.835, .5), (10.965, .55), (11.32, .35), (13.805, .3), (16.29, .45), (16.645, .4), (6.35, .25)]
ACC = [(round((a - A0) * FPS) / FPS, s) for a, s in ACC]


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_io(x):
    x = clamp(x)
    return x * x * x * (x * (6 * x - 15) + 10)


def ease_in(x, p=3.0):
    return clamp(x) ** p


def ease_out(x, p=3.0):
    return 1 - (1 - clamp(x)) ** p


def lerp(a, b, k):
    return a + (b - a) * k


def settle(d, k=1.0, w=26.0, tau=0.10):
    return k * math.exp(-d / tau) * math.cos(d * w) if d >= 0 else 0.0


def cu(s):
    return (MU + s[0] * SQU + SQU / 2, MU + (7 - s[1]) * SQU + SQU / 2)


def px(u):
    return (u[0] * RS, u[1] * RS)


def V(a, b):
    return np.array(b, float) - np.array(a, float)


def S(*names):
    pts = [cu(sq(n)) for n in names]
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


# ----------------------------------------------------------------- game, identities, meaning
SAN = parse_moves(open(WORK + "pgn_m3.txt").read())
_b = Board()
STATES = [dict(_b.b)]
INFO = [None]
for _s in SAN:
    INFO.append(_b.apply(_b.san_move(_s)))
    STATES.append(dict(_b.b))
MV = {p: INFO[p] for p in PLIES}
MEAN = {p: analyse(STATES[p], MV[p]) for p in PLIES}
START = STATES[32]
ID_START, ID_END = {}, {}
_pos = {s: i for i, s in enumerate(sorted(START))}
_cur = dict(_pos)
for i_, s in enumerate(sorted(START)):
    ID_START[i_] = (s, START[s])
for p in PLIES:
    m = MV[p]
    if m["captured"]:
        _cur.pop(m["captured"][0], None)
    _cur[m["to"]] = _cur.pop(m["from"])
ID_END = {i_: s for s, i_ in _cur.items()}

# ----------------------------------------------------------------- assets (the user's own piece PNGs)
SPR = {}
for c in "wb":
    for p_ in "PNBRQK":
        SPR[(c, p_)] = Image.open(WORK + "pieces5/%s%s.png" % (c, p_)).convert("RGBA")
_sc, _shc = {}, {}


def sprite(piece, size):
    k = (piece, int(size))
    if k not in _sc:
        _sc[k] = SPR[piece].resize((int(size), int(size)), Image.LANCZOS)
    return _sc[k]


def shadow(piece, size):
    k = (piece, int(size))
    if k not in _shc:
        a = sprite(piece, size).split()[3]
        pad = int(size * 0.1)
        cv = Image.new("L", (a.width + 2 * pad, a.height + 2 * pad), 0)
        cv.paste(a, (pad, pad))
        cv = cv.filter(ImageFilter.GaussianBlur(size * 0.035)).point(lambda v: int(v * 0.34))
        im = Image.new("RGBA", cv.size, (0, 0, 0, 0))
        im.putalpha(cv)
        _shc[k] = im
    return _shc[k]


BOARD = Image.open(WORK + "board_dim.jpg").convert("RGB").resize((BP, BP), Image.LANCZOS).point([int(v * 0.95) for v in range(256)] * 3)
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def put(canvas, im, cx, cy):
    canvas.alpha_composite(im, (int(round(cx - im.width / 2)), int(round(cy - im.height / 2))))


def fade_im(im, a):
    if a >= 0.999:
        return im
    al = im.split()[3].point(lambda v: int(v * a))
    im = im.copy()
    im.putalpha(al)
    return im


def tint_im(im, col, k, ang=0.0):
    """moving colour gradation across a piece (dynamic gradient, multiply-style)"""
    if k <= 0.01:
        return im
    a = np.asarray(im).astype(np.float32)
    n = a.shape[0]
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32) / n
    g = np.clip(xx * math.cos(ang) + yy * math.sin(ang), 0, 1)[..., None]
    c = np.array(col, np.float32)[None, None, :] / 255.0
    mix = (1 - g) * c + g * 1.0
    a[..., :3] = a[..., :3] * (1 - k + k * (0.55 + 0.45 * mix))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def draw_piece(canvas, piece, u, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, shad=True, lift=0.0, dark=1.0, tint=None):
    if alpha <= 0.01:
        return
    size = PSU * RS
    im = sprite(piece, size)
    if dark < 0.999:
        a = np.asarray(im).astype(np.float32)
        a[..., :3] *= dark
        im = Image.fromarray(a.astype(np.uint8), "RGBA")
    if tint is not None:
        im = tint_im(im, tint[0], tint[1], tint[2])
    flip = sx < 0
    if abs(abs(sx) - 1) > 1e-3 or abs(sy - 1) > 1e-3:
        im = im.resize((max(2, int(im.width * abs(sx))), max(2, int(im.height * abs(sy)))), Image.BICUBIC)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    if abs(rot) > 0.05:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    im = fade_im(im, alpha)
    x, y = px(u)
    if shad and alpha > 0.5:
        put(canvas, shadow(piece, size * max(0.1, abs(sx))), x + (2 + lift * 0.25) * RS, y + (5 + lift) * RS)
    put(canvas, im, x, y)


def shards_of(piece, n, seed):
    base = SPR[piece].resize((256, 256), Image.LANCZOS)
    arr = np.asarray(base)
    ys, xs = np.nonzero(arr[..., 3] > 20)
    rs = np.random.RandomState(seed)
    seeds = np.stack([rs.uniform(xs.min(), xs.max(), n), rs.uniform(ys.min(), ys.max(), n)], 1)
    lab = np.argmin((xs[:, None] - seeds[None, :, 0]) ** 2 + (ys[:, None] - seeds[None, :, 1]) ** 2, axis=1)
    out = []
    for k in range(n):
        m = lab == k
        if m.sum() < 40:
            continue
        fy, fx = ys[m], xs[m]
        x0, x1, y0, y1 = fx.min(), fx.max() + 1, fy.min(), fy.max() + 1
        frag = np.zeros((y1 - y0, x1 - x0, 4), np.uint8)
        frag[fy - y0, fx - x0] = arr[fy, fx]
        out.append((Image.fromarray(frag, "RGBA"), (fx.mean() - 128) / 256.0, (fy.mean() - 128) / 256.0))
    return out


SHARDS47 = shards_of(("b", "N"), 9, 5)

# ----------------------------------------------------------------- time remap: slow dips that land on the hit, freeze frames with catch-up
SLOW = [(T[38], 0.30, 0.30, 0.45), (T[41], 0.22, 0.30, 0.40), (T[47], 0.45, 0.20, 0.60)]   # (hit, dip length, dip speed, run-up)
STOPS = [(T[38], 0.06), (T[41], 0.10), (T[47], 0.06)]                                      # freeze right after the hit, then catch up


def build_warp():
    n = int((DUR + 1) * 960)
    ts = np.arange(n) / 960.0
    A = np.zeros(n)
    B = np.zeros(n)
    for h, d, s, e in SLOW:
        B[(ts >= h - d) & (ts < h)] = -(1 - s)
        A[(ts >= h - d - e) & (ts < h - d)] = (1 - s) * d / e
    for h, s in STOPS:
        rec = 0.25
        B[(ts >= h) & (ts < h + s)] = -1.0
        A[(ts >= h + s) & (ts < h + s + rec)] = s / rec
    sp = 1 + A + B
    k = int(0.03 * 960)
    sp = np.convolve(np.pad(sp, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), "valid")
    u = np.cumsum(sp) / 960.0
    for h, d, s, e in SLOW:
        i = int(round(h * 960))
        r = h - u[i]
        j0 = max(0, i - int((d + e + 0.1) * 960))
        u = u + r * np.clip((np.arange(n) - j0) / float(i - j0), 0, 1) * (np.arange(n) <= i) + r * (np.arange(n) > i) * 0
    return u


_U = build_warp()


def warp(t):
    return float(np.interp(t, np.arange(len(_U)) / 960.0, _U))


# ----------------------------------------------------------------- camera (top-down, tilted only at three moments)
FOC = 1500.0
KEYS = [  # (arrive, centre, zoom, pitch deg, roll deg, move duration)
    (0.0, (560, 560), 1.0, 0, 0, 0.0),
    (T[33] - 0.05, S("e6", "f5"), 1.50, 0, 0, 0.75),
    (T[36] - 0.05, S("f6", "g7"), 1.40, 0, 0, 0.50),
    (T[37] - 0.04, S("d4", "d6"), 1.35, 0, 0, 0.50),
    (T[38] - 0.20, S("g4", "g5"), 1.15, 0, -3, 0.35),
    (T[38] - 0.03, S("g4", "g3"), 2.25, 24, 6, 0.17),       # zoom crash onto the queen, board tilts for a moment
    (T[38] + 0.70, S("f4", "f5"), 1.50, 0, 0, 0.90),
    (T[39] - 0.05, (560, 470), 1.22, 0, 0, 0.50),
    (T[40] - 0.02, S("d7", "e7"), 1.80, 0, 0, 0.35),
    (T[41] - 0.04, S("b5", "c6"), 1.55, 18, -8, 0.90),
    (T[41] + 0.60, S("c6", "d7"), 1.70, 0, 5, 0.55),
    (T[42] - 0.03, S("d7", "e8"), 2.0, 0, 0, 0.45),
    (T[43] - 0.03, S("e6", "d7"), 1.75, 0, 0, 0.50),
    (T[44] - 0.02, S("d7", "e8"), 2.0, 0, 0, 0.45),
    (T[46] + 0.40, (450, 470), 1.12, 0, -3, 0.70),
    (T[47] - 0.12, S("c5", "e7"), 1.42, 14, 3, 1.00),
    (T[47] + 1.20, (560, 500), 1.10, 30, 7, 0.80),
    (REW1 - 0.05, (560, 560), 1.0, 0, 0, 0.95),
]


def cam_base(u):
    cx, cy, z, pi_, ro = KEYS[0][1][0], KEYS[0][1][1], KEYS[0][2], KEYS[0][3], KEYS[0][4]
    for i in range(1, len(KEYS)):
        ta, c, zz, pp, rr, md = KEYS[i]
        if u >= ta:
            cx, cy, z, pi_, ro = c[0], c[1], zz, pp, rr
        elif u > ta - md:
            k = ease_io((u - (ta - md)) / md)
            cx, cy, pi_, ro = lerp(cx, c[0], k), lerp(cy, c[1], k), lerp(pi_, pp, k), lerp(ro, rr, k)
            z = math.exp(lerp(math.log(z), math.log(zz), k))
            break
        else:
            break
    return cx, cy, z, pi_, ro


KICKS = [(T[p], KS[p]) for p in PLIES] + ACC
SWAY = [(T[46] + 0.45, T[47] - 0.15, 1.0), (T[47] + 1.0, REW0, 0.8), (T[39] + 0.15, T[40], 0.5)]


def camera(u):
    cx, cy, z, pi_, ro = cam_base(u)
    sx = sy = 0.0
    for tk, s in KICKS:
        d = u - tk
        if d < 0 or d > 0.9:
            continue
        z *= 1 + 0.07 * s * math.exp(-d / 0.11)
        ro += 1.2 * s * math.exp(-d / 0.28) * math.sin(d * 34 + tk * 3)
        sx += 13 * s * math.exp(-d / 0.10) * math.sin(d * 85 + tk)
        sy += 10 * s * math.exp(-d / 0.10) * math.cos(d * 75 + tk * 2)
    d = u - T[47]
    if 0 < d < 1.2:
        z *= 1 - 0.09 * math.exp(-d / 0.18) * math.cos(d * 22)
    for a, b, k in SWAY:
        w = ease_io((u - a) / 0.4) * (1 - ease_io((u - b + 0.4) / 0.4))
        if w > 0:
            ro += k * w * 1.5 * math.sin(u * 1.1 + 0.5)
            cx += k * w * 6 * math.sin(u * 0.9)
    return cx, cy, z, pi_, ro, sx, sy


def homography(cx, cy, z, pitch, roll, sx=0.0, sy=0.0):
    th, rh = math.radians(pitch), math.radians(roll)
    f = FOC
    d = f / z
    Wc, Hc = W / 2 + sx, H / 2 + sy
    return np.array([
        [f * math.cos(rh), -f * math.cos(th) * math.sin(rh) - Wc * math.sin(th), Wc * d],
        [f * math.sin(rh), f * math.cos(th) * math.cos(rh) - Hc * math.sin(th), Hc * d],
        [0.0, -math.sin(th), d]])


# ----------------------------------------------------------------- per-move motion graphs (each move has its own speed curve, scale and rotation keys)
SPEC = {
    33: dict(dur=.58, prog=[(0, 0), (.14, -.03), (.34, .07), (.6, .72), (.82, .97), (1, 1)], sc=[(0, 1), (.18, .9), (.4, 1.5), (.75, 1.4), (.93, 1.0), (1, 1)], rot=[(0, 0), (.34, 0), (.62, -230), (.92, -360), (1, -360)], st=.10, trail=2, col=CYN),
    34: dict(dur=.42, prog=[(0, 0), (.25, .38), (.5, .5), (.72, .66), (1, 1)], sc=[(0, 1), (.3, 1.2), (.55, 1.5), (.85, 1.1), (1, 1)], rot=[(0, 0), (.5, 25), (1, 0)], st=.08, col=AMB),
    35: dict(dur=.32, prog=[(0, 0), (.45, .12), (.8, .55), (1, 1)], sc=[(0, 1), (.5, .82), (.9, .9), (1, 1)], rot=[(0, 0), (.7, -14), (1, 0)], st=.12, trail=2, col=CYN),
    36: dict(dur=.50, prog=[(0, 0), (.4, .35), (1, 1)], sc=[(0, 1), (.5, 1.12), (1, 1)], rot=[(0, 0), (1, 0)], st=.04, col=AMB),
    37: dict(dur=.62, prog=[(0, 0), (.18, -.07), (.5, .25), (.85, .9), (1, 1)], sc=[(0, 1), (.4, 1.2), (1, 1)], rot=[(0, 0), (.4, -9), (1, 0)], st=.08, col=CYN),
    38: dict(dur=.74, prog=[(0, 0), (.14, -.06), (.34, .40), (.55, .47), (.72, .55), (.88, .9), (1, 1)], sc=[(0, 1), (.3, 1.2), (.5, 1.85), (.72, 1.85), (.9, 1.1), (1, 1)], rot=[(0, 0), (1, 0)], flip=[(.34, 0), (.72, 360)], st=.14, trail=3, col=AMB),
    39: dict(dur=.46, prog=[(0, 0), (.5, .15), (.85, .65), (1, 1)], sc=[(0, 1), (.5, .88), (1, 1)], rot=[(0, 0), (1, 0)], st=.26, trail=4, col=CYN),
    40: dict(dur=.30, prog=[(0, 0), (.5, .4), (1, 1)], sc=[(0, 1), (.35, .72), (.8, 1.4), (1, 1)], rot=[(0, 0), (.4, -26), (1, 0)], st=.08, col=AMB),
    41: dict(dur=.84, prog=[(0, 0), (.12, .02), (.3, .34), (.5, .42), (.7, .5), (.86, .88), (1, 1)], sc=[(0, 1), (.3, 1.4), (.55, 1.95), (.75, 1.95), (.92, 1.15), (1, 1)], rot=[(0, 0), (.3, 0), (.82, 360), (1, 360)], st=.10, trail=3, col=CYN),
    42: dict(dur=.32, prog=[(0, 0), (.3, .55), (1, 1)], sc=[(0, 1), (.5, 1.3), (1, 1)], rot=[(0, 0), (.5, -10), (1, 0)], st=.04, col=AMB),
    43: dict(dur=.50, prog=[(0, 0), (.3, .5), (.6, .8), (1, 1)], sc=[(0, 1), (.5, 1.22), (1, 1)], rot=[(0, 0), (.4, 12), (1, 0)], st=.06, col=CYN),
    44: dict(dur=.38, prog=[(0, 0), (.5, .15), (.8, .8), (1, 1)], sc=[(0, 1), (.5, .86), (1, 1)], rot=[(0, 0), (.5, 8), (1, 0)], st=.05, col=AMB),
    45: dict(dur=.36, prog=[(0, 0), (.12, -.05), (.3, .15), (.5, .3), (.75, .82), (1, 1)], sc=[(0, 1), (.4, 1.42), (.7, 1.3), (1, 1)], rot=[(0, 0), (1, 0)], flip=[(.3, 0), (.8, 360)], st=.14, trail=3, col=CYN),
    46: dict(dur=.55, prog=[(0, 0), (.5, .3), (1, 1)], sc=[(0, 1), (.5, .92), (1, 1)], rot=[(0, 0), (1, 0)], st=.04, col=AMB),
}
_ip = {}


def curve(p, name):
    k = (p, name)
    if k not in _ip:
        pts = SPEC[p][name]
        _ip[k] = PchipInterpolator([a for a, _ in pts], [b for _, b in pts])
    return _ip[k]


def mover(p, u):
    """-> (pos, sx, sy, rot, lift, trail, tint) while the mover is animated, else None"""
    m = MV[p]
    f, t = cu(m["from"]), cu(m["to"])
    h = T[p]
    L = np.linalg.norm(V(f, t))
    uv = V(f, t) / L
    if p == 47:
        return mover47(u, f, t, uv, L, h)
    sp = SPEC[p]
    dur = sp["dur"]
    if u < h - dur - 0.1 or u > h + 0.32:
        return None
    if u > h:
        d = u - h
        sqz = settle(d, 0.10 + sp["st"] * 0.6, 26, 0.11)
        o = settle(d, 0.10 * SQU, 22, 0.10) * (1 if p in (35, 39, 38, 41) else 0.4)
        return tuple(np.array(t) + uv * o), 1 + sqz, 1 - sqz, 0.0, 0, [], (sp["col"], 0.0, 0.0)
    if u < h - dur:                                         # anticipation: tiny crouch
        a = ease_io((u - (h - dur - 0.1)) / 0.1)
        return f, 1 + 0.05 * a, 1 - 0.07 * a, 0.0, 0, [], None
    k = (u - (h - dur)) / dur
    pr = float(curve(p, "prog")(k))
    sc = float(curve(p, "sc")(k))
    rot = float(curve(p, "rot")(k)) if "rot" in sp else 0.0
    dk = (float(curve(p, "prog")(min(1, k + .02))) - float(curve(p, "prog")(max(0, k - .02)))) / .04
    v = clamp(abs(dk) / 2.2)
    along = 1 + sp["st"] * v * 1.5
    sx_, sy_ = sc * (1 - 0.35 * sp["st"] * v), sc * along
    if "flip" in sp:
        fa = float(np.interp(k, [a for a, _ in sp["flip"]], [b for _, b in sp["flip"]]))
        c = math.cos(math.radians(fa))
        sx_ *= c if abs(c) > .1 else (.1 if c >= 0 else -.1)
    # rotate so the stretch lies along the direction of travel only for the 'streak' feel; otherwise upright
    pos = np.array(f) + (np.array(t) - np.array(f)) * pr
    tr = []
    for j in range(1, sp.get("trail", 0) + 1):
        kk = max(0.0, k - j * 0.07)
        tr.append((tuple(np.array(f) + (np.array(t) - np.array(f)) * float(curve(p, "prog")(kk))), 0.30 * (1 - j / (sp["trail"] + 1.0)), float(curve(p, "sc")(kk))))
    return tuple(pos), sx_, sy_, rot, (sc - 1) * 60 + 6, tr, (sp["col"], 0.45 * (0.3 + v), math.radians(20 + 330 * k))


def mover47(u, f, t, uv, L, h):
    t0, t1 = h - 0.55, h - 0.28
    if u < t0 or u > h + 0.4:
        return None
    back = 0.40 * SQU
    if u < t1:
        k = ease_out((u - t0) / (t1 - t0), 2.5)
        return tuple(np.array(f) - uv * back * k), 1 - 0.04 * k, 1 + 0.06 * k, -7 * k, 6, [], None
    if u < h:
        k = (u - t1) / (h - t1)
        e = ease_in(k, 3.2)
        pos = np.array(f) + uv * lerp(-back, L, e)
        tr = [(tuple(np.array(f) + uv * lerp(-back, L, ease_in(max(0, k - j * 0.07), 3.2))), 0.34 * (1 - j / 6.0), 1.0) for j in range(1, 6)]
        return tuple(pos), 1 - 0.06 * e, 1 + 0.18 * e, lerp(-7, 0, e) + 360 * ease_in(k, 1.6), 10, tr, (WHITE, 0.0, 0.0)
    d = u - h
    sq_ = 1 + 0.10 * math.exp(-d / 0.10) * math.cos(d * 28)
    o = 0.16 * SQU * math.exp(-d / 0.09) * math.cos(d * 24)
    return tuple(np.array(t) + uv * o), 1 / sq_, sq_, 0.0, 0, [], None


def captured_draw(p, u, canvas):
    m = MV[p]
    if not m["captured"]:
        return
    h = T[p]
    e = u - h
    if e < 0 or e > 1.4:
        return
    cs, pc = m["captured"]
    pos = np.array(cu(cs), float)
    f, t = np.array(cu(m["from"])), np.array(cu(m["to"]))
    uv = (t - f) / np.linalg.norm(t - f)
    if p == 34:                                    # swept off along the pawn's direction, spinning
        if e > 1.0:
            return
        d = (1 - math.exp(-2.4 * e)) / 2.4
        draw_piece(canvas, pc, tuple(pos + uv * 560 * d), 1, 1, 200 * d * 2, alpha=clamp(1 - (e - 0.3) / 0.6), shad=False)
    elif p == 35:                                  # flicked up, falls out of the board
        if e > 1.2:
            return
        draw_piece(canvas, pc, tuple(pos + np.array([70 * e, -520 * e + 1250 * e * e])), 1, 1, -300 * e, alpha=clamp(1 - (e - 0.55) / 0.5), shad=False)
    elif p == 33:
        return
    elif p == 38:                                  # sliced in two along the queen's path
        if e > 0.9:
            return
        size = PSU * RS
        arr = np.asarray(sprite(pc, size))
        n = arr.shape[0]
        yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
        nrm = np.array([-uv[1], uv[0]])
        side = ((xx - n / 2) * nrm[0] + (yy - n / 2) * nrm[1]) > 0
        off = (1 - math.exp(-5.5 * e)) * 80
        for sd, sign in ((side, 1), (~side, -1)):
            a = arr.copy()
            a[..., 3] = np.where(sd, a[..., 3], 0)
            hi = Image.fromarray(a, "RGBA").rotate(sign * 11 * (1 - math.exp(-4 * e)), resample=Image.BICUBIC)
            hi = fade_im(hi, clamp(1 - (e - 0.3) / 0.55))
            q = pos + nrm * sign * off + uv * 18 * e
            put(canvas, hi, q[0] * RS, q[1] * RS)
    elif p == 39:                                  # shot straight up and off the top, spinning on its axis
        if e > 0.8:
            return
        c = math.cos(2 * math.pi * 1.5 * e / 0.8)
        draw_piece(canvas, pc, tuple(pos + np.array([0, -1700 * e * e])), c if abs(c) > 0.1 else 0.1, 1.0 + 0.2 * e, 0, alpha=clamp(1 - (e - 0.35) / 0.4), shad=False)
    elif p == 40:                                  # thrown off the board to the upper left, faster and faster
        if e > 0.9:
            return
        d = np.array([-1.0, -0.55])
        draw_piece(canvas, pc, tuple(pos + d * 1900 * e * e * 1.2), 1 - 0.3 * e, 1 - 0.3 * e, -720 * e * e, alpha=clamp(1 - (e - 0.5) / 0.4), shad=False)
    elif p == 41:                                  # pawn pressed flat
        if e > 0.5:
            return
        k = ease_out(e / 0.16, 2.0)
        draw_piece(canvas, pc, tuple(pos + np.array([0, 20 * k])), 1 + 0.35 * k, max(0.04, 1 - 0.96 * k), 0, alpha=clamp(1 - (e - 0.2) / 0.3), shad=False)
    elif p == 42:                                  # queen lifted towards the camera, rotating, gone
        if e > 0.9:
            return
        k = ease_in(e / 0.9, 1.6)
        draw_piece(canvas, pc, tuple(pos + np.array([-30 * k, -90 * k])), 1 + 1.1 * k, 1 + 1.1 * k, 200 * k, alpha=clamp(1 - k * 1.15), shad=False)
    elif p == 47:                                  # shatter
        rs = np.random.RandomState(9)
        base_ang = math.atan2(uv[1], uv[0])
        for i, (fr, ox, oy) in enumerate(SHARDS47):
            ang = base_ang + rs.uniform(-1.15, 1.15)
            spd = rs.uniform(650, 1500)
            spin = rs.uniform(-420, 420)
            damp = (1 - math.exp(-3.2 * e)) / 3.2
            gx = pos[0] + ox * PSU + math.cos(ang) * spd * damp
            gy = pos[1] + oy * PSU + math.sin(ang) * spd * damp + 520 * e * e
            fa = clamp(1 - (e - 0.25) / 0.65)
            if fa <= 0:
                continue
            sz = PSU * RS / 256.0 * (1 - 0.15 * clamp(e / 0.9))
            im = fr.resize((max(2, int(fr.width * sz)), max(2, int(fr.height * sz))), Image.BICUBIC).rotate(spin * e, resample=Image.BICUBIC, expand=True)
            put(canvas, fade_im(im, fa), gx * RS, gy * RS)


# ----------------------------------------------------------------- graphic vocabulary
def arrow_poly(dv, p0, p1, prog, col, a, wd=24, head=1.0, from_off=52):
    p0, p1 = np.array(px(p0)), np.array(px(p1))
    v = p1 - p0
    L = np.linalg.norm(v)
    uv = v / L
    nrm = np.array([-uv[1], uv[0]])
    hw = wd * RS / 2
    hl, hh = 62 * RS * head, 40 * RS * head
    s = p0 + uv * from_off * RS
    tip = s + (p1 - uv * 22 * RS - s) * clamp(prog)
    shaft_end = tip - uv * hl
    if np.dot(shaft_end - s, uv) < 1:
        return
    col4 = col + (int(255 * clamp(a)),)
    dv.polygon([tuple(s + nrm * hw), tuple(shaft_end + nrm * hw), tuple(shaft_end + nrm * hh), tuple(tip),
                tuple(shaft_end - nrm * hh), tuple(shaft_end - nrm * hw), tuple(s - nrm * hw)], fill=col4)
    dv.ellipse((s[0] - hw, s[1] - hw, s[0] + hw, s[1] + hw), fill=col4)


def bracket(dv, s, col, a, grow=1.0, w=9, pad=4):
    c = px(cu(s))
    r = SQU * RS / 2 * grow - pad
    ln = SQU * RS * 0.30
    col4 = col + (int(255 * clamp(a)),)
    ww = int(w * RS / 2)
    for sx_, sy_ in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
        x, y = c[0] + sx_ * r, c[1] + sy_ * r
        dv.line([(x, y), (x - sx_ * ln, y)], fill=col4, width=ww)
        dv.line([(x, y), (x, y - sy_ * ln)], fill=col4, width=ww)


def sq_fill(dv, s, col, a):
    c = px(cu(s))
    r = SQU * RS / 2
    dv.rectangle((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=col + (int(255 * clamp(a)),))


def glow(canvas, pos, col, rad, a):
    if a <= 0.01:
        return
    n = 64
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    r = np.sqrt((xx - n / 2) ** 2 + (yy - n / 2) ** 2) / (n / 2)
    al = np.clip(1 - r, 0, 1) ** 1.8 * a
    arr = np.zeros((n, n, 4), np.uint8)
    arr[..., 0], arr[..., 1], arr[..., 2] = col
    arr[..., 3] = (al * 255).astype(np.uint8)
    im = Image.fromarray(arr, "RGBA").resize((int(rad * 2 * RS), int(rad * 2 * RS)), Image.BICUBIC)
    put(canvas, im, pos[0] * RS, pos[1] * RS)


def speed_lines(dv, centre, direction, length, count, seed, a, spread=420, wd=3.2, col=WHITE):
    rs = np.random.RandomState(seed)
    d = np.array(direction, float)
    d /= np.linalg.norm(d)
    nrm = np.array([-d[1], d[0]])
    for i in range(count):
        off = rs.uniform(-spread, spread)
        ln = length * rs.uniform(0.5, 1.3)
        back = rs.uniform(-0.2, 1.0) * length
        c0 = np.array(centre) + nrm * off - d * back
        p0, p1 = c0, c0 + d * ln
        dv.line([px(p0), px(p1)], fill=col + (int(255 * a * rs.uniform(0.35, 1.0)),), width=max(2, int(wd * RS * rs.uniform(0.6, 1.5))))


def bolt(dv, p0, p1, seed, wd=7, branches=3, col=CYN):
    rs = np.random.RandomState(seed)
    p0, p1 = np.array(p0, float), np.array(p1, float)
    v = p1 - p0
    L = np.linalg.norm(v)
    nrm = np.array([-v[1], v[0]]) / L
    n = 11
    pts = [p0] + [p0 + v * (i / n) + nrm * rs.uniform(-38, 38) for i in range(1, n)] + [p1]
    segs = [pts]
    for _ in range(branches):
        i = rs.randint(2, n - 2)
        d = (rs.uniform(-1, 1) * nrm + 0.5 * v / L) * rs.uniform(90, 170)
        segs.append([pts[i], pts[i] + d * 0.5 + rs.uniform(-12, 12, 2), pts[i] + d])
    for glow_w, a, c in ((wd * 3.4, 70, col), (wd * 1.8, 130, col), (wd * 0.7, 255, (235, 250, 255))):
        for sg in segs:
            dv.line([tuple(q * RS) for q in sg], fill=c + (a,), width=int(glow_w * RS / 2), joint="curve")


BADGE = {33: ("!!", (30, 188, 178)), 38: ("??", (214, 54, 50)), 41: ("!!", (30, 188, 178)), 47: ("#", (205, 160, 40))}
_badge_cache = {}


def badge_img(p):
    if p in _badge_cache:
        return _badge_cache[p]
    g, col = BADGE[p]
    R = 34 * RS
    n = int(R * 2.2)
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    c = n / 2
    d.ellipse((c - R - 3, c - R - 3, c + R + 3, c + R + 3), fill=(255, 255, 255, 255))
    d.ellipse((c - R, c - R, c + R, c + R), fill=col + (255,))
    f = ImageFont.truetype(FONT, int(R * (1.25 if len(g) == 1 else 1.0)))
    d.text((c, c + R * 0.04), g, font=f, fill=(255, 255, 255, 255), anchor="mm")
    _badge_cache[p] = im
    return im


def draw_badges(canvas, u):
    for p in BADGE:
        e = u - T[p]
        nxt = [T[q] for q in PLIES if q > p]
        end = (nxt[0] + 0.25) if nxt else REW0
        if p == 47:
            end = REW0 - 0.1
        if e < 0 or u > end:
            continue
        pop = 1 - math.exp(-e / 0.05) * math.cos(e * 20) if e < 1.0 else 1.0
        fadeout = clamp(1 - (u - (end - 0.25)) / 0.25)
        sc = max(0.01, pop) * (1.35 if p in (38, 41, 47) else 1.0)
        im = badge_img(p)
        b2 = im.resize((max(2, int(im.width * sc)), max(2, int(im.height * sc))), Image.BICUBIC)
        c = np.array(cu(MV[p]["to"])) + np.array([SQU * 0.46, -SQU * 0.46])
        put(canvas, fade_im(b2, fadeout), c[0] * RS, c[1] * RS)


# ----------------------------------------------------------------- effects under pieces (each designed for its move)
def accent(p):
    return CYN if MV[p]["piece"][0] == "w" else AMB


def under_fx(u, dv, canvas):
    cur = max([p for p in PLIES if T[p] - 0.12 <= u], default=None)
    if cur is not None and cur != 47 and u < REW0:
        k = ease_io((u - (T[cur] - 0.12)) / 0.18)
        col = accent(cur)
        sq_fill(dv, MV[cur]["from"], col, 0.20 * k)
        sq_fill(dv, MV[cur]["to"], col, 0.42 * k)
    for p in PLIES:
        e = u - T[p]
        if 0 <= e < 0.9 and p != 47:
            glow(canvas, cu(MV[p]["to"]), accent(p), 110 + 150 * KS[p], 0.5 * KS[p] * math.exp(-e / 0.32))
    # 33 Nf6+ : a fork. Red arrow to the king (check), cyan arrow to the queen on h5, amber bracket on the knight (it can be taken)
    h = T[33]
    if h <= u <= h + 1.5:
        e = u - h
        a = 0.95 * ease_io(e / 0.10) * (1 - ease_io((e - 0.95) / 0.45))
        arrow_poly(dv, cu(sq("f6")), cu(sq("e8")), ease_out(e / 0.22, 2.4), RED, a, wd=28)
        arrow_poly(dv, cu(sq("f6")), cu(sq("h5")), ease_out((e - 0.08) / 0.24, 2.4), CYN, a, wd=28)
        bracket(dv, sq("e8"), RED, a, 1 + 0.12 * math.exp(-e / 0.14), 11)
        bracket(dv, sq("h5"), CYN, a, 1 + 0.08 * math.sin(e * 14), 10)
        bracket(dv, sq("f6"), AMB, a * 0.9, 1 + 0.06 * math.sin(e * 16), 8)
    # 34 gxf6 : single short amber arrow g7 -> f6 (quiet)
    h = T[34]
    if h - 0.25 <= u <= h + 0.5:
        a = ease_io((u - h + 0.25) / 0.12) * (1 - ease_io((u - h) / 0.5))
        arrow_poly(dv, cu(sq("g7")), cu(sq("f6")), ease_out((u - h + 0.25) / 0.25, 2.0), AMB, 0.85 * a, wd=24)
    # 35 exf6 : the pawn now eyes e7 (target bracket) and g7
    h = T[35]
    if h <= u <= h + 0.9:
        e = u - h
        a = 1 - ease_io((e - 0.5) / 0.4)
        arrow_poly(dv, cu(sq("f6")), cu(sq("e7")), ease_out(e / 0.2, 2.0), CYN, 0.9 * a, wd=24)
        bracket(dv, sq("e7"), CYN, a, 1 + 0.08 * math.sin(e * 16), 9)
    # 36 Rg8 : g-file points at g2
    h = T[36]
    if h - 0.1 <= u <= h + 1.1:
        a = 0.8 * ease_io((u - h + 0.1) / 0.25) * (1 - ease_io((u - h - 0.55) / 0.55))
        arrow_poly(dv, cu(sq("g8")), cu(sq("g2")), ease_out((u - h + 0.1) / 0.5, 2.0), AMB, a, wd=22)
        bracket(dv, sq("g2"), AMB, a, 1 + 0.08 * math.sin((u - h) * 12), 8)
    # 37 Rad1 : the d-file aims at d7
    h = T[37]
    if h - 0.2 <= u <= h + 1.1:
        a = 0.9 * ease_io((u - h + 0.2) / 0.2) * (1 - ease_io((u - h - 0.45) / 0.65))
        arrow_poly(dv, cu(sq("d1")), cu(sq("d7")), ease_out((u - h + 0.2) / 0.6, 2.2), CYN, a * 0.85, wd=26)
        bracket(dv, sq("d7"), CYN, a, 1 + 0.08 * math.sin((u - h) * 14), 9)
    # 38 Qxf3?? : the queen hits d1 and d3, then white's reply (e1 -> e7) is foreshadowed in faint cyan
    h = T[38]
    if h <= u <= h + 1.6:
        e = u - h
        a = 0.92 * ease_io(e / 0.12) * (1 - ease_io((e - 0.8) / 0.5))
        arrow_poly(dv, cu(sq("f3")), cu(sq("d1")), ease_out(e / 0.30, 2.5), AMB, a, wd=26)
        arrow_poly(dv, cu(sq("f3")), cu(sq("d3")), ease_out((e - 0.08) / 0.30, 2.5), AMB, a, wd=26)
        bracket(dv, sq("d1"), AMB, a, 1 + 0.1 * math.sin(e * 16), 9)
        bracket(dv, sq("d3"), AMB, a, 1 + 0.1 * math.sin(e * 16 + 1), 9)
        b = 0.55 * ease_io((e - 0.55) / 0.3) * (1 - ease_io((e - 1.2) / 0.4))
        if b > 0.01:
            arrow_poly(dv, cu(sq("e1")), cu(sq("e7")), ease_out((e - 0.55) / 0.45, 2.0), CYN, b, wd=30)
    # 39 Rxe7+ : speed lines up the file under the rook; the file itself lights; check bracket on the king
    h = T[39]
    if h - 0.46 <= u <= h + 0.9:
        k = ease_in((u - (h - 0.46)) / 0.46, 2.0)
        a = 0.28 * (1 if u < h else 1 - ease_io((u - h) / 0.9))
        c0 = cu(sq("e1"))
        x0, x1 = (c0[0] - SQU / 2) * RS, (c0[0] + SQU / 2) * RS
        yb = (MU + 8 * SQU) * RS
        yt = yb - k * 7 * SQU * RS - SQU * RS / 2
        dv.rectangle((x0, min(yt, yb), x1, yb), fill=CYN + (int(255 * a),))
        if u < h:
            speed_lines(dv, (c0[0], lerp(cu(sq("e1"))[1], cu(sq("e7"))[1], k) + 120), (0, 1), 420, 14, 3, 0.6 * (1 - k * 0.3), spread=62)
    if u >= h:
        e = u - h
        a = 1 - ease_io((e - 0.55) / 0.35)
        bracket(dv, sq("e8"), RED, a, 1 + 0.14 * math.exp(-e / 0.14), 11)
        bracket(dv, sq("e7"), AMB, a * 0.9, 1 + 0.06 * math.sin(e * 18), 8)
    # 40 Nxe7 : short amber arrow only
    h = T[40]
    if h - 0.30 <= u <= h + 0.5:
        a = ease_io((u - h + 0.30) / 0.15) * (1 - ease_io((u - h) / 0.5))
        arrow_poly(dv, cu(sq("c6")), cu(sq("e7")), ease_out((u - h + 0.30) / 0.25, 2.0), AMB, 0.85 * a, wd=24)
    # 41 Qxd7+!! : a very wide neon beam a4 -> d7 draws first; king and queen both marked
    h = T[41]
    if h - 0.85 <= u <= h + 1.2:
        k = ease_out((u - (h - 0.85)) / 0.45, 2.2)
        a = 1 if u < h else 1 - ease_io((u - h) / 0.7)
        a0 = ov_glow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        dg = ImageDraw.Draw(a0)
        arrow_poly(dg, cu(sq("a4")), cu(sq("d7")), k, CYN, 0.9 * a, wd=60, head=1.4)
        canvas.alpha_composite(a0.filter(ImageFilter.GaussianBlur(26)))
        arrow_poly(dv, cu(sq("a4")), cu(sq("d7")), k, CYN, 0.92 * a, wd=36, head=1.25)
        if u >= h:
            e = u - h
            bracket(dv, sq("d7"), AMB, a, 1 + 0.07 * math.sin(e * 16), 10)
            bracket(dv, sq("e8"), RED, a, 1 + 0.12 * math.exp(-e / 0.15), 11)
    # 42 Kxd7 : forecast arrow d3 -> f5
    h = T[42]
    if h <= u <= h + 0.85:
        e = u - h
        a = 0.6 * ease_io(e / 0.15) * (1 - ease_io((e - 0.5) / 0.35))
        arrow_poly(dv, cu(sq("d3")), cu(sq("f5")), ease_out(e / 0.35, 2.0), CYN, a, wd=22)
    # 45 Bd7+ : diagonal speed lines behind the dash + one expanding square outline from d7
    h = T[45]
    if h - 0.36 <= u <= h:
        k = (u - (h - 0.36)) / 0.36
        c = V(cu(sq("f5")), cu(sq("d7")))
        speed_lines(dv, cu(sq("e6")), tuple(c), 380, 11, 5, 0.7 * (1 - 0.3 * k), spread=70)
    if h <= u <= h + 0.55:
        e = u - h
        k = e / 0.55
        c = px(cu(sq("d7")))
        r = SQU * RS / 2 * (1 + 1.6 * ease_out(k, 2.2))
        dv.rectangle((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=CYN + (int(255 * 0.95 * (1 - ease_in(k, 1.5))),), width=int(9 * RS / 2))
        bracket(dv, sq("e8"), RED, 1 - ease_io((e - 0.35) / 0.2), 1 + 0.12 * math.exp(-e / 0.14), 11)
    # 46 -> 47 : the mating diagonal a3 -> e7 draws itself slowly and throbs
    if T[46] + 0.30 <= u < T[47] + 0.35:
        g0, g1 = T[46] + 0.30, T[47] - 0.45
        gl = ease_io((u - g0) / (g1 - g0))
        fade = 1.0 if u < T[47] else clamp(1 - (u - T[47]) / 0.35)
        col = CYN if u < T[47] else WHITE
        thr = 1 + 0.10 * math.sin((u - g0) * 11) * (1 if u < T[47] else 0)
        arrow_poly(dv, cu(sq("a3")), cu(sq("e7")), gl, col, 0.88 * fade, wd=34 * thr, head=1.25)
        if gl > 0.9 and u < T[47]:
            bracket(dv, sq("e7"), CYN, 1.0, 1 + 0.08 * math.sin(u * 16), 10)
            bracket(dv, sq("f8"), RED, 0.8 + 0.2 * math.sin(u * 14), 1.0, 10)
    if T[47] <= u < REW0:
        e = u - T[47]
        a = 1 - ease_io((u - (REW0 - 0.4)) / 0.4)
        sq_fill(dv, sq("a3"), WHITE, 0.18 * a)
        sq_fill(dv, sq("e7"), WHITE, 0.40 * a)
        pulse = 1 + 0.12 * math.exp(-e / 0.10) * math.cos(e * 24)
        c = px(cu(sq("f8")))
        r = SQU * RS / 2 * pulse
        dv.rectangle((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=RED + (int(255 * clamp(e / 0.04) * 0.96 * a),))


def over_fx(u, df, canvas):
    # 38: a thin white slash across the knight's square
    h = T[38]
    if h <= u <= h + 0.30:
        e = u - h
        m = MV[38]
        uv = V(cu(m["from"]), cu(m["to"]))
        uv = uv / np.linalg.norm(uv)
        c = np.array(cu(m["to"]))
        g = ease_out(e / 0.07, 2.0)
        a = clamp(1 - (e - 0.08) / 0.22)
        df.line([px(c - uv * 95), px(c + uv * (95 * (2 * g - 1)))], fill=WHITE + (int(255 * a),), width=int(6 * RS))
    # 39: lightning along the e-file for a few frames (electric check)
    h = T[39]
    if h <= u < h + 0.22:
        e = u - h
        if int(e * 60) % 2 == 0 or e < 0.05:
            bolt(df, cu(sq("e1")), cu(sq("e8")), int(e * 60) + 7, wd=8, branches=4, col=CYN)
    # 41: a pillar of light drops on d7
    h = T[41]
    if h <= u <= h + 0.7:
        e = u - h
        a = 0.5 * math.exp(-e / 0.22)
        c = np.array(cu(sq("d7")))
        wd = SQU * (0.55 + 0.25 * ease_out(e / 0.2, 2.0)) / 2
        df.polygon([px((c[0] - wd * 0.7, c[1] - 700)), px((c[0] + wd * 0.7, c[1] - 700)), px((c[0] + wd, c[1])), px((c[0] - wd, c[1]))], fill=(210, 250, 255, int(255 * a * 0.55)))
    # 43: the bishop draws an arrow, aims along the diagonal and shoots the king on d7
    h = T[43]
    if h + 0.0 <= u <= h + 0.9:
        e = u - h
        f_, t_ = np.array(cu(sq("f5"))), np.array(cu(sq("d7")))
        uvv = (t_ - f_) / np.linalg.norm(t_ - f_)
        rel = h + 0.355                                     # release lands on the next hi-hat grid point
        if u < rel:
            pull = ease_out((u - h) / 0.2, 2.5)
            tail = f_ + uvv * (30 - 60 * pull)
            tipp = tail + uvv * 150
            fl = 0.9
        else:
            k = ease_in((u - rel) / 0.07, 1.6)
            tail = f_ + uvv * (30 + 250 * k)
            tipp = tail + uvv * 150
            fl = 1 if k < 1 else 0.0
        if fl > 0:
            n_ = np.array([-uvv[1], uvv[0]])
            df.line([px(tail), px(tipp - uvv * 24)], fill=(250, 250, 255, 255), width=int(9 * RS))
            df.polygon([px(tipp), px(tipp - uvv * 40 + n_ * 18), px(tipp - uvv * 40 - n_ * 18)], fill=CYN + (255,))
            for sgn in (-1, 1):
                df.line([px(tail), px(tail - uvv * 26 + n_ * 18 * sgn)], fill=CYN + (255,), width=int(6 * RS))
            if u >= rel:
                speed_lines(df, tuple((tail + tipp) / 2 - uvv * 80), tuple(uvv), 220, 5, 11, 0.6, spread=18, wd=2.4)
        if u >= rel + 0.07:                                   # arrow embedded in the king, impact ring
            q = u - rel - 0.07
            tip2 = t_ + np.array([0, 0]) - uvv * 8
            a = 1 - ease_io((q - 0.5) / 0.3)
            n_ = np.array([-uvv[1], uvv[0]])
            df.line([px(tip2 - uvv * 160), px(tip2 - uvv * 22)], fill=(250, 250, 255, int(255 * a)), width=int(9 * RS))
            df.polygon([px(tip2), px(tip2 - uvv * 40 + n_ * 18), px(tip2 - uvv * 40 - n_ * 18)], fill=CYN + (int(255 * a),))
            r = 30 + 150 * ease_out(q / 0.28, 2.0)
            cc = px(t_)
            df.ellipse((cc[0] - r * RS, cc[1] - r * RS, cc[0] + r * RS, cc[1] + r * RS), outline=WHITE + (int(220 * clamp(1 - q / 0.28)),), width=int(8 * RS))
    # 47: red cracks e7 -> f8 (+ the bishop's launch streaks)
    h = T[47]
    if h - 0.28 <= u < h:
        speed_lines(df, cu(sq("c5")), (1, -1), 520, 12, 17, 0.55 * ease_io((u - h + 0.28) / 0.1), spread=60, wd=3.6)
    if h <= u < REW0 - 0.3:
        e = u - h
        grow = ease_out(e / 0.20, 2.2)
        fade = clamp(1 - (e - 0.55) / 0.9)
        if grow > 0 and fade > 0:
            rs2 = np.random.RandomState(31)
            B_TO, K_TO = cu(sq("e7")), cu(sq("f8"))
            main = [np.array(B_TO, float)]
            v = V(B_TO, K_TO)
            nrm = np.array([-v[1], v[0]]) / (np.linalg.norm(v) + 1e-6)
            for i in range(1, 8):
                f_ = i / 8
                main.append(np.array(B_TO) + v * f_ + nrm * rs2.uniform(-30, 30) * (1 - abs(f_ - 0.5) * 0.6))
            main.append(np.array(K_TO, float))
            segs = [main]
            for bi in (3, 5):
                p_ = main[bi]
                ang = rs2.uniform(-1, 1) + (1.3 if bi == 3 else -1.4)
                ln = rs2.uniform(70, 130)
                segs.append([p_, p_ + np.array([math.cos(ang), math.sin(ang)]) * ln * 0.5 + rs2.uniform(-8, 8, 2), p_ + np.array([math.cos(ang + .3), math.sin(ang + .3)]) * ln])
            for ang in (2.2, 3.6, 5.2):
                p_ = np.array(B_TO, float)
                segs.append([p_, p_ + np.array([math.cos(ang), math.sin(ang)]) * 45 + rs2.uniform(-6, 6, 2), p_ + np.array([math.cos(ang + .25), math.sin(ang + .25)]) * 95])
            for si, pts in enumerate(segs):
                last = max(1, int(round((len(pts) - 1) * grow)))
                w = max(2, int((5.0 if si == 0 else 3.2) * RS))
                df.line([tuple(np.array(q) * RS) for q in pts[:last + 1]], fill=RED + (int(235 * fade),), width=w, joint="curve")


# ----------------------------------------------------------------- lighting (spotlight + vignette moments), grade, adjustment-layer effects
def light_events():
    return [
        (T[38] - 0.20, 0.20, 0.55, 0.55, 0.50, ("h5", "f3"), 330, 1.0, AMB),
        (T[39] - 0.10, 0.12, 0.30, 0.45, 0.30, ("e4", "e7"), 260, 0.8, CYN),
        (T[41] - 0.45, 0.30, 1.00, 0.60, 0.60, ("b5", "d7"), 340, 1.1, CYN),
        (T[45] - 0.12, 0.10, 0.25, 0.35, 0.40, ("d7", "e8"), 300, 0.9, CYN),
        (T[47] - 0.30, 0.30, 1.50, 0.80, 0.62, ("e7", "f8"), 270, 1.2, RED),
    ]


def light_map(u):
    amb = 1.0
    pools = []
    for (t0, ri, ho, fa, dip, cen, rad, st, col) in light_events():
        e = u - t0
        if e <= 0:
            continue
        k = ease_io(e / ri) * (1 - ease_io((e - ri - ho) / fa))
        if k <= 0.003:
            continue
        amb -= dip * k
        pools.append((S(*cen), rad * (1.5 - 0.5 * k), st * k, col))
    ex = 0.0
    for tk, s in KICKS:
        d = u - tk
        if 0 <= d < 0.3:
            ex += 0.16 * s * math.exp(-d / 0.07)
    return max(amb, 0.12) + ex, pools


def apply_light(canvas, u):
    amb, pools = light_map(u)
    if abs(amb - 1.0) < 0.01 and not pools:
        return canvas
    n = SWP // 8
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    ux, uy = (xx + 0.5) * 8 / RS, (yy + 0.5) * 8 / RS
    mult = np.full((n, n, 3), amb, np.float32)
    for (c, rad, st, col) in pools:
        g = np.exp(-(((ux - c[0]) ** 2 + (uy - c[1]) ** 2) / (rad ** 2))) * st
        tint = 0.55 + 0.45 * np.array(col, np.float32) / 255.0
        mult += g[..., None] * tint[None, None, :]
    m = np.asarray(Image.fromarray(np.clip(mult * 128, 0, 255).astype(np.uint8)).resize((SWP, SWP), Image.BILINEAR)).astype(np.float32) / 128.0
    arr = np.asarray(canvas).astype(np.float32)
    arr[..., :3] = np.clip(arr[..., :3] * m, 0, 255)
    return Image.fromarray(arr.astype(np.uint8), "RGBA")


GRADE = [(0.0, (1, 1, 1)), (T[33] + 0.3, (0.90, 1.0, 1.10)), (T[38] - 0.3, (0.88, 0.98, 1.12)), (T[38] + 0.3, (1.12, 1.0, 0.88)),
         (T[41] - 0.5, (1.10, 0.99, 0.90)), (T[41] + 0.2, (0.90, 1.06, 1.08)), (T[45], (1.0, 0.96, 1.10)),
         (T[47] - 0.3, (1.0, 0.97, 1.05)), (T[47] + 0.1, (1.14, 0.90, 0.90)), (REW0, (1.10, 0.92, 0.92)), (REW1, (1, 1, 1)), (DUR + 1, (1, 1, 1))]


def grade(u):
    ts = [a for a, _ in GRADE]
    return [1 + 0.55 * (float(np.interp(u, ts, [c[i] for _, c in GRADE])) - 1) for i in range(3)]


def post_fx(frame, u, t):
    arr = None
    # colour grade (split tone approximated as a tint that follows the story)
    g = grade(u)
    if max(abs(g[0] - 1), abs(g[1] - 1), abs(g[2] - 1)) > 0.004:
        arr = np.asarray(frame, np.float32) * np.array(g, np.float32)[None, None, :]
    # RGB split on three hits, flash frames on two
    rgb = 0.0
    for tk, amp, dec in ((T[38], 11, 0.10), (T[41], 7, 0.08), (T[47], 15, 0.16)):
        d = t - tk
        if 0 <= d < 0.4:
            rgb = max(rgb, amp * math.exp(-d / dec))
    flash = 0.0
    for tk, a, dec in ((T[38], 0.32, 0.05), (T[41], 0.28, 0.05), (T[47], 0.60, 0.07)):
        d = t - tk
        if 0 <= d < 0.4:
            flash = max(flash, a * math.exp(-d / dec))
    if rgb > 0.8 or flash > 0.01:
        if arr is None:
            arr = np.asarray(frame, np.float32).copy()
        if rgb > 0.8:
            s = int(rgb)
            arr[..., 0] = np.roll(arr[..., 0], s, axis=1)
            arr[..., 2] = np.roll(arr[..., 2], -s, axis=1)
        if flash > 0.01:
            arr = arr + (255 - arr) * flash
    if arr is None:
        return frame
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")


# ----------------------------------------------------------------- scene
def rewind_pieces(canvas, u):
    k = clamp((u - REW0) / (REW1 - REW0))
    for i_, (s0, pc) in ID_START.items():
        if i_ in ID_END:
            a, b = cu(ID_END[i_]), cu(s0)
            d = np.linalg.norm(V(a, b))
            delay = clamp(d / 1100.0) * 0.25
            kk = ease_io(clamp((k - delay * 0.5) / (1 - delay * 0.5)))
            pos = (lerp(a[0], b[0], kk), lerp(a[1], b[1], kk))
            lift = 40 * math.sin(math.pi * kk)
            rot = 0.0
            if pc == ("b", "K") and ID_END[i_] == sq("f8"):
                rot = lerp(-84, 0, kk)
                pos = (pos[0] + 24 * (1 - kk), pos[1] + 28 * (1 - kk))
            if d > 1:
                sc = 1 + 0.2 * math.sin(math.pi * kk)
                draw_piece(canvas, pc, pos, sc, sc, rot, lift=lift)
            else:
                draw_piece(canvas, pc, pos, 1, 1, rot)
    for i_, (s0, pc) in ID_START.items():
        if i_ not in ID_END:
            a = clamp((k - 0.55) / 0.4)
            sc = 0.6 + 0.4 * ease_out(a, 2.5)
            draw_piece(canvas, pc, cu(s0), sc, sc, 0, alpha=a)


def draw_scene(u):
    canvas = Image.new("RGBA", (SWP, SWP), (0, 0, 0, 0))
    canvas.paste(BOARD.convert("RGBA"), (MP, MP))
    ov = Image.new("RGBA", (SWP, SWP), (0, 0, 0, 0))
    under_fx(u, ImageDraw.Draw(ov), ov)
    canvas.alpha_composite(ov)
    if u >= REW0:
        rewind_pieces(canvas, u)
        return apply_light(canvas, u)
    base = sum(1 for p in PLIES if T[p] <= u)
    state = dict(STATES[32 + base])
    excl, movers = set(), []
    for p in PLIES:
        r = mover(p, u)
        if r is None:
            continue
        excl.add(MV[p]["from"] if u < T[p] else MV[p]["to"])
        movers.append((p, r))
    items = sorted(state.items(), key=lambda kv: -kv[0][1])
    kjit = {}
    for p in (33, 39, 41, 43, 45):
        e = u - T[p]
        if 0 <= e < 0.3:
            for s_, pc in state.items():
                if pc == ("b", "K"):
                    a = math.exp(-e / 0.09)
                    kjit[s_] = (5 * a * math.sin(e * 80), 4 * a * math.cos(e * 70))
    for s_, pc in items:
        if s_ in excl:
            continue
        pos, rot = cu(s_), 0.0
        if pc == ("b", "K") and u >= T[47] and s_ == sq("f8"):
            e = u - T[47]
            j = math.exp(-e / 0.12)
            pos = (pos[0] + 6 * j * math.sin(e * 90), pos[1] + 5 * j * math.cos(e * 70))
            rot = -11 * (1 - math.exp(-e / 0.05)) * (0.85 + 0.15 * math.exp(-e / 0.6))
            if e > 0.9:
                kk = ease_in((e - 0.9) / 0.55, 2.0)
                rot = lerp(-11, -84, kk) + settle(e - 1.45, 5, 18, 0.2) * (e > 1.45)
                pos = (pos[0] + 24 * kk, pos[1] + 28 * kk)
        elif s_ in kjit:
            pos = (pos[0] + kjit[s_][0], pos[1] + kjit[s_][1])
        draw_piece(canvas, pc, pos, 1, 1, rot)
    for p in PLIES:
        captured_draw(p, u, canvas)
    for p, (pos, sx, sy, rot, lift, tr, tint) in movers:
        pc = MV[p]["piece"]
        for tp, ta, tsc in tr:
            draw_piece(canvas, pc, tp, tsc, tsc, 0, alpha=ta, shad=False)
        draw_piece(canvas, pc, pos, sx, sy, rot, lift=lift, tint=tint if tint and tint[1] > 0 else None)
    fx = Image.new("RGBA", (SWP, SWP), (0, 0, 0, 0))
    over_fx(u, ImageDraw.Draw(fx), canvas)
    canvas.alpha_composite(fx)
    canvas = apply_light(canvas, u)
    draw_badges(canvas, u)
    return canvas


_bg = None


def background():
    global _bg
    if _bg is None:
        y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        a = np.array(BG1, np.float32)[None, None, :]
        b = np.array(BG2, np.float32)[None, None, :]
        _bg = np.repeat(a * (1 - y) + b * y, W, axis=1).astype(np.uint8)
    return _bg


def render(fi):
    t = fi / FPS
    u = warp(t)
    canvas = draw_scene(u)
    cx, cy, z, pi_, ro, sx, sy = camera(u)
    Hm = homography(cx, cy, z, pi_, ro, sx, sy)
    Hi = np.linalg.inv(Hm)
    A = np.array([[RS, 0, cx * RS], [0, RS, cy * RS], [0, 0, 1.0]])
    M = A @ Hi
    M = M / M[2, 2]
    coeffs = (M[0, 0], M[0, 1], M[0, 2], M[1, 0], M[1, 1], M[1, 2], M[2, 0], M[2, 1])
    wp = canvas.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    frame = Image.fromarray(background(), "RGB").convert("RGBA")
    frame.alpha_composite(wp)
    return post_fx(frame.convert("RGB"), u, t)


NFRAMES = int(round(DUR * FPS))


def encode_range(a, b, outfile):
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
                          "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "16",
                          "-pix_fmt", "yuv420p", "-g", "60", outfile], stdin=subprocess.PIPE)
    for fi in range(a, b):
        p.stdin.write(render(fi).tobytes())
    p.stdin.close()
    p.wait()


if __name__ == "__main__":
    mode = sys.argv[1]
    if mode == "frames":
        os.makedirs(WORK + "dbg9", exist_ok=True)
        import time
        for tt in sys.argv[2:]:
            t0 = time.time()
            render(int(round(float(tt) * FPS))).save(WORK + "dbg9/c_%s.png" % tt)
            print(tt, "%.2fs" % (time.time() - t0), flush=True)
    elif mode == "times":
        print({p: round(T[p], 3) for p in PLIES}, "REW", round(REW0, 2), round(REW1, 2), "DUR", round(DUR, 2), "frames", NFRAMES)
        print("warp check", [round(warp(T[p]) - T[p], 4) for p in (38, 41, 47)], "end", round(warp(DUR) - DUR, 3))
    else:
        encode_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
