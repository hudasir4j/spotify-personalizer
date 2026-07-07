import { getColorSync } from "colorthief";

const cache = new Map();

function parseRgb(css) {
  const match = css.match(/rgb\((\d+),\s*(\d+),\s*(\d+)\)/);
  if (!match) return null;
  return [Number(match[1]), Number(match[2]), Number(match[3])];
}

function rgbToHsl(r, g, b) {
  r /= 255;
  g /= 255;
  b /= 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  let h = 0;
  let s = 0;

  if (max !== min) {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r:
        h = ((g - b) / d + (g < b ? 6 : 0)) / 6;
        break;
      case g:
        h = ((b - r) / d + 2) / 6;
        break;
      default:
        h = ((r - g) / d + 4) / 6;
        break;
    }
  }
  return [h * 360, s * 100, l * 100];
}

function hslToRgb(h, s, l) {
  h /= 360;
  s /= 100;
  l /= 100;
  if (s === 0) {
    const v = Math.round(l * 255);
    return [v, v, v];
  }
  const hue2rgb = (p, q, t) => {
    let x = t;
    if (x < 0) x += 1;
    if (x > 1) x -= 1;
    if (x < 1 / 6) return p + (q - p) * 6 * x;
    if (x < 1 / 2) return q;
    if (x < 2 / 3) return p + (q - p) * (2 / 3 - x) * 6;
    return p;
  };
  const q = l < 0.5 ? l * (1 + s) : l + s - l * s;
  const p = 2 * l - q;
  return [
    Math.round(hue2rgb(p, q, h + 1 / 3) * 255),
    Math.round(hue2rgb(p, q, h) * 255),
    Math.round(hue2rgb(p, q, h - 1 / 3) * 255),
  ];
}

function toCss([r, g, b]) {
  return `rgb(${r}, ${g}, ${b})`;
}

/** Tune extracted color for dark UI: border accent + subtle card glow */
export function toAlbumAccent(rawCss) {
  const rgb = parseRgb(rawCss);
  if (!rgb) return null;

  const [h, s, l] = rgbToHsl(...rgb);
  const sat = Math.min(85, Math.max(45, s));
  const light = Math.min(62, Math.max(42, l < 38 ? 48 : l));

  const border = toCss(hslToRgb(h, sat, light));
  const glow = toCss(hslToRgb(h, sat * 0.7, light * 0.55));
  const wash = `hsla(${Math.round(h)}, ${Math.round(sat)}%, ${Math.round(light)}%, 0.12)`;

  return { border, glow, wash };
}

export function extractAlbumColor(url) {
  if (!url) return Promise.resolve(null);
  if (cache.has(url)) return Promise.resolve(cache.get(url));

  return new Promise((resolve) => {
    const img = new Image();
    img.crossOrigin = "Anonymous";
    img.onload = () => {
      try {
        const color = getColorSync(img);
        const accent = toAlbumAccent(color.css());
        if (accent) cache.set(url, accent);
        resolve(accent);
      } catch {
        resolve(null);
      }
    };
    img.onerror = () => resolve(null);
    img.src = url;
  });
}
