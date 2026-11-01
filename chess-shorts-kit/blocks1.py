HEADER = '''"""Tarrasch-Romberg (rook-odds FEN), plies 29-41 (15.Qxh6+ .. 21.N2f4#), house style v5 + editor's brief.
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
'''

GAME = '''SAN = parse_moves(open(TAL + "pgn_tar.txt").read())
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
'''

DRAWPIECE = '''CUR_PHI = 0.0          # 0 = top-down flat icons; 90 = pieces standing upright (tilted board moments)
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
'''
