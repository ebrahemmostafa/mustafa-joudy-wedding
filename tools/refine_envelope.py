"""Refine the medallion track: fit the photo oval directly in every frame.

Reads envelope_track.json (coarse template track) and writes
envelope_ellipses.json: per-frame [cx, cy, a, b, angle] of the photo oval,
smoothed over time. Also writes the same for the still image (index "still").
"""
import json, os
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source", "envelope-open-original.mp4")
STILL = os.path.join(HERE, "source", "envelope-original.jpg")

C0 = (543.0, 760.0)
A0 = (145.0, 218.0)


def fit_oval(img, c, a, b):
    g = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0).astype(np.float32)
    h, w = g.shape
    pts = []
    for th in np.linspace(0, 2 * np.pi, 180, endpoint=False):
        dx, dy = np.cos(th), np.sin(th)
        rs = np.linspace(0.8, 1.18, 60)
        xs = c[0] + rs * a * dx
        ys = c[1] + rs * b * dy
        ok = (xs >= 1) & (xs < w - 1) & (ys >= 1) & (ys < h - 1)
        if ok.sum() < 50:
            continue
        prof = cv2.remap(g, xs.astype(np.float32).reshape(1, -1), ys.astype(np.float32).reshape(1, -1), cv2.INTER_LINEAR)[0]
        d = np.diff(prof)
        k = int(np.argmax(d))
        if d[k] < 6:  # no clear dark->bright step (veil, glare)
            continue
        pts.append((xs[k], ys[k]))
    pts = np.array(pts, np.float32)
    if len(pts) < 30:
        return None
    for _ in range(3):
        (cx, cy), (ma, mb), ang = cv2.fitEllipse(pts)
        e = ((pts[:, 0] - cx) / (ma / 2)) ** 2 + ((pts[:, 1] - cy) / (mb / 2)) ** 2  # angle ~0
        res = np.abs(np.sqrt(e) - 1)
        keep = res < np.percentile(res, 75)
        pts = pts[keep]
    (cx, cy), (ma, mb), ang = cv2.fitEllipse(pts)
    if ang > 90:
        ang -= 180
    return [cx, cy, ma / 2, mb / 2, ang]


def main():
    track = json.load(open(os.path.join(HERE, "envelope_track.json")))
    cap = cv2.VideoCapture(SRC)
    raw = []
    i = 0
    while True:
        ok, f = cap.read()
        if not ok:
            break
        sx, sy, tx, ty, _ = track[i]
        c = (sx * C0[0] + tx, sy * C0[1] + ty)
        e = fit_oval(f, c, A0[0] * sx, A0[1] * sy)
        raw.append(e)
        i += 1
    # fill gaps, then smooth each parameter with a low-order fit in time
    n = len(raw)
    arr = np.array([r if r else [np.nan] * 5 for r in raw], np.float64)
    t = np.arange(n)
    out = np.zeros_like(arr)
    for j in range(5):
        m = ~np.isnan(arr[:, j])
        # robust polynomial fit (degree 5) on valid samples
        p = np.polyfit(t[m], arr[m, j], 5)
        fit = np.polyval(p, t)
        r = np.abs(arr[:, j] - fit)
        good = m & (r < np.nanpercentile(r, 85) + 1e-6)
        p = np.polyfit(t[good], arr[good, j], 5)
        out[:, j] = np.polyval(p, t)
    still = fit_oval(cv2.imread(STILL), C0, *A0)
    json.dump({"frames": out.tolist(), "raw": [r for r in raw], "still": still},
              open(os.path.join(HERE, "envelope_ellipses.json"), "w"))
    for k in range(0, n, 6):
        print(k, [round(v, 1) for v in out[k]], raw[k] and [round(v, 1) for v in raw[k]])
    print("still", still)


if __name__ == "__main__":
    main()
