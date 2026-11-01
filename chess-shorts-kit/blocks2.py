SLOWSTOPS = '''SLOW = [(T[29], 0.28, 0.30, 0.45), (T[37], 0.22, 0.30, 0.40), (T[41], 0.45, 0.20, 0.60)]   # (hit, dip length, dip speed, run-up)
STOPS = [(T[29], 0.06), (T[37], 0.10), (T[41], 0.06)]                                      # freeze right after the hit, then catch up
'''

KEYS = '''KEYS = [  # (arrive, centre, zoom, pitch deg, roll deg, move duration)
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
'''

KICKSWAY = '''KICKS = [(T[p], KS[p]) for p in PLIES] + ACC
SWAY = [(T[40] + 0.20, T[41] - 0.15, 0.6), (T[41] + 1.0, REW0, 0.8), (T[34] + 0.15, T[35] - 0.1, 0.5)]
'''

SPEC = '''SPEC = {
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
'''

MOVER = '''def rt(x):
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
'''

DECO = '''PAD_BASE = 469
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
'''

CAPTURED = '''def hole(canvas, pos, r, a):
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
'''

BADGE = '''BADGE = {29: ("!!", (30, 188, 178)), 37: ("!!", (30, 188, 178)), 41: ("#", (205, 160, 40))}
'''
