"""Tarrasch-Romberg (rook-odds FEN), plies 29-41 (15.Qxh6+ .. 21.N2f4#), house style v5 + editor's brief.
Three new acting animations (bazooka, cowboy hat + flower, crying), standing 3D pieces on tilted moments, loop track 'Loop the loop'."""
import sys, math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.interpolate import PchipInterpolator

WORK = os.path.dirname(os.path.abspath(__file__)) + "/"
TAL = WORK
sys.path.insert(0, WORK)
from minichess import Board, parse_moves, sq
from meaning import analyse
import decor as DC

W, H, FPS = 1080, 1920, 60
RS = 2.0
BU, SQU, MU = 1000, 125, 60
SWU = BU + 2 * MU
BP, MP, SWP = int(BU * RS), int(MU * RS), int(SWU * RS)
PSU = 112
A0 = 0.0
CYN = (46, 205, 255)
AMB = (255, 170, 52)
RED = (232, 40, 48)
MAG = (255, 60, 190)
WHITE = (240, 242, 248)
BG1, BG2 = (30, 32, 40), (8, 8, 12)
FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/1NBQKBNR w Kkq - 0 1"

# hit times on the beat grid of 'Loop the loop' (90 BPM, grid 1/6 s), audio seconds
HITS_A = [0.97, 1.475, 1.975, 2.64, 3.64, 4.145, 5.315, 6.31, 7.98, 8.415, 9.21, 10.315, 10.985]
PLIES = list(range(29, 42))
P0 = 28
T = {p: round((a - A0) * FPS) / FPS for p, a in zip(PLIES, HITS_A)}
REW0 = T[41] + 1.5          # pieces start rewinding to the opening position (loop)
REW1 = REW0 + 1.0
DUR = 13.6
KS = {29: 1.0, 30: .5, 31: .8, 32: .35, 33: .55, 34: .3, 35: .8, 36: .4, 37: 1.0, 38: .7, 39: .7, 40: .35, 41: 1.3}
ACC = [(2.975, .3), (4.645, .25), (5.715, .25), (6.815, .35), (7.315, .4)]
ACC = [(round((a - A0) * FPS) / FPS, s) for a, s in ACC]
CRY0 = T[39]                 # the king starts to cry when the bishop checks


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
SAN = parse_moves(open(TAL + "pgn_tar.txt").read())
_b = Board(FEN)
STATES = [dict(_b.b)]
INFO = [None]
for _s in SAN:
    INFO.append(_b.apply(_b.san_move(_s)))
    STATES.append(dict(_b.b))
MV = {p: INFO[p] for p in PLIES}
MEAN = {p: analyse(STATES[p], MV[p]) for p in PLIES}
START = STATES[P0]
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



CUR_PHI = 0.0          # 0 = top-down flat icons; 90 = pieces standing upright (tilted board moments)
PLIST = []


def stand_of(pitch):
    return 90.0 * ease_io(clamp((pitch - 2.0) / 30.0))


def contact_shadow(canvas, u, sx, lift):
    k = CUR_PHI / 90.0
    w = PSU * 0.82 * abs(sx)
    ov = Image.new("RGBA", (int(w * 2.4 * RS), int(w * 1.1 * RS)), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse((ov.width * 0.12, ov.height * 0.25, ov.width * 0.88, ov.height * 0.75), fill=(0, 0, 0, int(135 * k * (1 - 0.6 * clamp(lift / 120.0)))))
    ov = ov.filter(ImageFilter.GaussianBlur(3.2 * RS))
    put(canvas, ov, (u[0] + 9) * RS, (u[1] + 8 + lift * 0.25) * RS)


def draw_piece(canvas, piece, u, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, shad=True, lift=0.0, dark=1.0, tint=None, deco=None):
    if alpha <= 0.01:
        return
    size = PSU * RS
    if CUR_PHI > 0.5:
        PLIST.append(dict(piece=piece, u=u, sx=sx, sy=sy, rot=rot, alpha=alpha, lift=lift, dark=dark, tint=tint, deco=deco))
        if shad and alpha > 0.5:
            contact_shadow(canvas, u, sx, lift)
        return
    if deco is not None:
        k = DC.N / 512.0
        im = deco.resize((int(size * k), int(size * k)), Image.LANCZOS)
        tint = None
    else:
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


def make_proj(cx, cy, z, pitch, roll, sx, sy):
    th, rh = math.radians(pitch), math.radians(roll)
    f = FOC
    d = f / z
    r1 = np.array([math.cos(rh), math.sin(rh), 0.0])
    r2 = np.array([-math.cos(th) * math.sin(rh), math.cos(th) * math.cos(rh), -math.sin(th)])
    r3 = np.array([-math.sin(rh) * math.sin(th), math.cos(rh) * math.sin(th), math.cos(th)])
    t = np.array([0.0, 0.0, d])
    Wc, Hc = W / 2 + sx, H / 2 + sy

    def proj(X, Y, Zh):
        p = (X - cx) * r1 + (Y - cy) * r2 - Zh * r3 + t
        return (f * p[0] / p[2] + Wc, f * p[1] / p[2] + Hc, p[2])
    return proj


def persp_coeffs(dst, src):
    """PIL PERSPECTIVE coefficients mapping output (dst) pixels to input (src) pixels"""
    A, B = [], []
    for (x, y), (u_, v_) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u_ * x, -u_ * y])
        A.append([0, 0, 0, x, y, 1, -v_ * x, -v_ * y])
        B += [u_, v_]
    return np.linalg.solve(np.array(A, float), np.array(B, float))


def light_factor(u_t, pos):
    amb, pools = light_map(u_t)
    f = amb
    for (c, rad, st, col) in pools:
        g = math.exp(-(((pos[0] - c[0]) ** 2 + (pos[1] - c[1]) ** 2) / (rad ** 2))) * st
        f += g * 0.8
    return min(1.35, max(0.15, f))


