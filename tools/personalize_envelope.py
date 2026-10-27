"""Rebuild the envelope still + opening video with your own medallion.

  python personalize_envelope.py --initials "Y&M" --photo us.jpg  # your photo (black & white) in the oval
  python personalize_envelope.py --initials "Y&M"                 # plain emerald velvet in the oval

Needs envelope_ellipses.json (from track_envelope.py + refine_envelope.py).
Writes ../assets/images/envelope.jpg and ../assets/video/envelope-open.mp4
"""
import argparse, json, os, subprocess, sys
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from recolor import metal_to_gold  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
SRC = os.path.join(HERE, "source", "envelope-open-original.mp4")
STILL = os.path.join(HERE, "source", "envelope-original.jpg")
VELVET = os.path.join(ROOT, "assets", "images", "velvet.webp")
SCRIPT_FONT = os.path.join(HERE, "fonts", "GreatVibes-Regular.ttf")

# engraving block relative to the oval, measured on the still
ENG_DY = 1.325   # centre offset below oval centre, in oval half-heights
ENG_W = 0.80     # half width, in oval half-widths
ENG_H = 0.27     # half height, in oval half-heights


def load_ellipses():
    d = json.load(open(os.path.join(HERE, "envelope_ellipses.json")))
    raw = d["raw"]
    n = len(raw)
    arr = np.array([r if r else [np.nan] * 5 for r in raw], np.float64)
    t = np.arange(n)
    for j in range(4):
        m = ~np.isnan(arr[:, j])
        arr[:, j] = np.interp(t, t[m], arr[m, j])
    # light smoothing of size only; position follows the (stepwise) footage
    for j in (2, 3):
        arr[:, j] = np.convolve(np.pad(arr[:, j], 2, mode="edge"), np.ones(5) / 5, mode="valid")
    arr[:, 4] = 0.0
    return arr, d["still"]


def cover(img, w, h):
    ih, iw = img.shape[:2]
    s = max(w / iw, h / ih)
    r = cv2.resize(img, (max(w, int(iw * s + 0.5)), max(h, int(ih * s + 0.5))), interpolation=cv2.INTER_AREA)
    y = (r.shape[0] - h) // 2
    x = (r.shape[1] - w) // 2
    return r[y:y + h, x:x + w]


def oval_content(photo, w=600, h=900):
    """Content for the oval at a fixed master size (later resized per frame)."""
    if photo:
        img = cv2.imread(photo)
        g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        g = cv2.createCLAHE(clipLimit=1.6, tileGridSize=(4, 4)).apply(g)
        out = cv2.cvtColor(cover(g, w, h), cv2.COLOR_GRAY2BGR).astype(np.float32)
        # faint warm-silver tone like the original print
        out *= np.array([0.97, 0.99, 1.02], np.float32)
        return np.clip(out, 0, 255).astype(np.uint8)
    tile = cv2.imread(VELVET)
    reps = (h // tile.shape[0] + 2, w // tile.shape[1] + 2, 1)
    vel = np.tile(tile, reps)[:h, :w].astype(np.float32)
    # radial pile sheen
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w * 0.45) / w) ** 2 + ((yy - h * 0.4) / h) ** 2)
    vel *= (1.25 - 0.9 * r)[..., None]
    return np.clip(vel, 0, 255).astype(np.uint8)


