/** Gentle center wavy path for the scroll journey. */
export function buildWavyCenterPath(width, height) {
  const cx = width * 0.5;
  const amp = Math.min(110, width * 0.13);
  const top = height * 0.04;
  const bottom = height * 0.96;
  const span = bottom - top;
  const viewport =
    typeof window !== "undefined" ? window.innerHeight : 800;
  const wavePeriod = Math.max(420, viewport * 0.75);
  const waveCount = span / wavePeriod;
  const steps = Math.min(160, Math.max(48, Math.round(waveCount * 10)));
  const points = [];

  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const y = top + t * span;
    const envelope = Math.sin(t * Math.PI) ** 0.9;
    const phase = t * waveCount * Math.PI * 2;
    const x = cx + Math.sin(phase) * amp * envelope;
    points.push({ x, y });
  }

  return buildSoftPath(points);
}

/** Cubic segments that keep horizontal wave shape (control points stay on each x). */
function buildSoftPath(points) {
  if (points.length < 2) return "";
  let d = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`;

  for (let i = 0; i < points.length - 1; i += 1) {
    const p0 = points[i];
    const p1 = points[i + 1];
    const dy = (p1.y - p0.y) / 3;
    d += ` C ${p0.x.toFixed(1)} ${(p0.y + dy).toFixed(1)}, ${p1.x.toFixed(1)} ${(p1.y - dy).toFixed(1)}, ${p1.x.toFixed(1)} ${p1.y.toFixed(1)}`;
  }

  return d;
}

/** Map viewport-center Y to distance along the path (handles curves). */
export function headLengthAtCenter(container, pathEl, pathLen) {
  if (!container || !pathEl || pathLen <= 0) return 0;

  const rect = container.getBoundingClientRect();
  const targetY = window.innerHeight * 0.5 - rect.top;

  if (targetY <= 0) return 0;
  if (targetY >= container.offsetHeight) return pathLen;

  let lo = 0;
  let hi = pathLen;

  for (let i = 0; i < 40; i += 1) {
    const mid = (lo + hi) / 2;
    const pt = pathEl.getPointAtLength(mid);
    if (pt.y < targetY) lo = mid;
    else hi = mid;
  }

  return (lo + hi) / 2;
}
