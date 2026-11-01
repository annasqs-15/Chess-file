FXHELP = '''def beam(dv, canvas, a_sq, b_sq, wd, col, a, glow_w=0, prog=1.0):
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
'''

UNDER = '''def king_sq_at(u):
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
'''

OVER = '''def over_fx(u, df, canvas):
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
'''

LIGHT = '''def light_events():
    return [
        (T[29] - 0.45, 0.20, 0.55, 0.50, 0.45, ("h5", "h6"), 300, 1.0, AMB),
        (T[31] - 0.10, 0.12, 0.40, 0.50, 0.30, ("e3", "h6"), 380, 0.8, CYN),
        (T[36] - 0.10, 0.20, 0.50, 0.45, 0.40, ("g6", "h6"), 240, 0.7, (120, 150, 255)),
        (T[37] - 0.55, 0.30, 0.95, 0.50, 0.42, ("f4", "f6"), 300, 1.0, (255, 200, 90)),
        (T[41] - 0.30, 0.30, 1.20, 0.80, 0.62, ("f4", "g6"), 280, 1.2, RED),
    ]
'''

GRADE = '''GRADE = [(0.0, (1, 1, 1)), (0.4, (0.92, 1.0, 1.08)), (T[29] + 0.05, (1.14, 1.0, 0.86)), (T[31] - 0.3, (0.90, 1.0, 1.10)),
         (T[35], (0.95, 0.98, 1.06)), (T[36] + 0.3, (1.10, 1.02, 0.90)), (T[37] + 0.3, (0.90, 1.06, 1.08)), (T[39] - 0.1, (0.88, 0.95, 1.12)),
         (T[41] - 0.3, (1.0, 0.97, 1.05)), (T[41] + 0.1, (1.14, 0.90, 0.90)), (REW0, (1.10, 0.92, 0.92)), (REW1, (1, 1, 1)), (DUR + 1, (1, 1, 1))]
'''

SCENE = '''def draw_scene(u):
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
'''

RENDER = '''def render(fi):
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
'''
