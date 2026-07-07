export const VIBE_TAGLINES = {
  baddie: "unbothered. moisturized. in your lane.",
  "villain era": "even the opps wouldn't play with you right now...",
  "main character": "playlist? more like a soundtrack to your movie.",
  "locked in": "LOCKED in, no distractions.",
  "hopeless romantic": "you still believe in the slow burn.",
  yearning: "ooo, someone's in love!",
  delulu: "is it realllllly delusion though?",
  situationship: "what are we? (wrong answers only)",
  "it's ok i'm ok": "you're fine. totally fine. definitely fine.",
  "thugging it out": "a little emo, but we hanging in there!",
  "romanticizing life": "everything is golden hour somehow.",
  "soft girl autumn": "sweater weather and soft thoughts only.",
  "missing what used to be": "nostalgic AF",
  unc: "\"\"the good ol' days\"\" when life was simpler.",
  "moving on playlist": "new chapter, who dis?",
  "3am overthinking": "why did they say it like that tho.",
};

export function getVibeTagline(vibe) {
  return VIBE_TAGLINES[vibe] || "your playlist has main character energy.";
}

export function getVibeEnvelopeTeaser(vibe) {
  const teasers = {
    yearning: "spoiler: someone's catching feelings",
    baddie: "it's giving icon behavior inside",
    "villain era": "villain arc loading...",
    delulu: "delulu is the solulu (probably)",
    situationship: "it's complicated in there",
    "3am overthinking": "3am thoughts enclosed",
    "hopeless romantic": "love songs detected. proceed with caution.",
    "main character": "main character mail. obviously.",
    "it's ok i'm ok": "coping mechanisms inside",
    "thugging it out": "heavy feelings. handle with care.",
  };
  return teasers[vibe] || getVibeTagline(vibe);
}
