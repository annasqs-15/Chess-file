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
        _look_cache[key] = D2.golden(SPR[piece], key[1] / 24.0, key[2] / 24.0)
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
