"""Render the shareable invitation card from config.js.

  python tools/make_card.py

Writes assets/images/share-card.png (1080x1350, to send as an image)
and assets/images/og-card.jpg (1200x630, the WhatsApp/link preview).
"""
import json, os, subprocess
from datetime import datetime, timedelta, timezone
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
IMG = os.path.join(ROOT, "assets", "images")
F = os.path.join(HERE, "fonts")

S = 2  # supersample
W, H = 1080 * S, 1350 * S
IVORY = (247, 241, 230)
EMERALD = (23, 70, 52)
INK = (31, 58, 48)
GOLD_TXT = (138, 109, 54)
GOLD_LINE = (201, 169, 97)
MUTED = (86, 103, 94)


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


def velvet(w, h):
    tile = Image.open(os.path.join(IMG, "velvet.webp")).convert("RGB")
    tile = tile.resize((tile.width * S, tile.height * S), Image.LANCZOS)
    bg = Image.new("RGB", (w, h))
    for y in range(0, h, tile.height):
        for x in range(0, w, tile.width):
            bg.paste(tile, (x, y))
    a = np.asarray(bg).astype(np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.sqrt(((xx - w / 2) / w) ** 2 + ((yy - h * .45) / h) ** 2)
    a *= np.clip(1.15 - 1.1 * r, .45, 1.1)[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def paper(w, h):
    rng = np.random.default_rng(7)
    n = rng.normal(0, 1, (h // 2, w // 2)).astype(np.float32)
    n = np.asarray(Image.fromarray(((n * 18) + 128).clip(0, 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) - 128
    base = np.ones((h, w, 3), np.float32) * np.array(IVORY, np.float32)
    base += n[..., None] * np.array([.10, .09, .08])
    return base


def arch(card, w, h):
    """The floral arch, fitted to the card height and centred, multiplied onto the ivory."""
    art = Image.open(os.path.join(IMG, "floral-arch.jpg")).convert("RGB")
    aw = int(art.width * h / art.height)
    art = np.asarray(art.resize((aw, h), Image.LANCZOS)).astype(np.float32) / 255
    layer = np.ones((h, w, 3), np.float32)
    x0 = (w - aw) // 2
    layer[:, x0:x0 + aw] = art
    return card * layer, x0, aw


def centered(d, cx, y, text, f, fill, spacing=0):
    if spacing:
        widths = [d.textlength(ch, font=f) for ch in text]
        total = sum(widths) + spacing * (len(text) - 1)
        x = cx - total / 2
        for ch, w_ in zip(text, widths):
            d.text((x, y), ch, font=f, fill=fill)
            x += w_ + spacing
        return
    w_ = d.textlength(text, font=f)
    d.text((cx - w_ / 2, y), text, font=f, fill=fill)


def main():
    c = config()
    when = datetime.fromisoformat(c["date"])
    one, two = c["couple"]["one"], c["couple"]["two"]

    img = velvet(W, H)
    # card
    m = 84 * S
    cw, ch = W - 2 * m, H - 2 * m
    card, ax, aw = arch(paper(cw, ch), cw, ch)
    card_img = Image.fromarray(np.clip(card, 0, 255).astype(np.uint8))
    shadow = Image.new("L", (W, H), 0)
    ImageDraw.Draw(shadow).rectangle((m, m + 14 * S, m + cw, m + ch + 14 * S), fill=170)
    shadow = shadow.filter(ImageFilter.GaussianBlur(28 * S))
    img = Image.composite(Image.new("RGB", (W, H), (3, 18, 13)), img, shadow)
    img.paste(card_img, (m, m))
    d = ImageDraw.Draw(img)
    # gold double rule around the card
    d.rectangle((m, m, m + cw - 1, m + ch - 1), outline=GOLD_LINE, width=2 * S)
    i = 14 * S
    d.rectangle((m + i, m + i, m + cw - 1 - i, m + ch - 1 - i), outline=GOLD_LINE, width=S)

    cx = W / 2
    Y = lambda f: m + int(ch * f)  # positions as a fraction of the card height (follows the arch)

    serif_i = font("CormorantGaramond-Italic[wght].ttf", 26 * S, 400)
    serif = font("CormorantGaramond[wght].ttf", 26 * S, 400)
    serif_m = font("CormorantGaramond[wght].ttf", 24 * S, 500)
    sc = font("CormorantSC-Medium.ttf", 20 * S)
    script = font("GreatVibes-Regular.ttf", 92 * S)
    amp = font("GreatVibes-Regular.ttf", 44 * S)

    centered(d, cx, Y(.300), c["hero"]["above"], serif_i, INK)
    centered(d, cx, Y(.322), one, script, EMERALD)
    centered(d, cx, Y(.402), "&", amp, GOLD_TXT)
    centered(d, cx, Y(.428), two, script, EMERALD)
    centered(d, cx, Y(.532), c["hero"]["below"], serif, INK)

    # hairline with a centre knot
    ky = Y(.585)
    d.line((cx - 56 * S, ky, cx - 10 * S, ky), fill=GOLD_LINE, width=S)
    d.line((cx + 10 * S, ky, cx + 56 * S, ky), fill=GOLD_LINE, width=S)
    d.ellipse((cx - 3.5 * S, ky - 3.5 * S, cx + 3.5 * S, ky + 3.5 * S), fill=GOLD_TXT)

    date_line = f"{when.strftime('%A')} {when.day} {when.strftime('%B')} {when.year}"
    time_line = when.strftime("%I:%M %p").lstrip("0")
    centered(d, cx, Y(.603), date_line, sc, EMERALD, spacing=2 * S)
    centered(d, cx, Y(.632), time_line, sc, GOLD_TXT, spacing=2 * S)
    # long venue names shrink to stay clear of the flowers
    size = 24
    while size > 16 and d.textlength(c["venue"]["name"], font=serif_m) > 290 * S:
        size -= 1
        serif_m = font("CormorantGaramond[wght].ttf", size * S, 500)
    centered(d, cx, Y(.668) + (24 - size) * S // 2, c["venue"]["name"], serif_m, INK)
    city = c["venue"]["address"].split(",")[-1].strip()
    centered(d, cx, Y(.697), city, serif_i, MUTED)

    out = img.resize((W // S, H // S), Image.LANCZOS)
    out.save(os.path.join(IMG, "share-card.png"), optimize=True)

    # link preview: card on velvet, 1200x630
    og = velvet(1200 * S, 630 * S).resize((1200, 630), Image.LANCZOS)
    small = out.crop((84, 84, 1080 - 84, 1350 - 84))
    small = small.resize((int(small.width * 590 / small.height), 590), Image.LANCZOS)
    og.paste(small, ((1200 - small.width) // 2, 20))
    og.save(os.path.join(IMG, "og-card.jpg"), quality=88)
    # favicon: gold initials on an emerald disc
    fs = 256
    fav = Image.new("RGBA", (fs, fs), (0, 0, 0, 0))
    fd = ImageDraw.Draw(fav)
    fd.ellipse((4, 4, fs - 4, fs - 4), fill=(15, 59, 46, 255), outline=GOLD_LINE, width=8)
    mono = f"{one[0]}&{two[0]}"
    ff = font("GreatVibes-Regular.ttf", 120)
    bb = fd.textbbox((0, 0), mono, font=ff)
    fd.text(((fs - (bb[2] - bb[0])) / 2 - bb[0], (fs - (bb[3] - bb[1])) / 2 - bb[1]), mono, font=ff, fill=(240, 226, 182, 255))
    fav.resize((64, 64), Image.LANCZOS).save(os.path.join(IMG, "favicon.png"))
    print("wrote share-card.png, og-card.jpg and favicon.png")


if __name__ == "__main__":
    main()
