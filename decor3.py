"""Horror set (2D only): blood-stained queen, red-eyed king, ashen cracked king, burn-to-ash dissolve, skull, ghost fire, tendrils."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import decor as DC
from decor import N, PAD, clamp, ease_out, ease_io, king_holes
import decor2 as D2

_NZ = {}


def _noise(seed, size=512):
    if seed not in _NZ:
        rs = np.random.RandomState(seed)
        a = rs.rand(64, 64).astype(np.float32)
        a = np.asarray(Image.fromarray((a * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC), np.float32) / 255.0
        b = np.asarray(Image.fromarray((rs.rand(16, 16) * 255).astype(np.uint8)).resize((size, size), Image.BICUBIC), np.float32) / 255.0
        _NZ[seed] = 0.55 * a + 0.45 * b
    return _NZ[seed]


def _cracks(seed, n, length=(40, 110), c0=(256, 220)):
    rs = np.random.RandomState(seed)
    out = []
    for i in range(n):
        ang = rs.uniform(0, 2 * math.pi)
        x, y = c0[0] + rs.uniform(-60, 60), c0[1] + rs.uniform(-90, 90)
        pts = [(x, y)]
        for j in range(5):
            ang += rs.uniform(-0.7, 0.7)
            ln = rs.uniform(*length) / 3
            x += math.cos(ang) * ln
            y += math.sin(ang) * ln
            pts.append((x, y))
        out.append(pts)
    return out


def bloody(im, k, grey=0.0):
    """blood-fed queen: red tint + dark-red stains (k), then corpse-pale and cracked (grey)"""
    a = np.asarray(im).astype(np.float32)
    rgb = a[..., :3]
    alpha = a[..., 3]
    lum = (0.30 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]) / 255.0
    if k > 0.001:
        g = np.clip(lum * 1.25 + 0.10, 0, 1.2)[..., None] * np.array([205, 22, 30], np.float32)
        g = g + np.clip(lum - 0.85, 0, 1)[..., None] * 380
        rgb = rgb * (1 - k) + np.clip(g, 0, 255) * k
    if grey > 0.001:
        gg = np.clip(lum * 0.8 + 0.30, 0, 1)[..., None] * np.array([214, 208, 190], np.float32)
        rgb = rgb * (1 - grey) + gg * grey
    out = a.copy()
    out[..., :3] = np.clip(rgb, 0, 255)
    res = Image.fromarray(out.astype(np.uint8), "RGBA")
    ov = Image.new("RGBA", res.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    rs = np.random.RandomState(7)
    nb = int(10 * k)
    for i in range(nb):
        x, y = rs.uniform(150, 360), rs.uniform(120, 420)
        r = rs.uniform(12, 36)
        d.ellipse((x - r, y - r * 0.8, x + r, y + r * 0.8), fill=(96, 0, 8, 235))
        d.ellipse((x - r * 0.4, y - r * 0.5, x - r * 0.1, y - r * 0.2), fill=(230, 40, 44, 200))
        d.line([(x, y), (x + rs.uniform(-6, 6), y + rs.uniform(30, 70))], fill=(96, 0, 8, 235), width=int(r * 0.35) + 3)
    if grey > 0.05:
        for pts in _cracks(5, int(2 + 6 * grey)):
            d.line(pts, fill=(20, 12, 14, 255), width=6, joint="curve")
    m = Image.fromarray((alpha > 120).astype(np.uint8) * 255, "L")
    res.alpha_composite(Image.composite(ov, Image.new("RGBA", res.size, (0, 0, 0, 0)), m))
    return res


def king_redeyes(base, k, t=0.0):
    """white king: eyes light up blood-red with slit pupils and a glow"""
    spr = D2._canvas(base)
    holes = king_holes(base)
    eyes = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    glow = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for hm, (x0, y0, x1, y1) in holes:
        m = Image.fromarray((hm * 255).astype(np.uint8), "L")
        full = Image.new("RGBA", (512, 512), (255, int(40 + 30 * k), 30, 255))
        d = ImageDraw.Draw(full)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        d.ellipse((cx - 5, cy - 11, cx + 5, cy + 11), fill=(20, 0, 0, 255))
        tile = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        tile.paste(full, (0, 0), m)
        eyes.alpha_composite(tile, (PAD, PAD))
        gx, gy = cx + PAD, cy + PAD
        gd.ellipse((gx - 46, gy - 40, gx + 46, gy + 40), fill=(255, 30, 20, int(150 * k)))
    glow = glow.filter(ImageFilter.GaussianBlur(20))
    spr.alpha_composite(glow)
    eyes.putalpha(eyes.getchannel("A").point(lambda v: int(v * clamp(k * 1.4))))
    spr.alpha_composite(eyes)
    return spr


def king_ashen(base, t, k=1.0):
    """black king: drained to bone-white, hollow sockets, cracks spreading"""
    spr = D2._canvas(base)
    a = np.asarray(spr).astype(np.float32)
    rgb = a[..., :3]
    lum = (0.30 * rgb[..., 0] + 0.59 * rgb[..., 1] + 0.11 * rgb[..., 2]) / 255.0
    pale = np.clip(lum * 0.7 + 0.42, 0, 1)[..., None] * np.array([232, 226, 206], np.float32)
    mix = clamp(t / 0.5)
    out = a.copy()
    out[..., :3] = rgb * (1 - mix) + pale * mix
    spr = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA")
    holes = king_holes(base)
    sock = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    for hm, (x0, y0, x1, y1) in holes:
        m = Image.fromarray((hm * 255).astype(np.uint8), "L")
        full = Image.new("RGBA", (512, 512), (4, 2, 4, 255))
        d = ImageDraw.Draw(full)
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        jx, jy = 2.5 * math.sin(t * 60 + cx), 2.0 * math.cos(t * 51 + cx)
        d.ellipse((cx - 3 + jx, cy - 2 + jy, cx + 3 + jx, cy + 4 + jy), fill=(245, 245, 235, 255))
        tile = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
        tile.paste(full, (0, 0), m)
        sock.alpha_composite(tile, (PAD, PAD))
    spr.alpha_composite(sock)
    cr = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    d = ImageDraw.Draw(cr)
    prog = clamp((t - 0.15) / 0.9)
    for pts in _cracks(9, 7, (60, 160), (256, 250)):
        n = max(2, int(len(pts) * prog) + 1)
        d.line([(x + PAD, y + PAD) for x, y in pts[:n]], fill=(30, 10, 12, 255), width=7, joint="curve")
    alpha = spr.getchannel("A").point(lambda v: 255 if v > 120 else 0)
    spr.alpha_composite(Image.composite(cr, Image.new("RGBA", (N, N), (0, 0, 0, 0)), alpha))
    return spr


def dissolve(base, k, seed=3):
    """burn to ash: noise-threshold dissolve with glowing embers on the edge (k 0..1)"""
    nz = _noise(seed, base.width)
    a = np.asarray(base).astype(np.float32)
    thr = k * 1.15 - 0.08
    edge = np.clip((nz - thr) / 0.06, 0, 1)            # 0 = gone, 1 = intact
    ember = np.clip(1 - np.abs(nz - thr - 0.03) / 0.045, 0, 1) * (a[..., 3] > 10) * (k > 0.02)
    out = a.copy()
    out[..., 3] = a[..., 3] * (nz > thr)
    char = clamp(k * 1.4)
    out[..., :3] = a[..., :3] * (1 - 0.65 * char * (1 - ember[..., None]))
    em = np.array([255, 120, 20], np.float32)
    out[..., :3] = out[..., :3] * (1 - ember[..., None]) + em * ember[..., None]
    out[..., 3] = np.maximum(out[..., 3], ember * 255 * (nz > thr - 0.05))
    return D2._canvas(Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), "RGBA"))


# ------------------------------------------------------------ screen-space / canvas shapes
def skull(d, c, s, a, jaw=0.0, col=(232, 224, 200), ol=(24, 12, 14)):
    """flat cartoon skull; d = ImageDraw on RGBA canvas pixels, c = centre px, s = px per unit"""
    al = int(255 * clamp(a))
    x, y = c
    fc = col + (al,)
    oc = ol + (al,)
    d.ellipse((x - 30 * s, y - 36 * s, x + 30 * s, y + 20 * s), fill=fc, outline=oc, width=max(2, int(4 * s)))
    jy = jaw * 8 * s
    d.rounded_rectangle((x - 19 * s, y + 10 * s + jy, x + 19 * s, y + 38 * s + jy), radius=int(6 * s), fill=fc, outline=oc, width=max(2, int(4 * s)))
    for i in range(-2, 3):
        xx = x + i * 7.2 * s
        d.line([(xx, y + 22 * s + jy), (xx, y + 37 * s + jy)], fill=oc, width=max(1, int(2.4 * s)))
    for sd in (-1, 1):
        d.ellipse((x + sd * 14 * s - 9 * s, y - 14 * s, x + sd * 14 * s + 9 * s, y + 6 * s), fill=oc)
        d.ellipse((x + sd * 14 * s - 2.5 * s, y - 6 * s, x + sd * 14 * s + 2.5 * s, y - 1 * s), fill=(255, 40, 30, al))
    d.polygon([(x, y + 4 * s), (x - 5 * s, y + 14 * s), (x + 5 * s, y + 14 * s)], fill=oc)


def flame(ov, c, s, t, a, seed):
    """pale ghost-fire tongue rising from c (screen px)"""
    rs = np.random.RandomState(seed)
    h = (46 + rs.uniform(0, 30)) * s * (0.8 + 0.25 * math.sin(t * 14 + seed))
    w = (13 + rs.uniform(0, 6)) * s
    sw = math.sin(t * 9 + seed * 1.7) * 9 * s
    for sc, col in ((1.0, (90, 230, 190)), (0.62, (200, 255, 240)), (0.3, (255, 255, 255))):
        pts = [(c[0] - w * sc, c[1]), (c[0] - w * 0.5 * sc + sw * 0.4, c[1] - h * 0.5 * sc),
               (c[0] + sw * sc, c[1] - h * sc), (c[0] + w * 0.5 * sc + sw * 0.4, c[1] - h * 0.5 * sc), (c[0] + w * sc, c[1])]
        ov.poly(pts, col + (int(215 * a),))