def draw_pieces3d(frame, proj, u_t):
    phi = math.radians(CUR_PHI)
    cp, sp = math.cos(phi), math.sin(phi)
    k = PSU / 512.0
    recs = []
    for r in PLIST:
        im = r["deco"] if r["deco"] is not None else SPR[r["piece"]]
        Wp, Hp = im.size
        base_y = (PAD_BASE + DC.PAD) if r["deco"] is not None else PAD_BASE
        sx_, sy_ = abs(r["sx"]), r["sy"]
        x, y = r["u"]
        b0 = (Hp / 2 - base_y) * k * sy_
        rot = math.radians(r["rot"])
        cr, sr = math.cos(rot), math.sin(rot)
        corners_src = [(0, 0), (Wp, 0), (Wp, Hp), (0, Hp)]
        dep = proj(x, y, 0)[2]
        recs.append((dep, r, im, Hp, Wp, b0, sx_, sy_, cr, sr))
    recs.sort(key=lambda t: -t[0])
    K = 5
    for dep, r, im, Hp, Wp, b0, sx_, sy_, cr, sr in recs:
        x, y = r["u"]
        lf = light_factor(u_t, (x, y)) * r["dark"]
        base = im
        if r["sx"] < 0:
            base = base.transpose(Image.FLIP_LEFT_RIGHT)
        a = np.asarray(base).astype(np.float32)
        nl = K if (CUR_PHI > 45 and r["alpha"] > 0.5) else 1
        for li in range(nl):
            back = (nl - 1 - li) / max(1, nl - 1)          # 1 = rearmost layer
            shade = lf * (1.0 - 0.5 * back) if nl > 1 else lf
            pts = []
            for (spx, spy) in [(0, 0), (Wp, 0), (Wp, Hp), (0, Hp)]:
                aa = (spx - Wp / 2) * k * sx_
                bb = (Hp / 2 - spy) * k * sy_
                aa, bb = aa * cr - bb * sr, aa * sr + bb * cr
                X = x + aa
                Y = y - bb * cp
                Z = (bb - b0) * sp + r["lift"] * 0.9
                off = 9.0 * back
                X, Y, Z = X, Y + off * sp, Z - off * cp
                pts.append(proj(X, Y, Z)[:2])
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x0, y0, x1, y1 = int(min(xs)) - 2, int(min(ys)) - 2, int(max(xs)) + 3, int(max(ys)) + 3
            if x1 < 0 or y1 < 0 or x0 > W or y0 > H or x1 - x0 < 3 or y1 - y0 < 3 or x1 - x0 > 4000:
                continue
            dst = [(p[0] - x0, p[1] - y0) for p in pts]
            try:
                co = persp_coeffs(dst, [(0, 0), (Wp, 0), (Wp, Hp), (0, Hp)])
            except np.linalg.LinAlgError:
                continue
            arr = a.copy()
            arr[..., :3] = np.clip(arr[..., :3] * shade, 0, 255)
            arr[..., 3] = arr[..., 3] * r["alpha"]
            tile = Image.fromarray(arr.astype(np.uint8), "RGBA").transform((x1 - x0, y1 - y0), Image.PERSPECTIVE, tuple(co), Image.BICUBIC)
            frame.alpha_composite(tile, (x0, y0)) if x0 >= 0 and y0 >= 0 else frame.alpha_composite(tile.crop((max(0, -x0), max(0, -y0), tile.width, tile.height)), (max(0, x0), max(0, y0)))



# ----------------------------------------------------------------- time remap
SLOW = [(T[29], 0.28, 0.30, 0.45), (T[37], 0.22, 0.30, 0.40), (T[41], 0.45, 0.20, 0.60)]   # (hit, dip length, dip speed, run-up)
STOPS = [(T[29], 0.06), (T[37], 0.10), (T[41], 0.06)]                                      # freeze right after the hit, then catch up





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
    (0.52, S("h5", "g6"), 1.55, 0, 0, 0.48),
    (T[29] - 0.03, S("h5", "h6"), 2.05, 0, 3, 0.16),          # zoom crash on the explosion
    (T[30] - 0.05, S("g7", "h6"), 1.75, 0, 0, 0.30),
    (T[31] - 0.04, S("e3", "f4"), 1.12, 34, -6, 0.50),        # discovered check: board tilts, bishop's diagonal c1-h6 is visible
    (T[32] - 0.03, S("h5", "h6"), 1.70, 0, 0, 0.50),
    (T[33] - 0.03, S("f4", "h5"), 1.45, 0, 0, 0.55),
    (T[34] - 0.02, S("g5", "h6"), 1.70, 0, 0, 0.32),
    (T[35] - 0.04, S("d3", "f3"), 1.20, 0, 0, 0.62),
    (T[36] - 0.03, S("g6", "h6"), 1.80, 0, 0, 0.45),
    (T[36] + 0.34, S("f2", "f3"), 1.35, 0, 0, 0.30),
    (T[37] - 0.90, S("f4", "f4"), 1.28, 40, -6, 0.40),         # the walk of the cowboy rook: tilted, pieces stand up
    (T[37] + 0.25, S("f6", "g6"), 1.65, 38, -3, 0.45),
    (T[38] + 0.45, S("f5", "g6"), 1.65, 0, 0, 0.50),
    (T[39] - 0.03, S("g5", "g6"), 1.85, 0, 0, 0.28),
    (T[40] - 0.03, S("g6", "f6"), 1.95, 0, 0, 0.60),
    (T[41] - 0.12, S("f4", "g6"), 1.45, 42, 5, 0.55),         # mate: tilt, pieces stand
    (T[41] + 1.20, (560, 500), 1.10, 30, 7, 0.70),
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
SWAY = [(T[40] + 0.20, T[41] - 0.15, 0.6), (T[41] + 1.0, REW0, 0.8), (T[34] + 0.15, T[35] - 0.1, 0.5)]




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
    d = u - T[41]
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
    30: dict(dur=.30, prog=[(0, 0), (.4, .15), (1, 1)], sc=[(0, 1), (.5, 1.25), (1, 1)], rot=[(0, 0), (.5, 12), (1, 0)], st=.08, col=AMB),
    31: dict(dur=.42, prog=[(0, 0), (.2, -.05), (.55, .5), (.8, .92), (1, 1)], sc=[(0, 1), (.35, .72), (.75, 1.5), (1, 1)], rot=[(0, 0), (.3, 0), (.9, -360), (1, -360)], st=.08, trail=2, col=CYN),
    32: dict(dur=.35, prog=[(0, 0), (.5, .3), (1, 1)], sc=[(0, 1), (.5, .9), (1, 1)], rot=[(0, 0), (.4, -10), (1, 0)], st=.04, col=AMB),
    33: dict(dur=.50, prog=[(0, 0), (.15, -.04), (.4, .35), (.6, .75), (1, 1)], sc=[(0, 1), (.4, 1.25), (1, 1)], rot=[(0, 0), (1, 0)], flip=[(.3, 0), (.85, 360)], st=.10, trail=2, col=CYN),
    34: dict(dur=.26, prog=[(0, 0), (.5, .5), (1, 1)], sc=[(0, 1), (.5, 1.1), (1, 1)], rot=[(0, 0), (.5, 8), (1, 0)], st=.03, col=AMB),
    35: dict(dur=.50, prog=[(0, 0), (.3, .06), (.6, .7), (1, 1)], sc=[(0, 1), (.4, .85), (.8, 1.4), (1, 1)], rot=[(0, 0), (1, 0)], st=.12, trail=3, col=CYN),
    36: dict(dur=.30, prog=[(0, 0), (.5, .4), (1, 1)], sc=[(0, 1), (.5, 1.15), (1, 1)], rot=[(0, 0), (.4, -16), (.7, 10), (1, 0)], st=.03, col=AMB),
    38: dict(dur=.32, prog=[(0, 0), (.35, .1), (.75, .8), (1, 1)], sc=[(0, 1), (.4, 1.45), (1, 1)], rot=[(0, 0), (.5, -18), (1, 0)], st=.10, trail=2, col=AMB),
    39: dict(dur=.60, prog=[(0, 0), (.3, .1), (.7, .8), (1, 1)], sc=[(0, 1), (.4, .85), (1, 1)], rot=[(0, 0), (1, 0)], st=.26, trail=4, col=CYN),
    40: dict(dur=.30, prog=[(0, 0), (.5, .3), (1, 1)], sc=[(0, 1), (.5, 1.1), (1, 1)], rot=[(0, 0), (.4, -8), (1, 0)], st=.03, col=AMB),
}


