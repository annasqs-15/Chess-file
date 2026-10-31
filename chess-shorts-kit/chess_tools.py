"""Move meaning + move-quality labels without an engine (forced-mate search + material/sacrifice rules)."""
import sys, time
sys.path.insert(0, '.')
from minichess import Board, parse_moves, name
from meaning import analyse, VAL

def checks(b, c):
    out = []
    en = 'b' if c == 'w' else 'w'
    for mv in b.legal(c):
        n = b.copy(); n.apply(mv)
        if n.in_check(en): out.append(mv)
    return out

def mate_in(b, attacker, n):
    """smallest k<=n such that `attacker` (to move) forces mate in k moves using checking moves only; else None"""
    if n <= 0: return None
    defender = 'b' if attacker == 'w' else 'w'
    best = None
    for mv in checks(b, attacker):
        nb = b.copy(); nb.apply(mv)
        replies = nb.legal(defender)
        if not replies:
            return 1
        if n == 1: continue
        worst = 0
        for r in replies:
            nb2 = nb.copy(); nb2.apply(r)
            k = mate_in(nb2, attacker, n - 1)
            if k is None:
                worst = None; break
            worst = max(worst, k)
        if worst is not None:
            k = worst + 1
            if best is None or k < best: best = k
            if best <= 2: break
    return best

def classify(pgn_text, first_ply, last_ply, max_mate=5):
    san = parse_moves(pgn_text); b = Board(); rows = []
    for i, s in enumerate(san, 1):
        before = b.copy(); mv = b.san_move(s); info = b.apply(mv)
        if i < first_ply: continue
        mover = info['piece'][0]; opp = 'b' if mover == 'w' else 'w'
        st = dict(b.b); a = analyse(st, info)
        row = dict(ply=i, san=s, mover=mover, sac=0, forks=[], mate_for_mover=None, opp_mate=None, label=None, note='')
        if not b.legal(opp) and b.in_check(opp): row['label'] = 'mate'; rows.append(row); continue
        # material given up if the piece can be taken by something cheaper
        gained = VAL[info['captured'][1][1]] if info['captured'] else 0
        caps = [VAL[b.b[m[0]][1]] for m in b.legal(opp) if m[1] == info['to']]
        if caps:
            defended = any(info['to'] in __import__('meaning').attacks(st, q) for q in st if st[q][0] == mover and q != info['to'])
            row['sac'] = max(0, VAL[info['piece'][1]] - (min(caps) if defended else gained))
        row['forks'] = [(name(t), p) for t, p, d in a['targets'] if VAL[p] > VAL[info['piece'][1]] and (not d or p == 'K')]
        row['mate_for_mover'] = mate_in(b, mover, max_mate) if b.turn == mover else None
        # mover's own forced mate after their move needs mover to move again: test opponent's replies instead
        if b.turn == opp:
            row['opp_mate'] = mate_in(b, opp, max_mate)
            # does the mover keep a forced mate whatever the opponent does? (check via every reply)
            ok = True; worst = 0
            for r in b.legal(opp):
                nb = b.copy(); nb.apply(r)
                k = mate_in(nb, mover, max_mate)
                if k is None: ok = False; break
                worst = max(worst, k)
            row['mate_for_mover'] = (worst + 1) if ok and b.legal(opp) else None
            # blunder: opponent now has forced mate and some other legal move of mover avoided it
            if row['opp_mate'] is not None:
                alt_ok = False
                for alt in before.legal(mover):
                    nb = before.copy(); nb.apply(alt)
                    if not nb.legal(opp): continue
                    if mate_in(nb, opp, max_mate) is None: alt_ok = True; break
                if alt_ok: row['label'] = 'blunder'
        rows.append(row)
    # brilliant / great, at most one per 3 plies, strongest first
    cands = []
    for r in rows:
        if r['label']: continue
        if r['sac'] >= 3 and (r['mate_for_mover'] or r['forks']): cands.append((r['sac'] + (5 if r['mate_for_mover'] else 0), r['ply'], 'brilliant'))
    cands.sort(reverse=True); taken = []
    for sc, p, lab in cands:
        if all(abs(p - q) >= 3 for q in taken):
            taken.append(p); next(r for r in rows if r['ply'] == p)['label'] = lab
    return rows

if __name__ == '__main__':
    t = time.time()
    rows = classify(open('pgn_m3.txt').read(), 33, 47)
    for r in rows: print(r['ply'], r['san'], 'sac', r['sac'], 'forks', r['forks'], 'mate_for_mover', r['mate_for_mover'], 'opp_mate', r['opp_mate'], '->', r['label'])
    print('time', round(time.time() - t, 1), 's')
