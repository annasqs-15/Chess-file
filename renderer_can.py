"""Canal-NN (Scandinavian), plies 16-27 (16...Bb4 .. 27.Ba6#), house style v5 + editor's brief + real 3D (lathe) pieces on tilted moments.
Hand enters at the first move, greedy golden queen, sunglasses king, martyr queen, puppet strings, lava cracks, bear trap, iron grate."""
import sys, math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.interpolate import PchipInterpolator
from scipy import ndimage as ndi

WORK = os.path.dirname(os.path.abspath(__file__)) + "/"
TAL = WORK
sys.path.insert(0, WORK)
from minichess import Board, parse_moves, sq
from meaning import analyse
import decor as DC
import decor2 as D2

W, H, FPS = 1080, 1920, 60
RS = 2.0
BU, SQU, MU = 1000, 125, 60
SWU = BU + 2 * MU
BP, MP, SWP = int(BU * RS), int(MU * RS), int(SWU * RS)
PSU = 112
A0 = 6.7
CYN = (46, 205, 255)
AMB = (255, 170, 52)
RED = (232, 40, 48)
MAG = (255, 60, 190)
WHITE = (240, 242, 248)
GOLD = (255, 200, 64)
BG1, BG2 = (30, 32, 40), (8, 8, 12)

# hit times on the beat grid of the track (105 BPM, grid 0.2858 s), audio seconds
HITS_A = [7.76, 8.91, 9.48, 10.05, 10.62, 11.19, 11.76, 13.48, 15.19, 18.05, 18.62, 21.00]
PLIES = list(range(16, 28))
P0 = 15
T = {p: round((a - A0) * FPS) / FPS for p, a in zip(PLIES, HITS_A)}
REW0 = T[27] + 1.5
REW1 = REW0 + 1.0
DUR = REW1 + 0.12
KS = {16: .3, 17: .3, 18: .25, 19: .45, 20: .4, 21: .55, 22: 1.0, 23: .4, 24: .7, 25: 1.2, 26: .5, 27: 1.4}
ACC = [(15.76, .22), (16.34, .22), (16.91, .25), (17.48, .25)]
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




SAN = parse_moves(open(TAL + "pgn_can.txt").read())
_b = Board()
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
    if m.get("castle"):
        rf, rt_, _pc = m["extra"]
        _cur[rt_] = _cur.pop(rf)
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
PAD_BASE = 469         # row of the sprite where the piece touches the board
BASE = {k: v for k, v in SPR.items()}
_look_cache = {}


def stand_of(pitch):
    return 90.0 * ease_io(clamp((pitch - 2.0) / 30.0))


def look_img(piece, look):
    """base sprite recoloured: look = (gold 0..1, grey 0..1) or None"""
    if not look or (look[0] < 0.01 and look[1] < 0.01):
        return SPR[piece]
    key = (piece, int(look[0] * 24), int(look[1] * 24))
    if key not in _look_cache:
        if len(_look_cache) > 60:
            _look_cache.clear()
        _look_cache[key] = D2.golden(SPR[piece], key[1] / 24.0, key[2] / 24.0)
    return _look_cache[key]