_ip = {}


def curve(p, name):
    k = (p, name)
    if k not in _ip:
        pts = SPEC[p][name]
        _ip[k] = PchipInterpolator([a for a, _ in pts], [b for _, b in pts])
    return _ip[k]



PAD_BASE = 469
BASE = {k: v for k, v in SPR.items()}
_dc = {}


def deco_queen(u):
    if u >= T[29] + 0.50:
        return None
    key = ("q", round(u * 600))
    if key not in _dc:
        _dc.clear()
        _dc[key] = DC.queen_bazooka(BASE[("w", "Q")], u - T[29], lead=T[29])[0]
    return _dc[key]


def deco_rook(u):
    if u < WALK0 or u > T[38]:
        return None
    key = ("r", round(u * 600))
    if key not in _dc:
        _dc.clear()
        tip = ease_out((u - LAND[2]) / 0.18) if u >= LAND[2] else 0.0
        _dc[key] = DC.rook_cowboy(BASE[("w", "R")], 0, tip=tip, sway=u * 7.0, appear=clamp((u - WALK0) / 0.38))
    return _dc[key]


def cry_k(u):
    return clamp((u - CRY0) / 0.25) * (1 - ease_io((u - (REW0 - 0.45)) / 0.40))


def deco_king(u):
    if u < CRY0 or u >= REW0 or cry_k(u) <= 0.01:
        return None
    key = ("k", round(u * 600))
    if key not in _dc:
        _dc.clear()
        _dc[key] = DC.king_cry(BASE[("b", "K")], u - CRY0, k_in=cry_k(u), puddle=False)
    return _dc[key]


def deco_for_piece(pc, u, square=None, ply=None):
    if pc == ("w", "Q") and (ply == 29 or (square == sq("h5") and u < T[29])):
        return deco_queen(u)
    if pc == ("w", "R") and ply == 37:
        return deco_rook(u)
    if pc == ("b", "K"):
        return deco_king(u)
    return None



def rt(x):
    return round(x * FPS) / FPS


WALK0 = T[36] + 0.12
LAND = [rt(6.815), rt(7.315), T[37]]


def mover29(u, f, t, uv, L, h):
    """the queen lunges into the smoke AFTER the rocket has blown up h6"""
    if u < h or u > h + 0.55:
        return None
    d = u - h
    k = clamp(d / 0.24)
    pr = ease_out(k, 2.4)
    f, t = np.array(f), np.array(t)
    pos = f + (t - f) * pr
    s = math.sin(math.pi * min(1, k))
    sqz = settle(max(0.0, d - 0.24), 0.12, 26, 0.11)
    tr = [(tuple(f + (t - f) * ease_out(max(0, k - j * 0.12), 2.4)), 0.3 * (1 - j / 3.0), 1.0) for j in (1, 2)] if k < 1 else []
    return tuple(pos), (1 + sqz) * (1 - 0.1 * s), (1 - sqz) * (1 + 0.38 * s), 0.0, 14 * s, tr, None


def mover37(u, f, t, uv, L, h):
    """the cowboy rook strolls up the f-file in three hops on the beat, lands on f6 and tips its hat at the king"""
    if u < WALK0 or u > T[38]:
        return None
    f, t = np.array(f), np.array(t)
    prog_at = [0.0, 1 / 3.0, 2 / 3.0, 1.0]
    starts = [WALK0, LAND[0], LAND[1]]
    lift, rot, sx, sy = 0.0, 0.0, 1.0, 1.0
    pr = 1.0
    if u >= LAND[2]:
        d = u - LAND[2]
        sqz = settle(d, 0.10, 26, 0.10)
        sx, sy = 1 + sqz, 1 - sqz
        rot = 2.5 * math.sin(d * 14) * math.exp(-d / 0.3)
    else:
        for i in range(3):
            if u < LAND[i]:
                k = clamp((u - starts[i]) / (LAND[i] - starts[i]))
                pr = prog_at[i] + (prog_at[i + 1] - prog_at[i]) * ease_io(k)
                lift = 40 * math.sin(math.pi * k)
                rot = 9 * math.sin(math.pi * 2 * k) * (1 if i % 2 == 0 else -1)
                st = math.sin(math.pi * k)
                sx, sy = 1 - 0.10 * st, 1 + 0.16 * st
                if k < 0.12:
                    sy = 1 - 0.10 * (1 - k / 0.12)
                    sx = 1 + 0.08 * (1 - k / 0.12)
                break
    return tuple(f + (t - f) * pr), sx, sy, rot, lift, [], None


def mover(p, u):
    """-> (pos, sx, sy, rot, lift, trail, tint) while the mover is animated, else None"""
    m = MV[p]
    f, t = cu(m["from"]), cu(m["to"])
    h = T[p]
    L = np.linalg.norm(V(f, t))
    uv = V(f, t) / L
    if p == 41:
        return mover47(u, f, t, uv, L, h)
    if p == 29:
        return mover29(u, f, t, uv, L, h)
    if p == 37:
        return mover37(u, f, t, uv, L, h)
    sp = SPEC[p]
    dur = sp["dur"]
    if u < h - dur - 0.1 or u > h + 0.32:
        return None
    if u > h:
        d = u - h
        sqz = settle(d, 0.10 + sp["st"] * 0.6, 26, 0.11)
        o = settle(d, 0.10 * SQU, 22, 0.10) * (1 if p in (31, 33, 35, 39) else 0.4)
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



def hole(canvas, pos, r, a):
    if a <= 0.01 or r < 2:
        return
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    x, y = px(pos)
    d.ellipse((x - r * RS, y - r * RS * 0.9, x + r * RS, y + r * RS * 0.9), fill=(6, 6, 10, int(255 * a)))
    canvas.alpha_composite(ov)


