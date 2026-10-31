# Chess shorts kit (style "v5")

Reference implementation of the approved edit (Anderssen-Dufresne, plies 33-47). Copy this folder next to the PGN and music.

Files
- audio_grid.py         music -> drop time, beat grid (period/phase), strong grid points. Hits of chess moves sit on these.
- minichess.py          SAN engine (python-chess is not installable). meaning.py: attacked pieces, loose pieces, sacrifices.
- chess_tools.py        forced-mate search + move labels (mate / blunder / brilliant) without an engine. Takes ~10 s per 15 plies.
- renderer_reference.py full renderer for THIS game: camera, per-move motion specs (SPEC), effects (under_fx / over_fx), light, grade, rewind loop.
                        For a new PGN keep every helper and replace the per-move parts: HITS_A, PLIES, KEYS, SPEC, under_fx, over_fx, captured_draw, BADGE, light_events, GRADE.
- mix_reference.py      music window + SFX (repo edited-10x) + ducking + riser/boom/whoosh + limiter.
- pieces5/ board_dim.jpg  the user's piece PNGs (512 px) and the grey-white board.

Per-PGN procedure: 1 audio_grid -> pick hit times; 2 chess_tools -> labels; 3 design note per move; 4 write SPEC/effects; 5 test frames; 6 render 2 chunks; 7 mix; 8 verify.
