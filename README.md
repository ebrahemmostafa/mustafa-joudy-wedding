# Wedding invitation

A single-page wedding invitation in emerald and gold that mixes two templates: the envelope and photobooth from one, and the scratch-to-reveal date, menu frame and dress code from the other.

**Flow:** tap the envelope to open it → a background video of the couple walking hand in hand reveals the names → the gold photobooth prints a photo strip → scratch the gold disc to reveal the date (with countdown and add-to-calendar) → venue → programme → dress code → RSVP, saved to Supabase (guest list at `rsvp.html`).

## Edit the content

All text, the date, venue, programme and the Supabase keys are in [`config.js`](config.js).

- **Photobooth strip:** `python tools/make_booth.py` renders the three shots (names, date, time + venue) from `config.js` into `assets/photos/`. To use your own photos instead, put up to 3 images in `assets/photos/` and list them in `photos` in `config.js`. They print in black and white.
- **Initials on the envelope:** the envelope image and opening video are rendered with your initials:

  ```bash
  python tools/personalize_envelope.py --initials "M&J"
  python tools/personalize_envelope.py --initials "M&J" --photo tools/source/flow/oval-rings.jpg   # a photo in the oval (plain emerald velvet without --photo)
  ```

  Needs Python with `opencv-python`, `numpy`, `pillow`, and `ffmpeg` on the PATH.
- **RSVPs (Supabase):** replies are saved to the Supabase project `mustafa-joudy-wedding-rsvp`; its URL and publishable key are in `config.js`, and the table, access rules and functions are in [`supabase/rsvp.sql`](supabase/rsvp.sql). Guests can only add a reply. To read them, set a passcode (6+ characters) once in the Supabase SQL editor, then open `rsvp.html` and enter it. After 5 wrong tries from one device, or 20 overall, the list locks for 15 minutes; setting the passcode again clears the lock.

  ```sql
  select public.set_rsvp_passcode('your passcode');
  ```

- **Colours:** `python tools/recolor.py` rebuilds the emerald velvet, gold photobooth, gold scratch disc and green line art from the originals in `tools/source/`.
- **Share card + link preview:** after editing `config.js`, rebuild the image you send on WhatsApp (`assets/images/share-card.png`) and the link preview (`assets/images/og-card.jpg`):

  ```bash
  python tools/make_card.py
  ```

## Run locally

```bash
python -m http.server 8000
```

Then open http://localhost:8000.

## Publish

It is a static site, so it can be hosted anywhere. On GitHub Pages: repo **Settings → Pages → Deploy from branch → `main` / root**.