def petals_fx(canvas, pos, e, seed=3, n=9):
    rs = np.random.RandomState(seed)
    ov = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    for i in range(n):
        ang = rs.uniform(-math.pi, 0.2)
        spd = rs.uniform(180, 420)
        x = pos[0] + math.cos(ang) * spd * e + rs.uniform(-20, 20)
        y = pos[1] - 40 + math.sin(ang) * spd * e + 520 * e * e
        a = clamp(1 - (e - 0.5) / 0.6)
        if a <= 0:
            continue
        pet = Image.new("RGBA", (60, 60), (0, 0, 0, 0))
        dd = ImageDraw.Draw(pet)
        dd.ellipse((8, 18, 52, 42), fill=(255, 132, 172, 255), outline=(176, 40, 92, 255), width=3)
        dd.ellipse((16, 22, 34, 32), fill=(255, 196, 218, 255))
        pet = pet.rotate(rs.uniform(0, 360) + e * rs.uniform(-500, 500), resample=Image.BICUBIC, expand=True)
        pet = pet.resize((int(pet.width * RS * 0.62), int(pet.height * RS * 0.62)), Image.BICUBIC)
        ov.alpha_composite(fade_im(pet, a), (int(x * RS - pet.width / 2), int(y * RS - pet.height / 2)))
    canvas.alpha_composite(ov)


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
    if p == 29:                                    # the knight is blown away by the rocket: scorched, thrown up-left, spinning
        if e > 1.0:
            return
        dk = max(0.28, 1 - 2.4 * e)
        draw_piece(canvas, pc, tuple(pos + np.array([-300 * e, -820 * e + 760 * e * e])), 1 - 0.2 * e, 1 - 0.2 * e, -620 * e, alpha=clamp(1 - (e - 0.55) / 0.4), shad=False, dark=dk)
    elif p == 30:                                  # the queen is sucked into the king: spirals and shrinks into his square
        if e > 0.6:
            return
        k = ease_in(e / 0.5, 1.8)
        tgt = f
        q = pos + (tgt - pos) * k
        sc = max(0.02, 1 - k)
        draw_piece(canvas, pc, tuple(q), sc, sc, 520 * k, alpha=clamp(1 - k * 0.5), shad=False)
    elif p == 38:                                  # greedy king eats the rook: rook flicked up, hat spins off one way, petals the other
        if e > 1.2:
            return
        draw_piece(canvas, pc, tuple(pos + np.array([-60 * e, -560 * e + 1250 * e * e])), 1, 1, 340 * e, alpha=clamp(1 - (e - 0.55) / 0.5), shad=False)
        hat = DC.hat_alone(-25 + 700 * e, 1.0)
        draw_piece(canvas, pc, tuple(pos + np.array([260 * e, -700 * e + 1100 * e * e])), 1, 1, 0, alpha=clamp(1 - (e - 0.6) / 0.5), shad=False, deco=hat)
        petals_fx(canvas, pos, e)




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



BADGE = {29: ("!!", (30, 188, 178)), 37: ("!!", (30, 188, 178)), 41: ("#", (205, 160, 40))}


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
        if p == 41:
            end = REW0 - 0.1
        if e < 0 or u > end:
            continue
        pop = 1 - math.exp(-e / 0.05) * math.cos(e * 20) if e < 1.0 else 1.0
        fadeout = clamp(1 - (u - (end - 0.25)) / 0.25)
        sc = max(0.01, pop) * (1.35 if p in (29, 37, 41) else 1.0)
        im = badge_img(p)
        b2 = im.resize((max(2, int(im.width * sc)), max(2, int(im.height * sc))), Image.BICUBIC)
        c = np.array(cu(MV[p]["to"])) + np.array([SQU * 0.46, -SQU * 0.46])
        put(canvas, fade_im(b2, fadeout), c[0] * RS, c[1] * RS)



def beam(dv, canvas, a_sq, b_sq, wd, col, a, glow_w=0, prog=1.0):
    """thick flat beam between two squares; optional soft glow behind it"""
    p0, p1 = np.array(cu(sq(a_sq))), np.array(cu(sq(b_sq)))
    v = p1 - p0
    L = np.linalg.norm(v)
    n = np.array([-v[1], v[0]]) / L
    q1 = p0 + v * clamp(prog)
    poly = [tuple(px(p0 + n * wd / 2)), tuple(px(q1 + n * wd / 2)), tuple(px(q1 - n * wd / 2)), tuple(px(p0 - n * wd / 2))]
    if glow_w > 0:
        g = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        dg = ImageDraw.Draw(g)
        dg.polygon([tuple(px(p0 + n * glow_w / 2)), tuple(px(q1 + n * glow_w / 2)), tuple(px(q1 - n * glow_w / 2)), tuple(px(p0 - n * glow_w / 2))], fill=col + (int(200 * a),))
        canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(18)))
    dv.polygon(poly, fill=col + (int(255 * a),))


def dust(dv, c, e, a=0.7, r0=34):
    """cartoon dust cloud: a ring of puffs"""
    if e < 0 or e > 0.7:
        return
    k = ease_out(e / 0.7, 2.0)
    al = int(255 * a * (1 - ease_in(e / 0.7, 1.6)))
    for i in range(6):
        ang = i * math.pi / 3 + 0.4
        rr = r0 * (0.8 + 1.4 * k)
        x, y = c[0] + math.cos(ang) * rr * 1.0, c[1] + 18 + math.sin(ang) * rr * 0.32
        r_ = r0 * (0.32 + 0.42 * k)
        p = px((x, y))
        dv.ellipse((p[0] - r_ * RS, p[1] - r_ * RS, p[0] + r_ * RS, p[1] + r_ * RS), fill=(214, 206, 190, al))


def drop(df, x, y, r, a):
    """a sweat / tear drop in board units"""
    p = px((x, y))
    R = r * RS
    col = (150, 214, 255, int(255 * a))
    df.polygon([(p[0], p[1] - R * 1.9), (p[0] - R * 0.9, p[1] - R * 0.3), (p[0] + R * 0.9, p[1] - R * 0.3)], fill=col)
    df.ellipse((p[0] - R, p[1] - R, p[0] + R, p[1] + R), fill=col, outline=(60, 140, 220, int(255 * a)), width=max(2, int(2 * RS)))
    df.ellipse((p[0] - R * 0.45, p[1] - R * 0.5, p[0] - R * 0.1, p[1] + R * 0.1), fill=(245, 252, 255, int(255 * a)))


def twinkle(df, c, r, a, ang=0.0):
    p = px(c)
    for k, col in ((1.0, (255, 214, 90)), (0.45, (255, 252, 230))):
        pts = []
        for i in range(8):
            aa = math.radians(ang + i * 45)
            rr = r * RS * k * (1.0 if i % 2 == 0 else 0.22)
            pts.append((p[0] + math.cos(aa) * rr, p[1] + math.sin(aa) * rr))
        df.polygon(pts, fill=col + (int(255 * a),))


_QINFO = [None]


def muzzle_world(u):
    """muzzle of the bazooka in board units (queen sits on h5)"""
    qc = np.array(cu(sq("h5")), float)
    info = _QINFO[0]
    if info is None:
        return qc + np.array([30.0, -50.0])
    muz = info[0]
    return qc + (np.array(muz) - 256) * (PSU / 512.0)