def paste_oval(frame, e, content, gain):
    cx, cy, a, b, _ = e
    a2, b2 = a + 3, b + 0.5  # tuck under the rim (thin at the bottom)
    x0, y0 = int(cx - a2) - 2, int(cy - b2) - 2
    w, h = int(2 * a2) + 4, int(2 * b2) + 4
    H, W = frame.shape[:2]
    c = cv2.resize(content, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) * gain
    mask = np.zeros((h, w), np.float32)
    cv2.ellipse(mask, (int(cx - x0), int(cy - y0)), (int(a2), int(b2)), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
    # recessed look: soft shadow cast by the rim at the top
    yy = (np.arange(h)[:, None] - (cy - y0)) / b2
    xx = (np.arange(w)[None, :] - (cx - x0)) / a2
    rr = np.sqrt(xx ** 2 + yy ** 2)
    inner = np.clip((rr - 0.86) / 0.14, 0, 1) * np.clip(0.6 - 0.5 * yy, 0, 1)
    c *= (1 - 0.45 * inner)[..., None]
    sx0, sy0 = max(0, -x0), max(0, -y0)
    dx0, dy0 = max(0, x0), max(0, y0)
    ww, hh = min(w - sx0, W - dx0), min(h - sy0, H - dy0)
    if ww <= 0 or hh <= 0:
        return
    m = mask[sy0:sy0 + hh, sx0:sx0 + ww, None]
    roi = frame[dy0:dy0 + hh, dx0:dx0 + ww].astype(np.float32)
    frame[dy0:dy0 + hh, dx0:dx0 + ww] = np.clip(roi * (1 - m) + c[sy0:sy0 + hh, sx0:sx0 + ww] * m, 0, 255).astype(np.uint8)


def text_mask(text, w, h):
    """Script initials as a float mask, fitted inside w x h."""
    size = int(h * 1.6)
    while True:
        font = ImageFont.truetype(SCRIPT_FONT, size)
        bb = ImageDraw.Draw(Image.new("L", (10, 10))).textbbox((0, 0), text, font=font)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if tw <= w * 0.92 and th <= h * 0.92:
            break
        size -= 2
    im = Image.new("L", (w, h), 0)
    ImageDraw.Draw(im).text(((w - tw) / 2 - bb[0], (h - th) / 2 - bb[1]), text, font=font, fill=255)
    return np.array(im).astype(np.float32) / 255.0


def hipass(g):
    g = g.astype(np.float32)
    return g - cv2.GaussianBlur(g, (0, 0), 6)


def engrave_ref(frame, e):
    """Locate the original engraving on the first frame and capture its strokes."""
    cx, cy, a, b, _ = e
    ecx, ecy = cx, cy + ENG_DY * b
    hw, hh = ENG_W * a, ENG_H * b
    x0, x1, y0, y1 = int(ecx - hw), int(ecx + hw), int(ecy - hh), int(ecy + hh)
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    patch = g[y0:y1, x0:x1]
    dev = cv2.absdiff(patch, cv2.medianBlur(patch, 41))
    m = (dev > 5).astype(np.uint8) * 255
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    return {"e": e, "box": (x0, y0, x1, y1), "tpl": hipass(patch), "mask": m}


def engrave(frame, e, ref, text):
    e0 = ref["e"]
    bx0, by0, bx1, by1 = ref["box"]
    sx = e[2] / e0[2]
    sy0 = e[3] / e0[3]
    H, W = frame.shape[:2]
    g = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    # predicted box, then find the old engraving around it
    pcx = e[0] + ((bx0 + bx1) / 2 - e0[0]) * sx
    pcy = e[1] + ((by0 + by1) / 2 - e0[1]) * sy0
    bw, bh0 = (bx1 - bx0), (by1 - by0)
    best = None
    for k in np.linspace(0.8, 1.2, 9):
        sy = sy0 * k
        tw, th = max(8, int(bw * sx)), max(8, int(bh0 * sy))
        tpl = cv2.resize(ref["tpl"], (tw, th), interpolation=cv2.INTER_AREA)
        X0, X1 = int(pcx - tw / 2 - 24), int(pcx + tw / 2 + 24)
        Y0, Y1 = int(pcy - th / 2 - th * 0.7), int(pcy + th / 2 + th * 0.7)
        X0, Y0, X1, Y1 = max(0, X0), max(0, Y0), min(W, X1), min(H, Y1)
        if X1 - X0 <= tw or Y1 - Y0 <= th:
            continue
        r = cv2.matchTemplate(hipass(g[Y0:Y1, X0:X1]), tpl, cv2.TM_CCOEFF_NORMED)
        _, mv, _, ml = cv2.minMaxLoc(r)
        if best is None or mv > best[0]:
            best = (mv, X0 + ml[0], Y0 + ml[1], tw, th)
    if best is None:
        return
    _, x0, y0, tw, th = best
    x1, y1 = x0 + tw, y0 + th
    pad = 16
    X0, Y0, X1, Y1 = max(0, x0 - pad), max(0, y0 - pad), min(W, x1 + pad), min(H, y1 + pad)
    patch = frame[Y0:Y1, X0:X1]
    m = np.zeros(patch.shape[:2], np.uint8)
    wm = cv2.resize(ref["mask"], (tw, th), interpolation=cv2.INTER_NEAREST)
    ys, xs = y0 - Y0, x0 - X0
    hh_, ww_ = min(th, m.shape[0] - ys), min(tw, m.shape[1] - xs)
    m[ys:ys + hh_, xs:xs + ww_] = wm[:hh_, :ww_]
    m = cv2.dilate(m, np.ones((5, 5), np.uint8), iterations=3)
    # lighting from a smooth fill, grain from clean flap paper above the oval
    smooth = cv2.GaussianBlur(cv2.inpaint(patch, m, 9, cv2.INPAINT_TELEA).astype(np.float32), (0, 0), 3)
    grain = paper_grain(e, e0, patch.shape[1], patch.shape[0])
    fill = smooth + grain[..., None]
    mf = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 2.5)[..., None]
    clean = patch.astype(np.float32) * (1 - mf) + fill * mf
    # new initials, embossed like the original
    tm = np.zeros(patch.shape[:2], np.float32)
    txt = text_mask(text, tw, th)
    tm[ys:ys + hh_, xs:xs + ww_] = txt[:hh_, :ww_]
    hgt = cv2.GaussianBlur(tm, (0, 0), 1.1)
    gx = cv2.Sobel(hgt, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(hgt, cv2.CV_32F, 0, 1, ksize=3)
    lit = -(gx + gy) * 0.7071
    out = clean * (1 + 0.06 * tm[..., None])
    out = out + np.clip(lit, 0, None)[..., None] * 120 - np.clip(-lit, 0, None)[..., None] * out * 0.5
    frame[Y0:Y1, X0:X1] = np.clip(out, 0, 255).astype(np.uint8)


_GRAIN = {}


def paper_grain(e, e0, w, h):
    """High-frequency paper fibre texture from the still, scaled to the current frame."""
    if "src" not in _GRAIN:
        st = cv2.cvtColor(cv2.imread(STILL), cv2.COLOR_BGR2GRAY).astype(np.float32)
        band = st[300:520, 400:700]  # clean flap paper above the oval
        _GRAIN["src"] = band - cv2.GaussianBlur(band, (0, 0), 4)
    src = _GRAIN["src"]
    sx, sy = e[2] / e0[2], e[3] / e0[3]
    tex = cv2.resize(src, None, fx=sx, fy=sy, interpolation=cv2.INTER_LINEAR)
    reps = (h // tex.shape[0] + 1, w // tex.shape[1] + 1)
    return np.tile(tex, reps)[:h, :w]


def gild(frame, strength):
    """Tint the silver envelope towards antique gold (BGR in, BGR out)."""
    if strength <= 0:
        return frame
    rgb = frame[..., ::-1].astype(np.float32)
    g = metal_to_gold(rgb, strength)
    # keep it a soft champagne, not brass: lift the shadows back towards the paper
    g = g * 0.85 + rgb * 0.15 + 6
    return np.clip(g[..., ::-1], 0, 255).astype(np.uint8)


def paper_level(frame, e):
    cx, cy, a, b, _ = e
    x0, x1 = int(cx + a * 1.15), int(cx + a * 1.5)
    y0, y1 = int(cy - b * 0.4), int(cy + b * 0.4)
    H, W = frame.shape[:2]
    y0, y1 = max(0, y0), min(H, y1)
    if y1 - y0 < 10:
        return None
    return float(frame[y0:y1, x0:x1].mean())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--initials", default="Y&M")
    ap.add_argument("--photo", default=None)
    ap.add_argument("--still-only", action="store_true")
    ap.add_argument("--gold", type=float, default=0.62, help="how strongly the silver paper turns gold (0 keeps silver)")
    args = ap.parse_args()

    ells, still_e = load_ellipses()
    content = oval_content(args.photo)

    # still
    st = cv2.imread(STILL)
    sref = engrave_ref(st, still_e)
    st = gild(st, args.gold)
    paste_oval(st, still_e, content, 1.0)
    engrave(st, still_e, sref, args.initials)
    os.makedirs(os.path.join(ROOT, "assets", "images"), exist_ok=True)
    cv2.imwrite(os.path.join(ROOT, "assets", "images", "envelope.jpg"), st, [cv2.IMWRITE_JPEG_QUALITY, 88])
    if args.still_only:
        return

    # video
    cap = cv2.VideoCapture(SRC)
    W = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)); H = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    os.makedirs(os.path.join(ROOT, "assets", "video"), exist_ok=True)
    out = os.path.join(ROOT, "assets", "video", "envelope-open.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}",
                           "-r", "24", "-i", "-", "-c:v", "libx264", "-crf", "21", "-preset", "slow",
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", out], stdin=subprocess.PIPE)
    base = None
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        e = ells[i]
        lvl = paper_level(f, e)
        if base is None:
            base = lvl
            vref = engrave_ref(f, e)
        f = gild(f, args.gold)
        gain = (lvl / base) if (lvl and base) else 1.0
        paste_oval(f, e, content, min(1.25, max(0.8, gain)))
        engrave(f, e, vref, args.initials)
        ff.stdin.write(f.tobytes())
        i += 1
    ff.stdin.close(); ff.wait()
    print("wrote", out, i, "frames")


if __name__ == "__main__":
    main()
