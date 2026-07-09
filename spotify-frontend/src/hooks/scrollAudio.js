import { useRef, useCallback, useEffect } from "react";
import { playPreview, pausePreview, preloadPreview } from "../utils/audioUnlock";

export function songKey(song) {
  return song.track_id || `${song.song}::${song.artist}`;
}

export function useScrollPlayback(highlights = []) {
  const currentKeyRef = useRef(null);
  const highlightsRef = useRef(highlights);

  useEffect(() => {
    highlightsRef.current = highlights;
  }, [highlights]);

  const playSong = useCallback((song) => {
    if (!song?.preview_url) return;
    const key = songKey(song);
    if (currentKeyRef.current === key) return;

    playPreview(song.preview_url, key, (k) => {
      currentKeyRef.current = k;
    });

    const list = highlightsRef.current;
    const idx = list.findIndex((s) => songKey(s) === key);
    if (idx >= 0 && list[idx + 1]?.preview_url) {
      preloadPreview(list[idx + 1].preview_url);
    }
  }, []);

  const pause = useCallback(() => {
    pausePreview();
    currentKeyRef.current = null;
  }, []);

  return { playSong, pause, currentKeyRef };
}

export function useActiveSlideObserver(containerRef, slideSelector, onActive) {
  useEffect(() => {
    const root = containerRef.current;
    if (!root) return undefined;

    const observe = () => {
      const slides = root.querySelectorAll(slideSelector);
      if (!slides.length) return undefined;

      const ratios = new Map();

      const isPlayable = (id) =>
        id &&
        id !== "hero" &&
        !id.startsWith("era-") &&
        !id.startsWith("burst-");

      const pickActive = () => {
        let bestId = null;
        let bestRatio = 0;
        ratios.forEach((ratio, id) => {
          if (isPlayable(id) && ratio > bestRatio) {
            bestRatio = ratio;
            bestId = id;
          }
        });
        if (bestId && bestRatio >= 0.3) {
          onActive(bestId);
        }
      };

      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            const id = entry.target.getAttribute("data-slide-id");
            if (!id) return;
            if (entry.isIntersecting) {
              ratios.set(id, entry.intersectionRatio);
            } else {
              ratios.delete(id);
            }
          });
          pickActive();
        },
        { root: null, threshold: [0.2, 0.35, 0.5, 0.65, 0.8] }
      );

      slides.forEach((slide) => observer.observe(slide));
      return () => observer.disconnect();
    };

    let cleanup = observe();
    const timer = setTimeout(() => {
      if (cleanup) cleanup();
      cleanup = observe();
    }, 400);

    return () => {
      clearTimeout(timer);
      if (cleanup) cleanup();
    };
  }, [containerRef, slideSelector, onActive]);
}