def rocket_fx(df, canvas, u):
    e = u - T[29]
    tgt = np.array(cu(sq("h6")), float)
    mz = muzzle_world(u)
    if -0.10 <= e < 0:
        k = (e + 0.10) / 0.10
        head = mz + (tgt - mz) * ease_in(k, 1.6)
        d = (tgt - mz) / np.linalg.norm(tgt - mz)
        n = np.array([-d[1], d[0]])
        tail = head - d * 70
        # smoke trail + flame
        for j in range(9):
            q = mz + (head - mz) * (j / 9.0)
            r = 9 + 7 * (1 - j / 9.0) + 8 * k
            pp = px(q)
            df.ellipse((pp[0] - r * RS, pp[1] - r * RS, pp[0] + r * RS, pp[1] + r * RS), fill=(205, 208, 216, int(190 * (j / 9.0))))
        fl = [tuple(px(tail + n * 9)), tuple(px(tail - d * (40 + 30 * (k % 0.3 > 0.15)))), tuple(px(tail - n * 9))]
        df.polygon(fl, fill=(255, 160, 40, 255))
        df.polygon([tuple(px(tail + n * 5)), tuple(px(tail - d * 24)), tuple(px(tail - n * 5))], fill=(255, 238, 170, 255))
        # body, nose, fins
        body = [tuple(px(tail + n * 10)), tuple(px(head - d * 22 + n * 10)), tuple(px(head - d * 22 - n * 10)), tuple(px(tail - n * 10))]
        df.polygon(body, fill=(226, 228, 236, 255), outline=(46, 50, 58, 255))
        df.polygon([tuple(px(head - d * 22 + n * 10)), tuple(px(head + d * 10)), tuple(px(head - d * 22 - n * 10))], fill=(220, 50, 46, 255), outline=(46, 50, 58, 255))
        for s_ in (-1, 1):
            df.polygon([tuple(px(tail + n * 10 * s_ + d * 6)), tuple(px(tail + n * 24 * s_ - d * 10)), tuple(px(tail + n * 10 * s_ - d * 14))], fill=(120, 126, 138, 255), outline=(46, 50, 58, 255))
    if e >= 0:
        # lingering smoke trail
        d = (tgt - mz) / np.linalg.norm(tgt - mz)
        a = clamp(1 - e / 0.8)
        for j in range(9):
            q = mz + (tgt - mz) * (j / 9.0)
            r = (14 + 8 * (1 - j / 9.0)) * (1 + 2.2 * e)
            pp = px(q + np.array([0, -30 * e]))
            df.ellipse((pp[0] - r * RS, pp[1] - r * RS, pp[0] + r * RS, pp[1] + r * RS), fill=(205, 208, 216, int(150 * a * (j / 9.0))))


def explosion_fx(df, canvas, u):
    e = u - T[29]
    if e < 0 or e > 1.3:
        return
    c = np.array(cu(sq("h6")), float)
    if e < 0.06:
        r = 90 + 220 * e
        p = px(c)
        df.ellipse((p[0] - r * RS, p[1] - r * RS, p[0] + r * RS, p[1] + r * RS), fill=(255, 255, 255, int(255 * (1 - e / 0.06))))
    # smoke clouds (dark, rising)
    rs = np.random.RandomState(12)
    for i in range(7):
        ang = rs.uniform(0, 2 * math.pi)
        dist = rs.uniform(20, 70)
        r0 = rs.uniform(36, 58)
        k = ease_out(e / 0.9, 1.8)
        a = clamp(1 - (e - 0.4) / 0.8)
        q = c + np.array([math.cos(ang) * dist * (0.4 + k), math.sin(ang) * dist * (0.4 + k) - 70 * k])
        r = r0 * (0.5 + 0.9 * k)
        p = px(q)
        df.ellipse((p[0] - r * RS, p[1] - r * RS, p[0] + r * RS, p[1] + r * RS), fill=(66, 66, 76, int(215 * a)), outline=(38, 38, 46, int(230 * a)), width=int(3 * RS))
        df.ellipse((p[0] - r * 0.6 * RS, p[1] - r * 0.85 * RS, p[0] + r * 0.2 * RS, p[1] - r * 0.1 * RS), fill=(120, 120, 132, int(140 * a)))
    # cartoon fireball with lobes
    if e < 0.55:
        k = ease_out(e / 0.16, 2.2)
        fade = clamp(1 - (e - 0.16) / 0.38)
        for sc_, col in ((1.0, (232, 70, 26)), (0.78, (255, 140, 40)), (0.52, (255, 206, 70)), (0.28, (255, 248, 214))):
            R = (40 + 105 * k) * sc_ * (1 + 0.04 * math.sin(e * 40))
            pts = []
            for i in range(28):
                a_ = i * 2 * math.pi / 28
                rr = R * (1.0 + 0.2 * math.sin(a_ * 5 + sc_ * 7) + 0.1 * math.sin(a_ * 9 + e * 8))
                pts.append((c[0] + math.cos(a_) * rr, c[1] + math.sin(a_) * rr))
            pp = [px(q) for q in pts]
            df.polygon(pp, fill=col + (int(255 * fade),))
            if sc_ == 1.0:
                df.line(pp + [pp[0]], fill=(70, 28, 16, int(255 * fade)), width=int(5 * RS), joint="curve")
    # shock ring
    if e < 0.4:
        r = 50 + 260 * ease_out(e / 0.4, 2.0)
        p = px(c)
        df.ellipse((p[0] - r * RS, p[1] - r * RS, p[0] + r * RS, p[1] + r * RS), outline=(255, 255, 255, int(230 * (1 - e / 0.4))), width=int(8 * RS))
    # sparks / debris
    rs = np.random.RandomState(5)
    for i in range(16):
        ang = rs.uniform(0, 2 * math.pi)
        spd = rs.uniform(380, 900)
        ln = rs.uniform(24, 58)
        d0 = (1 - math.exp(-4.0 * e)) / 4.0 * spd
        a = clamp(1 - e / 0.45)
        if a <= 0:
            continue
        p0 = c + np.array([math.cos(ang), math.sin(ang)]) * d0 + np.array([0, 300 * e * e])
        p1 = p0 + np.array([math.cos(ang), math.sin(ang)]) * ln
        df.line([px(p0), px(p1)], fill=((255, 214, 80) if i % 2 else (255, 130, 40)) + (int(255 * a),), width=int(5 * RS))



# ----------------------------------------------------------------- effects under pieces (each designed for its move)
def accent(p):
    return CYN if MV[p]["piece"][0] == "w" else AMB



def king_sq_at(u):
    base = sum(1 for p in PLIES if T[p] <= u)
    st = STATES[P0 + base]
    for s_, pc in st.items():
        if pc == ("b", "K"):
            return s_
    return sq("g6")


