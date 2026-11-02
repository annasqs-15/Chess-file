"""Second set of vector acting: golden greedy queen, sunglasses king, shocked king, screen-space cartoon hand, angel wings + halo, coins."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import decor as DC
from decor import Layer, N, PAD, clamp, ease_out, ease_io, king_holes

W, H = 1080, 1920
OUT = (24, 26, 36, 255)


def golden(im, k, grey=0.0):
    """colourise a piece: k = gold amount, grey = desaturated cracked-stone look"""
    a = np.asarray(im).astype(np.float32)
    rgb = a[..., :3]
    lum = (0.30 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]) / 255.0
    if k > 0.001:
        g = np.clip(lum * 1.35 + 0.28, 0, 1.2)[..., None] * np.array([255, 190, 62], np.float32)
        g = g + np.clip(lum - 0.85, 0, 1)[..., None] * 600
        rgb = rgb * (1 - k) + np.clip(g, 0, 255) * k
    if grey > 0.001:
        gg = (np.clip(lum * 0.9 + 0.12, 0, 1)[..., None] * np.array([150, 154, 164], np.float32))
        rgb = rgb * (1 - grey) + gg * grey
    out = a.copy()
    out[..., :3] = np.clip(rgb, 0, 255)
    return Image.fromarray(out.astype(np.uint8), "RGBA")


def _canvas(base):
    spr = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    spr.alpha_composite(base, (PAD, PAD))
    return spr


def king_shades(base, drop=1.0):
    """sunglasses sliding down from above onto the king's face (drop 0..1, overshoot)"""
    spr = _canvas(base)
    e = DC.over_s(drop)
    dy = -(1 - e) * 300
    L = Layer()
    holes = king_holes(base)
    cs = []
    for hm, (x0, y0, x1, y1) in holes:
        cs.append(((x0 + x1) / 2, (y0 + y1) / 2))
        lens = DC.rrect(x0 - 16, y0 - 12 + dy, x1 + 16, y1 + 20 + dy, 26)
        L.gpoly(lens, (46, 52, 74), (8, 9, 14), 90, OUT, 8)
        L.poly([(x0 + 4, y0 - 2 + dy), (x0 + 30, y0 - 2 + dy), (x0 + 10, y1 + 8 + dy), (x0 - 16, y1 + 8 + dy)], (180, 200, 235, 150), None, 0)
    if len(cs) == 2:
        yb = cs[0][1] - 12 + dy
        L.line([(cs[0][0] + 60, yb), ((cs[0][0] + cs[1][0]) / 2, yb - 8), (cs[1][0] - 60, yb)], OUT, 14)
        L.line([(cs[0][0] - 64, yb + 6), (cs[0][0] - 96, yb + 18)], OUT, 12)
        L.line([(cs[1][0] + 64, yb + 6), (cs[1][0] + 96, yb + 18)], OUT, 12)
    spr.alpha_composite(L.out())
    return spr


def king_shock(base, t, k=1.0):
    """wide shocked eyes: big white sclera, tiny shaking pupils, brows shot up"""
    spr = _canvas(base)
    holes = king_holes(base)
    eyes = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    for hm, (x0, y0, x1, y1) in holes:
        m = Image.fromarray((hm * 255).astype(np.uint8), "L")
        full = Image.new("RGBA", (512, 512), (252, 252, 255, 255))
        d = ImageDraw.Draw(full)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        jx, jy = 3.5 * math.sin(t * 70 + cx), 3.0 * math.cos(t * 63 + cx)
        d.ellipse((cx - 8 + jx, cy - 6 + jy, cx + 8 + jx, cy + 10 + jy), fill=(20, 24, 40, 255))
        d.ellipse((cx - 4 + jx, cy - 3 + jy, cx + 1 + jx, cy + 3 + jy), fill=(255, 255, 255, 255))
        tile = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        tile.paste(full, (0, 0), m)
        eyes.alpha_composite(tile, (PAD, PAD))
    spr.alpha_composite(eyes)
    L = Layer()
    for hm, (x0, y0, x1, y1) in holes:
        cx = (x0 + x1) / 2
        side = -1 if cx < 256 else 1
        o = (cx + side * 44, y0 - 22)
        i_ = (cx - side * 36, y0 - 52 - 3 * math.sin(t * 40))
        mid = ((o[0] + i_[0]) / 2, min(o[1], i_[1]) - 14)
        L.line([o, mid, i_], (18, 20, 30, 255), 20)
        L.line([o, mid, i_], (210, 212, 222, 255), 10)
    spr.alpha_composite(L.out())
    return spr


