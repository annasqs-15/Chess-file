"""Canal-NN (Scandinavian), plies 16-27, HORROR edit: 2D only (no tilt, no 3D). Red eyes in the dark, vein pin, claw marks, ash dissolve,
abyss, blood splat, dead squares + skull, ghost fire, shadow tendrils, tombstone crosses, jump scare."""
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
import decor3 as D3

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
BG1, BG2 = (22, 8, 10), (3, 2, 4)
SICK = (110, 230, 150)
BLOOD = (205, 16, 26)
BONE = (226, 218, 190)

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
        _look_cache[key] = D3.bloody(SPR[piece], key[1] / 24.0, key[2] / 24.0)
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
KEYS = [  # (arrive, centre, zoom, pitch deg, roll deg, move duration) -- pitch is always 0: flat 2D only; small dutch-angle rolls
    (0.0, (560, 560), 1.0, 0, 0, 0.0),
    (T[16] - 0.05, S("d5"), 1.12, 0, -2, 0.9),
    (T[17] - 0.05, S("e2"), 1.55, 0, 3, 0.55),
    (T[18] - 0.03, S("c7", "d7"), 1.55, 0, -3, 0.40),
    (T[19] - 0.03, S("a3", "b4"), 1.75, 0, 3, 0.35),
    (T[20] - 0.03, S("b8", "c8"), 1.6, 0, -2, 0.35),
    (T[21] - 0.03, S("a3", "b4"), 1.75, 0, 2, 0.35),
    (T[22] - 0.20, S("a4"), 1.2, 0, 0, 0.30),
    (T[22] - 0.03, S("a2", "b2"), 1.7, 0, 4, 0.17),             # zoom crash on the queen's strike (dutch roll, flat)
    (T[22] + 0.75, S("c2", "d2"), 1.2, 0, 0, 0.80),
    (T[23] - 0.05, S("d2", "e1"), 1.5, 0, -2, 0.50),
    (T[24] - 0.03, S("d1", "e1"), 1.2, 0, 0, 0.35),
    (T[24] + 0.90, S("f3", "e3"), 1.3, 0, 0, 0.90),
    (T[25] - 0.40, S("f3"), 1.65, 0, 0, 0.60),
    (T[25] - 0.03, S("d4", "d5"), 1.55, 0, -5, 0.17),           # the sacrifice (flat, dutch roll)
    (T[25] + 0.55, S("c6", "c7"), 1.7, 0, 0, 0.60),
    (T[26] + 0.50, (560, 540), 1.05, 0, 0, 0.55),
    (T[27] - 0.70, S("c5", "d5"), 1.18, 0, 0, 1.20),
    (T[27] - 0.03, S("b7", "c7"), 1.9, 0, 0, 0.25),             # zoom crash, flat on the last move
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
    18: dict(dur=.50, prog=[(0, 0), (.2, .1), (.5, .5), (.8, .9), (1, 1)], sc=[(0, 1), (.5, .92), (1, 1)], rot=[(0, 0), (.3, 7), (.6, -7), (1, 0)], st=.04, step=6, col=BLOOD),
    19: dict(dur=.30, prog=[(0, 0), (.5, .4), (1, 1)], sc=[(0, 1), (.5, .9), (1, 1)], rot=[(0, 0), (.4, 6), (1, 0)], st=.03, col=CYN),
    20: dict(dur=.50, prog=[(0, 0), (.4, .3), (1, 1)], sc=[(0, 1), (.5, 1.1), (1, 1)], rot=[(0, 0), (.5, -6), (1, 0)], st=.03, col=AMB),
    21: dict(dur=.26, prog=[(0, 0), (.35, .05), (.75, .9), (1, 1)], sc=[(0, 1), (.3, .8), (.8, 1.35), (1, 1)], rot=[(0, 0), (.3, -12), (1, 0)], st=.22, trail=2, col=CYN),
    23: dict(dur=.55, prog=[(0, 0), (.3, .15), (.7, .85), (1, 1)], sc=[(0, 1), (.5, .95), (1, 1)], rot=[(0, 0), (.5, 5), (1, 0)], st=.03, col=CYN),
    24: dict(dur=.45, prog=[(0, 0), (.25, .2), (.55, .7), (1, 1)], sc=[(0, 1), (.4, 1.15), (1, 1)], rot=[(0, 0), (1, 0)], st=.26, trail=4, col=BLOOD),
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
    if sp.get("step"):                                    # stop-motion lurch: the piece jerks forward in a few steps
        n_ = sp["step"]
        k = min(1.0, math.floor(k * n_) / n_) if k < 1 else 1.0
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


def mover16(u, f, t, h):
    """the bishop creeps out of the dark: slow start, sudden slide, pale ghost echoes behind it"""
    d0 = 0.80
    if u < h - d0 or u > h + 0.30:
        return None
    f, t = np.array(f), np.array(t)
    if u > h:
        d = u - h
        sqz = settle(d, 0.10, 26, 0.11)
        return tuple(t), 1 + sqz, 1 - sqz, 0.0, 0, [], None
    k = (u - (h - d0)) / d0
    cv = PchipInterpolator([0, .35, .75, 1], [0, .04, .72, 1])
    pr = float(cv(k))
    tr = []
    for j in range(1, 5):
        kk = max(0.0, k - 0.05 * j)
        tr.append((tuple(f + (t - f) * float(cv(kk))), 0.30 * (1 - j / 5.0), 1.0))
    return tuple(f + (t - f) * pr), 1.0, 1.0, 3 * math.sin(k * 20) * (1 - k), 8 * math.sin(math.pi * pr), tr, None


def mover25(u, f, t, h):
    f, t = np.array(f, float), np.array(t, float)
    L = np.linalg.norm(t - f)
    uv = (t - f) / L
    if u < h - 0.80 or u > h + 0.40:
        return None
    if u < h - 0.28:                       # the martyr rises and hovers
        k = ease_io((u - (h - 0.80)) / 0.40)
        sh = np.array([3.2 * math.sin(u * 83), 2.6 * math.cos(u * 71)]) * k      # trembling, possessed
        return tuple(f + sh), 1 + 0.06 * k, 1 + 0.10 * k, 5 * math.sin(u * 57) * k, 30 * k, [], None
    if u < h:
        k = (u - (h - 0.28)) / 0.28
        e = ease_in(k, 2.6)
        pos = f + uv * L * e
        tr = [(tuple(f + uv * L * ease_in(max(0, k - j * 0.07), 2.6)), 0.30 * (1 - j / 6.0), 1.1) for j in range(1, 6)]
        return tuple(pos), 1.10 - 0.1 * e, 1.14 + 0.1 * e, lerp(0, 0, e), 54 * (1 - e) + 8, tr, (BLOOD, 0.0, 0.0)
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
    tr = [(tuple(f + (t - f) * ease_io(max(0.0, k - 0.07 * j))), 0.26 * (1 - j / 4.0), 1.0) for j in range(1, 4)]
    return tuple(f + (t - f) * pr), 1 - 0.04 * s, 1 + 0.06 * s, 0.0, 6 * s, tr, None


def mover(p, u):
    """-> (pos, sx, sy, rot, lift, trail, tint) while the mover is animated, else None"""
    m = MV[p]
    f, t = cu(m["from"]), cu(m["to"])
    h = T[p]
    if p == 16:
        return mover16(u, f, t, h)
    if p == 22:
        return lunge(u, f, t, h, back=0.55 * SQU, t0=0.55, t1=0.28, pw=3.2, col=BLOOD)
    if p == 25:
        return mover25(u, f, t, h)
    if p == 27:
        return lunge(u, f, t, h, back=0.5 * SQU, t0=0.60, t1=0.30, pw=3.4, spin=0.0, col=BLOOD)
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




BADGE = {25: ("!!", (70, 150, 120)), 27: ("#", (170, 14, 24))}

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



_dc = {}


def _cached(key, fn):
    if key not in _dc:
        if len(_dc) > 10:
            _dc.clear()
        _dc[key] = fn()
    return _dc[key]


def deco_for_piece(pc, u, square=None, ply=None):
    if pc == ("w", "K") and T[21] + 0.05 <= u < T[26] + 0.8:          # the hunter's eyes light up after the first kill
        k = ease_io((u - T[21] - 0.05) / 0.35) * (1 - ease_io((u - T[26] - 0.35) / 0.4))
        return _cached(("e", round(k * 14)), lambda: D3.king_redeyes(BASE[("w", "K")], round(k * 14) / 14.0))
    if pc == ("b", "K") and T[25] + 0.12 <= u < REW0:
        kk = 1.0 - ease_io((u - (REW0 - 0.35)) / 0.35)
        return _cached(("k", round(u * 60), round(kk * 20)), lambda: D2.blend_k(BASE[("b", "K")], D3.king_ashen(BASE[("b", "K")], u - T[25] - 0.12), kk))
    return None


def queen_look(u):
    """black queen: blood-fed (22, 24), then corpse-pale and cracked once the net closes"""
    g = 0.5 * ease_io((u - T[22]) / 0.5) + 0.5 * ease_io((u - T[24]) / 0.5)
    d = ease_io((u - (T[26] + 0.35)) / 0.65)
    return (g * (1 - d), d)


def queen_size(u):
    return 1.0 + 0.04 * (0.5 * ease_io((u - T[22]) / 0.5) + 0.5 * ease_io((u - T[24]) / 0.5)) * (1 - ease_io((u - (T[26] + 0.35)) / 0.65))


def accent(p):
    return BONE if MV[p]["piece"][0] == "w" else BLOOD


def sqn(n):
    return cu(sq(n))


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


# ------------------------------------------------------------- 16-18: the pin is a living vein from the bishop to the white king
_VEIN = []


def vein_paths():
    if _VEIN:
        return _VEIN
    rs = np.random.RandomState(12)
    a, b = np.array(sqn("b4"), float), np.array(sqn("e1"), float)
    v = b - a
    Ln = np.linalg.norm(v)
    nrm = np.array([-v[1], v[0]]) / Ln
    n = 30
    main = [a + v * (i / n) + nrm * rs.uniform(-9, 9) * math.sin(math.pi * i / n) for i in range(n + 1)]
    _VEIN.append((main, 0.0))
    for _ in range(10):
        i = rs.randint(3, n - 2)
        ang = rs.uniform(-1.3, 1.3)
        d = (v / Ln) * math.cos(ang) + nrm * math.sin(ang)
        ln = rs.uniform(45, 115)
        _VEIN.append(([main[i] + d * ln * (j / 5.0) + nrm * rs.uniform(-7, 7) for j in range(6)], i / float(n)))
    return _VEIN


def veins_fx(u, dv):
    t0, t1 = T[16] + 0.30, T[18] + 0.45
    if u < t0 or u > t1:
        return
    prog = ease_out((u - t0) / 0.9, 2.0)
    fade = clamp(1 - (u - (t1 - 0.4)) / 0.4)
    pul = 1 + 0.40 * heart(u)
    for pts, at in vein_paths():
        pr = prog if at == 0 else clamp((prog - at) / max(1e-3, 1 - at) * 1.5)
        if pr <= 0:
            continue
        pp = [tuple(np.array(q) * RS) for q in part(pts, pr)]
        if len(pp) < 2:
            continue
        w = 1.0 if at == 0 else 0.55
        dv.line(pp, fill=(40, 0, 6, int(235 * fade)), width=int(19 * w * pul * RS), joint="curve")
        dv.line(pp, fill=(172, 10, 22, int(255 * fade)), width=int(9.5 * w * pul * RS), joint="curve")
        dv.line(pp, fill=(255, 84, 80, int(210 * fade)), width=int(3 * w * RS), joint="curve")
    bracket(dv, sq("e1"), BLOOD, clamp((u - t0) / 0.6) * fade)


# ------------------------------------------------------------- 20: the castling rook drags a dark smear across the back rank
def smear_fx(u, dv):
    t0, t1 = T[20] - 0.45, T[20] + 1.3
    if not (t0 <= u < t1):
        return
    rf, rt_, _pc = MV[20]["extra"]
    f, t = np.array(cu(rf), float), np.array(cu(rt_), float)
    k = ease_io(clamp((u - t0) / 0.5))
    fade = clamp(1 - (u - (T[20] + 0.3)) / 1.0)
    end = f + (t - f) * k
    rs = np.random.RandomState(3)
    for j in range(5):
        off = rs.uniform(-20, 20)
        w = rs.uniform(12, 26)
        dv.line([px(f + np.array([0, off])), px(end + np.array([0, off * 0.5]))], fill=(84, 0, 10, int(165 * fade)), width=int(w * RS))


# ------------------------------------------------------------- board effect 1 (22): an abyss opens at a1 and swallows the rook
def abyss_fx(u, dv):
    t0, t1 = T[21] + 0.10, T[22] + 1.15
    if not (t0 <= u < t1):
        return
    grow = ease_out((u - t0) / 0.55, 2.2)
    col = ease_in((u - (T[22] + 0.55)) / 0.55, 1.6)
    R = 76 * grow * (1 - col)
    if u >= T[22]:
        R *= 1 + 0.28 * math.exp(-(u - T[22]) / 0.12)
    if R < 2:
        return
    c = np.array(sqn("a1"))
    for scale, fill in ((1.0, (112, 6, 14, 235)), (0.90, (3, 1, 5, 250)), (0.60, (22, 2, 30, 255)), (0.32, (0, 0, 0, 255))):
        pts = []
        for i in range(72):
            th = 2 * math.pi * i / 72
            r = R * scale * (1 + 0.10 * math.sin(5 * th + u * 8 + scale * 3) + 0.06 * math.sin(9 * th - u * 12))
            pts.append(px((c[0] + math.cos(th) * r, c[1] + math.sin(th) * r)))
        dv.polygon(pts, fill=fill)
    for j in range(3):
        pts = []
        for i in range(26):
            th = u * 6 + j * 2.09 + i * 0.22
            r = R * 0.85 * (1 - i / 27.0)
            pts.append(px((c[0] + math.cos(th) * r, c[1] + math.sin(th) * r)))
        dv.line(pts, fill=(150, 22, 66, 210), width=max(2, int(3.5 * RS)), joint="curve")


def rank_fx(u, dv):
    for i, nm in enumerate(("b1", "c1", "d1")):
        e = u - T[22] - 0.07 * i
        if 0 < e < 0.9:
            sq_fill(dv, sq(nm), BLOOD, 0.5 * clamp(1 - e / 0.9) * (0.6 + 0.4 * (math.sin(e * 70) > 0)))


# ------------------------------------------------------------- board effect 2 (24): blood splatter on h1
def splat_fx(u, dv):
    t0, t1 = T[24], T[24] + 2.4
    if not (t0 <= u < t1):
        return
    e = u - t0
    k = ease_out(e / 0.16, 2.5)
    dry = clamp(e / 1.6)
    fade = clamp(1 - (e - 1.7) / 0.7)
    col = (int(196 - 96 * dry), int(10 - 8 * dry), int(22 - 12 * dry))
    c = np.array(sqn("h1")) + np.array([-6, -6])
    pts = []
    for i in range(44):
        th = 2 * math.pi * i / 44
        r = (36 + 7 * math.sin(th * 4 + 1) + 5 * math.sin(th * 7)) * k
        pts.append(px((c[0] + math.cos(th) * r, c[1] + math.sin(th) * r)))
    dv.polygon(pts, fill=col + (int(240 * fade),))
    rs = np.random.RandomState(31)
    for i in range(17):
        th = rs.uniform(0, 2 * math.pi)
        d = np.array([math.cos(th), math.sin(th)])
        n = np.array([-d[1], d[0]])
        ln = rs.uniform(60, 190) * k
        w = rs.uniform(5, 12)
        p0, p1 = c + d * 26, c + d * ln
        dv.polygon([px(p0 + n * w / 2), px(p1), px(p0 - n * w / 2)], fill=col + (int(235 * fade),))
        q = px(p1 + d * rs.uniform(8, 28) * k)
        r_ = rs.uniform(4, 9) * RS * k
        dv.ellipse((q[0] - r_, q[1] - r_, q[0] + r_, q[1] + r_), fill=col + (int(235 * fade),))
    q = px(c + np.array([-12, -12]))
    dv.ellipse((q[0] - 7 * RS * k, q[1] - 5 * RS * k, q[0] + 7 * RS * k, q[1] + 5 * RS * k), fill=(255, 96, 96, int(150 * fade * (1 - dry))))


# ------------------------------------------------------------- board effect 3 (24 -> 25): the diagonal h1-c6 goes dead, square by square
DEAD = ("g2", "f3", "e4", "d5", "c6")


def dead_fx(u, dv):
    for i, nm in enumerate(DEAD):
        t0 = T[24] + 0.90 + 0.34 * i
        e = u - t0
        if e < 0 or u > T[25] + 1.0:
            continue
        fade = clamp(1 - (u - (T[25] + 0.4)) / 0.6)
        fl = 1.0 if e > 0.28 else (0.35 + 0.65 * (math.sin(e * 95) > 0))
        sq_fill(dv, sq(nm), (6, 16, 10), 0.82 * fl * fade)
        c = px(cu(sq(nm)))
        r = SQU * RS / 2 - 3
        dv.rectangle((c[0] - r, c[1] - r, c[0] + r, c[1] + r), outline=(80, 230, 130, int(230 * fl * fade)), width=int(5 * RS))


# ------------------------------------------------------------- 25-27 marks
def slash_fx(u, dv):
    t0 = T[26] + 0.55
    if not (t0 <= u < T[27] + 0.1):
        return
    a = clamp(1 - (u - T[27]) / 0.1)
    k = ease_io((u - t0) / (T[27] - 0.15 - t0))
    p0, p1 = np.array(sqn("e2")), np.array(sqn("a6"))
    v = p1 - p0
    nrm = np.array([-v[1], v[0]]) / np.linalg.norm(v)
    rs = np.random.RandomState(14)
    offs = rs.uniform(-7, 7, 24)
    pts = [p0 + v * (i / 23.0) + nrm * offs[i] for i in range(24)]
    pp = [tuple(np.array(q) * RS) for q in part(pts, k)]
    if len(pp) >= 2:
        dv.line(pp, fill=(40, 0, 6, int(235 * a)), width=int(17 * RS), joint="curve")
        dv.line(pp, fill=(215, 20, 30, int(255 * a)), width=int(8 * RS), joint="curve")
        dv.line(pp, fill=(255, 205, 195, int(235 * a)), width=int(3 * RS), joint="curve")
    bracket(dv, sq("c8"), BLOOD, clamp((u - t0) / 0.3) * a)


def under_fx(u, dv, canvas):
    cur = max([p for p in PLIES if T[p] - 0.05 <= u], default=None)
    if cur is not None and cur != 27:
        e = u - T[cur]
        a = clamp(1 - (e - 0.9) / 0.5) * 0.17
        sq_fill(dv, MV[cur]["from"], accent(cur), a * 0.6)
        sq_fill(dv, MV[cur]["to"], accent(cur), a * 1.3)
    veins_fx(u, dv)
    smear_fx(u, dv)
    abyss_fx(u, dv)
    rank_fx(u, dv)
    splat_fx(u, dv)
    dead_fx(u, dv)
    if T[25] <= u < T[26] + 0.2:
        a = clamp(1 - (u - T[26] - 0.05) / 0.15)
        sq_fill(dv, sq("c8"), BLOOD, 0.30 * a * (0.7 + 0.3 * heart(u)))
        bracket(dv, sq("c8"), BLOOD, a)
    slash_fx(u, dv)
    if u >= T[27]:
        e = u - T[27]
        sq_fill(dv, sq("c8"), BLOOD, clamp(e / 0.04) * 0.9 * (1 - ease_in((u - (REW0 - 0.4)) / 0.4)))


# ------------------------------------------------------------- over pieces
def drips_fx(df, u):
    if not (T[19] + 0.1 < u < T[21] + 0.05):
        return
    c = np.array(sqn("b4"))
    a = clamp((u - T[19] - 0.1) / 0.1) * clamp(1 - (u - T[21]) / 0.05)
    for i, dx in enumerate((-26, 2, 24)):
        ph = (u * 1.1 + i * 0.37) % 1.0
        p = px((c[0] + dx, c[1] + 20 + ph * ph * 95))
        R = 7 * (1 - 0.4 * ph) * RS
        al = int(255 * a * clamp(1 - ph * 0.9))
        df.polygon([(p[0], p[1] - R * 2.6), (p[0] - R * 0.9, p[1] - R * 0.2), (p[0] + R * 0.9, p[1] - R * 0.2)], fill=(190, 10, 22, al))
        df.ellipse((p[0] - R, p[1] - R, p[0] + R, p[1] + R), fill=(190, 10, 22, al))


def claws_fx(df, u):
    e = u - T[19]
    if e < 0 or u > T[21] + 0.05:
        return
    c = np.array(sqn("b4"))
    a = clamp(1 - (u - (T[21] - 0.1)) / 0.15)
    for i, off in enumerate((-26, 0, 26)):
        k = ease_out(clamp((e - 0.06 * i) / 0.14), 2.0)
        if k <= 0:
            continue
        p0 = np.array([c[0] - 50 + off, c[1] - 54])
        p1 = p0 + np.array([84, 104]) * k
        df.line([px(p0), px(p1)], fill=(30, 0, 4, int(235 * a)), width=int(15 * RS))
        df.line([px(p0), px(p1)], fill=(215, 20, 30, int(255 * a)), width=int(8 * RS))
        df.line([px(p0 + np.array([2, 0])), px(p1 + np.array([2, 0]))], fill=(255, 190, 180, int(200 * a)), width=int(2.4 * RS))


def ash_fx(df, u):
    e = u - T[21]
    if e < 0 or e > 1.5:
        return
    c = np.array(sqn("b4"))
    rs = np.random.RandomState(17)
    for i in range(38):
        x0, y0 = rs.uniform(-50, 50), rs.uniform(-45, 35)
        d0 = rs.uniform(0, 0.2)
        ee = e - d0
        if ee < 0:
            continue
        p = c + np.array([x0 + 38 * ee + 14 * math.sin(ee * 5 + i), y0 - 78 * ee + 10 * math.cos(ee * 4 + i)])
        a = clamp(1 - ee / 1.25)
        q = px(p)
        r_ = (3 + (i % 4)) * RS * (1 - 0.3 * ee)
        col = (255, 150, 40) if (ee < 0.35 and i % 2) else (176, 170, 166)
        df.ellipse((q[0] - r_, q[1] - r_, q[0] + r_, q[1] + r_), fill=col + (int(235 * a),))


def shards_fx(df, u, t0, cs, seed, n=9):
    e = u - t0
    if e < 0 or e > 0.9:
        return
    c = np.array(sqn(cs) if isinstance(cs, str) else cs, float)
    rs = np.random.RandomState(seed)
    for i in range(n):
        ang = rs.uniform(0, 2 * math.pi)
        sp = rs.uniform(170, 400)
        d = (1 - math.exp(-3.5 * e)) / 3.5
        p = c + np.array([math.cos(ang), math.sin(ang)]) * sp * d + np.array([0, 160 * e * e])
        r0 = rs.uniform(11, 22)
        rot = rs.uniform(0, 6.28) + e * rs.uniform(-12, 12)
        pts = [px((p[0] + math.cos(rot + k_ * 2.1) * r0 * (1 if k_ else 1.6), p[1] + math.sin(rot + k_ * 2.1) * r0 * (1 if k_ else 1.6))) for k_ in range(3)]
        a = int(255 * clamp(1 - (e - 0.45) / 0.45))
        df.polygon(pts, fill=BONE + (a,), outline=(40, 20, 20, a))


def skull_fx(df, u):
    e = u - T[25]
    if e < 0 or e > 1.4:
        return
    pop = 1 + 0.7 * math.exp(-e / 0.08)
    a = clamp(1 - (e - 0.8) / 0.6)
    c = np.array(sqn("c6")) + np.array([0, -78 - 38 * ease_out(e / 1.3, 1.6)])
    D3.skull(df, px(c), 0.95 * RS * pop, a, jaw=abs(math.sin(e * 26)) * (e < 0.6))


def cross_fx(df, u):
    for nm, dly in (("b7", 0.0), ("c7", 0.07), ("b8", 0.14)):
        e = u - T[27] - dly
        if e < 0:
            continue
        f_ = clamp(1 - (u - (REW0 - 0.25)) / 0.25)
        if f_ <= 0.02:
            continue
        k = 1 + 0.8 * (1 - ease_out(e / 0.10, 2.0))
        a = clamp(e / 0.03) * f_
        al = int(255 * a)
        c = px(cu(sq(nm)))
        r = (SQU / 2 - 6) * k * RS
        df.rectangle((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=(34, 0, 8, int(205 * a)), outline=(160, 12, 22, al), width=int(7 * RS))
        s = k * RS
        df.rectangle((c[0] - 7 * s, c[1] - 36 * s, c[0] + 7 * s, c[1] + 32 * s), fill=BONE + (al,), outline=(30, 10, 12, al), width=max(2, int(3 * s)))
        df.rectangle((c[0] - 24 * s, c[1] - 20 * s, c[0] + 24 * s, c[1] - 7 * s), fill=BONE + (al,), outline=(30, 10, 12, al), width=max(2, int(3 * s)))
        df.rectangle((c[0] - 5 * s, c[1] - 33 * s, c[0] - 2 * s, c[1] + 28 * s), fill=(255, 255, 245, int(170 * a)))


def smoke_fx(canvas, u):
    e = u - T[26]
    if e < 0 or e > 1.5:
        return
    a_, b_ = np.array(sqn("c6")), np.array(sqn("e2"))
    rs = np.random.RandomState(33)
    nrm = np.array([-(b_ - a_)[1], (b_ - a_)[0]])
    nrm = nrm / np.linalg.norm(nrm)
    g = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    dg = ImageDraw.Draw(g)
    for i in range(18):
        k = clamp((e - i * 0.025) / 0.85)
        if k <= 0 or k >= 1:
            continue
        ctrl = (a_ + b_) / 2 + nrm * rs.uniform(-150, 150)
        for tr in range(5):
            kk = ease_io(clamp(k - tr * 0.035))
            p = (1 - kk) ** 2 * a_ + 2 * (1 - kk) * kk * ctrl + kk ** 2 * b_
            q = px(p)
            r_ = (13 + 7 * kk + tr * 3) * RS
            col = (138, 10, 22) if i % 2 else (64, 56, 66)
            dg.ellipse((q[0] - r_, q[1] - r_, q[0] + r_, q[1] + r_), fill=col + (int(170 * (1 - tr * 0.17)),))
    canvas.alpha_composite(g.filter(ImageFilter.GaussianBlur(7 * RS)))
    t0 = T[26] + 0.7
    if u > t0:
        glow(canvas, sqn("e2"), BLOOD, (70 + 70 * clamp((u - t0) / 0.8)) * (0.80 + 0.30 * heart(u)), 0.9 * clamp((u - t0) / 0.3))


def over_fx(u, df, canvas):
    drips_fx(df, u)
    claws_fx(df, u)
    ash_fx(df, u)
    shards_fx(df, u, T[24], "h1", 41, 10)
    shards_fx(df, u, T[25], "c6", 42, 11)
    skull_fx(df, u)
    smoke_fx(canvas, u)
    cross_fx(df, u)


# ------------------------------------------------------------- captured pieces
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
    if p == 21:                                    # the bishop burns to ash
        if e > 0.9:
            return
        k = ease_in(e / 0.85, 1.2)
        draw_piece(canvas, pc, tuple(pos), 1, 1, 0, alpha=1.0, shad=False, deco=_cached(("ash", round(k * 30)), lambda: D3.dissolve(BASE[pc], round(k * 30) / 30.0)))
    elif p == 22:                                  # the rook sinks into the abyss
        if e > 0.5:
            return
        k = ease_in(e / 0.45, 1.5)
        draw_piece(canvas, pc, tuple(pos), 1 - 0.9 * k, 1 - 0.9 * k, 200 * k, alpha=clamp(1 - k * 0.9), shad=False)
    elif p == 24:                                  # the rook turns red, shakes and bursts into bone (shards in over_fx)
        if e > 0.22:
            return
        k = e / 0.22
        j = np.array([5 * math.sin(e * 150), 4 * math.cos(e * 130)])
        draw_piece(canvas, pc, tuple(pos + j), 1 + 0.15 * k, 1 + 0.15 * k, 0, alpha=clamp(1 - k * 0.8), shad=False, tint=(BLOOD, 0.85 * k, 0.0))
    elif p == 26:                                  # the martyr queen turns to pale smoke and rises
        if e > 0.9:
            return
        k = ease_out(e / 0.9, 1.6)
        draw_piece(canvas, pc, tuple(pos + np.array([0, -60 * k])), 1 - 0.15 * k, 1 + 0.55 * k, 0, alpha=clamp(1 - k * 1.05), shad=False, look=(0.0, 0.85 * k))


# ------------------------------------------------------------- screen-space layer: red eyes in the dark, ghost fire, shadow tendrils
def white_queen_state(u):
    h = T[25]
    f, t = cu(MV[25]["from"]), cu(MV[25]["to"])
    r = mover25(u, f, t, h)
    if r is None:
        return (np.array(f if u < h else t, float), 0.0)
    return (np.array(r[0], float), r[4])


def eye_state(u):
    o = ease_io((u - 0.25) / 0.30) * (1 - ease_io((u - (T[16] + 0.9)) / 0.3))
    sc, al, cy = 1.0, 0.92, 190
    for tb in (0.95, T[16] + 0.35):
        d = u - tb
        if 0 <= d < 0.14:
            o *= 1 - math.sin(math.pi * d / 0.14)
    o2 = ease_io((u - (T[27] + 0.35)) / 0.25) * (1 - ease_io((u - (REW0 - 0.35)) / 0.30))
    if o2 > 0.01:
        o, sc, al, cy = o2, 1.5, 0.66, 150
    return o, sc, al, cy


def eyes_fx(frame, u):
    o, sc, al, cy = eye_state(u)
    if o < 0.03:
        return
    lay = Image.new("RGBA", (900, 300), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    look = 0.6 * math.sin(u * 2.2) if sc < 1.2 else 0.0
    for sd in (-1, 1):
        ex, ey = 450 + sd * 150 * sc, 150
        w, h = 92 * sc, 46 * sc * o
        slant = 15 * sc
        up, lo = [], []
        for i in range(25):
            f = -1 + 2 * i / 24.0
            x = ex + f * w
            sl = slant * f * (-sd)
            up.append((x, ey - h * (1 - f * f) ** 0.8 + sl))
            lo.append((x, ey + h * 0.65 * (1 - f * f) ** 0.8 + sl))
        d.polygon(up + lo[::-1], fill=(255, 38, 28, 255))
        if o > 0.2:
            d.ellipse((ex + look * 22 * sc - 7 * sc, ey - h * 0.85, ex + look * 22 * sc + 7 * sc, ey + h * 0.6), fill=(24, 0, 0, 255))
        d.ellipse((ex - w * 0.55, ey - h * 0.55, ex - w * 0.2, ey - h * 0.15), fill=(255, 190, 170, 190))
    gl = lay.filter(ImageFilter.GaussianBlur(24))
    ga = gl.getchannel("A").point(lambda v: min(255, int(v * 1.7 * al)))
    gl.putalpha(ga)
    la = lay.getchannel("A").point(lambda v: int(v * al))
    lay.putalpha(la)
    frame.alpha_composite(gl, (540 - 450, cy - 150))
    frame.alpha_composite(lay, (540 - 450, cy - 150))


def tendril(ov, p0, p1, sag, wid, a):
    """tapered black-red tendril from screen point p0 to p1 (a quadratic curve), wide at the root"""
    ctrl = ((p0[0] + p1[0]) / 2 + sag[0], (p0[1] + p1[1]) / 2 + sag[1])
    pts = [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * ctrl[0] + t * t * p1[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * ctrl[1] + t * t * p1[1]) for t in np.linspace(0, 1, 18)]
    L_, R_ = [], []
    for i, q in enumerate(pts):
        nx, ny = (pts[min(i + 1, 17)][0] - pts[max(i - 1, 0)][0]), (pts[min(i + 1, 17)][1] - pts[max(i - 1, 0)][1])
        nl = math.hypot(nx, ny) + 1e-6
        nx, ny = -ny / nl, nx / nl
        w = wid * (1 - 0.88 * i / 17.0) / 2
        L_.append((q[0] + nx * w, q[1] + ny * w))
        R_.append((q[0] - nx * w, q[1] - ny * w))
    ov.poly(L_ + R_[::-1], (12, 2, 10, int(240 * a)), (160, 12, 24, int(255 * a)), 2.0)


def screen_fx(frame, u, cam):
    eyes_fx(frame, u)
    ov = None
    e = u - T[26]
    if -0.62 < e < 0.45:                           # 26: shadow tendrils haul the pawn to its doom
        ov = D2.Ov()
        top_k = ease_out((e + 0.62) / 0.3, 2.0) * (1 - ease_in((e - 0.12) / 0.3, 1.5))
        r = mover(26, u)
        ppos = np.array(r[0] if r is not None else cu(MV[26]["from"] if u < T[26] else MV[26]["to"]), float)
        x, y, d = project_pt(cam, ppos[0], ppos[1], 12.0)
        s_ = FOC / d
        tight = clamp(1 - abs(e) / 0.3)
        roots = [(-60, -40), (330, -60), (760, -30), (1140, -50), (-60, 700), (1140, 560)]
        for i, (rx, ry) in enumerate(roots):
            tip = (rx + (x - rx) * top_k + 14 * s_ * math.sin(u * 9 + i), ry + (y - ry) * top_k + 10 * s_ * math.cos(u * 8 + i))
            sag = ((1 - tight) * 70 * math.sin(u * 5 + i * 1.3), 40 + (1 - tight) * 30 * math.cos(u * 6 + i))
            if top_k > 0.02:
                tendril(ov, (rx, ry), tip, sag, 34 * s_ * 0.7 + 10, clamp(top_k * 3))
    if T[25] - 0.80 < u < T[26] + 0.30:            # 25: the white queen burns with pale ghost fire
        ov = ov or D2.Ov()
        pos, lift = white_queen_state(u)
        unf = ease_out((u - (T[25] - 0.80)) / 0.40, 2.0)
        blast = 1 + 0.9 * math.exp(-max(0.0, u - T[25]) / 0.10) if u >= T[25] else 1.0
        vanish = clamp(1 - (u - T[26]) / 0.25)
        x, y, d = project_pt(cam, pos[0], pos[1], lift * 0.9)
        s_ = FOC / d
        for i, (dx, dy) in enumerate(((-34, 20), (34, 20), (-46, -2), (46, -2), (-22, -22), (22, -22), (0, -34), (0, 30))):
            D3.flame(ov, (x + dx * s_ * 0.9, y + dy * s_ * 0.9 + 10 * s_), s_ * 0.62 * unf * blast, u, vanish * 0.85, i + 3)
    if ov is not None:
        ov.blit(frame)


AMB0 = 0.60            # the board lives in the dark; lantern pools reveal it
DIPS = [(0.30, .30, .06), (0.42, .22, .05), (1.95, .28, .05), (3.65, .32, .07), (4.78, .30, .05), (6.15, .38, .08),
        (7.35, .30, .06), (9.25, .28, .05), (10.45, .36, .07), (12.95, .45, .08), (13.55, .38, .05)]


def light_events():
    """(t0, rise, hold, fall, ambient dip, (sq a, sq b), radius, strength, colour)"""
    return [
        (0.10, 0.60, 0.80, 0.50, 0.0, ("d6", "d6"), 330, 0.85, BONE),
        (T[16] - 0.25, 0.25, 0.90, 0.40, 0.0, ("b4", "b4"), 250, 0.95, SICK),
        (T[17] - 0.20, 0.25, 0.50, 0.30, 0.0, ("b4", "e1"), 340, 0.80, BLOOD),
        (T[18] - 0.20, 0.20, 0.35, 0.30, 0.0, ("c7", "d7"), 260, 0.80, SICK),
        (T[19] - 0.20, 0.20, 0.40, 0.30, 0.0, ("a3", "b4"), 260, 0.95, BLOOD),
        (T[20] - 0.20, 0.20, 0.35, 0.30, 0.0, ("b8", "d8"), 300, 0.80, BONE),
        (T[21] - 0.20, 0.20, 0.30, 0.30, 0.0, ("a3", "b4"), 280, 0.95, BLOOD),
        (T[22] - 0.30, 0.20, 1.10, 0.50, 0.30, ("a1", "a1"), 270, 1.10, BLOOD),
        (T[23] - 0.20, 0.25, 0.80, 0.50, 0.0, ("d2", "e1"), 290, 0.80, BONE),
        (T[24] - 0.20, 0.20, 0.70, 0.40, 0.0, ("h1", "h1"), 270, 1.00, BLOOD),
        (T[24] + 0.80, 0.60, 1.40, 0.40, 0.25, ("f3", "f3"), 300, 1.00, SICK),
        (T[25] - 0.10, 0.12, 0.35, 0.50, 0.0, ("c6", "c6"), 300, 1.20, SICK),
        (T[26] + 0.00, 0.30, 1.40, 0.50, 0.20, ("e2", "e2"), 300, 1.00, BLOOD),
        (T[27] - 0.20, 0.20, 0.60, 0.70, 0.30, ("c8", "c8"), 300, 1.20, BLOOD),
    ]


def light_map(u):
    amb = AMB0
    for (td, dd, dl) in DIPS:                              # failing-bulb flicker
        d = u - td
        if 0 <= d < dl:
            amb -= dd * AMB0 * math.sin(math.pi * d / dl)
    amb += 0.025 * math.sin(u * 47.0) * math.sin(u * 13.0)
    pools = []
    for (t0, ri, ho, fa, dip, cen, rad, st, col) in light_events():
        e = u - t0
        if e <= 0:
            continue
        k = ease_io(e / ri) * (1 - ease_io((e - ri - ho) / fa))
        if k <= 0.003:
            continue
        amb -= dip * k
        pools.append((S(*cen), rad * (1.5 - 0.5 * k), st * k * 0.72, col))
    ex = 0.0
    for tk, s in KICKS:
        d = u - tk
        if 0 <= d < 0.3:
            ex += 0.10 * s * math.exp(-d / 0.07)
    return max(amb, 0.10) + ex, pools


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




GRADE = [(0.0, (0.92, 1.0, 0.94)), (T[17], (0.90, 1.02, 0.92)), (T[21], (1.06, 0.96, 0.94)), (T[22] - 0.2, (0.95, 0.98, 0.95)),
         (T[22] + 0.05, (1.30, 0.80, 0.80)), (T[24] + 0.6, (1.12, 0.92, 0.90)), (T[25] - 0.4, (0.84, 1.06, 0.96)),
         (T[25] + 0.1, (0.82, 1.10, 0.98)), (T[26] + 0.2, (1.20, 0.86, 0.86)), (T[27] - 0.3, (1.12, 0.90, 0.90)),
         (T[27] + 0.1, (1.38, 0.72, 0.72)), (REW0, (1.20, 0.84, 0.84)), (REW1, (0.92, 1.0, 0.94)), (DUR + 1, (0.92, 1.0, 0.94))]


def grade(u):
    ts = [a for a, _ in GRADE]
    return [1 + 0.55 * (float(np.interp(u, ts, [c[i] for _, c in GRADE])) - 1) for i in range(3)]



_VIG = None
_FOG = None
_GR = None
DESAT = 0.38


def _tables():
    global _VIG, _FOG, _GR
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.50) / (H * 0.60)) ** 2)
        _VIG = r.astype(np.float32)
        rs = np.random.RandomState(4)
        lo = ndi.gaussian_filter(rs.rand(120, 90).astype(np.float32), 5.0, mode="wrap")
        lo = (lo - lo.min()) / (lo.max() - lo.min())
        mid = ndi.gaussian_filter(rs.rand(240, 180).astype(np.float32), 5.0, mode="wrap")
        mid = (mid - mid.min()) / (mid.max() - mid.min())
        lo = np.asarray(Image.fromarray((lo * 255).astype(np.uint8)).resize((180, 240), Image.BICUBIC), np.float32) / 255.0
        f = 0.65 * lo + 0.35 * mid
        f = np.clip((f - 0.30) * 1.9, 0, 1)
        _FOG = np.asarray(Image.fromarray((f * 255).astype(np.uint8)).resize((W + 360, H + 360), Image.BICUBIC), np.float32) / 255.0
        g = np.random.RandomState(9).randn(6, H, W).astype(np.float16) * 5.0
        _GR = g


