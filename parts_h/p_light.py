AMB0 = 0.60            # the board lives in the dark; lantern pools reveal it
DIPS = [(0.30, .30, .06), (0.42, .22, .05), (1.95, .28, .05), (3.65, .32, .07), (4.78, .30, .05), (6.15, .38, .08),
        (7.35, .30, .06), (9.25, .28, .05), (10.45, .36, .07), (12.95, .45, .08), (13.55, .38, .05)]


def light_events():
    """(t0, rise, hold, fall, ambient dip, (sq a, sq b), radius, strength, colour)"""
    return [
        (0.10, 0.60, 0.80, 0.50, 0.0, ("d6", "d6"), 330, 0.85, BONE),
        (T[16] - 0.25, 0.25, 0.90, 0.40, 0.0, ("b4", "b4"), 250, 0.95, SICK),
        (T[17] - 0.20, 0.25, 0.50, 0.30, 0.0, ("b4", "e1"), 340, 0.80, BLOOD),
        (T[18] - 0.20, 0.20, 0.35, 0.30, 0.0, ("c7", "d7"), 260, 0.80, SICK),
        (T[19] - 0.20, 0.20, 0.40, 0.30, 0.0, ("a3", "b4"), 260, 0.95, BLOOD),
        (T[20] - 0.20, 0.20, 0.35, 0.30, 0.0, ("b8", "d8"), 300, 0.80, BONE),
        (T[21] - 0.20, 0.20, 0.30, 0.30, 0.0, ("a3", "b4"), 280, 0.95, BLOOD),
        (T[22] - 0.30, 0.20, 1.10, 0.50, 0.30, ("a1", "a1"), 270, 1.10, BLOOD),
        (T[23] - 0.20, 0.25, 0.80, 0.50, 0.0, ("d2", "e1"), 290, 0.80, BONE),
        (T[24] - 0.20, 0.20, 0.70, 0.40, 0.0, ("h1", "h1"), 270, 1.00, BLOOD),
        (T[24] + 0.80, 0.60, 1.40, 0.40, 0.25, ("f3", "f3"), 300, 1.00, SICK),
        (T[25] - 0.10, 0.12, 0.35, 0.50, 0.0, ("c6", "c6"), 300, 1.20, SICK),
        (T[26] + 0.00, 0.30, 1.40, 0.50, 0.20, ("e2", "e2"), 300, 1.00, BLOOD),
        (T[27] - 0.20, 0.20, 0.60, 0.70, 0.30, ("c8", "c8"), 300, 1.20, BLOOD),
    ]


def light_map(u):
    amb = AMB0
    for (td, dd, dl) in DIPS:                              # failing-bulb flicker
        d = u - td
        if 0 <= d < dl:
            amb -= dd * AMB0 * math.sin(math.pi * d / dl)
    amb += 0.025 * math.sin(u * 47.0) * math.sin(u * 13.0)
    pools = []
    for (t0, ri, ho, fa, dip, cen, rad, st, col) in light_events():
        e = u - t0
        if e <= 0:
            continue
        k = ease_io(e / ri) * (1 - ease_io((e - ri - ho) / fa))
        if k <= 0.003:
            continue
        amb -= dip * k
        pools.append((S(*cen), rad * (1.5 - 0.5 * k), st * k * 0.72, col))
    ex = 0.0
    for tk, s in KICKS:
        d = u - tk
        if 0 <= d < 0.3:
            ex += 0.10 * s * math.exp(-d / 0.07)
    return max(amb, 0.10) + ex, pools