def contact_shadow(canvas, u, sx, lift):
    k = CUR_PHI / 90.0
    w = PSU * 0.82 * abs(sx)
    ov = Image.new("RGBA", (int(w * 2.4 * RS), int(w * 1.1 * RS)), (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    d.ellipse((ov.width * 0.12, ov.height * 0.25, ov.width * 0.88, ov.height * 0.75), fill=(0, 0, 0, int(135 * k * (1 - 0.6 * clamp(lift / 120.0)))))
    ov = ov.filter(ImageFilter.GaussianBlur(3.2 * RS))
    put(canvas, ov, (u[0] + 9) * RS, (u[1] + 8 + lift * 0.25) * RS)


def draw_piece(canvas, piece, u, sx=1.0, sy=1.0, rot=0.0, alpha=1.0, shad=True, lift=0.0, dark=1.0, tint=None, deco=None, look=None):
    if alpha <= 0.01:
        return
    size = PSU * RS
    if CUR_PHI > 0.5:
        if alpha > 0.5:
            PLIST.append(dict(piece=piece, u=u, sx=sx, sy=sy, rot=rot, alpha=alpha, lift=lift, dark=dark, deco=deco, look=look))
            if shad:
                contact_shadow(canvas, u, sx, lift)
        return
    if deco is not None:
        k = DC.N / 512.0
        im = deco.resize((int(size * k), int(size * k)), Image.LANCZOS)
        tint = None
    elif look and (look[0] > 0.01 or look[1] > 0.01):
        im = look_img(piece, look).resize((int(size), int(size)), Image.LANCZOS)
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


# ----------------------------------------------------------------- real 3D pieces: lathe meshes from the sprite silhouettes, inflated knight
_MESH = {}
NTH = 170
LDIR = np.array([-0.44, 0.34, 0.83])
LDIR = LDIR / np.linalg.norm(LDIR)


def _lathe(arr):
    alpha = arr[..., 3] > 100
    ys = np.nonzero(alpha.any(1))[0]
    y0, y1 = ys[0], ys[-1]
    xmin = np.zeros(512)
    xmax = np.zeros(512)
    for y in range(y0, y1 + 1):
        xs = np.nonzero(alpha[y])[0]
        xmin[y], xmax[y] = (xs.min(), xs.max()) if len(xs) else (256, 256)
    cx = (xmin + xmax) / 2.0
    r = np.maximum(alpha.sum(1) / 2.0, 1.0)         # area-equivalent radius: gaps (crown spikes, eye holes, slits) narrow the body
    rows = np.arange(y0, y1 + 1)
    rs = np.convolve(np.pad(r[rows], 3, mode="edge"), np.ones(7) / 7, "valid")
    # profile polyline: top centre, outward along the top, down the side
    prof = [(0.0, float(y0))] + [(float(rs[i]), float(rows[i])) for i in range(len(rows))]
    prof = np.array(prof)
    seg = np.hypot(np.diff(prof[:, 0]), np.diff(prof[:, 1]))
    cum = np.r_[0, np.cumsum(seg)]
    M = 300
    sp = np.linspace(0, cum[-1], M)
    rr = np.interp(sp, cum, prof[:, 0])
    yy = np.interp(sp, cum, prof[:, 1])
    dr = np.gradient(rr)
    db = -np.gradient(yy)
    ln = np.hypot(dr, db) + 1e-6
    nr = -db / ln          # radial component of the outward normal
    nb = dr / ln           # vertical component (up)
    th = np.linspace(-np.pi, np.pi, NTH, endpoint=False)
    st, ct = np.sin(th), np.cos(th)
    R = rr[:, None] * np.ones_like(th)[None, :]
    a = R * st[None, :]
    c = R * ct[None, :]
    b = 256.0 - yy[:, None] * np.ones_like(th)[None, :]
    na = nr[:, None] * st[None, :]
    nc = nr[:, None] * ct[None, :]
    nbb = nb[:, None] * np.ones_like(th)[None, :]
    cxr = np.interp(yy, rows, cx[rows])
    tx = np.clip(np.round(cxr[:, None] + a), 0, 511).astype(int)
    ty = np.clip(np.round(yy[:, None] * np.ones_like(th)[None, :]), 0, 511).astype(int)
    f = lambda v: v.ravel()
    return dict(a=f(a), b=f(b), c=f(c), na=f(na), nb=f(nbb), nc=f(nc), tx=f(tx), ty=f(ty), back=f(np.where(c < 0, 1, 0)))


def _inflate(arr):
    mask = arr[..., 3] > 100
    d = ndi.distance_transform_edt(mask)
    Rr = 30.0
    z = 74.0 * np.sqrt(np.clip(1 - (1 - np.minimum(d, Rr) / Rr) ** 2, 0, 1)) * (0.72 + 0.28 * np.minimum(d / 90.0, 1))
    z = ndi.gaussian_filter(z, 1.5)
    gy, gx = np.gradient(z)
    ys, xs = np.nonzero(mask)
    sel = ((xs % 2) == 0) & ((ys % 2) == 0)
    xs, ys = xs[sel], ys[sel]
    zz = z[ys, xs]
    nx, ny, nz = -gx[ys, xs], gy[ys, xs], np.ones_like(zz)      # local normal (a, b up, c) for the front
    nl = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    nx, ny, nz = nx / nl, ny / nl, nz / nl
    a = (xs - 256.0)
    b = 256.0 - ys
    A = np.r_[a, a]
    B = np.r_[b, b]
    C = np.r_[zz, -zz]
    return dict(a=A, b=B, c=C, na=np.r_[nx, -nx], nb=np.r_[ny, -ny], nc=np.r_[nz, -nz], tx=np.r_[xs, xs], ty=np.r_[ys, ys],
                back=np.r_[np.zeros(len(xs)), np.ones(len(xs))])


def mesh_of(piece):
    if piece not in _MESH:
        arr = np.asarray(SPR[piece])
        m = _inflate(arr) if piece[1] == "N" else _lathe(arr)
        if piece[1] == "K":      # keep the eye holes as dark sockets (decor paints the eyes / sunglasses into them)
            solid = arr[..., 3] > 60
            idx = ndi.distance_transform_edt(~solid, return_distances=False, return_indices=True)
            fill = arr[idx[0], idx[1], :3].astype(np.float32) * 0.45
            a_ = arr[m["ty"], m["tx"], 3] > 60
            m["col"] = np.where(a_[:, None], arr[m["ty"], m["tx"], :3].astype(np.float32), fill[m["ty"], m["tx"]])
        else:
            keep = arr[m["ty"], m["tx"], 3] > 60
            m = {k: v[keep] for k, v in m.items()}
            m["col"] = arr[m["ty"], m["tx"], :3].astype(np.float32)
        _MESH[piece] = m
    return _MESH[piece]


def cam_pack(cx, cy, z, pitch, roll, shx, shy):
    th, rh = math.radians(pitch), math.radians(roll)
    r1 = np.array([math.cos(rh), math.sin(rh), 0.0])
    r2 = np.array([-math.cos(th) * math.sin(rh), math.cos(th) * math.cos(rh), -math.sin(th)])
    r3 = np.array([-math.sin(rh) * math.sin(th), math.cos(rh) * math.sin(th), math.cos(th)])
    return dict(cx=cx, cy=cy, r=(r1, r2, r3), t=np.array([0.0, 0.0, FOC / z]), Wc=W / 2 + shx, Hc=H / 2 + shy, sth=math.sin(th), cth=math.cos(th))


def project(cam, X, Y, Zh):
    r1, r2, r3 = cam["r"]
    p = (X - cam["cx"])[:, None] * r1 + (Y - cam["cy"])[:, None] * r2 - Zh[:, None] * r3 + cam["t"]
    return FOC * p[:, 0] / p[:, 2] + cam["Wc"], FOC * p[:, 1] / p[:, 2] + cam["Hc"], p[:, 2]


def project_pt(cam, X, Y, Zh=0.0):
    x, y, d = project(cam, np.array([float(X)]), np.array([float(Y)]), np.array([float(Zh)]))
    return float(x[0]), float(y[0]), float(d[0])


def light_factor(u_t, pos):
    amb, pools = light_map(u_t)
    f = amb
    for (c, rad, st, col) in pools:
        g = math.exp(-(((pos[0] - c[0]) ** 2 + (pos[1] - c[1]) ** 2) / (rad ** 2))) * st
        f += g * 0.8
    return min(1.35, max(0.15, f))


def draw_pieces3d(frame, cam, u_t):
    phi = math.radians(CUR_PHI)
    cp, sp = math.cos(phi), math.sin(phi)
    k = PSU / 512.0
    SS = 2
    Xs, Ys, Zs, Cs = [], [], [], []
    for r in PLIST:
        m = mesh_of(r["piece"])
        sx_, sy_ = abs(r["sx"]), r["sy"]
        x, y = r["u"]
        a = m["a"] * sx_ * (-1 if r["sx"] < 0 else 1)
        b = m["b"] * sy_
        c = m["c"] * sx_
        na, nb, nc = m["na"] * (-1 if r["sx"] < 0 else 1), m["nb"], m["nc"]
        rot = math.radians(r["rot"])
        cr, sr = math.cos(rot), math.sin(rot)
        a, b = a * cr - b * sr, a * sr + b * cr
        na, nb = na * cr - nb * sr, na * sr + nb * cr
        b0 = (256.0 - PAD_BASE) * sy_
        X = x + a * k
        Y = y - b * k * cp + c * k * sp
        Zh = (b - b0) * k * sp + c * k * cp + r["lift"] * 0.9
        # normals -> world
        nX = na
        nY = -nb * cp + nc * sp
        nZ = nb * sp + nc * cp
        ndl = nX * LDIR[0] + nY * LDIR[1] + nZ * LDIR[2]
        shade = 0.66 + 0.34 * np.clip(ndl / 0.83, -0.45, 1.15)
        if r["deco"] is not None:
            tex = np.asarray(r["deco"])
            tt = tex[m["ty"] + DC.PAD, m["tx"] + DC.PAD]
            col = np.where((tt[:, 3] > 60)[:, None], tt[:, :3].astype(np.float32), m["col"])
        elif r["look"] and (r["look"][0] > 0.01 or r["look"][1] > 0.01):
            col = np.asarray(look_img(r["piece"], r["look"]))[m["ty"], m["tx"], :3].astype(np.float32)
        else:
            col = m["col"]
        lf = light_factor(u_t, (x, y)) * r["dark"]
        col = np.clip(col * (shade * lf)[:, None], 0, 255)
        face = (nY * cam["sth"] + nZ * cam["cth"]) > -0.12          # back-face culling: no see-through
        Xs.append(X[face]); Ys.append(Y[face]); Zs.append(Zh[face]); Cs.append(col[face])
    if not Xs:
        return
    X = np.concatenate(Xs); Y = np.concatenate(Ys); Zh = np.concatenate(Zs if False else Zs); col = np.concatenate(Cs)
    sxp, syp, dep = project(cam, X, Y, Zh)
    sxp, syp = sxp * SS, syp * SS
    ok = (sxp > -4) & (sxp < W * SS + 4) & (syp > -4) & (syp < H * SS + 4) & (dep > 1)
    sxp, syp, dep, col = sxp[ok], syp[ok], dep[ok], col[ok]
    if len(sxp) == 0:
        return
    x0, x1 = int(sxp.min()) - 3, int(sxp.max()) + 4
    y0, y1 = int(syp.min()) - 3, int(syp.max()) + 4
    x0, y0 = max(x0, 0), max(y0, 0)
    x1, y1 = min(x1, W * SS), min(y1, H * SS)
    bw, bh = x1 - x0, y1 - y0
    buf = np.zeros((bh, bw, 4), np.uint8)
    order = np.argsort(-dep)
    ix = np.round(sxp[order]).astype(int) - x0
    iy = np.round(syp[order]).astype(int) - y0
    cc = np.concatenate([col[order].astype(np.uint8), np.full((len(order), 1), 255, np.uint8)], 1)
    for dy in (-2, -1, 0, 1, 2):
        for dx in (-2, -1, 0, 1, 2):
            jx, jy = ix + dx, iy + dy
            v = (jx >= 0) & (jx < bw) & (jy >= 0) & (jy < bh)
            buf[jy[v], jx[v]] = cc[v]
    f = buf.astype(np.float32)
    al = f[..., 3:4] / 255.0
    pm = f[..., :3] * al
    h2, w2 = (bh // SS) * SS, (bw // SS) * SS
    pm = pm[:h2, :w2].reshape(h2 // SS, SS, w2 // SS, SS, 3).mean((1, 3))
    a2 = al[:h2, :w2].reshape(h2 // SS, SS, w2 // SS, SS, 1).mean((1, 3))
    rgb = np.where(a2 > 0.003, pm / np.maximum(a2, 1e-3), 0)
    out = np.concatenate([np.clip(rgb, 0, 255), a2 * 255], 2).astype(np.uint8)
    tile = Image.fromarray(out, "RGBA")
    ox, oy = x0 // SS, y0 // SS
    fw, fh = frame.size
    tile = tile.crop((max(0, -ox), max(0, -oy), min(tile.width, fw - ox), min(tile.height, fh - oy)))
    frame.alpha_composite(tile, (max(0, ox), max(0, oy)))


SLOW = [(T[22], 0.25, 0.30, 0.45), (T[25], 0.30, 0.28, 0.45), (T[27], 0.45, 0.20, 0.60)]   # (hit, dip length, dip speed, run-up)
STOPS = [(T[22], 0.06), (T[25], 0.10), (T[27], 0.06)]                                       # freeze right after the hit, then catch up


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



FOC = 1500.0
KEYS = [  # (arrive, centre, zoom, pitch deg, roll deg, move duration)
    (0.0, (560, 560), 1.0, 0, 0, 0.0),
    (T[16] - 0.05, S("d5"), 1.12, 0, 0, 0.9),
    (T[17] - 0.05, S("e2"), 1.55, 0, 0, 0.55),
    (T[18] - 0.03, S("c7", "d7"), 1.55, 0, 0, 0.40),
    (T[19] - 0.03, S("a3", "b4"), 1.75, 0, 0, 0.35),
    (T[20] - 0.03, S("b8", "c8"), 1.6, 0, 0, 0.35),
    (T[21] - 0.03, S("a3", "b4"), 1.75, 0, 0, 0.35),
    (T[22] - 0.20, S("a4"), 1.2, 0, 0, 0.30),
    (T[22] - 0.03, S("a3", "b3"), 1.5, 52, 5, 0.17),            # zoom crash on the queen's strike, board tilts: real 3D pieces
    (T[22] + 0.75, S("c2", "d2"), 1.2, 0, 0, 0.80),
    (T[23] - 0.05, S("d2", "e1"), 1.5, 0, 0, 0.50),
    (T[24] - 0.03, S("d1", "e1"), 1.2, 0, 0, 0.35),
    (T[24] + 0.90, S("f3", "e3"), 1.3, 0, 0, 0.90),
    (T[25] - 0.40, S("f3"), 1.65, 0, 0, 0.60),
    (T[25] - 0.03, S("d4", "d5"), 1.45, 55, 6, 0.17),           # the sacrifice: second tilted moment
    (T[25] + 0.55, S("c6", "c7"), 1.7, 0, 0, 0.60),             # flat again before bxc6
    (T[26] + 0.50, (560, 540), 1.05, 0, 0, 0.55),
    (T[27] - 0.70, S("c5", "d5"), 1.18, 0, 0, 1.20),
    (T[27] - 0.03, S("b7", "c7"), 1.9, 0, 0, 0.25),             # zoom crash, flat top-down on the last move
    (T[27] + 0.70, (560, 540), 1.35, 0, 0, 0.90),
    (REW1 - 0.05, (560, 560), 1.0, 0, 0, 0.95),
]
KICKS = [(T[p], KS[p]) for p in PLIES] + ACC
SWAY = []


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
    d = u - T[27]
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



SPEC = {
    17: dict(dur=.40, prog=[(0, 0), (.4, .3), (1, 1)], sc=[(0, 1), (.5, 1.12), (1, 1)], rot=[(0, 0), (.5, -8), (1, 0)], st=.04, col=CYN),
    18: dict(dur=.45, prog=[(0, 0), (.2, -.03), (.5, .5), (.8, .95), (1, 1)], sc=[(0, 1), (.3, .8), (.6, 1.4), (1, 1)], rot=[(0, 0), (.3, 0), (.9, -360), (1, -360)], st=.08, trail=2, col=AMB),
    19: dict(dur=.30, prog=[(0, 0), (.5, .4), (1, 1)], sc=[(0, 1), (.5, .9), (1, 1)], rot=[(0, 0), (.4, 6), (1, 0)], st=.03, col=CYN),
    20: dict(dur=.50, prog=[(0, 0), (.4, .3), (1, 1)], sc=[(0, 1), (.5, 1.1), (1, 1)], rot=[(0, 0), (.5, -6), (1, 0)], st=.03, col=AMB),
    21: dict(dur=.26, prog=[(0, 0), (.35, .05), (.75, .9), (1, 1)], sc=[(0, 1), (.3, .8), (.8, 1.35), (1, 1)], rot=[(0, 0), (.3, -12), (1, 0)], st=.22, trail=2, col=CYN),
    23: dict(dur=.55, prog=[(0, 0), (.3, .15), (.7, .85), (1, 1)], sc=[(0, 1), (.5, .95), (1, 1)], rot=[(0, 0), (.5, 5), (1, 0)], st=.03, col=CYN),
    24: dict(dur=.45, prog=[(0, 0), (.25, .2), (.55, .7), (1, 1)], sc=[(0, 1), (.4, 1.15), (1, 1)], rot=[(0, 0), (1, 0)], st=.26, trail=4, col=AMB),
    26: dict(dur=.55, prog=[(0, 0), (.18, 0), (.30, .28), (.45, .28), (.58, .62), (.72, .62), (.88, 1.0), (1, 1)], sc=[(0, 1), (.5, 1.1), (1, 1)],
             rot=[(0, 0), (.2, 10), (.35, -10), (.5, 10), (.65, -8), (.85, 6), (1, 0)], st=.02, col=AMB),
}
_ip = {}


def curve(p, name):
    k = (p, name)
    if k not in _ip:
        pts = SPEC[p][name]
        _ip[k] = PchipInterpolator([a for a, _ in pts], [b for _, b in pts])
    return _ip[k]


def mover_std(p, u, f, t, h):
    sp = SPEC[p]
    dur = sp["dur"]
    uv = V(f, t) / np.linalg.norm(V(f, t))
    if u < h - dur - 0.1 or u > h + 0.32:
        return None
    if u > h:
        d = u - h
        sqz = settle(d, 0.10 + sp["st"] * 0.6, 26, 0.11)
        o = settle(d, 0.10 * SQU, 22, 0.10) * (1 if p in (22, 24, 27) else 0.4)
        return tuple(np.array(t) + uv * o), 1 + sqz, 1 - sqz, 0.0, 0, [], (sp["col"], 0.0, 0.0)
    if u < h - dur:
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
    pos = np.array(f) + (np.array(t) - np.array(f)) * pr
    tr = []
    for j in range(1, sp.get("trail", 0) + 1):
        kk = max(0.0, k - j * 0.07)
        tr.append((tuple(np.array(f) + (np.array(t) - np.array(f)) * float(curve(p, "prog")(kk))), 0.30 * (1 - j / (sp["trail"] + 1.0)), float(curve(p, "sc")(kk))))
    return tuple(pos), sx_, sy_, rot, (sc - 1) * 60 + 6, tr, (sp["col"], 0.45 * (0.3 + v), math.radians(20 + 330 * k))


def lunge(u, f, t, h, back=0.4 * SQU, t0=0.55, t1=0.28, pw=3.2, spin=0.0, hover=0.0, ntr=5, col=WHITE):
    """wind-up backwards (and optionally hover up), then an accelerating dash that lands ON the hit"""
    f, t = np.array(f, float), np.array(t, float)
    L = np.linalg.norm(t - f)
    uv = (t - f) / L
    if u < h - t0 or u > h + 0.42:
        return None
    if u < h - t1:
        k = ease_out((u - (h - t0)) / (t0 - t1), 2.5)
        return tuple(f - uv * back * k), 1 - 0.04 * k, 1 + 0.06 * k + 0.08 * hover * k, -7 * k, 6 + hover * 46 * k, [], None
    if u < h:
        k = (u - (h - t1)) / t1
        e = ease_in(k, pw)
        pos = f + uv * lerp(-back, L, e)
        tr = [(tuple(f + uv * lerp(-back, L, ease_in(max(0, k - j * 0.07), pw))), 0.34 * (1 - j / (ntr + 1.0)), 1.0) for j in range(1, ntr + 1)]
        return tuple(pos), 1 - 0.06 * e, 1 + 0.18 * e, lerp(-7, 0, e) + spin * ease_in(k, 1.6), 10 + (hover * 46 + 6) * (1 - e), tr, (col, 0.0, 0.0)
    d = u - h
    sq_ = 1 + 0.10 * math.exp(-d / 0.10) * math.cos(d * 28)
    o = 0.16 * SQU * math.exp(-d / 0.09) * math.cos(d * 24)
    return tuple(t + uv * o), 1 / sq_, sq_, 0.0, 0, [], None


HAND_T0 = 0.62          # the hand closes on the bishop
HAND_FAR = np.array([170.0, -1500.0])


def mover16(u, f, t, h):
    if u < HAND_T0 or u > h + 0.30:
        return None
    f, t = np.array(f), np.array(t)
    if u > h:
        d = u - h
        sqz = settle(d, 0.10, 26, 0.11)
        return tuple(t), 1 + sqz, 1 - sqz, 0.0, 0, [], None
    k = (u - HAND_T0) / (h - HAND_T0)
    pr = float(PchipInterpolator([0, .25, .7, 1], [0, .05, .8, 1])(k))
    pos = f + (t - f) * pr
    lift = 14 + 34 * math.sin(math.pi * pr)
    return tuple(pos), 1.05, 1.05, 4 * math.sin(math.pi * k), lift, [], None


def hand_state(u):
    """-> (tip in board units, grip, lean) or None; the hand is drawn in screen space"""
    h = T[16]
    f = np.array(cu(MV[16]["from"]), float)
    t = np.array(cu(MV[16]["to"]), float)
    if u < 0.05 or u > h + 0.85:
        return None
    head = np.array([0.0, -16.0])
    if u < HAND_T0:
        k = ease_out((u - 0.05) / (HAND_T0 - 0.05), 2.2)
        tip = HAND_FAR + (f + head - HAND_FAR) * k
        grip = 0.0 if u < 0.40 else ease_io((u - 0.40) / 0.2)
        return tip, 0.0 + 0.0 * grip if u < 0.5 else grip, 12
    if u <= h:
        k = (u - HAND_T0) / (h - HAND_T0)
        pr = float(PchipInterpolator([0, .25, .7, 1], [0, .05, .8, 1])(k))
        return f + (t - f) * pr + head, 1.0, 12 - 4 * math.sin(math.pi * pr)
    if u < h + 0.18:
        return t + head, 1 - ease_io((u - h) / 0.18), 12
    k = ease_in((u - h - 0.18) / 0.67, 2.0)
    return (t + head) + (HAND_FAR + np.array([60.0, 0.0]) - (t + head)) * k, 0.0, 12


def mover25(u, f, t, h):
    f, t = np.array(f, float), np.array(t, float)
    L = np.linalg.norm(t - f)
    uv = (t - f) / L
    if u < h - 0.80 or u > h + 0.40:
        return None
    if u < h - 0.28:                       # the martyr rises and hovers
        k = ease_io((u - (h - 0.80)) / 0.40)
        bob = 5 * math.sin(u * 9)
        return tuple(f + np.array([0, -bob * k])), 1 + 0.10 * k, 1 + 0.14 * k, 3 * math.sin(u * 7) * k, 54 * k, [], None
    if u < h:
        k = (u - (h - 0.28)) / 0.28
        e = ease_in(k, 2.6)
        pos = f + uv * L * e
        tr = [(tuple(f + uv * L * ease_in(max(0, k - j * 0.07), 2.6)), 0.30 * (1 - j / 6.0), 1.1) for j in range(1, 6)]
        return tuple(pos), 1.10 - 0.1 * e, 1.14 + 0.1 * e, lerp(0, 0, e), 54 * (1 - e) + 8, tr, (CYN, 0.0, 0.0)
    d = u - h
    sq_ = 1 + 0.10 * math.exp(-d / 0.10) * math.cos(d * 28)
    o = 0.14 * SQU * math.exp(-d / 0.09) * math.cos(d * 24)
    return tuple(t + uv * o), 1 / sq_, sq_, 0.0, 0, [], None


def castle_rook(u):
    """rook a8 -> d8 hops over the king (ply 20); returns (pos, sx, sy, rot, lift, [], None) or None"""
    h = T[20]
    if u < h - 0.55 or u > h + 0.30:
        return None
    rf, rt_, pc = MV[20]["extra"]
    f, t = np.array(cu(rf), float), np.array(cu(rt_), float)
    if u > h:
        d = u - h
        sqz = settle(d, 0.12, 26, 0.10)
        return tuple(t), 1 + sqz, 1 - sqz, 0.0, 0, [], None
    k = clamp((u - (h - 0.55)) / 0.55)
    pr = ease_io(k)
    s = math.sin(math.pi * k)
    return tuple(f + (t - f) * pr), 1 + 0.26 * s, 1 + 0.26 * s, 14 * math.sin(2 * math.pi * k), 76 * s, [], None


def mover(p, u):
    """-> (pos, sx, sy, rot, lift, trail, tint) while the mover is animated, else None"""
    m = MV[p]
    f, t = cu(m["from"]), cu(m["to"])
    h = T[p]
    if p == 16:
        return mover16(u, f, t, h)
    if p == 22:
        return lunge(u, f, t, h, back=0.55 * SQU, t0=0.55, t1=0.28, pw=3.2, col=GOLD)
    if p == 25:
        return mover25(u, f, t, h)
    if p == 27:
        return lunge(u, f, t, h, back=0.5 * SQU, t0=0.60, t1=0.30, pw=3.4, spin=360.0, col=WHITE)
    return mover_std(p, u, f, t, h)


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




BADGE = {25: ("!!", (30, 188, 178)), 27: ("#", (205, 160, 40))}

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
        if p == 27:
            end = REW0 - 0.1
        if e < 0 or u > end:
            continue
        pop = 1 - math.exp(-e / 0.05) * math.cos(e * 20) if e < 1.0 else 1.0
        fadeout = clamp(1 - (u - (end - 0.25)) / 0.25)
        sc = max(0.01, pop) * (1.35 if p in (25, 27) else 1.0)
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



SH0 = round((16.34 - A0) * FPS) / FPS          # sunglasses drop on a beat
_dc = {}


def _cached(key, fn):
    if key not in _dc:
        if len(_dc) > 8:
            _dc.clear()
        _dc[key] = fn()
    return _dc[key]


def deco_for_piece(pc, u, square=None, ply=None):
    if pc == ("w", "K") and SH0 <= u < T[26] + 0.40:
        if u < T[26] + 0.10:
            dr = clamp((u - SH0) / 0.35)
        else:
            dr = 1 - ease_io((u - T[26] - 0.10) / 0.28)
        return _cached(("s", round(dr * 200)), lambda: D2.king_shades(BASE[("w", "K")], dr))
    if pc == ("b", "K") and T[25] + 0.12 <= u < REW0:
        kk = 1.0 - ease_io((u - (REW0 - 0.35)) / 0.35)
        return _cached(("k", round(u * 90), round(kk * 20)), lambda: D2.blend_k(BASE[("b", "K")], D2.king_shock(BASE[("b", "K")], u - T[25] - 0.12), kk))
    return None


def queen_look(u):
    """black queen: greedy gold (22, 24), then drained grey stone when the net closes"""
    g = 0.55 * ease_io((u - T[22]) / 0.6) + 0.45 * ease_io((u - T[24]) / 0.6)
    d = ease_io((u - (T[26] + 0.35)) / 0.65)
    return (g * (1 - d), d)


def queen_size(u):
    s = 1.0 + 0.08 * ease_io((u - T[22]) / 0.6) + 0.09 * ease_io((u - T[24]) / 0.6)
    d = ease_io((u - (T[26] + 0.35)) / 0.65)
    return s - 0.17 * d * (s - 1.0) / 0.17 if False else 1.0 + (s - 1.0) * (1 - d)


def accent(p):
    return CYN if MV[p]["piece"][0] == "w" else AMB


def sqn(n):
    return cu(sq(n))


# ------------------------------------------------------------- board effect 1: bear-trap jaws spring up at a1 and snap shut on the queen
def trap(dv, c, s, open_k, a):
    if s <= 0.02 or a <= 0.01:
        return
    R = 60 * s
    al = int(255 * clamp(a))
    p = px(c)
    dv.ellipse((p[0] - R * 1.18 * RS, p[1] - R * 1.18 * RS, p[0] + R * 1.18 * RS, p[1] + R * 1.18 * RS), fill=(10, 10, 14, int(170 * clamp(a))))
    for side in (-1, 1):
        cx = c[0] + side * open_k * 50 * s
        pts = []
        for i in range(0, 25):
            th = math.radians(90 + 180 * i / 24.0) if side < 0 else math.radians(-90 + 180 * i / 24.0)
            pts.append((cx + math.cos(th) * R, c[1] + math.sin(th) * R))
        dv.polygon([px(q) for q in pts], fill=(150, 158, 176, al), outline=(30, 34, 44, al))
        dv.line([px(q) for q in pts + [pts[0]]], fill=(30, 34, 44, al), width=int(5 * RS), joint="curve")
        inner = [(cx + math.cos(math.radians((90 if side < 0 else -90) + (180 * i / 24.0))) * R * 0.74, c[1] + math.sin(math.radians((90 if side < 0 else -90) + 180 * i / 24.0)) * R * 0.74) for i in range(25)]
        dv.line([px(q) for q in inner], fill=(104, 110, 128, al), width=int(4 * RS), joint="curve")
        for j in range(-4, 4):
            y0 = c[1] + j * 14 * s + (7 * s if side > 0 else 0)
            tri = [(cx, y0), (cx - side * 17 * s, y0 + 7 * s), (cx, y0 + 14 * s)]
            dv.polygon([px(q) for q in tri], fill=(206, 212, 226, al), outline=(30, 34, 44, al))


def ring(dv, c, r, w, col, a):
    if a <= 0.01 or r < 1:
        return
    p = px(c)
    dv.ellipse((p[0] - r * RS, p[1] - r * RS, p[0] + r * RS, p[1] + r * RS), outline=col + (int(255 * clamp(a)),), width=max(2, int(w * RS)))


# ------------------------------------------------------------- board effect 2: lava cracks run from the greedy queen's square to the sacrifice
_LAVA = []


def lava_paths():
    if _LAVA:
        return _LAVA
    rs = np.random.RandomState(11)
    a, b = np.array(sqn("h1"), float), np.array(sqn("c6"), float)
    v = b - a
    Ln = np.linalg.norm(v)
    nrm = np.array([-v[1], v[0]]) / Ln
    n = 26
    main = [a + v * (i / n) + nrm * rs.uniform(-26, 26) * math.sin(math.pi * i / n) for i in range(n + 1)]
    paths = [(main, 0.0)]
    for _ in range(9):
        i = rs.randint(3, n - 2)
        ang = rs.uniform(-1.1, 1.1)
        d = (v / Ln) * math.cos(ang) + nrm * math.sin(ang)
        ln = rs.uniform(90, 200)
        pts = [main[i] + d * ln * (j / 6.0) + nrm * rs.uniform(-12, 12) for j in range(7)]
        paths.append((pts, i / float(n)))
    _LAVA.extend(paths)
    return _LAVA


def part(pts, prog):
    seg = [np.linalg.norm(np.array(pts[i + 1]) - np.array(pts[i])) for i in range(len(pts) - 1)]
    tot = sum(seg) * clamp(prog)
    out = [pts[0]]
    acc = 0.0
    for i, s_ in enumerate(seg):
        if acc + s_ <= tot:
            out.append(pts[i + 1])
            acc += s_
        else:
            k = (tot - acc) / max(s_, 1e-6)
            out.append(np.array(pts[i]) + (np.array(pts[i + 1]) - np.array(pts[i])) * k)
            break
    return out


def lava_fx(u, canvas, dv):
    t0 = T[24] + 0.35
    if u < t0 or u > T[25] + 1.9:
        return
    main_p = ease_io((u - t0) / (T[25] - t0))
    cool = clamp((u - (T[25] + 0.25)) / 1.2)
    fade = clamp(1 - (u - (T[25] + 1.2)) / 0.7)
    col_o = tuple(int(v) for v in np.array((255, 112, 16)) * (1 - cool) + np.array((70, 26, 18)) * cool)
    col_y = tuple(int(v) for v in np.array((255, 228, 120)) * (1 - cool) + np.array((120, 50, 30)) * cool)
    g = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for pts, at in lava_paths():
        pr = main_p if at == 0 else clamp((main_p - at) / max(1e-3, 1 - at) * 1.4)
        if pr <= 0:
            continue
        pp = [tuple(np.array(q) * RS) for q in part(pts, pr)]
        if len(pp) < 2:
            continue
        w = 1.0 if at == 0 else 0.62
        dv.line(pp, fill=(24, 10, 8, int(235 * fade)), width=int(21 * w * RS), joint="curve")
        dv.line(pp, fill=col_o + (int(255 * fade),), width=int(11 * w * RS), joint="curve")
        dv.line(pp, fill=col_y + (int(255 * fade),), width=int(4.4 * w * RS), joint="curve")
        dg.line(pp, fill=col_o + (int(190 * fade * (1 - 0.8 * cool)),), width=int(30 * w * RS), joint="curve")
    canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(16 * RS)))


# ------------------------------------------------------------- iron grate that slams on the king's flight squares
def grate(dv, s_name, e):
    if e < 0:
        return
    c = np.array(sqn(s_name))
    k = 1 + 0.55 * (1 - ease_out(e / 0.12, 2.0))
    hs = (SQU / 2 - 5) * k
    a = int(255 * clamp(e / 0.04))
    x0, y0, x1, y1 = c[0] - hs, c[1] - hs, c[0] + hs, c[1] + hs
    dv.rectangle((px((x0, y0))[0], px((x0, y0))[1], px((x1, y1))[0], px((x1, y1))[1]), fill=(72, 10, 16, int(a * 0.82)))
    n = 7
    for i in range(n):
        x = x0 + (x1 - x0) * (i + 0.5) / n
        dv.line([px((x, y0)), px((x, y1))], fill=(198, 204, 218, a), width=int(8 * RS))
        dv.line([px((x + 2.5, y0)), px((x + 2.5, y1))], fill=(120, 126, 142, a), width=int(2.5 * RS))
    for yy in (y0 + (y1 - y0) * 0.22, y0 + (y1 - y0) * 0.78):
        dv.line([px((x0, yy)), px((x1, yy))], fill=(150, 156, 172, a), width=int(10 * RS))
    dv.rectangle((px((x0, y0))[0], px((x0, y0))[1], px((x1, y1))[0], px((x1, y1))[1]), outline=(36, 40, 52, a), width=int(9 * RS))
    for (xx, yy) in ((x0, y0), (x1, y0), (x0, y1), (x1, y1)):
        p = px((xx, yy))
        dv.ellipse((p[0] - 7 * RS, p[1] - 7 * RS, p[0] + 7 * RS, p[1] + 7 * RS), fill=(220, 224, 236, a), outline=(36, 40, 52, a), width=int(3 * RS))


# ------------------------------------------------------------- under pieces
def under_fx(u, dv, canvas):
    cur = max([p for p in PLIES if T[p] - 0.05 <= u], default=None)
    if cur is not None and cur != 27:
        e = u - T[cur]
        a = clamp(1 - (e - 0.9) / 0.5) * 0.20
        sq_fill(dv, MV[cur]["from"], accent(cur), a * 0.6)
        sq_fill(dv, MV[cur]["to"], accent(cur), a * 1.3)
    # 16: the pin, a taut line from b4 to e1 that hums
    e = u - T[16]
    if 0.05 < e < (T[17] - T[16]) + 0.55:
        a = clamp(e / 0.15) * clamp(1 - (e - (T[17] - T[16])) / 0.5)
        p0, p1 = np.array(sqn("b4")), np.array(sqn("e1"))
        vv = p1 - p0
        nn = np.array([-vv[1], vv[0]]) / np.linalg.norm(vv)
        pts = []
        for i in range(0, 31):
            s_ = i / 30.0
            off = 15 * math.sin(math.pi * s_) * math.sin(e * 58 - s_ * 9) * math.exp(-e * 1.1)
            pts.append(px(p0 + vv * s_ + nn * off))
        dv.line(pts, fill=AMB + (int(255 * a),), width=int(9 * RS), joint="curve")
        bracket(dv, sq("e1"), RED, a)
        bracket(dv, sq("c3"), AMB, a)
    # 19: the pawn eyes the loose bishop
    if T[19] <= u < T[21] + 0.05:
        a = clamp(1 - (u - T[21]) / 0.05)
        arrow_poly(dv, sqn("a3"), sqn("b4"), ease_out((u - T[19]) / 0.25), CYN, 0.9 * a, wd=28)
        bracket(dv, sq("b4"), AMB, a)
    # board effect 1: the trap at a1
    t0 = T[21] + 0.15
    if t0 <= u < T[22] + 1.0:
        s = ease_out((u - t0) / 0.4, 2.5)
        ok = 1.0 if u < T[22] - 0.04 else 1 - ease_out((u - (T[22] - 0.04)) / 0.08, 2.0) + 0.0
        if u > T[22] + 0.04:
            ok = max(0.0, -0.08 * math.exp(-(u - T[22] - 0.04) / 0.08) * math.sin((u - T[22] - 0.04) * 40))
        sink = clamp((u - (T[22] + 0.55)) / 0.4)
        trap(dv, sqn("a1"), s * (1 - 0.8 * sink), ok, 1 - sink)
    # 22: check on the long rank
    if T[22] <= u < T[23] + 0.1:
        a = clamp(1 - (u - T[23]) / 0.1)
        arrow_poly(dv, sqn("a1"), sqn("e1"), ease_out((u - T[22]) / 0.15), RED, a, wd=34)
        bracket(dv, sq("e1"), RED, a)
    # the white queen is foreshadowed: faint arrow f3 -> c6 while the music holds
    t0 = T[24] + 0.9
    if t0 <= u < T[25]:
        arrow_poly(dv, sqn("f3"), sqn("c6"), ease_io((u - t0) / (T[25] - t0)), CYN, 0.40, wd=30)
        bracket(dv, sq("c6"), AMB, 0.8)
    # board effect 2 (lava) + ripple at the sacrifice
    lava_fx(u, canvas, dv)
    for dly in (0.0, 0.14):
        e = u - T[25] - dly
        if 0 <= e < 0.9:
            ring(dv, sqn("c6"), 520 * ease_out(e / 0.9, 2.2), 16 * (1 - e / 0.9) + 2, (255, 214, 150), 1 - ease_in(e / 0.9, 1.4))
    # 25: check on the black king
    if T[25] <= u < T[26] + 0.2:
        a = clamp(1 - (u - T[26] - 0.05) / 0.15)
        arrow_poly(dv, sqn("c6"), sqn("c8"), ease_out((u - T[25]) / 0.15), RED, a, wd=34)
        bracket(dv, sq("c8"), RED, a)
    # the mate plan: wide arrow drawn slowly through the hush
    t0 = T[26] + 0.55
    if t0 <= u < T[27] + 0.1:
        a = clamp(1 - (u - T[27]) / 0.1)
        arrow_poly(dv, sqn("e2"), sqn("a6"), ease_io((u - t0) / (T[27] - 0.15 - t0)), CYN, 0.95 * a, wd=38, head=1.15)
        bracket(dv, sq("c8"), RED, clamp((u - t0) / 0.3) * a)
    if u >= T[27]:
        e = u - T[27]
        sq_fill(dv, sq("c8"), RED, clamp(e / 0.04) * 0.9 * (1 - ease_in((u - (REW0 - 0.4)) / 0.4)))


# ------------------------------------------------------------- over pieces
def coins_fx(df, u, t0, src, tgt, seed):
    e = u - t0
    if e < 0 or e > 0.9:
        return
    rs = np.random.RandomState(seed)
    for i in range(10):
        ang = rs.uniform(0, 2 * math.pi)
        R = rs.uniform(70, 190)
        d0 = rs.uniform(0.0, 0.12)
        ee = e - d0
        if ee < 0:
            continue
        out = ease_out(min(ee / 0.32, 1.0), 2.5)
        home = ease_in(clamp((ee - 0.28) / 0.55), 2.0)
        p = np.array(src) + np.array([math.cos(ang), math.sin(ang)]) * R * out
        p = p + (np.array(tgt) + np.array([0, -10.0]) - p) * home
        a = 1 - clamp((ee - 0.75) / 0.1)
        D2.coin(df, px(p), 12 * RS * (1 - 0.3 * home), ee * 22 + i, a)


def feathers_fx(df, u, c):
    e = u - T[25]
    if e < 0 or e > 1.1:
        return
    rs = np.random.RandomState(5)
    for i in range(12):
        ang = rs.uniform(0, 2 * math.pi)
        sp = rs.uniform(90, 260)
        d = (1 - math.exp(-3 * e)) / 3.0
        p = np.array(c) + np.array([math.cos(ang), math.sin(ang)]) * sp * d + np.array([0, 40 * e * e])
        a = int(255 * clamp(1 - (e - 0.4) / 0.7))
        q = px(p)
        r_ = (9 + (i % 3) * 3) * RS
        sw = math.sin(e * 9 + i) 
        df.ellipse((q[0] - r_ * abs(sw) - 2, q[1] - r_ * 1.9, q[0] + r_ * abs(sw) + 2, q[1] + r_ * 1.9), fill=(250, 252, 255, a), outline=(120, 150, 196, a), width=2)


def eruption_fx(df, canvas, u):
    e = u - T[25]
    if e < 0 or e > 1.0:
        return
    c = np.array(sqn("c6"))
    rs = np.random.RandomState(21)
    big = ease_out(e / 0.2, 2.0) * (1 - ease_in((e - 0.15) / 0.5))
    if big > 0.02:
        for rr, col in ((78, (255, 90, 20)), (52, (255, 170, 40)), (28, (255, 238, 150))):
            q = px(c)
            R = rr * big * RS
            df.ellipse((q[0] - R, q[1] - R, q[0] + R, q[1] + R), fill=col + (int(235 * big),))
    for i in range(26):
        ang = rs.uniform(0, 2 * math.pi)
        spd = rs.uniform(140, 420)
        d = (1 - math.exp(-3.2 * e)) / 3.2
        p = c + np.array([math.cos(ang), math.sin(ang)]) * spd * d
        a = int(255 * clamp(1 - (e - 0.3) / 0.7))
        r_ = (7 + (i % 4) * 2) * RS * (1 - 0.5 * e)
        q = px(p)
        df.ellipse((q[0] - r_, q[1] - r_, q[0] + r_, q[1] + r_), fill=((255, 150, 30) if i % 2 else (255, 226, 110)) + (a,))


def energy_fx(df, canvas, u):
    e = u - T[26]
    if e < 0 or e > 1.5:
        return
    a_, b_ = np.array(sqn("c6")), np.array(sqn("e2"))
    rs = np.random.RandomState(33)
    nrm = np.array([-(b_ - a_)[1], (b_ - a_)[0]])
    nrm = nrm / np.linalg.norm(nrm)
    for i in range(18):
        dly = i * 0.025
        k = clamp((e - dly) / 0.85)
        if k <= 0 or k >= 1:
            continue
        ctrl = (a_ + b_) / 2 + nrm * rs.uniform(-150, 150)
        for tr in range(4):
            kk = clamp(k - tr * 0.03)
            kk = ease_io(kk)
            p = (1 - kk) ** 2 * a_ + 2 * (1 - kk) * kk * ctrl + kk ** 2 * b_
            q = px(p)
            r_ = (10 - tr * 2) * RS
            df.ellipse((q[0] - r_, q[1] - r_, q[0] + r_, q[1] + r_), fill=(255, 214 + tr * 8, 90 + tr * 20, int(255 * (1 - tr * 0.22))))
    t0 = T[26] + 0.7
    if u > t0:
        pul = 0.75 + 0.25 * math.sin(u * 14)
        glow(canvas, sqn("e2"), GOLD, (70 + 70 * clamp((u - t0) / 0.8)) * pul, 0.9 * clamp((u - t0) / 0.3))


_CR = []


def crack_fx(df, u):
    t0 = T[26] + 0.85
    if u < t0:
        return
    if not _CR:
        rs = np.random.RandomState(8)
        for i in range(8):
            ang = rs.uniform(0, 2 * math.pi) 
            pts = [(0.0, 0.0)]
            x = y = 0.0
            for j in range(6):
                ang += rs.uniform(-0.6, 0.6)
                x += math.cos(ang) * rs.uniform(10, 18)
                y += math.sin(ang) * rs.uniform(10, 18)
                pts.append((x, y))
            _CR.append(pts)
    k = ease_out((u - t0) / 0.9, 2.0)
    c = np.array(sqn("h1")) + np.array([0, -6])
    for pts in _CR:
        pp = [px(c + np.array(q) * k) for q in pts]
        df.line(pp, fill=(14, 14, 18, 235), width=int(3.4 * RS), joint="curve")
        df.line([(x + 1.5, y - 1.5) for x, y in pp], fill=(205, 208, 220, 150), width=int(1.4 * RS), joint="curve")


def over_fx(u, df, canvas):
    # greed: the rooks glint like bait, coins pour into the queen
    if T[19] + 0.2 < u < T[22]:
        a = 0.6 + 0.4 * math.sin(u * 11)
        twinkle(df, np.array(sqn("a1")) + np.array([-20, -28]), 22 * a, a, u * 90)
    if T[22] + 0.7 < u < T[24]:
        a = 0.6 + 0.4 * math.sin(u * 11)
        twinkle(df, np.array(sqn("h1")) + np.array([-20, -28]), 22 * a, a, u * 90)
    coins_fx(df, u, T[22], sqn("a1"), sqn("a1"), 3)
    coins_fx(df, u, T[24], sqn("h1"), sqn("h1"), 4)
    # speed lines on the strikes
    for p, cen, dirv in ((22, S("a3", "a4"), (0, 1)), (24, S("d1", "e1"), (1, 0)), (27, S("c4", "c5"), (-1, -1))):
        e = u - T[p]
        a = clamp(1 - e / 0.12) if e >= 0 else clamp(1 - (T[p] - u) / 0.30) * 0.9
        if a > 0.02 and -0.35 < e < 0.14:
            speed_lines(df, cen, dirv, 380, 14, p, a)
    feathers_fx(df, u, sqn("c6"))
    eruption_fx(df, canvas, u)
    energy_fx(df, canvas, u)
    crack_fx(df, u)
    e = u - T[27]
    if 0 <= e < 0.14:
        bolt(df, sqn("e2"), sqn("a6"), 7, wd=9, col=(255, 240, 200))
    for nm, dly in (("b7", 0.0), ("c7", 0.07), ("b8", 0.14)):
        if u >= T[27] + dly:
            f_ = clamp(1 - (u - (REW0 - 0.25)) / 0.25)
            if f_ > 0.02:
                grate(df, nm, u - T[27] - dly)


# ------------------------------------------------------------- captured pieces
def poof(df, c, e, a=0.8):
    dust(df, c, e, a)


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
    if p == 21:                                    # bishop popped off in a puff
        if e > 0.7:
            return
        k = ease_in(e / 0.5, 1.6)
        draw_piece(canvas, pc, tuple(pos + np.array([0, -40 * k])), 1 - 0.7 * k, 1 - 0.7 * k, 260 * k, alpha=clamp(1 - k * 1.1), shad=False)
    elif p in (22, 24):                            # rooks burst into coins (drawn in over_fx); the sprite shrinks away
        if e > 0.22:
            return
        k = ease_in(e / 0.2, 1.4)
        draw_piece(canvas, pc, tuple(pos), 1 + 0.2 * k, max(0.05, 1 - k), 0, alpha=clamp(1 - k), shad=False)
    elif p == 25:                                  # pawn swept away along the queen's line
        if e > 0.7:
            return
        d = (1 - math.exp(-2.6 * e)) / 2.6
        draw_piece(canvas, pc, tuple(pos + uv * 520 * d), 1, 1, 220 * d * 2, alpha=clamp(1 - (e - 0.3) / 0.4), shad=False)
    elif p == 26:                                  # the martyr queen dissolves into golden light that flows to the bishop
        if e > 0.9:
            return
        k = ease_out(e / 0.9, 1.6)
        draw_piece(canvas, pc, tuple(pos + np.array([0, -30 * k])), 1 + 0.25 * k, 1 + 0.25 * k, 0, alpha=clamp(1 - k * 1.05), shad=False, lift=30 * k)


# ------------------------------------------------------------- screen-space layer: the cartoon hand, puppet strings, wings and halo
def white_queen_state(u):
    """(board pos, lift) of the white queen during the sacrifice"""
    h = T[25]
    f, t = cu(MV[25]["from"]), cu(MV[25]["to"])
    r = mover25(u, f, t, h)
    if r is None:
        return (np.array(f if u < h else t, float), 0.0)
    return (np.array(r[0], float), r[4])


def screen_fx(frame, u, cam):
    ov = None
    phi = math.radians(CUR_PHI)
    cp, sp = math.cos(phi), math.sin(phi)
    hs = hand_state(u)
    if hs is not None:
        tip, grip, lean = hs
        ov = ov or D2.Ov()
        x, y, d = project_pt(cam, tip[0], tip[1], 22.0)
        D2.hand(ov, (x, y), FOC / d * 1.05, lean, grip, wob=1.6 * math.sin(u * 8))
    e = u - T[26]
    if -0.62 < e < 0.45:
        ov = ov or D2.Ov()
        top_k = ease_out((e + 0.62) / 0.3, 2.0) * (1 - ease_in((e - 0.12) / 0.3, 1.5))
        pw = SPEC[26]
        r = mover(26, u)
        if r is not None:
            ppos = np.array(r[0], float)
        else:
            ppos = np.array(cu(MV[26]["from"] if u < T[26] else MV[26]["to"]), float)
        tight = clamp(1 - abs(e) / 0.3)
        for i, (dx, dy) in enumerate(((-16, -4), (0, -18), (16, -4))):
            x, y, d = project_pt(cam, ppos[0] + dx, ppos[1] + dy * cp, 34.0 * sp + 26.0)
            s_ = FOC / d
            topx = x + (i - 1) * 26 * s_ * 0.5 + 20
            sag = (1 - tight) * 24 * s_ * math.sin(u * 7 + i)
            bx, by = topx + (x - topx) * 0.0, -30.0
            yy = by + (y - by) * top_k
            pts = [(topx, by), ((topx + x) / 2 + sag, (by + yy) / 2), (x + (topx - x) * (1 - top_k) * 0.0, yy)]
            ov.line(pts, (236, 236, 244, 235), 3.2 * s_ * 0.8 + 1.0)
            ov.ellipse((x, yy), 6 * s_ * 0.8, 6 * s_ * 0.8, (236, 236, 244, 255), (70, 70, 90, 255), 1.5)
    if T[25] - 0.80 < u < T[26] + 0.30:
        ov = ov or D2.Ov()
        pos, lift = white_queen_state(u)
        unf = ease_out((u - (T[25] - 0.80)) / 0.40, 2.0)
        dash = clamp((u - (T[25] - 0.28)) / 0.28) * clamp(1 - (u - T[25]) / 0.12)
        fold = ease_io((u - T[25]) / 0.35)
        vanish = clamp(1 - (u - T[26]) / 0.25)
        x, y, d = project_pt(cam, pos[0], pos[1] - 6 * cp, lift * 0.9 + 62 * sp)
        s_ = FOC / d * 0.50 * unf * (1 - 0.35 * fold) * vanish
        flap = 15 * math.sin(u * 17) * (1 - 0.8 * fold)
        D2.wings(ov, (x, y), s_, flap=flap, back=min(1.0, dash + 0.55 * fold))
        hx, hy, hd = project_pt(cam, pos[0], pos[1] - 42 * cp, lift * 0.9 + 108 * sp)
        D2.halo(ov, (hx, hy), FOC / hd * 0.55 * unf * vanish, a=1.0, flick=0.82 + 0.18 * math.sin(u * 23))
    if ov is not None:
        ov.blit(frame)


def light_events():
    return [
        (T[22] - 0.20, 0.20, 0.55, 0.55, 0.45, ("a5", "a1"), 300, 1.0, AMB),
        (T[24] + 0.05, 0.15, 0.35, 0.40, 0.30, ("d1", "h1"), 300, 0.8, AMB),
        (T[24] + 0.80, 0.60, 1.40, 0.40, 0.55, ("f3", "f3"), 230, 1.2, CYN),
        (T[25] - 0.10, 0.12, 0.30, 0.45, 0.35, ("c6", "f3"), 300, 0.9, CYN),
        (T[26] + 0.10, 0.30, 1.50, 0.50, 0.60, ("e2", "c8"), 380, 1.0, MAG),
        (T[27] - 0.20, 0.20, 0.60, 0.70, 0.55, ("c8", "a6"), 270, 1.2, RED),
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




GRADE = [(0.0, (1, 1, 1)), (T[21], (0.92, 1.0, 1.08)), (T[22] - 0.2, (0.90, 1.0, 1.10)), (T[22] + 0.05, (1.15, 1.0, 0.84)),
         (T[24] + 1.0, (1.10, 1.0, 0.88)), (T[25] - 0.4, (0.92, 1.02, 1.08)), (T[25] + 0.1, (0.90, 1.06, 1.08)),
         (T[26] + 0.5, (1.0, 0.96, 1.10)), (T[27] - 0.3, (1.0, 0.97, 1.06)), (T[27] + 0.1, (1.14, 0.90, 0.90)),
         (REW0, (1.10, 0.92, 0.92)), (REW1, (1, 1, 1)), (DUR + 1, (1, 1, 1))]


def grade(u):
    ts = [a for a, _ in GRADE]
    return [1 + 0.55 * (float(np.interp(u, ts, [c[i] for _, c in GRADE])) - 1) for i in range(3)]



def post_fx(frame, u, t):
    arr = None
    g = grade(u)
    if max(abs(g[0] - 1), abs(g[1] - 1), abs(g[2] - 1)) > 0.004:
        arr = np.asarray(frame, np.float32) * np.array(g, np.float32)[None, None, :]
    rgb = 0.0
    for tk, amp, dec in ((T[22], 11, 0.10), (T[25], 8, 0.09), (T[27], 15, 0.16)):
        d = t - tk
        if 0 <= d < 0.4:
            rgb = max(rgb, amp * math.exp(-d / dec))
    flash = 0.0
    for tk, a, dec in ((T[22], 0.30, 0.05), (T[25], 0.30, 0.05), (T[27], 0.60, 0.07)):
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
            if pc == ("b", "K") and ID_END[i_] == sq("c8"):
                rot = lerp(-84, 0, kk)
                pos = (pos[0] + 24 * (1 - kk), pos[1] + 28 * (1 - kk))
            look = (0.0, 1 - kk) if (pc == ("b", "Q")) else None
            if d > 1:
                sc = 1 + 0.2 * math.sin(math.pi * kk)
                draw_piece(canvas, pc, pos, sc, sc, rot, lift=lift, look=look)
            else:
                draw_piece(canvas, pc, pos, 1, 1, rot, look=look)
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
        movers.append((p, MV[p]["piece"], r))
    cr = castle_rook(u)
    if cr is not None:
        rf, rt_, rpc = MV[20]["extra"]
        excl.add(rf if u < T[20] else rt_)
        movers.append((20, rpc, cr))
    items = sorted(state.items(), key=lambda kv: -kv[0][1])
    kjit = {}
    for p, side in ((22, "w"), (25, "b"), (27, "b")):
        e = u - T[p]
        if 0 <= e < 0.3:
            for s_, pc in state.items():
                if pc == (side, "K"):
                    a = math.exp(-e / 0.09)
                    kjit[s_] = (5 * a * math.sin(e * 80), 4 * a * math.cos(e * 70))
    ql, qs = queen_look(u), queen_size(u)
    for s_, pc in items:
        if s_ in excl:
            continue
        pos, rot = cu(s_), 0.0
        sx_ = sy_ = 1.0
        look = None
        if pc == ("b", "K") and u >= T[27] and s_ == sq("c8"):
            e = u - T[27]
            j = math.exp(-e / 0.12)
            pos = (pos[0] + 6 * j * math.sin(e * 90), pos[1] + 5 * j * math.cos(e * 70))
            rot = -11 * (1 - math.exp(-e / 0.05)) * (0.85 + 0.15 * math.exp(-e / 0.6))
            if e > 0.9:
                kk = ease_in((e - 0.9) / 0.55, 2.0)
                rot = lerp(-11, -84, kk) + settle(e - 1.45, 5, 18, 0.2) * (e > 1.45)
                pos = (pos[0] + 24 * kk, pos[1] + 28 * kk)
        elif s_ in kjit:
            pos = (pos[0] + kjit[s_][0], pos[1] + kjit[s_][1])
        elif pc == ("b", "B") and T[19] + 0.08 <= u < T[21]:       # the threatened bishop shivers
            a = 0.6 + 0.4 * math.sin(u * 7)
            pos = (pos[0] + 2.6 * a * math.sin(u * 95), pos[1] + 1.8 * math.cos(u * 83))
            sx_ = sy_ = 0.97
        if pc == ("b", "Q"):
            look = ql
            sx_ *= qs
            sy_ *= qs
        draw_piece(canvas, pc, pos, sx_, sy_, rot, deco=deco_for_piece(pc, u, square=s_), look=look)
    for p in PLIES:
        captured_draw(p, u, canvas)
    for p, pc, (pos, sx, sy, rot, lift, tr, tint) in movers:
        look = None
        if pc == ("b", "Q"):
            look = ql
            sx *= qs
            sy *= qs
        dk = deco_for_piece(pc, u, ply=p)
        for tp, ta, tsc in tr:
            draw_piece(canvas, pc, tp, tsc, tsc, 0, alpha=ta, shad=False, look=look)
        draw_piece(canvas, pc, pos, sx, sy, rot, lift=lift, tint=tint if tint and tint[1] > 0 else None, deco=dk, look=look)
    fx = Image.new("RGBA", (SWP, SWP), (0, 0, 0, 0))
    over_fx(u, ImageDraw.Draw(fx), canvas)
    canvas.alpha_composite(fx)
    canvas = apply_light(canvas, u)
    draw_badges(canvas, u)
    return canvas


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
    cam = cam_pack(cx, cy, z, pi_, ro, sx, sy)
    if PLIST:
        draw_pieces3d(frame, cam, u)
    screen_fx(frame, u, cam)
    return post_fx(frame.convert("RGB"), u, t)


_bg = None


def background():
    global _bg
    if _bg is None:
        y = np.linspace(0, 1, H, dtype=np.float32)[:, None, None]
        a = np.array(BG1, np.float32)[None, None, :]
        b = np.array(BG2, np.float32)[None, None, :]
        _bg = np.repeat(a * (1 - y) + b * y, W, axis=1).astype(np.uint8)
    return _bg




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
        print("warp check", [round(warp(T[p]) - T[p], 4) for p in (22, 25, 27)], "end", round(warp(DUR) - DUR, 3))
    else:
        encode_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])


