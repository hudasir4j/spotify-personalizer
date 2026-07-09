/** Per-vibe visual identity for scroll journey chapters */
export const ERA_VISUALS = {
  baddie: {
    gradient: "linear-gradient(135deg, #2a0818 0%, #45062c 40%, #1a0520 100%)",
    glow: "rgba(255, 107, 157, 0.25)",
    accent: "#ff6b9d",
  },
  "villain era": {
    gradient: "linear-gradient(160deg, #0d0d12 0%, #32021f 50%, #1e0213 100%)",
    glow: "rgba(180, 80, 255, 0.2)",
    accent: "#c084fc",
  },
  "main character": {
    gradient: "linear-gradient(145deg, #1e0213 0%, #3d1a4a 50%, #2a1040 100%)",
    glow: "rgba(168, 255, 120, 0.3)",
    accent: "#a8ff78",
  },
  "locked in": {
    gradient: "linear-gradient(180deg, #1a0e2e 0%, #0f2818 100%)",
    glow: "rgba(100, 220, 120, 0.2)",
    accent: "#6ee7a0",
  },
  "hopeless romantic": {
    gradient: "linear-gradient(135deg, #32021f 0%, #4a2040 60%, #1e0213 100%)",
    glow: "rgba(255, 150, 180, 0.22)",
    accent: "#ffb3c6",
  },
  yearning: {
    gradient: "linear-gradient(160deg, #1e0213 0%, #2d1835 45%, #45062c 100%)",
    glow: "rgba(168, 255, 120, 0.18)",
    accent: "#a8ff78",
  },
  delulu: {
    gradient: "linear-gradient(135deg, #2a1535 0%, #1e0213 100%)",
    glow: "rgba(200, 160, 255, 0.2)",
    accent: "#d8b4fe",
  },
  situationship: {
    gradient: "linear-gradient(145deg, #1a1225 0%, #32021f 100%)",
    glow: "rgba(255, 200, 120, 0.15)",
    accent: "#fcd34d",
  },
  "it's ok i'm ok": {
    gradient: "linear-gradient(180deg, #1e0213 0%, #253040 100%)",
    glow: "rgba(120, 180, 255, 0.15)",
    accent: "#93c5fd",
  },
  "thugging it out": {
    gradient: "linear-gradient(160deg, #0a0a0f 0%, #1e0213 60%, #2a0818 100%)",
    glow: "rgba(100, 100, 140, 0.2)",
    accent: "#94a3b8",
  },
  "romanticizing life": {
    gradient: "linear-gradient(135deg, #2a2010 0%, #45062c 50%, #1e0213 100%)",
    glow: "rgba(255, 200, 100, 0.2)",
    accent: "#fde68a",
  },
  "soft girl autumn": {
    gradient: "linear-gradient(145deg, #2a1810 0%, #32021f 100%)",
    glow: "rgba(255, 180, 120, 0.18)",
    accent: "#fdba74",
  },
  "missing what used to be": {
    gradient: "linear-gradient(160deg, #1a1520 0%, #2d2035 100%)",
    glow: "rgba(150, 130, 180, 0.2)",
    accent: "#c4b5fd",
  },
  unc: {
    gradient: "linear-gradient(135deg, #1e2830 0%, #32021f 100%)",
    glow: "rgba(120, 200, 200, 0.15)",
    accent: "#7dd3fc",
  },
  "moving on playlist": {
    gradient: "linear-gradient(180deg, #1e0213 0%, #1a3020 100%)",
    glow: "rgba(168, 255, 120, 0.15)",
    accent: "#86efac",
  },
  "3am overthinking": {
    gradient: "linear-gradient(160deg, #050508 0%, #1a0e2e 50%, #0f0a18 100%)",
    glow: "rgba(100, 100, 255, 0.15)",
    accent: "#818cf8",
  },
};

const DEFAULT_VISUAL = {
  gradient: "linear-gradient(45deg, #45062c, #1e0213, #32021F)",
  glow: "rgba(168, 255, 120, 0.2)",
  accent: "#a8ff78",
};

export function getEraVisual(vibe) {
  return ERA_VISUALS[vibe] || DEFAULT_VISUAL;
}

/** Layout pattern cycles for song slides within a chapter */
export const SLIDE_LAYOUTS = ["center", "split-left", "immersive", "split-right"];

export function getSlideLayout(chapterIndex, songIndex) {
  return SLIDE_LAYOUTS[(chapterIndex + songIndex) % SLIDE_LAYOUTS.length];
}
