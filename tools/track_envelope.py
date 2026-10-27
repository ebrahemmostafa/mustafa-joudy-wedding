"""Track the oval medallion on the envelope flap through envelope-open.mp4.

Writes tools/envelope_track.json: per-frame [sx, sy, tx, ty] mapping frame-0
coordinates to frame-t coordinates (x' = sx*x + tx, y' = sy*y + ty).
Run once; personalize_envelope.py reuses the track.
"""
import json, os, subprocess, sys
import cv2
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source", "envelope-open-original.mp4")

# medallion (rim + engraving) in frame-0 pixel coords
X0, Y0, X1, Y1 = 360, 500, 725, 1140


def frames(path):
    cap = cv2.VideoCapture(path)
    while True:
        ok, f = cap.read()
        if not ok:
            break
        yield f
    cap.release()


def edges(g):
    g = cv2.GaussianBlur(g, (5, 5), 0)
    gx = cv2.Sobel(g, cv2.CV_32F, 1, 0)
    gy = cv2.Sobel(g, cv2.CV_32F, 0, 1)
    return cv2.magnitude(gx, gy)


def main():
    fs = list(frames(SRC))
    pad = 700
    g0 = cv2.cvtColor(fs[0], cv2.COLOR_BGR2GRAY)
    tpl_full = edges(g0)[Y0:Y1, X0:X1]
    track = []
    prev = (1.0, 1.0, 0.0, 0.0)
    for i, f in enumerate(fs):
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        g = cv2.copyMakeBorder(g, pad, 0, 0, 0, cv2.BORDER_REPLICATE)
        e = edges(g)
        best = None
        psy = prev[1]
        for sy in np.arange(max(0.45, psy - 0.12), min(1.06, psy + 0.06), 0.01):
            for sx in (0.97, 0.985, 1.0, 1.015):
                tpl = cv2.resize(tpl_full, None, fx=sx, fy=sy, interpolation=cv2.INTER_AREA)
                # search near previous position
                py = int(prev[1] * Y0 + prev[3]) + pad
                px = int(prev[0] * X0 + prev[2])
                ys, ye = max(0, py - 160), min(e.shape[0], py + 60 + tpl.shape[0])
                xs, xe = max(0, px - 60), min(e.shape[1], px + 60 + tpl.shape[1])
                roi = e[ys:ye, xs:xe]
                if roi.shape[0] < tpl.shape[0] or roi.shape[1] < tpl.shape[1]:
                    continue
                r = cv2.matchTemplate(roi, tpl, cv2.TM_CCOEFF_NORMED)
                _, mv, _, ml = cv2.minMaxLoc(r)
                if best is None or mv > best[0]:
                    x = ml[0] + xs
                    y = ml[1] + ys - pad
                    best = (mv, sx, sy, x - sx * X0, y - sy * Y0)
        mv, sx, sy, tx, ty = best
        prev = (sx, sy, tx, ty)
        track.append([float(sx), float(sy), float(tx), float(ty), float(mv)])
        print(i, round(mv, 3), round(sx, 3), round(sy, 3), round(tx, 1), round(ty, 1))
    with open(os.path.join(HERE, "envelope_track.json"), "w") as fh:
        json.dump(track, fh)


if __name__ == "__main__":
    main()
