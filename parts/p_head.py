"""Canal-NN (Scandinavian), plies 16-27 (16...Bb4 .. 27.Ba6#), house style v5 + editor's brief + real 3D (lathe) pieces on tilted moments.
Hand enters at the first move, greedy golden queen, sunglasses king, martyr queen, puppet strings, lava cracks, bear trap, iron grate."""
import sys, math, os, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy.interpolate import PchipInterpolator
from scipy import ndimage as ndi

WORK = os.path.dirname(os.path.abspath(__file__)) + "/"
TAL = WORK
sys.path.insert(0, WORK)
from minichess import Board, parse_moves, sq
from meaning import analyse
import decor as DC
import decor2 as D2

W, H, FPS = 1080, 1920, 60
RS = 2.0
BU, SQU, MU = 1000, 125, 60
SWU = BU + 2 * MU
BP, MP, SWP = int(BU * RS), int(MU * RS), int(SWU * RS)
PSU = 112
A0 = 6.7
CYN = (46, 205, 255)
AMB = (255, 170, 52)
RED = (232, 40, 48)
MAG = (255, 60, 190)
WHITE = (240, 242, 248)
GOLD = (255, 200, 64)
BG1, BG2 = (30, 32, 40), (8, 8, 12)

# hit times on the beat grid of the track (105 BPM, grid 0.2858 s), audio seconds
HITS_A = [7.76, 8.91, 9.48, 10.05, 10.62, 11.19, 11.76, 13.48, 15.19, 18.05, 18.62, 21.00]
PLIES = list(range(16, 28))
P0 = 15
T = {p: round((a - A0) * FPS) / FPS for p, a in zip(PLIES, HITS_A)}
REW0 = T[27] + 1.5
REW1 = REW0 + 1.0
DUR = REW1 + 0.12
KS = {16: .3, 17: .3, 18: .25, 19: .45, 20: .4, 21: .55, 22: 1.0, 23: .4, 24: .7, 25: 1.2, 26: .5, 27: 1.4}
ACC = [(15.76, .22), (16.34, .22), (16.91, .25), (17.48, .25)]
ACC = [(round((a - A0) * FPS) / FPS, s) for a, s in ACC]
