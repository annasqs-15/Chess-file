_dc = {}


def _cached(key, fn):
    if key not in _dc:
        if len(_dc) > 10:
            _dc.clear()
        _dc[key] = fn()
    return _dc[key]


def deco_for_piece(pc, u, square=None, ply=None):
    if pc == ("w", "K") and T[21] + 0.05 <= u < T[26] + 0.8:          # the hunter's eyes light up after the first kill
        k = ease_io((u - T[21] - 0.05) / 0.35) * (1 - ease_io((u - T[26] - 0.35) / 0.4))
        return _cached(("e", round(k * 14)), lambda: D3.king_redeyes(BASE[("w", "K")], round(k * 14) / 14.0))
    if pc == ("b", "K") and T[25] + 0.12 <= u < REW0:
        kk = 1.0 - ease_io((u - (REW0 - 0.35)) / 0.35)
        return _cached(("k", round(u * 60), round(kk * 20)), lambda: D2.blend_k(BASE[("b", "K")], D3.king_ashen(BASE[("b", "K")], u - T[25] - 0.12), kk))
    return None


def queen_look(u):
    """black queen: blood-fed (22, 24), then corpse-pale and cracked once the net closes"""
    g = 0.5 * ease_io((u - T[22]) / 0.5) + 0.5 * ease_io((u - T[24]) / 0.5)
    d = ease_io((u - (T[26] + 0.35)) / 0.65)
    return (g * (1 - d), d)


def queen_size(u):
    return 1.0 + 0.04 * (0.5 * ease_io((u - T[22]) / 0.5) + 0.5 * ease_io((u - T[24]) / 0.5)) * (1 - ease_io((u - (T[26] + 0.35)) / 0.65))
