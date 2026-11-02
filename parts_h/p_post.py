_VIG = None
_FOG = None
_GR = None
DESAT = 0.38


def _tables():
    global _VIG, _FOG, _GR
    if _VIG is None:
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H * 0.50) / (H * 0.60)) ** 2)
        _VIG = r.astype(np.float32)
        rs = np.random.RandomState(4)
        lo = ndi.gaussian_filter(rs.rand(120, 90).astype(np.float32), 5.0, mode="wrap")
        lo = (lo - lo.min()) / (lo.max() - lo.min())
        mid = ndi.gaussian_filter(rs.rand(240, 180).astype(np.float32), 5.0, mode="wrap")
        mid = (mid - mid.min()) / (mid.max() - mid.min())
        lo = np.asarray(Image.fromarray((lo * 255).astype(np.uint8)).resize((180, 240), Image.BICUBIC), np.float32) / 255.0
        f = 0.65 * lo + 0.35 * mid
        f = np.clip((f - 0.30) * 1.9, 0, 1)
        _FOG = np.asarray(Image.fromarray((f * 255).astype(np.uint8)).resize((W + 360, H + 360), Image.BICUBIC), np.float32) / 255.0
        g = np.random.RandomState(9).randn(6, H, W).astype(np.float16) * 5.0
        _GR = g


def heart(u):
    ph = (u % 0.571) / 0.571
    return math.exp(-((ph - 0.04) / 0.05) ** 2) + 0.65 * math.exp(-((ph - 0.30) / 0.05) ** 2)


def fog_amount(u):
    a = 0.13
    a += 0.16 * clamp(1 - u / 2.0) * clamp(u / 0.3)                      # creeping in at the start
    a += 0.10 * (ease_io((u - (T[26] + 0.4)) / 0.5) * (1 - ease_io((u - (T[27] - 0.05)) / 0.1)))
    a += 0.12 * ease_io((u - (T[27] + 0.3)) / 0.5) * (1 - ease_io((u - (REW0 - 0.2)) / 0.3))
    for tk in (T[22], T[25]):
        d = u - tk
        if 0 <= d < 0.6:
            a -= 0.10 * math.exp(-d / 0.15)                              # blown clear by the hit
    return clamp(a, 0, 0.42)


def post_fx(frame, u, t):
    _tables()
    fi = int(round(t * FPS))
    arr = np.asarray(frame, np.float32) * np.array(grade(u), np.float32)[None, None, :]
    lum = (arr[..., 0] * 0.30 + arr[..., 1] * 0.59 + arr[..., 2] * 0.11)[..., None]
    arr = lum + (arr - lum) * (1 - DESAT)
    fa = fog_amount(u)
    if fa > 0.005:
        ox, oy = int((u * 34) % 360), int((u * 11 + 90) % 360)
        fg = _FOG[oy:oy + H, ox:ox + W][..., None] * fa
        arr = arr * (1 - fg) + np.array([150, 168, 160], np.float32) * fg
    hb = heart(u)
    v = np.clip(_VIG - 0.42, 0, 1.2)
    dark = np.clip(v * (0.95 + 0.30 * hb), 0, 1.0)
    arr = arr * (1 - 0.82 * dark[..., None] ** 1.3) + np.array([34, 0, 4], np.float32) * (0.35 * dark[..., None] ** 1.3) * (0.4 + hb)
    rgb = 0.0
    for tk, amp, dec in ((T[22], 12, 0.10), (T[25], 9, 0.09), (T[27], 18, 0.16)):
        d = t - tk
        if 0 <= d < 0.4:
            rgb = max(rgb, amp * math.exp(-d / dec))
    if rgb > 0.8:
        s = int(rgb)
        arr[..., 0] = np.roll(arr[..., 0], s, axis=1)
        arr[..., 2] = np.roll(arr[..., 2], -s, axis=1)
    arr = arr + _GR[fi % 6].astype(np.float32)[..., None]
    for tk, a, dec, col in ((T[22], 0.30, 0.05, (255, 60, 50)), (T[25], 0.30, 0.05, (210, 255, 225)), (T[27], 0.65, 0.09, (255, 24, 24))):
        d = t - tk
        if 0.0 <= d < 0.4 and not (tk == T[27] and d < 0.05):
            fl = a * math.exp(-d / dec)
            if fl > 0.01:
                arr = arr + (np.array(col, np.float32) - arr) * fl
    if T[27] <= t < T[27] + 0.05:                                         # jump scare: one black beat on the mate
        arr = arr * 0.0
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
