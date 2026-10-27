"""Render the three photobooth shots (names, date, evening) from config.js.

  python tools/make_booth.py

Each shot is lettering lit over a soft, out-of-focus Flow photo, so the strip
still reads as photographs once it prints in black and white.
Writes assets/photos/names.jpg, date.jpg and evening.jpg (1200x900).
"""
import json, os, subprocess
from datetime import datetime
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
OUT = os.path.join(ROOT, "assets", "photos")
FLOW = os.path.join(HERE, "source", "flow")
F = os.path.join(HERE, "fonts")

W, H = 1200, 900
S = 2  # supersample the lettering
LIGHT = (246, 238, 222)


def config():
    js = "global.window={};require(process.argv[1]);console.log(JSON.stringify(window.INVITE))"
    out = subprocess.check_output(["node", "-e", js, os.path.join(ROOT, "config.js")])
    return json.loads(out)


def font(name, size, wght=None):
    f = ImageFont.truetype(os.path.join(F, name), size)
    if wght:
        try:
            f.set_variation_by_axes([wght])
        except Exception:
            pass
    return f


def backdrop(src, shift=(0.5, 0.5)):
    """The Flow photo, deep out of focus and pulled down so the lettering carries the frame."""
    img = Image.open(os.path.join(FLOW, src)).convert("L")
    s = max(W / img.width, H / img.height)
    img = img.resize((int(img.width * s + .5), int(img.height * s + .5)), Image.LANCZOS)
    x = int((img.width - W) * shift[0])
    y = int((img.height - H) * shift[1])
    img = img.crop((x, y, x + W, y + H)).filter(ImageFilter.GaussianBlur(26))
    a = np.asarray(img).astype(np.float32)
    a = 18 + a * 0.42
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H / 2) / H) ** 2)
    a *= np.clip(1.25 - 1.3 * r, .35, 1.1)
    return a


def lettering(lines):
    """lines: [(text, font, y_centre)] at supersampled size -> alpha mask at W x H."""
    m = Image.new("L", (W * S, H * S), 0)
    d = ImageDraw.Draw(m)
    for text, f, cy in lines:
        l, t, r, b = d.textbbox((0, 0), text, font=f)
        d.text(((W * S - (r - l)) / 2 - l, cy * S - (t + b) / 2), text, font=f, fill=255)
    return np.asarray(m.resize((W, H), Image.LANCZOS)).astype(np.float32) / 255


def compose(bg, mask, rule_y=None):
    glow = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(18))).astype(np.float32) / 255
    shadow = np.asarray(Image.fromarray((mask * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(5))).astype(np.float32) / 255
    shadow = np.roll(shadow, (5, 4), axis=(0, 1))
    a = bg * (1 - 0.55 * shadow) + 70 * glow
    rgb = np.repeat(a[..., None], 3, axis=2)
    rgb = rgb * (1 - mask[..., None]) + np.array(LIGHT, np.float32) * mask[..., None]
    if rule_y is not None:  # a hairline with a small diamond, like the paper sections
        im = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        cx, half = W // 2, 150
        d.line((cx - half, rule_y, cx - 18, rule_y), fill=(200, 192, 176), width=2)
        d.line((cx + 18, rule_y, cx + half, rule_y), fill=(200, 192, 176), width=2)
        d.polygon([(cx, rule_y - 8), (cx + 8, rule_y), (cx, rule_y + 8), (cx - 8, rule_y)], fill=LIGHT)
        rgb = np.asarray(im).astype(np.float32)
    rng = np.random.default_rng(11)
    rgb += rng.normal(0, 7, (H, W, 1))  # film grain
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8))


def main():
    c = config()
    when = datetime.fromisoformat(c["date"])
    one, two = c["couple"]["one"], c["couple"]["two"]
    script = lambda px: font("GreatVibes-Regular.ttf", px * S)
    sc = lambda px: font("CormorantSC-Medium.ttf", px * S)
    serif = lambda px, w=500: font("CormorantGaramond[wght].ttf", px * S, w)

    # 1 · the names
    m = lettering([(one, script(250), 300), ("& " + two, script(250), 600)])
    compose(backdrop("veilA.jpg", (.5, .35)), m).save(os.path.join(OUT, "names.jpg"), quality=90)

    # 2 · the date
    m = lettering([
        (f"{when.day:02d} · {when.month:02d}", serif(330, 400), 360),
        (str(when.year), sc(170), 690),
    ])
    compose(backdrop("champA.jpg"), m, rule_y=560).save(os.path.join(OUT, "date.jpg"), quality=90)

    # 3 · the evening: start time over the venue's short name
    hour = when.strftime("%I").lstrip("0") + (f":{when.minute:02d}" if when.minute else "")
    place = c["venue"]["name"].split()[-1]
    m = lettering([(f"{hour} {when.strftime('%p')}", sc(270), 340), (place, script(210), 670)])
    compose(backdrop("handsA.jpg"), m, rule_y=520).save(os.path.join(OUT, "evening.jpg"), quality=90)
    print("wrote names.jpg, date.jpg, evening.jpg")


if __name__ == "__main__":
    main()
