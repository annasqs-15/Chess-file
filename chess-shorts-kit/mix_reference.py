import numpy as np, subprocess, scipy.io.wavfile as w, math
from scipy.ndimage import minimum_filter1d, uniform_filter1d
from scipy.signal import butter, sosfilt
SR=48000; A0=2.4; FPS=60
HA=[float(v) for v in np.load('hits9_audio.npy')]
T=[round((a-A0)*FPS)/FPS for a in HA]            # video hit times, plies 33..47
REW0=T[-1]+2.05; DUR=REW0+1.0+0.12
D='/home/claude/annasqs-15/chess-file/edited-10x/'
def load(f):
    r=subprocess.run(['ffmpeg','-v','error','-i',D+f,'-f','f32le','-ac','2','-ar',str(SR),'-'],capture_output=True).stdout
    return np.frombuffer(r,np.float32).reshape(-1,2)
sf={k:load(v) for k,v in dict(self='move-self.mp3',cap='capture.mp3',chk='move-check.mp3',mate='Checkmate.m4a').items()}
ons=dict(self=.006,cap=.006,chk=.008,mate=.012)
sr,x=w.read('song4.wav'); x=x.astype(np.float32)/32768
n=int(DUR*SR); mus=x[int(A0*SR):int(A0*SR)+n].copy()
kinds=[['chk'],['cap'],['cap'],['self'],['self'],['cap'],['cap','chk'],['cap'],['cap','chk'],['cap'],['chk'],['self'],['chk'],['self'],['cap','mate']]
def sat(s,drive): return np.tanh(s*drive)/np.tanh(drive)
sfx=np.zeros((n,2),np.float32); duck=np.ones(n,np.float32); sd=np.zeros((n,2),np.float32)
for t,ks in zip(T,kinds):
    for k in ks:
        g=0.75 if k=='chk' and len(ks)>1 else 1.0
        s=sat(sf[k]*5.0*g*0.708,5.0)*0.95
        i=int(round((t-ons[k])*SR)); e=min(n,i+len(s)); sfx[i:e]+=s[:e-i]
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
T38,T41,T46,T47=T[5],T[8],T[13],T[14]
place(riser(1.5),T38,gain=0.55)                             # build into the drop
at(boom(0.8,100,32),T38,gain=1.0)
at(whoosh(0.5),T41-0.55,gain=0.55); at(boom(0.6,80,36),T41,gain=0.7)
place(riser(1.2),T47,gain=0.6)
at(boom(1.1,110,28),T47,gain=1.2)
at(whoosh(0.9),REW0,gain=0.45)                              # the rewind
sd=np.tanh(sd*1.6)/np.tanh(1.6)*0.85
mus*=0.46/np.abs(mus).max()
out=mus*duck[:,None]+sfx+sd*0.9
fi=int(.1*SR); out[:fi]*=np.linspace(0,1,fi)[:,None]
fo=int(.35*SR); out[-fo:]*=np.linspace(1,0,fo)[:,None]
print('pre peak',20*np.log10(np.abs(out).max()))
ceil=10**(-4.0/20)
g=np.minimum(1,ceil/np.maximum(np.abs(out).max(1),1e-6))
g=minimum_filter1d(g,int(.020*SR),mode='nearest'); g=uniform_filter1d(g,int(.015*SR),mode='nearest')
out=out*g[:,None]; print('post',20*np.log10(np.abs(out).max()),'min gain dB',20*np.log10(g.min()),'DUR',DUR)
w.write('audio9.wav',SR,(out*32767).astype(np.int16))