def under_fx(u, dv, canvas):
    cur = max([p for p in PLIES if T[p] - 0.12 <= u], default=None)
    if cur is not None and cur != 41 and u < REW0:
        k = ease_io((u - (T[cur] - 0.12)) / 0.18)
        col = accent(cur)
        sq_fill(dv, MV[cur]["from"], col, 0.20 * k)
        sq_fill(dv, MV[cur]["to"], col, 0.42 * k)
    for p in PLIES:
        e = u - T[p]
        if 0 <= e < 0.9 and p != 41:
            glow(canvas, cu(MV[p]["to"]), accent(p), 110 + 150 * KS[p], 0.5 * KS[p] * math.exp(-e / 0.32))
    # scorch mark on h6 after the rocket
    h = T[29]
    if u >= h:
        sq_fill(dv, sq("h6"), (20, 16, 14), 0.38 * clamp(1 - (u - h - 0.5) / 1.5) * clamp((u - h) / 0.05))
    # puddles of the crying king (flat on the board, under the piece)
    if CRY0 <= u < REW0 + 0.0:
        fade = clamp(1 - (u - (REW0 - 0.5)) / 0.4)
        for sqn, t0, t1 in (("f6", CRY0, T[40] + 0.9), ("g6", T[40], 99)):
            if u < t0:
                continue
            w = ease_out((u - t0) / 1.3, 2.0) * 300 * (1 - clamp((u - t1) / 0.6)) * fade
            if w < 6:
                continue
            c = px(cu(sq(sqn)))
            c = (c[0], c[1] + 42 * RS)
            dv.ellipse((c[0] - w / 2 * RS, c[1] - w / 7 * RS, c[0] + w / 2 * RS, c[1] + w / 7 * RS), fill=(70, 150, 235, 130), outline=(160, 218, 255, 190), width=int(3 * RS))
            dv.ellipse((c[0] - w / 4 * RS, c[1] - w / 16 * RS, c[0] + w / 6 * RS, c[1] + w / 30 * RS), fill=(190, 230, 255, 130))
    # 29 Qxh6+ : target lock on h6, then the red check arrow to the king
    h = T[29]
    if 0.35 <= u < h:
        k = ease_io((u - 0.35) / 0.45)
        bracket(dv, sq("h6"), AMB, 0.9 * k, 1.9 - 0.9 * k, 11)
    if h <= u <= h + 1.2:
        e = u - h
        a = 0.95 * ease_io((e - 0.05) / 0.10) * (1 - ease_io((e - 0.8) / 0.4))
        arrow_poly(dv, cu(sq("h6")), cu(sq("g7")), ease_out((e - 0.05) / 0.20, 2.4), RED, a, wd=30)
        bracket(dv, sq("g7"), RED, a, 1 + 0.14 * math.exp(-e / 0.14), 11)
    # 30 Kxh6 : greedy king, short amber arrow
    h = T[30]
    if h - 0.2 <= u <= h + 0.6:
        a = ease_io((u - h + 0.2) / 0.12) * (1 - ease_io((u - h) / 0.5))
        arrow_poly(dv, cu(sq("g7")), cu(sq("h6")), ease_out((u - h + 0.2) / 0.25, 2.0), AMB, 0.85 * a, wd=24)
    # 31 Ne6+ : the knight steps aside and the bishop's diagonal c1-h6 hits the king (discovered check)
    h = T[31]
    if h - 0.05 <= u <= h + 1.1:
        e = u - h + 0.05
        a = ease_io(e / 0.08) * (1 - ease_io((e - 0.55) / 0.55))
        beam(dv, canvas, "c1", "h6", 40 * (1 + 0.3 * math.exp(-e / 0.12)), (232, 246, 255), 0.95 * a, glow_w=78, prog=ease_out(e / 0.16, 2.0))
        bracket(dv, sq("h6"), RED, a, 1 + 0.14 * math.exp(-e / 0.14), 11)
        bracket(dv, sq("c1"), CYN, a * 0.9, 1 + 0.06 * math.sin(e * 16), 9)
    # 32 Kh5 : amber arrow; the next knight route d5 -> f4 is foreshadowed
    h = T[32]
    if h - 0.2 <= u <= h + 1.1:
        e = u - h
        a = ease_io((e + 0.2) / 0.1) * (1 - ease_io((e - 0.1) / 0.4))
        arrow_poly(dv, cu(sq("h6")), cu(sq("h5")), ease_out((e + 0.2) / 0.25, 2.0), AMB, 0.85 * a, wd=24)
        b = 0.5 * ease_io((e - 0.35) / 0.25) * (1 if u < T[33] else 0)
        if b > 0.01:
            arrow_poly(dv, cu(sq("d5")), cu(sq("f4")), ease_out((e - 0.35) / 0.55, 2.0), CYN, b, wd=30)
    # 33 Ndf4+ : knight blocks its own bishop's diagonal; a hexagon flash on f4; red check arrow to h5
    h = T[33]
    if h <= u <= h + 1.0:
        e = u - h
        a = 0.95 * ease_io(e / 0.08) * (1 - ease_io((e - 0.55) / 0.4))
        arrow_poly(dv, cu(sq("f4")), cu(sq("h5")), ease_out(e / 0.20, 2.4), RED, a, wd=30)
        bracket(dv, sq("h5"), RED, a, 1 + 0.14 * math.exp(-e / 0.14), 11)
        if e < 0.5:
            c = cu(sq("f4"))
            r = SQU * (0.55 + 0.9 * ease_out(e / 0.5, 2.0))
            pts = [px((c[0] + math.cos(math.radians(60 * i + 30)) * r, c[1] + math.sin(math.radians(60 * i + 30)) * r)) for i in range(6)]
            dv.line(pts + [pts[0]], fill=CYN + (int(255 * 0.9 * (1 - e / 0.5)),), width=int(8 * RS / 2), joint="curve")
    # 34 Kh6 : back into the diagonal, red bracket throbbing
    h = T[34]
    if h - 0.2 <= u <= h + 1.0:
        e = u - h
        a = ease_io((e + 0.2) / 0.1) * (1 - ease_io((e - 0.1) / 0.4))
        arrow_poly(dv, cu(sq("h5")), cu(sq("h6")), ease_out((e + 0.2) / 0.22, 2.0), AMB, 0.85 * a, wd=24)
        bracket(dv, sq("h6"), RED, 0.9 * clamp(e / 0.15) * (1 - ease_io((e - 0.8) / 0.2)), 1 + 0.08 * math.sin(e * 14), 10)
    # 35 Ne2+ : the knight leaps away again (curved cyan arrow), diagonal reopens
    h = T[35]
    if h - 0.1 <= u <= h + 0.9:
        e = u - h
        a = 0.9 * ease_io((e + 0.1) / 0.1) * (1 - ease_io((e - 0.4) / 0.4))
        arrow_poly(dv, cu(sq("f4")), cu(sq("e2")), ease_out((e + 0.1) / 0.25, 2.0), CYN, a, wd=26)
        bracket(dv, sq("h6"), RED, a, 1 + 0.12 * math.exp(-e / 0.14), 11)
    # 36 Kg6 : amber arrow; the rook route f1 -> f6 is foreshadowed slowly
    h = T[36]
    if h - 0.2 <= u <= h + 1.5:
        e = u - h
        a = ease_io((e + 0.2) / 0.1) * (1 - ease_io((e - 0.1) / 0.4))
        arrow_poly(dv, cu(sq("h6")), cu(sq("g6")), ease_out((e + 0.2) / 0.22, 2.0), AMB, 0.85 * a, wd=24)
        b = 0.5 * ease_io((e - 0.4) / 0.3) * (1 if u < WALK0 + 0.9 else 0)
        if b > 0.01:
            arrow_poly(dv, cu(sq("f1")), cu(sq("f6")), ease_out((e - 0.4) / 0.9, 2.0), CYN, b, wd=30)
    # 37 : dust puffs at every hop landing, then the red check arrow to the king
    for lt in LAND:
        dust(dv, cu(sq("f1")) if False else (cu(sq("f1"))[0], cu(sq("f1"))[1] - (LAND.index(lt) + 1) / 3.0 * 5 * SQU), u - lt)
    h = T[37]
    if h <= u <= h + 0.9:
        e = u - h
        a = 0.95 * ease_io(e / 0.10) * (1 - ease_io((e - 0.35) / 0.1))
        arrow_poly(dv, cu(sq("f6")), cu(sq("g6")), ease_out(e / 0.20, 2.4), RED, a, wd=30)
        bracket(dv, sq("g6"), RED, a, 1 + 0.14 * math.exp(-e / 0.14), 11)
    # 38 Kxf6 : short amber arrow
    h = T[38]
    if h - 0.25 <= u <= h + 0.5:
        a = ease_io((u - h + 0.25) / 0.15) * (1 - ease_io((u - h) / 0.5))
        arrow_poly(dv, cu(sq("g6")), cu(sq("f6")), ease_out((u - h + 0.25) / 0.25, 2.0), AMB, 0.85 * a, wd=24)
    # 39 Bg5+ : speed lines along the diagonal, red check arrow
    h = T[39]
    if h - 0.60 <= u < h:
        k = (u - (h - 0.60)) / 0.60
        speed_lines(dv, S("d2", "e3"), tuple(V(cu(sq("c1")), cu(sq("g5")))), 380, 10, 8, 0.6 * (1 - 0.3 * k), spread=70)
    if h <= u <= h + 1.0:
        e = u - h
        a = 0.95 * ease_io(e / 0.10) * (1 - ease_io((e - 0.6) / 0.4))
        arrow_poly(dv, cu(sq("g5")), cu(sq("f6")), ease_out(e / 0.20, 2.4), RED, a, wd=30)
        bracket(dv, sq("f6"), RED, a, 1 + 0.14 * math.exp(-e / 0.14), 11)
    # 40 Kg6 : amber arrow; the mating knight route e2 -> f4 draws slowly
    h = T[40]
    if h - 0.2 <= u <= h + 0.5:
        a = ease_io((u - h + 0.2) / 0.12) * (1 - ease_io((u - h) / 0.5))
        arrow_poly(dv, cu(sq("f6")), cu(sq("g6")), ease_out((u - h + 0.2) / 0.25, 2.0), AMB, 0.85 * a, wd=24)
    if T[40] + 0.20 <= u < T[41] + 0.35:
        g0, g1 = T[40] + 0.20, T[41] - 0.25
        gl = ease_io((u - g0) / (g1 - g0))
        fade = 1.0 if u < T[41] else clamp(1 - (u - T[41]) / 0.35)
        col = CYN if u < T[41] else WHITE
        thr = 1 + 0.10 * math.sin((u - g0) * 11) * (1 if u < T[41] else 0)
        arrow_poly(dv, cu(sq("e2")), cu(sq("f4")), gl, col, 0.88 * fade, wd=34 * thr, head=1.25)
        arrow_poly(dv, cu(sq("f4")), cu(sq("g6")), gl, col, 0.60 * fade, wd=26 * thr, head=1.0)
        if gl > 0.9 and u < T[41]:
            bracket(dv, sq("g6"), RED, 0.8 + 0.2 * math.sin(u * 14), 1.0, 10)
    if T[41] <= u < REW0:
        e = u - T[41]
        a = 1 - ease_io((u - (REW0 - 0.4)) / 0.4)
        sq_fill(dv, sq("e2"), WHITE, 0.18 * a)
        sq_fill(dv, sq("f4"), WHITE, 0.40 * a)
        pulse = 1 + 0.12 * math.exp(-e / 0.10) * math.cos(e * 24)
        c = px(cu(sq("g6")))
        r = SQU * RS / 2 * pulse
        dv.rectangle((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=RED + (int(255 * clamp(e / 0.04) * 0.96 * a),))



def over_fx(u, df, canvas):
    # 29: the bazooka rocket and the explosion on h6
    rocket_fx(df, canvas, u)
    explosion_fx(df, canvas, u)
    # 35: lightning along the bishop's diagonal c1 -> h6 (electric discovered check)
    h = T[35]
    if h <= u < h + 0.22:
        e = u - h
        if int(e * 60) % 2 == 0 or e < 0.05:
            bolt(df, cu(sq("c1")), cu(sq("h6")), int(e * 60) + 7, wd=8, branches=4, col=CYN)
    # 36: the king sweats: three drops fly off and fall
    h = T[36]
    if h <= u < h + 1.1:
        e = u - h
        kc = cu(sq("g6"))
        for j, (dx, vx, vy) in enumerate(((-30, -90, -240), (24, 70, -300), (4, 10, -200))):
            ee = e - 0.08 * j
            if ee < 0:
                continue
            x = kc[0] + dx + vx * ee
            y = kc[1] - 46 + vy * ee + 700 * ee * ee
            drop(df, x, y, 8, clamp(1 - (ee - 0.5) / 0.4))
    # 37: the hat's buckle twinkles when the cowboy lands and tips his hat
    h = T[37]
    if h + 0.04 <= u <= T[38]:
        e = u - h - 0.04
        c = cu(sq("f6"))
        twinkle(df, (c[0] - 6, c[1] - 56), 22 * ease_out(e / 0.12, 2.0) * (1 - clamp((e - 0.12) / 0.3)), 1.0, ang=e * 90)
    # 41: the knight's launch streaks, then red cracks f4 -> g6 (the king breaks)
    h = T[41]
    if h - 0.28 <= u < h:
        speed_lines(df, cu(sq("e2")), (1, -2), 520, 12, 17, 0.55 * ease_io((u - h + 0.28) / 0.1), spread=60, wd=3.6)
    if h <= u < REW0 - 0.3:
        e = u - h
        grow = ease_out(e / 0.20, 2.2)
        fade = clamp(1 - (e - 0.55) / 0.9)
        if grow > 0 and fade > 0:
            rs2 = np.random.RandomState(31)
            B_TO, K_TO = cu(sq("f4")), cu(sq("g6"))
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
                p_ = np.array(K_TO, float)
                segs.append([p_, p_ + np.array([math.cos(ang), math.sin(ang)]) * 45 + rs2.uniform(-6, 6, 2), p_ + np.array([math.cos(ang + .25), math.sin(ang + .25)]) * 95])
            for si, pts in enumerate(segs):
                last = max(1, int(round((len(pts) - 1) * grow)))
                w = max(2, int((5.0 if si == 0 else 3.2) * RS))
                df.line([tuple(np.array(q) * RS) for q in pts[:last + 1]], fill=RED + (int(235 * fade),), width=w, joint="curve")



# ----------------------------------------------------------------- lighting
def light_events():
    return [
        (T[29] - 0.45, 0.20, 0.55, 0.50, 0.45, ("h5", "h6"), 300, 1.0, AMB),
        (T[31] - 0.10, 0.12, 0.40, 0.50, 0.30, ("e3", "h6"), 380, 0.8, CYN),
        (T[36] - 0.10, 0.20, 0.50, 0.45, 0.40, ("g6", "h6"), 240, 0.7, (120, 150, 255)),
        (T[37] - 0.55, 0.30, 0.95, 0.50, 0.42, ("f4", "f6"), 300, 1.0, (255, 200, 90)),
        (T[41] - 0.30, 0.30, 1.20, 0.80, 0.62, ("f4", "g6"), 280, 1.2, RED),
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



GRADE = [(0.0, (1, 1, 1)), (0.4, (0.92, 1.0, 1.08)), (T[29] + 0.05, (1.14, 1.0, 0.86)), (T[31] - 0.3, (0.90, 1.0, 1.10)),
         (T[35], (0.95, 0.98, 1.06)), (T[36] + 0.3, (1.10, 1.02, 0.90)), (T[37] + 0.3, (0.90, 1.06, 1.08)), (T[39] - 0.1, (0.88, 0.95, 1.12)),
         (T[41] - 0.3, (1.0, 0.97, 1.05)), (T[41] + 0.1, (1.14, 0.90, 0.90)), (REW0, (1.10, 0.92, 0.92)), (REW1, (1, 1, 1)), (DUR + 1, (1, 1, 1))]




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
    for tk, amp, dec in ((T[29], 11, 0.10), (T[37], 7, 0.08), (T[41], 15, 0.16)):
        d = t - tk
        if 0 <= d < 0.4:
            rgb = max(rgb, amp * math.exp(-d / dec))
    flash = 0.0
    for tk, a, dec in ((T[29], 0.32, 0.05), (T[37], 0.28, 0.05), (T[41], 0.60, 0.07)):
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
            if pc == ("b", "K") and ID_END[i_] == sq("g6"):
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
    state = dict(STATES[P0 + base])
    excl, movers = set(), []
    for p in PLIES:
        r = mover(p, u)
        if r is None:
            continue
        excl.add(MV[p]["from"] if u < T[p] else MV[p]["to"])
        movers.append((p, r))
    items = sorted(state.items(), key=lambda kv: -kv[0][1])
    kjit = {}
    for p in (29, 31, 33, 35, 37, 39):
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
        if pc == ("b", "K") and u >= T[41] and s_ == sq("g6"):
            e = u - T[41]
            j = math.exp(-e / 0.12)
            pos = (pos[0] + 6 * j * math.sin(e * 90), pos[1] + 5 * j * math.cos(e * 70))
            rot = -11 * (1 - math.exp(-e / 0.05)) * (0.85 + 0.15 * math.exp(-e / 0.6))
            if e > 0.9:
                kk = ease_in((e - 0.9) / 0.55, 2.0)
                rot = lerp(-11, -84, kk) + settle(e - 1.45, 5, 18, 0.2) * (e > 1.45)
                pos = (pos[0] + 24 * kk, pos[1] + 28 * kk)
        elif pc == ("b", "K") and CRY0 <= u < REW0:      # sobbing: small hiccup bounces and a tremble
            hop = abs(math.sin(u * 9.4))
            pos = (pos[0] + 1.6 * math.sin(u * 57), pos[1] - 3.2 * hop ** 3)
        elif s_ in kjit:
            pos = (pos[0] + kjit[s_][0], pos[1] + kjit[s_][1])
        draw_piece(canvas, pc, pos, 1, 1, rot, deco=deco_for_piece(pc, u, square=s_))
    for p in PLIES:
        captured_draw(p, u, canvas)
    for p, (pos, sx, sy, rot, lift, tr, tint) in movers:
        pc = MV[p]["piece"]
        dk = deco_for_piece(pc, u, ply=p)
        if pc == ("b", "K") and CRY0 <= u < REW0:
            pos = (pos[0] + 1.6 * math.sin(u * 57), pos[1] - 3.2 * abs(math.sin(u * 9.4)) ** 3)
        for tp, ta, tsc in tr:
            draw_piece(canvas, pc, tp, tsc, tsc, 0, alpha=ta, shad=False)
        draw_piece(canvas, pc, pos, sx, sy, rot, lift=lift, tint=tint if tint and tint[1] > 0 else None, deco=dk)
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
    global CUR_PHI
    t = fi / FPS
    u = warp(t)
    cx, cy, z, pi_, ro, sx, sy = camera(u)
    CUR_PHI = stand_of(pi_)
    PLIST.clear()
    canvas = draw_scene(u)
    Hm = homography(cx, cy, z, pi_, ro, sx, sy)
    Hi = np.linalg.inv(Hm)
    A = np.array([[RS, 0, cx * RS], [0, RS, cy * RS], [0, 0, 1.0]])
    M = A @ Hi
    M = M / M[2, 2]
    coeffs = (M[0, 0], M[0, 1], M[0, 2], M[1, 0], M[1, 1], M[1, 2], M[2, 0], M[2, 1])
    wp = canvas.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    frame = Image.fromarray(background(), "RGB").convert("RGBA")
    frame.alpha_composite(wp)
    if PLIST:
        draw_pieces3d(frame, make_proj(cx, cy, z, pi_, ro, sx, sy), u)
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
        os.makedirs(TAL + "dbgt", exist_ok=True)
        import time
        for tt in sys.argv[2:]:
            t0 = time.time()
            render(int(round(float(tt) * FPS))).save(TAL + "dbgt/c_%s.png" % tt)
            print(tt, "%.2fs" % (time.time() - t0), flush=True)
    elif mode == "times":
        print({p: round(T[p], 3) for p in PLIES}, "REW", round(REW0, 2), round(REW1, 2), "DUR", round(DUR, 2), "frames", NFRAMES)
        print("warp check", [round(warp(T[p]) - T[p], 4) for p in (29, 37, 41)], "end", round(warp(DUR) - DUR, 3))
    else:
        encode_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])
