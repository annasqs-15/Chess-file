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
