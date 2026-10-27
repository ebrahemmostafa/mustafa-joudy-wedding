"""Recolour the shared assets to the emerald & gold palette.

  python tools/recolor.py

Reads the originals in tools/source/ and writes into assets/images/.
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source")
OUT = os.path.join(HERE, "..", "assets", "images")

EMERALD = np.array([15, 59, 46], np.float32)
INK = np.array([23, 70, 52], np.float32)
# gradient map stops for antique gold: shadow, body, highlight
GOLD = [(0.0, (38, 28, 12)), (0.45, (150, 116, 58)), (0.75, (208, 176, 110)), (1.0, (252, 240, 205))]


def lum(a):
    return a[..., 0] * 0.299 + a[..., 1] * 0.587 + a[..., 2] * 0.114


def gradient_map(l, stops):
    """l in 0..1 -> RGB along the stops."""
    xs = np.array([s[0] for s in stops], np.float32)
    out = np.zeros(l.shape + (3,), np.float32)
    for c in range(3):
        out[..., c] = np.interp(l, xs, np.array([s[1][c] for s in stops], np.float32))
    return out


def velvet_to_emerald(a, ref=None):
    l = lum(a)
    m = ref if ref is not None else l.mean()
    return np.clip(EMERALD[None, None] * (l / m)[..., None], 0, 255)


def metal_to_gold(a, strength=1.0):
    l = lum(a) / 255.0
    # stretch the plate's tonal range a little so the gold reads as metal, not paint
    l = np.clip((l - 0.08) / 0.84, 0, 1)
    g = gradient_map(l, GOLD)
    return a * (1 - strength) + g * strength


def save(arr, name, mode="RGB", alpha=None, quality=90):
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    if alpha is not None:
        img.putalpha(Image.fromarray(alpha))
    path = os.path.join(OUT, name)
    if name.endswith(".webp"):
        img.save(path, quality=quality, method=6)
    elif name.endswith(".jpg"):
        img.convert("RGB").save(path, quality=quality)
    else:
        img.save(path, optimize=True)
    print("wrote", name)


def main():
    # velvet tile
    v = np.asarray(Image.open(os.path.join(SRC, "velvet-tile.webp")).convert("RGB")).astype(np.float32)
    vref = lum(v).mean()
    save(velvet_to_emerald(v, vref), "velvet.webp")

    # photobooth: red velvet surround -> emerald, silver plate -> gold
    p = np.asarray(Image.open(os.path.join(SRC, "photobooth.webp")).convert("RGB")).astype(np.float32)
    r, g, b = p[..., 0], p[..., 1], p[..., 2]
    red = np.clip(((r - g) / (r + 1) - 0.25) / 0.2, 0, 1)  # 1 on velvet, 0 on neutral metal
    from PIL import ImageFilter
    red = np.asarray(Image.fromarray((red * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32) / 255
    vel = velvet_to_emerald(p, lum(p)[red > 0.9].mean())
    gold = metal_to_gold(p)
    save(vel * red[..., None] + gold * (1 - red[..., None]), "photobooth.webp", quality=88)

    # scratch disc: silver -> gold, keep alpha
    s = Image.open(os.path.join(SRC, "scratch-silver.png")).convert("RGBA")
    sa = np.asarray(s).astype(np.float32)
    save(metal_to_gold(sa[..., :3]), "scratch-gold.png", alpha=sa[..., 3].astype(np.uint8))

    # line art: keep alpha, paint in emerald ink
    for name, out in (("ribbon-frame.png", "ribbon-frame.png"), ("venue.webp", "venue.webp")):
        im = np.asarray(Image.open(os.path.join(SRC, name)).convert("RGBA")).astype(np.float32)
        l = lum(im[..., :3]) / 255.0
        # darker strokes stay darker, so the drawing keeps its weight
        col = INK[None, None] * (0.75 + 0.6 * l[..., None])
        save(col, out, alpha=im[..., 3].astype(np.uint8))


if __name__ == "__main__":
    main()
