SH0 = round((16.34 - A0) * FPS) / FPS          # sunglasses drop on a beat
_dc = {}


def _cached(key, fn):
    if key not in _dc:
        if len(_dc) > 8:
            _dc.clear()
        _dc[key] = fn()
    return _dc[key]


def deco_for_piece(pc, u, square=None, ply=None):
    if pc == ("w", "K") and SH0 <= u < T[26] + 0.40:
        if u < T[26] + 0.10:
            dr = clamp((u - SH0) / 0.35)
        else:
            dr = 1 - ease_io((u - T[26] - 0.10) / 0.28)
        return _cached(("s", round(dr * 200)), lambda: D2.king_shades(BASE[("w", "K")], dr))
    if pc == ("b", "K") and T[25] + 0.12 <= u < REW0:
        kk = 1.0 - ease_io((u - (REW0 - 0.35)) / 0.35)
        return _cached(("k", round(u * 90), round(kk * 20)), lambda: D2.blend_k(BASE[("b", "K")], D2.king_shock(BASE[("b", "K")], u - T[25] - 0.12), kk))
    return None


def queen_look(u):
    """black queen: greedy gold (22, 24), then drained grey stone when the net closes"""
    g = 0.55 * ease_io((u - T[22]) / 0.6) + 0.45 * ease_io((u - T[24]) / 0.6)
    d = ease_io((u - (T[26] + 0.35)) / 0.65)
    return (g * (1 - d), d)


def queen_size(u):
    s = 1.0 + 0.08 * ease_io((u - T[22]) / 0.6) + 0.09 * ease_io((u - T[24]) / 0.6)
    d = ease_io((u - (T[26] + 0.35)) / 0.65)
    return s - 0.17 * d * (s - 1.0) / 0.17 if False else 1.0 + (s - 1.0) * (1 - d)
