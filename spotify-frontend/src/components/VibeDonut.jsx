import React, { useMemo } from "react";
import { motion } from "framer-motion";

const SEGMENT_COLORS = [
  "#a8ff78",
  "#8ef066",
  "#c8ff9a",
  "#6fd84a",
  "#d4ffb8",
  "#5bc738",
  "#e2ffc4",
  "#4aab2e",
  "#b8f088",
  "#3d8f24",
];

function polar(cx, cy, r, angleDeg) {
  const rad = ((angleDeg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arcPath(cx, cy, r, startDeg, endDeg) {
  if (endDeg - startDeg >= 359.99) {
    return [
      `M ${cx} ${cy - r}`,
      `A ${r} ${r} 0 1 1 ${cx - 0.01} ${cy - r}`,
      "Z",
    ].join(" ");
  }
  const start = polar(cx, cy, r, endDeg);
  const end = polar(cx, cy, r, startDeg);
  const large = endDeg - startDeg > 180 ? 1 : 0;
  return `M ${cx} ${cy} L ${start.x} ${start.y} A ${r} ${r} 0 ${large} 0 ${end.x} ${end.y} Z`;
}

function VibeDonut({ themes, totalSongs, activeTheme, onSelect }) {
  const sorted = useMemo(
    () => [...themes].sort((a, b) => b.count - a.count),
    [themes]
  );

  const total = useMemo(
    () => sorted.reduce((s, t) => s + t.count, 0) || 1,
    [sorted]
  );

  const segments = useMemo(() => {
    let angle = 0;
    return sorted.map((t, i) => {
      const sweep = (t.count / total) * 360;
      const seg = {
        ...t,
        start: angle,
        end: angle + sweep,
        pct: Math.round((t.count / total) * 100),
        color: SEGMENT_COLORS[i % SEGMENT_COLORS.length],
      };
      angle += sweep;
      return seg;
    });
  }, [sorted, total]);

  const top = segments[0];

  return (
    <div className="vibe-donut-wrap">
      <div className="donut-chart">
        <svg viewBox="0 0 200 200" className="donut-svg" aria-hidden="true">
          <circle cx="100" cy="100" r="72" fill="rgba(255,255,255,0.04)" />
          {segments.map((seg) => (
            <motion.path
              key={seg.theme}
              d={arcPath(100, 100, 88, seg.start, seg.end)}
              fill={seg.color}
              opacity={activeTheme && activeTheme !== seg.theme ? 0.25 : 0.92}
              stroke={activeTheme === seg.theme ? "#fff" : "transparent"}
              strokeWidth={activeTheme === seg.theme ? 2 : 0}
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{
                opacity: activeTheme && activeTheme !== seg.theme ? 0.25 : 0.92,
                scale: 1,
              }}
              transition={{ duration: 0.4 }}
              style={{ transformOrigin: "100px 100px", cursor: "pointer" }}
              onClick={() => onSelect(seg.theme)}
            />
          ))}
          <circle cx="100" cy="100" r="52" fill="#1e0213" />
        </svg>
        <div className="donut-center">
          {top && (
            <>
              <span className="donut-pct">{top.pct}%</span>
              <span className="donut-label">{top.theme}</span>
            </>
          )}
        </div>
      </div>

      <ul className="donut-legend">
        {segments.map((seg) => (
          <li key={seg.theme}>
            <button
              type="button"
              className={`legend-item${activeTheme === seg.theme ? " active" : ""}`}
              onClick={() => onSelect(seg.theme)}
            >
              <span className="swatch" style={{ background: seg.color }} />
              <span className="legend-name">{seg.theme}</span>
              <span className="legend-meta">
                {seg.count} · {seg.pct}%
              </span>
            </button>
          </li>
        ))}
      </ul>

      <p className="donut-footnote">{totalSongs} tracks mapped</p>
    </div>
  );
}

export default VibeDonut;
