"""Pure-Python fallback for the `noise` C extension.

Why this exists
---------------
`raenim/animation.py` does `from noise import pnoise1` at module import time, so
`from raenim import *` fails outright without it. The upstream `noise` package
(1.2.2, last released 2015) ships no wheels for CPython 3.11 and needs an MSVC
toolchain to build from source.

Its only consumer in raenim is `RWiggle`, a cosmetic Perlin-noise tremor. A
classic 1-D Perlin implementation is faithful enough for that, so we inject this
module instead of forcing a multi-GB Build Tools install.

Implements the subset of the `noise` API that raenim touches. `pnoise2`/`pnoise3`
are provided for completeness in case scene code reaches for them.
"""

from __future__ import annotations

import math

__all__ = ["pnoise1", "pnoise2", "pnoise3", "SHIM"]

# Marks this as the fallback so preflight can tell it apart from the real package.
SHIM = True

# Ken Perlin's reference permutation table, doubled to avoid index wrapping.
_P = [
    151, 160, 137, 91, 90, 15, 131, 13, 201, 95, 96, 53, 194, 233, 7, 225,
    140, 36, 103, 30, 69, 142, 8, 99, 37, 240, 21, 10, 23, 190, 6, 148,
    247, 120, 234, 75, 0, 26, 197, 62, 94, 252, 219, 203, 117, 35, 11, 32,
    57, 177, 33, 88, 237, 149, 56, 87, 174, 20, 125, 136, 171, 168, 68, 175,
    74, 165, 71, 134, 139, 48, 27, 166, 77, 146, 158, 231, 83, 111, 229, 122,
    60, 211, 133, 230, 220, 105, 92, 41, 55, 46, 245, 40, 244, 102, 143, 54,
    65, 25, 63, 161, 1, 216, 80, 73, 209, 76, 132, 187, 208, 89, 18, 169,
    200, 196, 135, 130, 116, 188, 159, 86, 164, 100, 109, 198, 173, 186, 3, 64,
    52, 217, 226, 250, 124, 123, 5, 202, 38, 147, 118, 126, 255, 82, 85, 212,
    207, 206, 59, 227, 47, 16, 58, 17, 182, 189, 28, 42, 223, 183, 170, 213,
    119, 248, 152, 2, 44, 154, 163, 70, 221, 153, 101, 155, 167, 43, 172, 9,
    129, 22, 39, 253, 19, 98, 108, 110, 79, 113, 224, 232, 178, 185, 112, 104,
    218, 246, 97, 228, 251, 34, 242, 193, 238, 210, 144, 12, 191, 179, 162, 241,
    81, 51, 145, 235, 249, 14, 239, 107, 49, 192, 214, 31, 181, 199, 106, 157,
    184, 84, 204, 176, 115, 121, 50, 45, 127, 4, 150, 254, 138, 236, 205, 93,
    222, 114, 67, 29, 24, 72, 243, 141, 128, 195, 78, 66, 215, 61, 156, 180,
]
_PERM = _P * 2


def _fade(t: float) -> float:
    # 6t^5 - 15t^4 + 10t^3 — Perlin's improved smoothstep.
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp(a: float, b: float, t: float) -> float:
    return a + t * (b - a)


def _grad1(h: int, x: float) -> float:
    return x if (h & 1) == 0 else -x


def _perlin1(x: float, repeat: int, base: int) -> float:
    if repeat > 0:
        x = math.fmod(x, repeat)
        if x < 0:
            x += repeat
    xi = int(math.floor(x))
    xf = x - xi
    i = (xi + base) & 255
    j = (xi + 1 + base) & 255
    u = _fade(xf)
    return _lerp(_grad1(_PERM[i], xf), _grad1(_PERM[j], xf - 1.0), u)


def _fbm(sample, octaves: int, persistence: float, lacunarity: float) -> float:
    """Fractal Brownian motion: sum octaves, normalised to roughly [-1, 1]."""
    total = 0.0
    freq = 1.0
    amp = 1.0
    max_amp = 0.0
    for _ in range(max(1, int(octaves))):
        total += sample(freq) * amp
        max_amp += amp
        amp *= persistence
        freq *= lacunarity
    return total / max_amp if max_amp else 0.0


def pnoise1(
    x: float,
    octaves: int = 1,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    repeat: int = 1024,
    base: int = 0,
) -> float:
    """1-D Perlin noise in roughly [-1, 1]. Signature matches `noise.pnoise1`."""
    return _fbm(lambda f: _perlin1(x * f, repeat, base), octaves, persistence, lacunarity)


def _grad2(h: int, x: float, y: float) -> float:
    h &= 3
    if h == 0:
        return x + y
    if h == 1:
        return -x + y
    if h == 2:
        return x - y
    return -x - y


def _perlin2(x: float, y: float, base: int) -> float:
    xi, yi = int(math.floor(x)) & 255, int(math.floor(y)) & 255
    xf, yf = x - math.floor(x), y - math.floor(y)
    u, v = _fade(xf), _fade(yf)
    b = base & 255
    aa = _PERM[_PERM[xi + b] + yi]
    ab = _PERM[_PERM[xi + b] + yi + 1]
    ba = _PERM[_PERM[xi + 1 + b] + yi]
    bb = _PERM[_PERM[xi + 1 + b] + yi + 1]
    x1 = _lerp(_grad2(aa, xf, yf), _grad2(ba, xf - 1, yf), u)
    x2 = _lerp(_grad2(ab, xf, yf - 1), _grad2(bb, xf - 1, yf - 1), u)
    return _lerp(x1, x2, v)


def pnoise2(
    x: float,
    y: float,
    octaves: int = 1,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    repeatx: int = 1024,
    repeaty: int = 1024,
    base: int = 0,
) -> float:
    """2-D Perlin noise. `repeatx`/`repeaty` are accepted but not tiled."""
    return _fbm(lambda f: _perlin2(x * f, y * f, base), octaves, persistence, lacunarity)


def pnoise3(
    x: float,
    y: float,
    z: float,
    octaves: int = 1,
    persistence: float = 0.5,
    lacunarity: float = 2.0,
    repeatx: int = 1024,
    repeaty: int = 1024,
    repeatz: int = 1024,
    base: int = 0,
) -> float:
    """3-D noise approximated by averaging orthogonal 2-D slices.

    Not true 3-D Perlin. Adequate for decorative jitter; do not rely on it for
    anything that needs exact gradient continuity along z.
    """
    return _fbm(
        lambda f: (_perlin2(x * f, y * f, base) + _perlin2(y * f, z * f, base + 31)) * 0.5,
        octaves,
        persistence,
        lacunarity,
    )
