"""Usage: python3 audio_grid.py song.(m4a|mp3|wav)  ->  prints drop time, grid period/phase and the strong grid points (JSON in grid.json).
Method used for the Chess shorts: STFT spectral flux (5 ms hop), autocorrelation for the 8th-note period, comb fit for phase,
then every grid point is scored by flux. Hits for chess moves must sit on strong grid points (or the drop)."""
import sys, json, subprocess, numpy as np, scipy.signal as s, scipy.io.wavfile as w
src = sys.argv[1]
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-ac', '2', '-ar', '48000', '/tmp/_ag.wav'], check=True)
sr, x = w.read('/tmp/_ag.wav'); m = (x.astype(float) / 32768).mean(1)
f, t, Z = s.stft(m, sr, nperseg=1024, noverlap=1024 - 240)             # 5 ms hop
L = np.log1p(np.abs(Z) * 30)
flux = np.maximum(0, np.diff(L, axis=1, prepend=L[:, :1])).sum(0)
hop = 240; e = np.sqrt(np.add.reduceat(m ** 2, np.arange(0, len(m) - hop, hop)) / hop)
jump = np.convolve(e, np.ones(100) / 100, 'same'); jump = np.roll(jump, -100) - jump       # 0.5 s after minus 0.5 s before
drop = float(np.argmax(jump[: len(jump) - 120]) / 200.0)
d = flux - flux.mean(); ac = np.correlate(d, d, 'full')[len(d) - 1:]; ac /= ac[0]
pk, _ = s.find_peaks(ac[40:400]); lags = (pk + 40) / 200.0; vals = ac[pk + 40]
period = float(lags[np.argsort(-vals)[:4]].min())                      # smallest strong lag = grid unit (usually 8th note)
period = float(np.round(period / 0.0005) * 0.0005)
best = max(((np.mean([flux[max(0, i - 1): i + 2].max() for i in np.round(np.arange(ph, len(flux) / 200.0, period) * 200).astype(int) if i < len(flux)]), ph)
            for ph in np.arange(drop - period, drop + period, 0.005)))
phase = float(best[1])
grid = np.arange(phase % period, len(m) / sr, period)
pts = [(round(float(g), 3), round(float(flux[int(round(g * 200)) - 2: int(round(g * 200)) + 3].max()), 1)) for g in grid if g * 200 < len(flux) - 3]
json.dump(dict(drop=drop, period=period, phase=phase, grid=pts), open('grid.json', 'w'))
print('drop', round(drop, 2), 'period', period, 'phase', round(phase, 3))
print('strong grid points (flux>=60% of the 90th percentile):')
thr = 0.6 * np.percentile([v for _, v in pts], 90)
print([g for g, v in pts if v >= thr])