def blend_k(base, deco, k):
    """cross-fade from the plain sprite (k=0) to a decorated sprite (k=1)"""
    if k >= 0.999:
        return deco
    b = _canvas(base)
    return Image.blend(b, deco, clamp(k))


# ------------------------------------------------------------------ screen-space overlay (hand, strings, wings)
class Ov:
    def __init__(self, ss=2):
        self.ss = ss
        self.im = Image.new("RGBA", (W * ss, H * ss), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def _p(self, pts):
        return [(x * self.ss, y * self.ss) for x, y in pts]

    def poly(self, pts, fill, outline=None, ow=0):
        pp = self._p(pts)
        self.d.polygon(pp, fill=fill)
        if outline and ow > 0:
            self.d.line(pp + [pp[0]], fill=outline, width=max(1, int(ow * self.ss)), joint="curve")

    def line(self, pts, fill, w, caps=True):
        pp = self._p(pts)
        self.d.line(pp, fill=fill, width=max(1, int(w * self.ss)), joint="curve")
        if caps:
            r = w * self.ss / 2
            for (x, y) in (pp[0], pp[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=fill)

    def ellipse(self, c, rx, ry, fill, outline=None, ow=0):
        x, y = c[0] * self.ss, c[1] * self.ss
        self.d.ellipse((x - rx * self.ss, y - ry * self.ss, x + rx * self.ss, y + ry * self.ss), fill=fill,
                       outline=outline if (outline and ow > 0) else None, width=max(1, int(ow * self.ss)))

    def blit(self, frame):
        small = self.im.resize((W, H), Image.LANCZOS)
        frame.alpha_composite(small)


SKIN = (255, 213, 172, 255)
SKIN_SH = (232, 172, 130, 255)
HOUT = (78, 48, 38, 255)


def hand(ov, tip, s, ang, grip, wob=0.0):
    """cartoon hand pinching at screen point `tip`; its body is out of frame (the forearm leaves through the top edge).
    s = pixels per local unit, ang = degrees the arm leans (clockwise), grip 0 open .. 1 pinched"""
    a = math.radians(ang + wob)
    ca, sa = math.cos(a), math.sin(a)

    def m(p):
        return (tip[0] + (p[0] * ca - p[1] * sa) * s, tip[1] + (p[0] * sa + p[1] * ca) * s)

    def M(ps):
        return [m(p) for p in ps]
    # soft shadow of the hand on the board
    ov.ellipse(m((8, 10)), 70 * s, 34 * s, (0, 0, 0, 55))
    # sleeve (dark jacket) running out of the frame
    p0, p1 = m((0, -330)), m((0, -2600))
    dv = (p1[0] - p0[0], p1[1] - p0[1])
    L_ = math.hypot(*dv)
    nrm = (-dv[1] / L_, dv[0] / L_)
    w0, w1 = 58 * s, 58 * s + 2600 * s * 0.012
    ov.poly([(p0[0] + nrm[0] * w0, p0[1] + nrm[1] * w0), (p1[0] + nrm[0] * w1, p1[1] + nrm[1] * w1),
             (p1[0] - nrm[0] * w1, p1[1] - nrm[1] * w1), (p0[0] - nrm[0] * w0, p0[1] - nrm[1] * w0)], (34, 40, 72, 255), HOUT, 5 * s)
    ov.line([(p0[0] - nrm[0] * w0 * 0.45, p0[1] - nrm[1] * w0 * 0.45), (p1[0] - nrm[0] * w1 * 0.45, p1[1] - nrm[1] * w1 * 0.45)], (62, 72, 118, 255), 9 * s, caps=False)
    ov.poly(M([(-56, -340), (56, -340), (62, -200), (-62, -200)]), (34, 40, 72, 255), HOUT, 5 * s)
    ov.line(M([(-30, -330), (-34, -206)]), (62, 72, 118, 255), 9 * s, caps=False)
    # shirt cuff
    ov.poly(M(DC.rrect(-66, -212, 66, -164, 14)), (248, 248, 252, 255), HOUT, 5 * s)
    ov.poly(M([(-60, -178), (60, -178), (60, -168), (-60, -168)]), (214, 218, 230, 255), None, 0)
    # curled fingers on the right (knuckles), palm, thumb, index
    for (cx, cy) in ((52, -74), (60, -104), (56, -134)):
        ov.ellipse(m((cx, cy)), 27 * s, 23 * s, SKIN, HOUT, 5 * s)
        ov.line(M([(cx - 22, cy), (cx - 6, cy + 2)]), SKIN_SH, 4 * s, caps=False)
    ov.poly(M(DC.rrect(-62, -172, 62, -58, 40)), SKIN, HOUT, 5 * s)
    ov.ellipse(m((10, -76)), 44 * s, 24 * s, SKIN_SH)
    th_tip = (-62 + 52 * grip, 8 - 16 * grip)
    ix_tip = (34 - 26 * grip, 22 - 24 * grip)
    for base_, tp, wd in (((-50, -102), th_tip, 40), (((14, -112)), ix_tip, 37)):
        ov.line(M([base_, tp]), HOUT, (wd + 10) * s)
        ov.line(M([base_, tp]), SKIN, wd * s)
        ov.line(M([(base_[0] + 6, base_[1] + 4), (tp[0] + 5, tp[1] - 8)]), SKIN_SH, wd * 0.22 * s, caps=False)
        ov.ellipse(m((tp[0], tp[1] - 4)), wd * 0.42 * s, wd * 0.30 * s, (255, 236, 222, 255))
    ov.ellipse(m((-12 + 0 * grip, -140)), 14 * s, 9 * s, (255, 255, 255, 120))


def feather(ov, c, ang, ln, wd, s, col=(250, 252, 255, 255), sh=(196, 220, 250, 255)):
    a = math.radians(ang)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    n = 9
    for i in range(n + 1):
        t = i / n
        w_ = wd * math.sin(math.pi * (0.1 + 0.9 * t) ** 0.8) * (1 - 0.25 * t)
        pts.append((t * ln, w_ / 2))
    pts += [(t_, -w_) for (t_, w_) in reversed(pts)]
    out = [(c[0] + (x * ca - y * sa) * s, c[1] + (x * sa + y * ca) * s) for x, y in pts]
    ov.poly(out, col, (92, 124, 170, 255), 3.5 * s)
    half = [(c[0] + (x * ca - abs(y) * 0.1 * sa + 0 * sa) * s, c[1] + (x * sa + abs(y) * 0.9 * ca) * s) for x, y in pts[:n + 1]]
    ov.poly(out[:n + 1] + [(c[0] + (ln * 0.1) * ca * s, c[1] + (ln * 0.1) * sa * s)], sh, None, 0)


def wings(ov, c, s, flap=0.0, back=0.0, a=1.0):
    """angel wings behind a piece at screen point c (shoulder height); flap in deg, back 0..1 sweeps them back/down"""
    for side in (-1, 1):
        for i in range(7):
            t = i / 6.0
            deg = -62 + 100 * t + flap * (1 - 0.4 * t) + back * 45
            ln = 260 - 110 * t
            wd = 60 - 12 * t
            ang_ = deg if side > 0 else 180 - deg
            feather(ov, (c[0] + side * 18 * s, c[1]), ang_, ln, wd, s)


def lerp_(a, b, k):
    return a + (b - a) * k


def halo(ov, c, s, a=1.0, flick=1.0):
    r = 56 * s
    for rr, al in ((1.5, 40), (1.25, 70)):
        ov.ellipse(c, r * rr, r * rr * 0.42, (255, 220, 110, int(al * a * flick)))
    ov.ellipse(c, r, r * 0.4, (0, 0, 0, 0), (255, 214, 84, int(255 * a * flick)), 9 * s)
    ov.ellipse(c, r, r * 0.4, (0, 0, 0, 0), (255, 246, 190, int(255 * a * flick)), 3.5 * s)


def coin(df, p, r, spin, a, RSs=1.0):
    """gold coin on an RGBA ImageDraw `df` at pixel p (already scaled), r px, spin angle radians"""
    rx = max(2.0, abs(math.cos(spin)) * r)
    col = (255, 204, 60, int(255 * a))
    df.ellipse((p[0] - rx, p[1] - r, p[0] + rx, p[1] + r), fill=col, outline=(150, 96, 20, int(255 * a)), width=max(2, int(r * 0.16)))
    df.ellipse((p[0] - rx * 0.62, p[1] - r * 0.62, p[0] + rx * 0.62, p[1] + r * 0.62), outline=(255, 238, 150, int(230 * a)), width=max(1, int(r * 0.12)))
    if rx > r * 0.4:
        df.line((p[0] - rx * 0.3, p[1] - r * 0.15, p[0] + rx * 0.1, p[1] - r * 0.5), fill=(255, 252, 225, int(230 * a)), width=max(1, int(r * 0.14)))
