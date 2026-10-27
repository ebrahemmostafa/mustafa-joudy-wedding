(() => {
  const C = window.INVITE;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const TZ = C.timeZone || "Africa/Cairo";
  const when = new Date(C.date);

  const UI = {
      tapToOpen: "Tap to open",
      scroll: "Scroll",
      boothLine: "Three little frames, from us to you",
      print: "Print our photos",
      dateTitle: "Save the date",
      scratchHint: "Scratch the gold to reveal the date",
      days: "days", hours: "hours", mins: "minutes", secs: "seconds",
      addToCalendar: "Add to calendar",
      venueTitle: "The venue",
      openMap: "Open in Google Maps",
      programmeTitle: "The evening",
      dressTitle: "Dress code",
      rsvpTitle: "Will you join us?",
      rsvpBy: "Kindly reply by {date}",
      fName: "Your name",
      fNameError: "Write your name so we know who is coming.",
      fAttend: "Will you attend?",
      fYes: "Joyfully accepts",
      fNo: "Regretfully declines",
      fGuests: "Number of guests",
      fMessage: "A note for the couple (optional)",
      fSend: "Send reply on WhatsApp",
      fNote: "Your reply opens in WhatsApp, ready to send.",
      waTitle: "RSVP for {names}",
      waName: "Name", waAttend: "Attending", waYes: "Yes", waNo: "No", waGuests: "Guests", waMsg: "Message",
      calTitle: "Wedding of {names}",
  };

  const names = () => `${C.couple.one} & ${C.couple.two}`;

  function t(key) {
    if (UI[key] != null) return UI[key];
    if (key === "couple.joiner") return "&";
    return key.split(".").reduce((o, k) => (o == null ? "" : o[k]), C) || "";
  }

  const fmt = (opts, d = when) => new Intl.DateTimeFormat("en-GB", { timeZone: TZ, ...opts }).format(d);
  const num = (n, pad = 2) => new Intl.NumberFormat("en-GB", { minimumIntegerDigits: pad, useGrouping: false }).format(n);

  function timeOf(hhmm) {
    const day = C.date.slice(0, 10);
    return new Intl.DateTimeFormat("en-US", { timeZone: TZ, hour: "numeric", minute: "2-digit" }).format(new Date(`${day}T${hhmm}:00+02:00`));
  }

  /* ---------- text ---------- */
  function apply() {
    document.title = names();
    $$("[data-t]").forEach((el) => { el.textContent = t(el.dataset.t); });

    $("#dWeekday").textContent = fmt({ weekday: "long" });
    $("#dDay").textContent = fmt({ day: "numeric" });
    $("#dMonth").textContent = fmt({ month: "long" });
    $("#dYear").textContent = fmt({ year: "numeric" });

    $("#venueTime").textContent = fmt({ weekday: "long", day: "numeric", month: "long" }) + ", " + timeOf(C.date.slice(11, 16));
    $("#mapLink").href = C.venue.mapUrl;

    $("#programme").replaceChildren();
    C.programme.forEach((p) => {
      const li = document.createElement("li");
      const tm = document.createElement("time");
      tm.textContent = timeOf(p.time);
      const sp = document.createElement("span");
      sp.textContent = p.what;
      li.append(tm, sp);
      $("#programme").append(li);
    });

    const deadline = new Date(`${C.rsvp.deadline}T12:00:00+02:00`);
    $("#rsvpBy").textContent = t("rsvpBy").replace("{date}", fmt({ day: "numeric", month: "long" }, deadline));

    $(".strip__foot").textContent = new Intl.DateTimeFormat("en-GB", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "numeric" }).format(when).replace(/\//g, ".");
    $$(".strip__shot--mono").forEach((el) => { el.textContent = `${C.couple.one[0]}&${C.couple.two[0]}`; });
    $("#seal").textContent = `${C.couple.one[0]}&${C.couple.two[0]}`;
    $(".strip__shot--names") && ($(".strip__shot--names").textContent = names());

    $("#envelope").setAttribute("aria-label", t("tapToOpen"));
    buildCalendar();
    tick();
  }

  /* ---------- music ---------- */
  const music = $("#music");
  const soundBtn = $("#soundToggle");
  function startMusic() {
    music.volume = 0;
    music.play().then(() => {
      soundBtn.hidden = false;
      let v = 0;
      const fade = setInterval(() => { v = Math.min(0.55, v + 0.03); music.volume = v; if (v >= 0.55) clearInterval(fade); }, 120);
    }).catch(() => { soundBtn.hidden = false; soundBtn.classList.add("is-muted"); });
  }
  soundBtn.addEventListener("click", () => {
    if (music.paused) { music.play(); soundBtn.classList.remove("is-muted"); soundBtn.setAttribute("aria-label", "Mute music"); }
    else { music.pause(); soundBtn.classList.add("is-muted"); soundBtn.setAttribute("aria-label", "Play music"); }
  });

  /* ---------- 1 · envelope ---------- */
  const env = $("#envelope");
  const envVideo = $(".envelope__video");
  let opened = false;

  function openEnvelope() {
    if (opened) return;
    opened = true;
    startMusic();
    if (reduced) return finishEnvelope();
    env.classList.add("is-playing");
    envVideo.currentTime = 0;
    envVideo.play().catch(finishEnvelope);
    // start the fade a little before the flap leaves the frame
    envVideo.addEventListener("timeupdate", function watch() {
      if (envVideo.currentTime >= 2.0) {
        envVideo.removeEventListener("timeupdate", watch);
        finishEnvelope();
      }
    });
    setTimeout(finishEnvelope, 4500); // safety net if the video stalls
  }
  let finished = false;
  function finishEnvelope() {
    if (finished) return;
    finished = true;
    env.classList.add("is-fading");
    setTimeout(() => {
      document.body.classList.remove("is-sealed");
      window.scrollTo(0, 0);
      env.classList.add("is-gone");
      bloom();
    }, reduced ? 0 : 1000);
  }
  env.addEventListener("click", openEnvelope);
  env.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openEnvelope(); } });

  /* ---------- 2 · the couple walking ---------- */
  const stage = $("#stage");
  const walk = $(".stage__video");
  function bloom() {
    if (!reduced) walk.play().catch(() => {}); // reduced motion keeps the still poster
    requestAnimationFrame(() => requestAnimationFrame(() => stage.classList.add("is-bloomed")));
  }

  /* ---------- 3 · photobooth ---------- */
  const strip = $("#strip");
  const shots = $$(".strip__shot", strip);
  const fallback = ["strip__shot--mono", "strip__shot--names", "strip__shot--mono"];
  shots.forEach((s, i) => {
    const src = (C.photos || [])[i];
    if (src) s.style.backgroundImage = `url("${src}")`;
    else s.classList.add(fallback[i]);
  });
  $("#printBtn").addEventListener("click", () => {
    const booth = $(".booth");
    booth.classList.add("is-printing");
    if (reduced) { strip.classList.add("is-printed"); return; }
    strip.classList.add("is-printing");
    strip.addEventListener("animationend", () => { strip.classList.remove("is-printing"); strip.classList.add("is-printed"); }, { once: true });
  });

  /* ---------- 4 · scratch to reveal ---------- */
  const scratch = $("#scratch");
  const foil = $("#foil");
  const ctx = foil.getContext("2d", { willReadFrequently: true });
  const disc = new Image();
  disc.src = "assets/images/scratch-gold.png";
  let revealed = false;

  function paintFoil() {
    const r = foil.getBoundingClientRect();
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    foil.width = Math.round(r.width * dpr);
    foil.height = Math.round(r.height * dpr);
    ctx.globalCompositeOperation = "source-over";
    // slight overscan so the disc's soft edge never shows the date
    const o = foil.width * 0.06;
    ctx.drawImage(disc, -o, -o, foil.width + 2 * o, foil.height + 2 * o);
    ctx.lineCap = ctx.lineJoin = "round";
    ctx.lineWidth = foil.width * 0.16;
  }
  disc.onload = paintFoil;

  let last = null;
  function pos(e) {
    const r = foil.getBoundingClientRect();
    return [(e.clientX - r.left) * (foil.width / r.width), (e.clientY - r.top) * (foil.height / r.height)];
  }
  function cleared() {
    const d = ctx.getImageData(0, 0, foil.width, foil.height).data;
    let seen = 0, gone = 0;
    for (let i = 3; i < d.length; i += 4 * 24) { seen++; if (d[i] < 40) gone++; }
    return gone / seen;
  }
  function reveal() {
    if (revealed) return;
    revealed = true;
    scratch.classList.add("is-revealed");
    $("#scratchHint").style.opacity = 0;
  }
  foil.addEventListener("pointerdown", (e) => { foil.setPointerCapture(e.pointerId); last = pos(e); });
  foil.addEventListener("pointermove", (e) => {
    if (!last || revealed) return;
    const p = pos(e);
    ctx.globalCompositeOperation = "destination-out";
    ctx.beginPath(); ctx.moveTo(...last); ctx.lineTo(...p); ctx.stroke();
    last = p;
  });
  const lift = () => { last = null; if (!revealed && cleared() > 0.45) reveal(); };
  foil.addEventListener("pointerup", lift);
  foil.addEventListener("pointercancel", lift);
  foil.tabIndex = 0;
  foil.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); reveal(); } });
  window.addEventListener("resize", () => { if (!revealed && disc.complete) paintFoil(); });

  /* ---------- countdown ---------- */
  function tick() {
    let s = Math.max(0, Math.floor((when - Date.now()) / 1000));
    const d = Math.floor(s / 86400); s %= 86400;
    const h = Math.floor(s / 3600); s %= 3600;
    const m = Math.floor(s / 60); s %= 60;
    $("#cDays").textContent = num(d, 1);
    $("#cHours").textContent = num(h);
    $("#cMins").textContent = num(m);
    $("#cSecs").textContent = num(s);
  }
  setInterval(tick, 1000);

  /* ---------- calendar ---------- */
  let icsUrl = null;
  function buildCalendar() {
    const end = new Date(when.getTime() + C.durationHours * 3600e3);
    const z = (d) => d.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
    const title = t("calTitle").replace("{names}", names());
    const place = `${C.venue.name}, ${C.venue.address}`;
    $("#calGoogle").href = `https://calendar.google.com/calendar/render?action=TEMPLATE&text=${encodeURIComponent(title)}&dates=${z(when)}/${z(end)}&location=${encodeURIComponent(place)}`;
    $("#calOutlook").href = `https://outlook.live.com/calendar/0/deeplink/compose?path=/calendar/action/compose&rru=addevent&subject=${encodeURIComponent(title)}&startdt=${when.toISOString()}&enddt=${end.toISOString()}&location=${encodeURIComponent(place)}`;
    const ics = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//invitation//EN", "BEGIN:VEVENT",
      `UID:${z(when)}-invitation`, `DTSTAMP:${z(new Date())}`, `DTSTART:${z(when)}`, `DTEND:${z(end)}`,
      `SUMMARY:${title}`, `LOCATION:${place.replace(/,/g, "\\,")}`, "END:VEVENT", "END:VCALENDAR"].join("\r\n");
    if (icsUrl) URL.revokeObjectURL(icsUrl);
    icsUrl = URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" }));
    $("#calApple").href = icsUrl;
  }
  const calBtn = $("#calBtn"), calMenu = $("#calMenu");
  calBtn.addEventListener("click", () => {
    const open = calMenu.hidden;
    calMenu.hidden = !open;
    calBtn.setAttribute("aria-expanded", String(open));
  });
  calMenu.addEventListener("click", () => { calMenu.hidden = true; calBtn.setAttribute("aria-expanded", "false"); });
  document.addEventListener("click", (e) => { if (!e.target.closest(".calendar")) { calMenu.hidden = true; calBtn.setAttribute("aria-expanded", "false"); } });

  /* ---------- rsvp ---------- */
  const form = $("#rsvpForm");
  form.addEventListener("change", () => { $("#guestsField").hidden = form.attend.value === "no"; });
  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const name = form.name.value.trim();
    const err = $(".field__error", form);
    err.hidden = !!name;
    form.name.setAttribute("aria-invalid", String(!name));
    if (!name) { form.name.focus(); return; }
    const yes = form.attend.value === "yes";
    const lines = [
      t("waTitle").replace("{names}", names()),
      `${t("waName")}: ${name}`,
      `${t("waAttend")}: ${yes ? t("waYes") : t("waNo")}`,
    ];
    if (yes) lines.push(`${t("waGuests")}: ${form.guests.value}`);
    if (form.message.value.trim()) lines.push(`${t("waMsg")}: ${form.message.value.trim()}`);
    window.open(`https://wa.me/${C.rsvp.whatsapp}?text=${encodeURIComponent(lines.join("\n"))}`, "_blank", "noopener");
  });

  apply();
})();
