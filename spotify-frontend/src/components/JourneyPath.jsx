import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import { buildWavyCenterPath, headLengthAtCenter } from "../utils/journeyPath";

const LERP = 0.06;

function JourneyPath({ containerRef }) {
  const [pathD, setPathD] = useState("");
  const [dims, setDims] = useState({ w: 0, h: 0 });
  const [pathLen, setPathLen] = useState(0);
  const [segment, setSegment] = useState({ tail: 0, head: 0 });
  const measurePathRef = useRef(null);
  const smoothHead = useRef(0);
  const rafRef = useRef(null);

  const measure = useCallback(() => {
    const root = containerRef.current;
    if (!root) return;

    const w = root.offsetWidth;
    const h = root.offsetHeight;
    if (!w || !h) return;

    setDims({ w, h });
    setPathD(buildWavyCenterPath(w, h));
    smoothHead.current = 0;
  }, [containerRef]);

  useEffect(() => {
    measure();
    const delayed = setTimeout(measure, 400);
    const later = setTimeout(measure, 1600);
    window.addEventListener("resize", measure);

    const root = containerRef.current;
    const observer = root ? new ResizeObserver(measure) : null;
    if (root && observer) observer.observe(root);

    return () => {
      clearTimeout(delayed);
      clearTimeout(later);
      window.removeEventListener("resize", measure);
      if (observer) observer.disconnect();
    };
  }, [measure, containerRef]);

  useLayoutEffect(() => {
    if (measurePathRef.current && pathD) {
      setPathLen(measurePathRef.current.getTotalLength());
    }
  }, [pathD]);

  useEffect(() => {
    const tick = () => {
      const root = containerRef.current;
      const pathEl = measurePathRef.current;

      if (root && pathEl && pathLen > 0) {
        const targetHead = headLengthAtCenter(root, pathEl, pathLen);
        smoothHead.current += (targetHead - smoothHead.current) * LERP;

        const trailPx = Math.min(
          window.innerHeight * 0.5,
          pathLen * 0.12
        );
        const head = smoothHead.current;
        const tail = Math.max(0, head - trailPx);

        setSegment({ tail, head });
      }

      rafRef.current = requestAnimationFrame(tick);
    };

    rafRef.current = requestAnimationFrame(tick);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [containerRef, pathLen]);

  if (!pathD || !dims.w) return null;

  const visibleLen = Math.max(0, segment.head - segment.tail);
  const viewBox = `0 0 ${dims.w} ${dims.h}`;

  return (
    <svg
      className="journey-path-svg"
      viewBox={viewBox}
      preserveAspectRatio="xMidYMin meet"
      aria-hidden="true"
    >
      <path ref={measurePathRef} d={pathD} className="journey-path-measure" />
      {pathLen > 0 && visibleLen > 1 && (
        <path
          d={pathD}
          className="journey-path-line"
          vectorEffect="non-scaling-stroke"
          style={{
            strokeDasharray: `${visibleLen} ${pathLen}`,
            strokeDashoffset: -segment.tail,
          }}
        />
      )}
    </svg>
  );
}

export default JourneyPath;
