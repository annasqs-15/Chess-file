import sys; sys.path.insert(0,'.')
from minichess import *
VAL=dict(P=1,N=3,B=3,R=5,Q=9,K=100)
def attacks(st,s):
    c,p=st[s]; out=[]
    f,r=s
    def ray(dirs):
        for df,dr in dirs:
            x,y=f+df,r+dr
            while 0<=x<8 and 0<=y<8:
                out.append((x,y))
                if (x,y) in st: break
                x+=df;y+=dr
    if p=='N':
        for df,dr in [(1,2),(2,1),(-1,2),(-2,1),(1,-2),(2,-1),(-1,-2),(-2,-1)]:
            if 0<=f+df<8 and 0<=r+dr<8: out.append((f+df,r+dr))
    elif p=='K':
        for df in (-1,0,1):
            for dr in (-1,0,1):
                if (df or dr) and 0<=f+df<8 and 0<=r+dr<8: out.append((f+df,r+dr))
    elif p=='P':
        d=1 if c=='w' else -1
        for df in (-1,1):
            if 0<=f+df<8 and 0<=r+d<8: out.append((f+df,r+d))
    elif p=='B': ray([(1,1),(1,-1),(-1,1),(-1,-1)])
    elif p=='R': ray([(1,0),(-1,0),(0,1),(0,-1)])
    elif p=='Q': ray([(1,1),(1,-1),(-1,1),(-1,-1),(1,0),(-1,0),(0,1),(0,-1)])
    return out
def analyse(st,mv):
    s=mv['to']; c,p=mv['piece']; en='b' if c=='w' else 'w'
    tg=[]
    for t in attacks(st,s):
        if t in st and st[t][0]==en:
            defended=any(t in attacks(st,q) for q in st if st[q][0]==en and q!=t)
            tg.append((t,st[t][1],defended))
    att=sorted([VAL[st[q][1]] for q in st if st[q][0]==en and s in attacks(st,q)])
    hang= (len(att)>0 and (VAL[p]>att[0] or not any(s in attacks(st,q) for q in st if st[q][0]==c and q!=s)))
    return dict(targets=tg,attackers=att,en_prise=bool(att) and VAL[p]>att[0])
if __name__=='__main__':
    SAN=parse_moves(open('pgn_m3.txt').read()); b=Board(); 
    for i,sn in enumerate(SAN,1):
        inf=b.apply(b.san_move(sn))
        if i>=33:
            a=analyse(b.b,inf); nm=lambda q:name(q)
            print(i,sn,[(name(t),pp,'def' if d else 'LOOSE') for t,pp,d in a['targets']],'attackers',a['attackers'],'SAC' if a['en_prise'] else '')
