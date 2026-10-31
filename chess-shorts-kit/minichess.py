"""Minimal chess rules engine: SAN parsing, legality, FEN-free board tracking."""

FILES = "abcdefgh"


def sq(name):
    return (FILES.index(name[0]), int(name[1]) - 1)


def name(s):
    return FILES[s[0]] + str(s[1] + 1)


KNIGHT = [(1, 2), (2, 1), (-1, 2), (-2, 1), (1, -2), (2, -1), (-1, -2), (-2, -1)]
KING = [(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)]
ROOK = [(1, 0), (-1, 0), (0, 1), (0, -1)]
BISHOP = [(1, 1), (1, -1), (-1, 1), (-1, -1)]


def inb(f, r):
    return 0 <= f < 8 and 0 <= r < 8


class Board:
    def __init__(self):
        self.b = {}
        back = "RNBQKBNR"
        for i, p in enumerate(back):
            self.b[(i, 0)] = ("w", p)
            self.b[(i, 7)] = ("b", p)
            self.b[(i, 1)] = ("w", "P")
            self.b[(i, 6)] = ("b", "P")
        self.turn = "w"
        self.castle = {"wK": True, "wQ": True, "bK": True, "bQ": True}
        self.ep = None

    def copy(self):
        n = Board.__new__(Board)
        n.b = dict(self.b)
        n.turn = self.turn
        n.castle = dict(self.castle)
        n.ep = self.ep
        return n

    # attack detection
    def attacked(self, target, by):
        for (f, r), (c, p) in self.b.items():
            if c != by:
                continue
            df, dr = target[0] - f, target[1] - r
            if p == "P":
                d = 1 if c == "w" else -1
                if dr == d and abs(df) == 1:
                    return True
            elif p == "N":
                if (df, dr) in KNIGHT:
                    return True
            elif p == "K":
                if max(abs(df), abs(dr)) == 1:
                    return True
            else:
                dirs = ROOK if p == "R" else BISHOP if p == "B" else ROOK + BISHOP
                for d in dirs:
                    x, y = f + d[0], r + d[1]
                    while inb(x, y):
                        if (x, y) == target:
                            return True
                        if (x, y) in self.b:
                            break
                        x += d[0]
                        y += d[1]
        return False

    def king_sq(self, c):
        for s, (cc, p) in self.b.items():
            if cc == c and p == "K":
                return s

    def in_check(self, c):
        return self.attacked(self.king_sq(c), "b" if c == "w" else "w")

    def pseudo(self, c):
        """yield (from, to, promo, flag) pseudo-legal moves for colour c"""
        out = []
        for (f, r), (cc, p) in list(self.b.items()):
            if cc != c:
                continue
            if p == "P":
                d = 1 if c == "w" else -1
                start = 1 if c == "w" else 6
                last = 7 if c == "w" else 0
                if inb(f, r + d) and (f, r + d) not in self.b:
                    tos = [(f, r + d)]
                    if r == start and (f, r + 2 * d) not in self.b:
                        tos.append((f, r + 2 * d))
                    for t in tos:
                        if t[1] == last:
                            for pr in "QRBN":
                                out.append(((f, r), t, pr, None))
                        else:
                            out.append(((f, r), t, None, "dbl" if abs(t[1] - r) == 2 else None))
                for df in (-1, 1):
                    t = (f + df, r + d)
                    if not inb(*t):
                        continue
                    if t in self.b and self.b[t][0] != c:
                        if t[1] == last:
                            for pr in "QRBN":
                                out.append(((f, r), t, pr, None))
                        else:
                            out.append(((f, r), t, None, None))
                    elif t == self.ep:
                        out.append(((f, r), t, None, "ep"))
            elif p in "NK":
                for d in (KNIGHT if p == "N" else KING):
                    t = (f + d[0], r + d[1])
                    if inb(*t) and (t not in self.b or self.b[t][0] != c):
                        out.append(((f, r), t, None, None))
                if p == "K":
                    rank = 0 if c == "w" else 7
                    if (f, r) == (4, rank) and not self.in_check(c):
                        opp = "b" if c == "w" else "w"
                        if self.castle[c + "K"] and self.b.get((7, rank)) == (c, "R") \
                                and (5, rank) not in self.b and (6, rank) not in self.b \
                                and not self.attacked((5, rank), opp) and not self.attacked((6, rank), opp):
                            out.append(((f, r), (6, rank), None, "K"))
                        if self.castle[c + "Q"] and self.b.get((0, rank)) == (c, "R") \
                                and all((x, rank) not in self.b for x in (1, 2, 3)) \
                                and not self.attacked((3, rank), opp) and not self.attacked((2, rank), opp):
                            out.append(((f, r), (2, rank), None, "Q"))
            else:
                dirs = ROOK if p == "R" else BISHOP if p == "B" else ROOK + BISHOP
                for d in dirs:
                    x, y = f + d[0], r + d[1]
                    while inb(x, y):
                        if (x, y) in self.b:
                            if self.b[(x, y)][0] != c:
                                out.append(((f, r), (x, y), None, None))
                            break
                        out.append(((f, r), (x, y), None, None))
                        x += d[0]
                        y += d[1]
        return out

    def apply(self, mv):
        """apply move in place; return dict describing it for animation"""
        f, t, promo, flag = mv
        c, p = self.b[f]
        info = {"from": f, "to": t, "piece": (c, p), "captured": None, "promo": promo,
                "extra": None, "castle": flag if flag in ("K", "Q") else None}
        if t in self.b:
            info["captured"] = (t, self.b[t])
        if flag == "ep":
            cs = (t[0], f[1])
            info["captured"] = (cs, self.b.pop(cs))
        del self.b[f]
        self.b[t] = (c, promo) if promo else (c, p)
        if flag in ("K", "Q"):
            rank = f[1]
            rf, rt = ((7, rank), (5, rank)) if flag == "K" else ((0, rank), (3, rank))
            self.b[rt] = self.b.pop(rf)
            info["extra"] = (rf, rt, self.b[rt])
        # castling rights
        if p == "K":
            self.castle[c + "K"] = self.castle[c + "Q"] = False
        for s, key in (((0, 0), "wQ"), ((7, 0), "wK"), ((0, 7), "bQ"), ((7, 7), "bK")):
            if f == s or t == s:
                self.castle[key] = False
        self.ep = (f[0], (f[1] + t[1]) // 2) if flag == "dbl" else None
        self.turn = "b" if c == "w" else "w"
        return info

    def legal(self, c):
        res = []
        for mv in self.pseudo(c):
            n = self.copy()
            n.apply(mv)
            if not n.in_check(c):
                res.append(mv)
        return res

    def san_move(self, san):
        c = self.turn
        s = san.rstrip("+#!?")
        legal = self.legal(c)
        if s in ("O-O", "O-O-O", "0-0", "0-0-0"):
            flag = "K" if s.count("O") + s.count("0") == 2 else "Q"
            for mv in legal:
                if mv[3] == flag:
                    return mv
            raise ValueError("illegal castle " + san)
        promo = None
        if "=" in s:
            s, promo = s.split("=")
        piece = "P"
        if s[0] in "NBRQK":
            piece = s[0]
            s = s[1:]
        s = s.replace("x", "")
        target = sq(s[-2:])
        dis = s[:-2]
        cands = []
        for mv in legal:
            f, t, pr, fl = mv
            if t != target or self.b[f][1] != piece:
                continue
            if (pr or None) != (promo or None):
                continue
            if dis:
                if len(dis) == 2 and name(f) != dis:
                    continue
                if len(dis) == 1:
                    if dis in FILES and FILES[f[0]] != dis:
                        continue
                    if dis in "12345678" and str(f[1] + 1) != dis:
                        continue
            cands.append(mv)
        if len(cands) != 1:
            raise ValueError("ambiguous/illegal %s: %d candidates" % (san, len(cands)))
        return cands[0]

    def fen_board(self):
        rows = []
        for r in range(7, -1, -1):
            row, e = "", 0
            for f in range(8):
                if (f, r) in self.b:
                    if e:
                        row += str(e)
                        e = 0
                    c, p = self.b[(f, r)]
                    row += p if c == "w" else p.lower()
                else:
                    e += 1
            if e:
                row += str(e)
            rows.append(row)
        return "/".join(rows)


def parse_moves(movetext):
    import re
    toks = re.sub(r"\d+\.(\.\.)?", " ", movetext).split()
    return [t for t in toks if t not in ("1-0", "0-1", "1/2-1/2", "*")]
