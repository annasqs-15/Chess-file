def post_fx(frame, u, t):
    arr = None
    g = grade(u)
    if max(abs(g[0] - 1), abs(g[1] - 1), abs(g[2] - 1)) > 0.004:
        arr = np.asarray(frame, np.float32) * np.array(g, np.float32)[None, None, :]
    rgb = 0.0
    for tk, amp, dec in ((T[22], 11, 0.10), (T[25], 8, 0.09), (T[27], 15, 0.16)):
        d = t - tk
        if 0 <= d < 0.4:
            rgb = max(rgb, amp * math.exp(-d / dec))
    flash = 0.0
    for tk, a, dec in ((T[22], 0.30, 0.05), (T[25], 0.30, 0.05), (T[27], 0.60, 0.07)):
        d = t - tk
        if 0 <= d < 0.4:
            flash = max(flash, a * math.exp(-d / dec))
    if rgb > 0.8 or flash > 0.01:
        if arr is None:
            arr = np.asarray(frame, np.float32).copy()
        if rgb > 0.8:
            s = int(rgb)
            arr[..., 0] = np.roll(arr[..., 0], s, axis=1)
            arr[..., 2] = np.roll(arr[..., 2], -s, axis=1)
        if flash > 0.01:
            arr = arr + (255 - arr) * flash
    if arr is None:
        return frame
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