def heart(u):
    ph = (u % 0.571) / 0.571
    return math.exp(-((ph - 0.04) / 0.05) ** 2) + 0.65 * math.exp(-((ph - 0.30) / 0.05) ** 2)


def fog_amount(u):
    a = 0.13
    a += 0.16 * clamp(1 - u / 2.0) * clamp(u / 0.3)                      # creeping in at the start
    a += 0.10 * (ease_io((u - (T[26] + 0.4)) / 0.5) * (1 - ease_io((u - (T[27] - 0.05)) / 0.1)))
    a += 0.12 * ease_io((u - (T[27] + 0.3)) / 0.5) * (1 - ease_io((u - (REW0 - 0.2)) / 0.3))
    for tk in (T[22], T[25]):
        d = u - tk
        if 0 <= d < 0.6:
            a -= 0.10 * math.exp(-d / 0.15)                              # blown clear by the hit
    return clamp(a, 0, 0.42)


def post_fx(frame, u, t):
    _tables()
    fi = int(round(t * FPS))
    arr = np.asarray(frame, np.float32) * np.array(grade(u), np.float32)[None, None, :]
    lum = (arr[..., 0] * 0.30 + arr[..., 1] * 0.59 + arr[..., 2] * 0.11)[..., None]
    arr = lum + (arr - lum) * (1 - DESAT)
    fa = fog_amount(u)
    if fa > 0.005:
        ox, oy = int((u * 34) % 360), int((u * 11 + 90) % 360)
        fg = _FOG[oy:oy + H, ox:ox + W][..., None] * fa
        arr = arr * (1 - fg) + np.array([150, 168, 160], np.float32) * fg
    hb = heart(u)
    v = np.clip(_VIG - 0.42, 0, 1.2)
    dark = np.clip(v * (0.95 + 0.30 * hb), 0, 1.0)
    arr = arr * (1 - 0.82 * dark[..., None] ** 1.3) + np.array([34, 0, 4], np.float32) * (0.35 * dark[..., None] ** 1.3) * (0.4 + hb)
    rgb = 0.0
    for tk, amp, dec in ((T[22], 12, 0.10), (T[25], 9, 0.09), (T[27], 18, 0.16)):
        d = t - tk
        if 0 <= d < 0.4:
            rgb = max(rgb, amp * math.exp(-d / dec))
    if rgb > 0.8:
        s = int(rgb)
        arr[..., 0] = np.roll(arr[..., 0], s, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -s, axis=1)
    arr = arr + _GR[fi % 6].astype(np.float32)[..., None]
    for tk, a, dec, col in ((T[22], 0.30, 0.05, (255, 60, 50)), (T[25], 0.30, 0.05, (210, 255, 225)), (T[27], 0.65, 0.09, (255, 24, 24))):
        d = t - tk
        if 0.0 <= d < 0.4 and not (tk == T[27] and d < 0.05):
            fl = a * math.exp(-d / dec)
            if fl > 0.01:
                arr = arr + (np.array(col, np.float32) - arr) * fl
    if T[27] <= t < T[27] + 0.05:                                         # jump scare: one black beat on the mate
        arr = arr * 0.0
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
        elif pc == ("b", "B") and T[19] + 0.08 <= u < T[21]:       # the doomed bishop sees double: a blood-red ghost slips out of it
            a = 0.6 + 0.4 * math.sin(u * 7)
            gx_ = 11 * a * math.sin(u * 31)
            draw_piece(canvas, pc, (pos[0] + gx_, pos[1] + 3 * math.cos(u * 23)), 1.0, 1.0, 0.0, alpha=0.55, shad=False, tint=(BLOOD, 0.9, 0.0))
            pos = (pos[0] - 0.4 * gx_, pos[1])
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
    cx, cy, z, pi_, ro, sx, sy = camera(u)
    assert abs(pi_) < 1e-6                         # flat 2D only: no tilt, no 3D pieces
    canvas = draw_scene(u)
    Hm = homography(cx, cy, z, 0.0, ro, sx, sy)
    Hi = np.linalg.inv(Hm)
    A = np.array([[RS, 0, cx * RS], [0, RS, cy * RS], [0, 0, 1.0]])
    M = A @ Hi
    M = M / M[2, 2]
    coeffs = (M[0, 0], M[0, 1], M[0, 2], M[1, 0], M[1, 1], M[1, 2], M[2, 0], M[2, 1])
    wp = canvas.transform((W, H), Image.PERSPECTIVE, coeffs, Image.BICUBIC)
    frame = Image.fromarray(background(), "RGB").convert("RGBA")
    frame.alpha_composite(wp)
    cam = cam_pack(cx, cy, z, 0.0, ro, sx, sy)
    screen_fx(frame, u, cam)
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
        print("warp check", [round(warp(T[p]) - T[p], 4) for p in (22, 25, 27)], "end", round(warp(DUR) - DUR, 3))
    else:
        encode_range(int(sys.argv[2]), int(sys.argv[3]), sys.argv[4])


