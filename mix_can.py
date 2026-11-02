import numpy as np, subprocess, scipy.io.wavfile as w, math
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import butter, sosfilt
SR=48000; A0=6.7; FPS=60
import sys; sys.path.insert(0,'.')
HA=[7.76,8.91,9.48,10.05,10.62,11.19,11.76,13.48,15.19,18.05,18.62,21.00]
T=[round((a-A0)*FPS)/FPS for a in HA]            # video hit times, plies 16..27
REW0=T[-1]+1.5; DUR=REW0+1.0+0.12
D='/home/claude/annasqs-15/chess-file/edited-10x/'
def load(f):
    r=subprocess.run(['ffmpeg','-v','error','-i',D+f,'-f','f32le','-ac','2','-ar',str(SR),'-'],capture_output=True).stdout
    return np.frombuffer(r,np.float32).reshape(-1,2)
sf={k:load(v) for k,v in dict(self='move-self.mp3',cap='capture.mp3',chk='move-check.mp3',mate='Checkmate.m4a').items()}
ons=dict(self=.006,cap=.006,chk=.008,mate=.012,self2=.006)
sr,x=w.read('song_c.wav'); x=x.astype(np.float32)/32768
n=int(DUR*SR); mus=x[int(A0*SR):int(A0*SR)+n].copy()
from minichess import parse_moves
SANS=parse_moves(open('pgn_can.txt').read())[15:27]
kinds=[]
for m in SANS:
    if m.startswith('O-O'): k=['self','self2']
    elif m.endswith('#'): k=['cap','mate'] if 'x' in m else ['mate']
    elif 'x' in m: k=['cap','chk'] if '+' in m else ['cap']
    elif '+' in m: k=['chk']
    else: k=['self']
    kinds.append(k)
print(list(zip(SANS,kinds)))
def sat(s,drive): return np.tanh(s*drive)/np.tanh(drive)
sfx=np.zeros((n,2),np.float32); duck=np.ones(n,np.float32); sd=np.zeros((n,2),np.float32)
for t,ks in zip(T,kinds):
    for k in ks:
        g=0.75 if k=='chk' and len(ks)>1 else 1.0
        kk='self' if k=='self2' else k
        if k=='self2': g=0.84
        s=sat(sf[kk]*5.0*g*0.708,5.0)*0.95
        i=int(round((t-ons[k]+(0.035 if k=='self2' else 0.0))*SR)); e=min(n,i+len(s)); sfx[i:e]+=s[:e-i]
    i=int(t*SR); a0=max(0,i-int(.012*SR)); L=int(.26*SR)
    env=np.ones(n,np.float32); env[a0:i+L]=0.50
    duck=np.minimum(duck,env)
duck=uniform_filter1d(duck,int(.03*SR),mode='nearest')
rng=np.random.RandomState(4)
def noise(d): return rng.randn(int(d*SR)).astype(np.float32)
def band(sig,lo,hi):
    return sosfilt(butter(2,[lo,hi],btype='band',fs=SR,output='sos'),sig)
def place(sig,t_end,stereo=True,gain=1.0):                 # sound that ends exactly at t_end
    i=int(round(t_end*SR))-len(sig); 
    if i<0: sig=sig[-i:]; i=0
    e=min(n,i+len(sig)); sd[i:e]+=sig[:e-i,None]*gain
def riser(d):                                              # filtered-noise sweep that swells to the hit
    s=noise(d); tt=np.linspace(0,1,len(s))
    out=np.zeros_like(s)
    for lo,hi in ((300,900),(900,2600),(2600,7000)):
        out+=band(s,lo,hi)*(tt**2.2)
    return out*0.9
def boom(d=0.7,f0=95,f1=34):                               # sub drop + short noise burst
    tt=np.linspace(0,d,int(d*SR),endpoint=False); f=f1+(f0-f1)*np.exp(-tt/0.12)
    ph=2*np.pi*np.cumsum(f)/SR; s=np.sin(ph)*np.exp(-tt/0.28)
    b=band(noise(d),100,2200)*np.exp(-tt/0.05)*0.6
    return (s+b).astype(np.float32)
def whoosh(d):
    s=noise(d); tt=np.linspace(0,1,len(s)); env=np.sin(np.pi*tt)**1.5
    return band(s,500,5000)*env*0.7
def at(sig,t0,gain=1.0):                                   # sound starting at t0
    i=int(round(t0*SR)); e=min(n,i+len(sig)); sd[i:e]+=sig[:e-i,None]*gain
T22,T25,T27=T[6],T[9],T[11]
at(whoosh(0.5),0.25,gain=0.35)                                         # the hand reaches in
place(riser(0.8),T22,gain=0.45); at(boom(0.9,100,30),T22,gain=0.9)     # the greedy strike (drop)
place(riser(1.0),T[9]-0.0,gain=0.5); at(whoosh(0.4),T25-0.30,gain=0.5); at(boom(1.0,95,32),T25,gain=1.0)   # the sacrifice
at(whoosh(0.35),T[10]-0.35,gain=0.4)                                   # puppet strings pull
place(riser(1.0),T27,gain=0.55); at(boom(1.1,110,28),T27,gain=1.1)     # the mate
at(whoosh(0.9),REW0,gain=0.45)
sd=np.tanh(sd*1.6)/np.tanh(1.6)*0.85
mus*=0.46/np.abs(mus).max()
print("peaks mus",20*np.log10(np.abs(mus*duck[:,None]).max()),"sfx",20*np.log10(np.abs(sfx).max()),"sd",20*np.log10(np.abs(sd).max()));out=mus*duck[:,None]+sfx+sd*0.9
fi=int(.1*SR); out[:fi]*=np.linspace(0,1,fi)[:,None]
fo=int(.35*SR); out[-fo:]*=np.linspace(1,0,fo)[:,None]
print('pre peak',20*np.log10(np.abs(out).max()))
ceil=10**(-5.5/20)
g=np.minimum(1,ceil/np.maximum(np.abs(out).max(1),1e-6))
g=minimum_filter1d(g,int(.020*SR),mode='nearest'); g=uniform_filter1d(g,int(.015*SR),mode='nearest')
out=out*g[:,None]; print('post',20*np.log10(np.abs(out).max()),'min gain dB',20*np.log10(g.min()),'DUR',DUR)
w.write('audio_can.wav',SR,(out*32767).astype(np.int16))
