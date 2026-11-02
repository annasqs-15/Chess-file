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
