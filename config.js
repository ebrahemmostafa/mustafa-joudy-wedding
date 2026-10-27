/*
  Everything you need to edit lives in this file.
  After changing the initials, rebuild the envelope:
    python tools/personalize_envelope.py --initials "M&J" --photo tools/source/flow/oval-rings.jpg
  After changing the names or date, rebuild the photobooth strip:
    python tools/make_booth.py
*/
window.INVITE = {
  couple: { one: "Mustafa", two: "Joudy" },

  // date + time of the wedding, with the Cairo offset (11 December 2026, 7:00 pm – 12:00 am)
  date: "2026-12-11T19:00:00+02:00",
  timeZone: "Africa/Cairo",
  durationHours: 5,

  hero: {
    above: "Together with Anter's Family",
    below: "invite you to celebrate their wedding",
  },

  // up to 3 photos for the photobooth strip (printed in black and white)
  photos: ["assets/photos/names.jpg", "assets/photos/date.jpg", "assets/photos/evening.jpg"],

  venue: {
    name: "InterContinental Cairo Semiramis",
    address: "Corniche El Nil, Garden City, Cairo",
    mapUrl: "https://share.google/CeagsZfxzkTNolvxy",
  },

  programme: [
    { time: "19:00", what: "Guests arrive" },
    { time: "19:30", what: "Katb El-Ketab" },
    { time: "20:30", what: "Zaffa & first dance" },
    { time: "22:00", what: "Dinner" },
  ],

  dressCode: {
    title: "Formal evening wear",
    note: "Kindly keep white for the bride.",
  },

  // RSVP replies are saved to Supabase (project "mustafa-joudy-wedding-rsvp", schema in supabase/rsvp.sql).
  // The publishable key is meant for browsers: guests can only add replies with it.
  supabase: {
    url: "https://qnhfythwuicajjtlllrw.supabase.co",
    key: "sb_publishable_MIGuuluNz2TN0PQM0SJQYw_qWD8tpDc",
  },

  closing: "We can't wait to celebrate with you · Anter's Family",
};
