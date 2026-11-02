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
