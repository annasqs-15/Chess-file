"""Vector decorations drawn onto the user's piece PNGs (512 px sprites, extended canvas N=870, piece at offset PAD).
Three acting animations: bazooka (queen), cowboy hat + flower (rook), crying (king).  Everything is drawn at 2x and downsampled."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage as ndi

N = 870
PAD = (N - 512) // 2
SS = 2
OUT = (46, 50, 58)
OUT_DK = (22, 22, 26)


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease_out(x, p=3.0):
    return 1 - (1 - clamp(x)) ** p


def ease_io(x):
    x = clamp(x)
    return x * x * x * (x * (6 * x - 15) + 10)


def over_s(x, w=2.2):
    """pop with overshoot 0..1 -> 0..1.x"""
    x = clamp(x)
    return 1 - math.exp(-6 * x) * math.cos(x * 8) if x < 1 else 1.0


class Layer:
    def __init__(self):
        self.im = Image.new("RGBA", (N * SS, N * SS), (0, 0, 0, 0))
        self.d = ImageDraw.Draw(self.im)

    def P(self, pts):
        return [((x + PAD) * SS, (y + PAD) * SS) for x, y in pts]

    def poly(self, pts, fill, outline=OUT, ow=6):
        pp = self.P(pts)
        self.d.polygon(pp, fill=fill)
        if outline and ow > 0:
            self.d.line(pp + [pp[0]], fill=outline, width=int(ow * SS), joint="curve")

    def ellipse(self, cx, cy, rx, ry, fill, outline=OUT, ow=6):
        a, b = (cx + PAD) * SS, (cy + PAD) * SS
        self.d.ellipse((a - rx * SS, b - ry * SS, a + rx * SS, b + ry * SS), fill=fill, outline=outline if ow > 0 else None, width=int(ow * SS))

    def line(self, pts, fill, w, joint="curve"):
        self.d.line(self.P(pts), fill=fill, width=int(w * SS), joint=joint)

    def gpoly(self, pts, c0, c1, ang=90, outline=OUT, ow=6, mid=None):
        """polygon filled with a linear gradient c0 -> (mid) -> c1 along angle (deg, 90 = top to bottom)"""
        pp = self.P(pts)
        xs = [p[0] for p in pp]
        ys = [p[1] for p in pp]
        x0, y0, x1, y1 = int(min(xs)) - 1, int(min(ys)) - 1, int(max(xs)) + 2, int(max(ys)) + 2
        w, h = x1 - x0, y1 - y0
        if w < 2 or h < 2:
            return
        m = Image.new("L", (w, h), 0)
        ImageDraw.Draw(m).polygon([(x - x0, y - y0) for x, y in pp], fill=255)
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        a = math.radians(ang)
        g = (xx - w / 2) * math.cos(a) + (yy - h / 2) * math.sin(a)
        g = (g - g.min()) / max(1e-3, g.max() - g.min())
        c0, c1 = np.array(c0, np.float32), np.array(c1, np.float32)
        if mid is not None:
            cm = np.array(mid, np.float32)
            col = np.where(g[..., None] < 0.5, c0 + (cm - c0) * (g[..., None] * 2), cm + (c1 - cm) * ((g[..., None] - 0.5) * 2))
        else:
            col = c0 + (c1 - c0) * g[..., None]
        arr = np.dstack([col, np.full((h, w), 255, np.float32)]).astype(np.uint8)
        tile = Image.fromarray(arr, "RGBA")
        tile.putalpha(m)
        self.im.alpha_composite(tile, (x0, y0))
        if outline and ow > 0:
            self.d.line(pp + [pp[0]], fill=outline, width=int(ow * SS), joint="curve")

    def out(self):
        return self.im.resize((N, N), Image.LANCZOS)


def rot_pts(pts, ang_deg, org=(0, 0), at=(0, 0)):
    a = math.radians(ang_deg)
    c, s = math.cos(a), math.sin(a)
    return [(at[0] + (x - org[0]) * c - (y - org[1]) * s, at[1] + (x - org[0]) * s + (y - org[1]) * c) for x, y in pts]


def rrect(x0, y0, x1, y1, r, n=7):
    pts = []
    for (cx, cy, a0) in ((x1 - r, y0 + r, -90), (x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90), (x0 + r, y0 + r, 180)):
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def mitt(L, c, r=30, col=(250, 250, 252), shade=(205, 206, 214), ang=0.0, thumb=True):
    """cartoon glove hand"""
    x, y = c
    L.ellipse(x, y, r, r * 0.92, col, OUT, 5)
    L.ellipse(x - r * 0.18, y + r * 0.22, r * 0.62, r * 0.5, shade, None, 0)
    L.ellipse(x - r * 0.25, y - r * 0.28, r * 0.42, r * 0.3, (255, 255, 255), None, 0)
    if thumb:
        a = math.radians(ang - 60)
        tx, ty = x + math.cos(a) * r * 0.9, y + math.sin(a) * r * 0.9
        L.ellipse(tx, ty, r * 0.42, r * 0.34, col, OUT, 4)


def arm(L, a, b, w=34, col=(250, 250, 252), shade=(205, 206, 214)):
    L.line([a, b], OUT, w + 10)
    L.line([a, b], col, w)
    L.line([(a[0] + 4, a[1] + 5), (b[0] + 4, b[1] + 5)], shade, w * 0.35)


def smoke(L, x, y, r, a, col=(210, 212, 220)):
    for k, (dx, dy, rr) in enumerate(((0, 0, 1.0), (-0.55, 0.35, 0.72), (0.5, 0.4, 0.68), (0.1, -0.5, 0.6))):
        L.ellipse(x + dx * r, y + dy * r, r * rr, r * rr, col + (int(a * (0.85 - 0.1 * k)),), None, 0)


# ------------------------------------------------------------------------------------------------ bazooka
def bazooka_tube(L, org, ang, scale=1.0, recoil=0.0, rocket=1.0, flash=0.0):
    """tube drawn in a local frame (x forward) rotated by ang about org; returns key points (muzzle, grip, support) in sprite coords"""
    def T(pts):
        return rot_pts([(x * scale - recoil, y * scale) for x, y in pts], ang, (0, 0), org)

    def Tp(p):
        return T([p])[0]
    # rear venturi
    L.gpoly(T([(-92, -30), (-150, -52), (-156, 52), (-92, 30)]), (118, 122, 132), (52, 56, 66), ang + 90, OUT, 6, mid=(84, 88, 98))
    L.poly(T([(-150, -40), (-156, -40), (-156, 40), (-150, 40)]), (40, 42, 50), OUT, 3)
    # warhead sitting in the muzzle (before launch)
    if rocket > 0.01:
        L.gpoly(T([(190, -22), (232, -24), (232, 24), (190, 22)]), (210, 214, 222), (120, 126, 138), ang + 90, OUT, 5)
        L.gpoly(T([(232, -24), (262, -14), (292, 0), (262, 14), (232, 24)]), (240, 96, 80), (170, 30, 32), ang + 90, OUT, 5)
        L.poly(T([(232, -24), (240, -24), (240, 24), (232, 24)]), (50, 54, 62), OUT, 3)
    # main tube
    L.gpoly(T(rrect(-92, -34, 212, 34, 14)), (146, 168, 96), (60, 78, 42), ang + 90, OUT, 7, mid=(100, 122, 64))
    # highlight streak and shade
    L.gpoly(T(rrect(-70, -24, 190, -14, 5)), (200, 222, 150), (176, 200, 126), ang + 90, None, 0)
    # bands
    for x0, w_ in ((18, 12), (126, 12)):
        L.gpoly(T([(x0, -34), (x0 + w_, -34), (x0 + w_, 34), (x0, 34)]), (70, 84, 48), (42, 54, 30), ang + 90, OUT, 3)
    L.gpoly(T([(158, -34), (176, -34), (176, 34), (158, 34)]), (255, 222, 84), (214, 170, 40), ang + 90, OUT, 3)
    # muzzle ring
    L.gpoly(T(rrect(206, -42, 244, 42, 8)), (136, 140, 150), (58, 62, 72), ang + 90, OUT, 6, mid=(96, 100, 110))
    # sight
    L.gpoly(T([(80, -34), (80, -56), (118, -56), (118, -34)]), (120, 124, 134), (62, 66, 76), ang + 90, OUT, 4)
    L.poly(T([(184, -34), (184, -52), (194, -52), (194, -34)]), (70, 74, 84), OUT, 4)
    # grip + guard
    L.gpoly(T([(18, 34), (62, 34), (52, 104), (10, 100)]), (84, 88, 98), (40, 42, 50), ang + 90, OUT, 5)
    L.line(T([(66, 36), (88, 62), (66, 70)]), OUT, 8)
    # stencil stripe dots
    for x_ in (50, 88):
        e = Tp((x_, -4))
        L.ellipse(e[0], e[1], 4, 4, (40, 52, 28), None, 0)
    if flash > 0.01:
        m = Tp((250 * scale / scale, 0))
        flash_burst(L, m, ang, flash)
    return Tp((250, 0)), Tp((36, 100)), Tp((140, 44))


def flash_burst(L, c, ang, k):
    """muzzle flash star: white core, yellow, orange"""
    for scale, col in ((1.0, (255, 150, 40, 235)), (0.72, (255, 214, 70, 245)), (0.42, (255, 250, 220, 255))):
        pts = []
        for i in range(16):
            a = math.radians(ang + i * 22.5 - 90 + 90)
            r = (150 if i % 2 == 0 else 62) * scale * k
            if i % 4 == 0:
                r *= 1.35
            pts.append((c[0] + math.cos(a) * r, c[1] + math.sin(a) * r))
        L.poly(pts, col, None, 0)


def queen_bazooka(base, t, aim=-100.5, lead=0.97):
    """t = seconds relative to the hit; the rocket launches at -0.10 s. returns padded sprite (N x N RGBA)."""
    L = Layer()
    spr = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    spr.alpha_composite(base, (PAD, PAD))
    # timeline
    appear = ease_out((t + lead) / 0.38, 2.2)                # t=-0.97 is video time 0
    sc = over_s((t + lead) / 0.42) if t < -0.55 else 1.0
    sc *= clamp((t + lead) / 0.06)
    vanish = clamp((t - 0.05) / 0.35)
    sc *= (1 - ease_io(vanish))
    if sc <= 0.01:
        return spr, None
    sway = 3.0 * math.sin(t * 9) * (1 - clamp((t + 0.35) / 0.3))
    ang = aim + sway + (-26 * (1 - ease_out((t + 0.72) / 0.45, 2.5)) if t < -0.27 else 0)
    launch = -0.10
    recoil = 0.0
    if t >= launch:
        d = t - launch
        recoil = 34 * math.exp(-d / 0.10) * (1 if d >= 0 else 0) - 6 * clamp(d / 0.4)
        ang += 5 * math.exp(-d / 0.12) * math.sin(d * 40)
    else:
        recoil = -10 * ease_io((t + 0.28) / 0.18) if t > -0.28 else 0      # tiny pull-in before the shot
    org = (256 + 118 * sc, 318)                                 # on the queen's shoulder
    flash = math.exp(-(t - launch) / 0.045) if t >= launch else 0.0
    rocket = 1.0 if t < launch else 0.0
    muz, grip, sup = bazooka_tube(L, org, ang, scale=sc * 1.2, recoil=recoil, rocket=rocket, flash=clamp(flash) * 1.0 if flash > 0.02 else 0)
    # hands + arms (drawn after tube so the mitts grip it)
    sh_a, sh_b = (250, 360), (330, 340)
    arm(L, sh_a, (grip[0] - 4, grip[1] - 6), 34)
    arm(L, sh_b, (sup[0], sup[1] + 4), 34)
    mitt(L, (grip[0], grip[1]), 38 * sc, ang=ang)
    mitt(L, (sup[0], sup[1] + 6), 36 * sc, ang=ang)
    # backblast smoke behind the tube
    if t >= launch:
        d = t - launch
        rear = rot_pts([(-170, 0)], ang, (0, 0), org)[0]
        a = clamp(1 - d / 0.7) * 0.85
        for k in range(5):
            dd = d * (240 + 70 * k)
            p = rot_pts([(-170 - dd * 0.7, (k - 2) * 26 * (1 + d * 3))], ang, (0, 0), org)[0]
            smoke(L, p[0], p[1], 28 + 60 * d + 8 * k, a * 255 * 0.7)
        # smoke wisp from the muzzle
        w_ = clamp(1 - d / 0.9) * 150 * (1 if d > 0.05 else 0)
        for k in range(3):
            p = rot_pts([(250 + 20 * k + d * 120, -d * 40 * (k + 1))], ang, (0, 0), org)[0]
            smoke(L, p[0], p[1], 16 + 40 * d + 6 * k, w_, (196, 198, 206))
    spr.alpha_composite(L.out())
    return spr, (muz, ang)


# ------------------------------------------------------------------------------------------------ cowboy hat + flower
def cowboy_hat(L, c, tilt=0.0, lift=0.0, scale=1.0):
    cx, cy = c[0], c[1] - lift
    def Tt(pts):
        return rot_pts([(x * scale, y * scale) for x, y in pts], tilt, (0, 0), (cx, cy))
    # brim: curved ends up
    top, bot = [], []
    for i in range(0, 25):
        u = -1 + i / 12.0
        x = u * 210
        y = 6 - 44 * abs(u) ** 2.3
        top.append((x, y))
    for i in range(24, -1, -1):
        u = -1 + i / 12.0
        x = u * 200
        y = 6 - 44 * abs(u) ** 2.3 + 26 - 6 * abs(u)
        bot.append((x, y))
    brim = top + bot
    L.gpoly(Tt(brim), (206, 144, 80), (136, 86, 44), 90, OUT, 7, mid=(176, 118, 64))
    # underside shadow lip along the front edge
    lip = [(x, y - 2) for (x, y) in bot[::2]]
    L.line(Tt(lip), (90, 56, 30), 5)
    # crown with a pinched dent
    crown = [(-110, 8), (-102, -60), (-84, -106), (-52, -128), (-18, -128), (0, -118), (18, -128), (52, -128), (84, -106), (102, -60), (110, 8)]
    L.gpoly(Tt(crown), (214, 150, 86), (140, 90, 48), 90, OUT, 7, mid=(182, 122, 66))
    # side creases
    L.line(Tt([(-64, -20), (-52, -92), (-40, -126)]), (126, 80, 42), 5)
    L.line(Tt([(64, -20), (52, -92), (40, -126)]), (126, 80, 42), 5)
    L.line(Tt([(0, -112), (0, -60)]), (150, 100, 56), 4)
    # soft highlight on the crown
    L.ellipse(*Tt([(-52, -86)])[0], 30 * scale, 14 * scale, (236, 182, 120, 110), None, 0)
    # hat band + buckle
    band = [(-103, -14), (103, -14), (101, -48), (-101, -48)]
    L.gpoly(Tt(band), (96, 58, 34), (58, 34, 20), 90, OUT, 5)
    for sx in (-1, 1):
        pass
    bk = Tt([(-22, -50), (26, -50), (26, -12), (-22, -12)])
    L.gpoly(bk, (255, 230, 120), (214, 166, 48), 90, OUT, 5)
    ib = Tt([(-10, -40), (14, -40), (14, -22), (-10, -22)])
    L.poly(ib, (86, 52, 28), (120, 80, 40), 3)


def flower(L, base, ang, sc=1.0, bloom=1.0):
    """stem from `base` growing along ang (deg, -90 = up); returns the bloom centre"""
    a = math.radians(ang)
    ln = 190 * sc
    bend = 0.18
    pts = []
    for i in range(0, 13):
        u = i / 12
        pts.append((base[0] + math.cos(a) * ln * u + math.cos(a + math.pi / 2) * ln * bend * math.sin(u * math.pi) * 0.5,
                    base[1] + math.sin(a) * ln * u + math.sin(a + math.pi / 2) * ln * bend * math.sin(u * math.pi) * 0.5))
    L.line(pts, (30, 82, 42), 15 * sc)
    L.line(pts, (70, 168, 78), 9 * sc)
    # leaves
    for u, side in ((0.35, 1), (0.55, -1)):
        p = pts[int(u * 12)]
        la = a + side * math.radians(60)
        lf = [(p[0], p[1]), (p[0] + math.cos(la - 0.45) * 58 * sc, p[1] + math.sin(la - 0.45) * 58 * sc),
              (p[0] + math.cos(la) * 86 * sc, p[1] + math.sin(la) * 86 * sc), (p[0] + math.cos(la + 0.45) * 58 * sc, p[1] + math.sin(la + 0.45) * 58 * sc)]
        L.gpoly(lf, (110, 200, 100), (46, 130, 62), 90, (30, 82, 42), 4)
    c = pts[-1]
    # petals
    r = 34 * sc * bloom
    for i in range(7):
        pa = math.radians(i * 360 / 7 + ang)
        px_, py_ = c[0] + math.cos(pa) * r * 0.95, c[1] + math.sin(pa) * r * 0.95
        L.ellipse(px_, py_, r * 0.78, r * 0.7, (255, 132, 172), (176, 40, 92), 4)
        L.ellipse(px_ - r * 0.1, py_ - r * 0.12, r * 0.4, r * 0.3, (255, 190, 214), None, 0)
    L.ellipse(c[0], c[1], r * 0.62, r * 0.62, (255, 210, 70), (214, 130, 26), 4)
    L.ellipse(c[0] - r * 0.12, c[1] - r * 0.12, r * 0.26, r * 0.22, (255, 240, 170), None, 0)
    for i in range(5):
        pa = math.radians(i * 72 + 18)
        L.ellipse(c[0] + math.cos(pa) * r * 0.32, c[1] + math.sin(pa) * r * 0.32, r * 0.07, r * 0.07, (190, 110, 20), None, 0)
    return c


def rook_cowboy(base, t, mode="walk", tip=0.0, sway=0.0, hat_off=None, petals=0.0, appear=1.0, hat=True):
    """mode 'walk': hat on, flower in the hand; tip 0..1 = hat tipped; hat_off = (dx, dy, rot) detached hat; petals 0..1 = scatter. sway = phase."""
    L = Layer()
    spr = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    spr.alpha_composite(base, (PAD, PAD))
    # arm + hand on the right side of the body holding the flower
    sh = (352, 330)
    hand = (440 + 10 * math.sin(sway * 1.2), 292 + 6 * math.cos(sway))
    if tip > 0.01:
        hand = (lerp(hand[0], 470, tip), lerp(hand[1], 240, tip))
    arm(L, sh, hand, 34)
    fl_ang = -88 + 14 * math.sin(sway) - 10 * tip
    c = flower(L, (hand[0], hand[1] - 6), fl_ang, 0.95 * clamp(appear * 2 - 0.3), 1.0 - 0.6 * petals)
    mitt(L, hand, 37)
    # second arm tips the hat when tip>0
    if tip > 0.01:
        h2 = (lerp(160, 118, tip), lerp(300, 118, tip))
        arm(L, (160, 330), h2, 32)
        mitt(L, h2, 35, ang=180)
    if hat and hat_off is None:
        hcx = 256
        hcy = 96 + 8
        lift = 34 * tip + (-300 * (1 - ease_out(appear * 1.3, 3.0)) + 0)
        lift = 34 * tip + (300 * (math.exp(-7 * clamp(appear)) * math.cos(clamp(appear) * 9)) if appear < 1 else 0)
        cowboy_hat(L, (hcx + 2 * math.sin(sway * 0.8), hcy), tilt=-14 * tip + 2 * math.sin(sway), lift=lift)
    spr.alpha_composite(L.out())
    return spr


def lerp(a, b, k):
    return a + (b - a) * k


def hat_alone(ang, scale=1.0):
    L = Layer()
    cowboy_hat(L, (256, 256), tilt=ang, scale=scale)
    return L.out()


# ------------------------------------------------------------------------------------------------ crying king
_HOLES = {}


def king_holes(base):
    if "m" not in _HOLES:
        a = np.asarray(base)[..., 3]
        lab, n = ndi.label(a < 20)
        ms = []
        for i in range(1, n + 1):
            ys, xs = np.nonzero(lab == i)
            if 200 < len(xs) < 30000:
                ms.append((lab == i, (xs.min(), ys.min(), xs.max(), ys.max())))
        ms.sort(key=lambda m: m[1][0])
        _HOLES["m"] = ms
    return _HOLES["m"]


def teardrop(L, x, y, r, a=235):
    pts = [(x, y - r * 1.9)]
    for i in range(0, 17):
        t = math.pi * (0.15 + 0.7 * i / 16)
        pts.append((x + math.cos(t - math.pi / 2 + math.pi / 2 * 0) * r * 0.0, y))
    # drawn as a circle + pointed top
    L.poly([(x, y - r * 1.9), (x - r * 0.92, y - r * 0.35), (x + r * 0.92, y - r * 0.35)], (140, 208, 255, a), None, 0)
    L.ellipse(x, y, r, r, (140, 208, 255, a), (60, 140, 220, a), 3)
    L.ellipse(x - r * 0.3, y - r * 0.25, r * 0.28, r * 0.4, (240, 250, 255, a), None, 0)


def king_cry(base, t, k_in=1.0, puddle=False):
    """t = seconds since the crying starts; k_in 0..1 intensity (fade). Sprite with sad eyes, brows, tear streams, droplets, puddle."""
    L = Layer()
    spr = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    # puddle on the board under the king (behind the piece)
    pw = ease_out(t / 1.6, 2.0) * 330 * k_in
    if puddle and pw > 4:
        L.ellipse(256, 476, pw / 2, pw / 7.5, (70, 150, 235, 120), (150, 214, 255, 190), 3)
        L.ellipse(256 - pw * 0.1, 474, pw / 3.4, pw / 15, (180, 226, 255, 150), None, 0)
        for r_ in (0.28, 0.46):
            ph = (t * 1.3 + r_) % 1.0
            L.ellipse(256 + 40 * math.sin(r_ * 20), 476, pw * r_ * ph * 0.55, pw * r_ * ph * 0.09, (0, 0, 0, 0), (190, 232, 255, int(160 * (1 - ph))), 2)
    spr.alpha_composite(L.out())
    spr.alpha_composite(base, (PAD, PAD))
    L = Layer()
    holes = king_holes(base)
    # eyes in the heart-shaped holes: white sclera clipped to the hole, wet lower half
    eyes = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    ea = ImageDraw.Draw(eyes)
    for hm, (x0, y0, x1, y1) in holes:
        m = Image.fromarray((hm * 255).astype(np.uint8), "L")
        full = Image.new("RGBA", (512, 512), (250, 252, 255, 255))
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        d = ImageDraw.Draw(full)
        # tear water pooling in the lower part of the eye
        lvl = y1 - (y1 - y0) * (0.30 + 0.12 * math.sin(t * 7))
        d.rectangle((x0, lvl, x1, y1 + 4), fill=(150, 212, 255, 255))
        d.line((x0, lvl, x1, lvl), fill=(220, 244, 255, 255), width=3)
        # pupil looking down-inward
        side = -1 if cx < 256 else 1
        px_, py_ = cx - side * 4, cy + 12
        d.ellipse((px_ - 20, py_ - 21, px_ + 20, py_ + 21), fill=(26, 34, 58, 255))
        d.ellipse((px_ - 11, py_ - 15, px_ - 1, py_ - 4), fill=(255, 255, 255, 255))
        d.ellipse((px_ + 5, py_ + 2, px_ + 12, py_ + 9), fill=(190, 220, 255, 255))
        tile = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        tile.paste(full, (0, 0), m)
        eyes.alpha_composite(tile, (PAD, PAD))
        # lash/upper lid: dark line on the top edge of the hole
    spr.alpha_composite(eyes)
    for hm, (x0, y0, x1, y1) in holes:
        cx = (x0 + x1) / 2
        side = -1 if cx < 256 else 1
        # sad brow: inner end raised
        o = (cx + side * 48, y0 - 6)
        i_ = (cx - side * 40, y0 - 46 - 4 * math.sin(t * 6))
        L.line([o, ((o[0] + i_[0]) / 2, (o[1] + i_[1]) / 2 - 4), i_], OUT_DK, 22)
        L.line([o, ((o[0] + i_[0]) / 2, (o[1] + i_[1]) / 2 - 4), i_], (214, 216, 224), 11)
    # tear streams running down the body from the lower tip of each eye + fountain droplets
    for hm, (x0, y0, x1, y1) in holes:
        cx = (x0 + x1) / 2
        side = -1 if cx < 256 else 1
        sx = cx + side * 8
        ln = (y1 + 6) + (400 - y1) * ease_out(t / 0.7, 2.0)
        for w_, col in ((20, (80, 160, 236, 235)), (13, (146, 210, 255, 245)), (4, (240, 250, 255, 255))):
            xoff = {20: 0, 13: 0, 4: -3}[w_]
            L.line([(sx + xoff, y1 + 2), (sx + side * 4 + xoff, (y1 + ln) / 2), (sx + side * 8 + xoff, ln)], col, w_)
        # droplets thrown out sideways, parabolic
        for j in range(6):
            ph = ((t * 1.6 + j / 6.0 + (0.08 if side > 0 else 0)) % 1.0)
            vx = side * (130 + 24 * j)
            x = cx + side * 20 + vx * ph
            y = y1 - 10 + (-150 * ph + 420 * ph * ph) * (1 + 0.08 * j)
            teardrop(L, x, y, 10 + (j % 3) * 2, int(240 * clamp(1 - ph * 0.6) * k_in))
    spr.alpha_composite(L.out())
    return spr
