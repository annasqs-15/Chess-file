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
