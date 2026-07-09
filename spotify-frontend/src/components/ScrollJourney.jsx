import React, { useMemo, useRef, useCallback, useState, useEffect } from "react";
import { motion, useScroll, useTransform } from "framer-motion";
import {
  songKey,
  useScrollPlayback,
  useActiveSlideObserver,
} from "../hooks/scrollAudio";
import { getVibeTagline } from "../utils/vibeCopy";
import { getEraVisual, getSlideLayout } from "../utils/eraVisuals";
import { isAudioUnlocked } from "../utils/audioUnlock";
import JourneyPath from "./JourneyPath";

function JourneyProgress({ chapters, activeId, songMap }) {
  const activeSong = activeId ? songMap.get(activeId) : null;
  const activeVibe = activeSong?.theme;

  return (
    <nav className="journey-rail" aria-label="Journey progress">
      {chapters.map((ch, i) => (
        <div
          key={ch.vibe}
          className={`rail-chapter${activeVibe === ch.vibe ? " active" : ""}`}
        >
          <span className="rail-dot" style={{ background: getEraVisual(ch.vibe).accent }} />
          <span className="rail-label">{ch.vibe}</span>
        </div>
      ))}
    </nav>
  );
}

function HorizontalBurst({ songs, eraVisual, chapterIndex }) {
  return (
    <div className="horizontal-burst" data-slide-id={`burst-${chapterIndex}`}>
      <p className="burst-label">rapid fire</p>
      <div className="burst-track">
        {songs.map((song) => (
          <div key={songKey(song)} className="burst-card">
            {song.album_art && (
              <img src={song.album_art} alt="" className="burst-art" loading="lazy" />
            )}
            <p className="burst-line">"{song.line.slice(0, 48)}{song.line.length > 48 ? "…" : ""}"</p>
            <span>{song.song}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function SongSlide({
  song,
  index,
  isActive,
  hasPreview,
  layout,
  eraVisual,
  chapterIndex,
}) {
  const id = songKey(song);
  const isImmersive = layout === "immersive";

  return (
    <article
      className={`song-slide layout-${layout}${isActive ? " is-active" : ""}${!hasPreview ? " no-preview" : ""}`}
      data-slide-id={id}
      style={{
        "--era-accent": eraVisual.accent,
        "--era-glow": eraVisual.glow,
      }}
    >
      {isImmersive && song.album_art && (
        <div
          className="slide-bg-blur"
          style={{ backgroundImage: `url(${song.album_art})` }}
          aria-hidden="true"
        />
      )}

      <div className="slide-inner">
        {song.album_art && (
          <motion.div
            className="slide-art-wrap"
            animate={
              isActive
                ? { scale: 1, opacity: 1, rotate: layout === "split-right" ? 3 : layout === "split-left" ? -3 : 0 }
                : { scale: 0.88, opacity: 0.45, rotate: 0 }
            }
            transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
          >
            <img src={song.album_art} alt="" className="slide-art" loading="lazy" />
            {isActive && hasPreview && (
              <div className="waveform" aria-hidden="true">
                {[0, 1, 2, 3, 4].map((i) => (
                  <span key={i} className="wave-bar" style={{ animationDelay: `${i * 0.12}s` }} />
                ))}
              </div>
            )}
          </motion.div>
        )}

        <div className="slide-copy">
        <motion.blockquote
          className="slide-lyric"
          animate={isActive ? { opacity: 1, y: 0 } : { opacity: 0.55, y: 12 }}
          transition={{ duration: 0.4 }}
        >
          "{song.line}"
        </motion.blockquote>

        <div className="slide-meta">
          <h3>{song.song}</h3>
          <p>{song.artist}</p>
        </div>

        {isActive && hasPreview && isAudioUnlocked() && (
          <p className="slide-playing-label">♫ now playing</p>
        )}
        {isActive && !hasPreview && (
          <p className="slide-no-preview">no 30s preview — open in Spotify</p>
        )}
        </div>

        <span className="slide-index">{String(index + 1).padStart(2, "0")}</span>
      </div>
    </article>
  );
}

function ScrollJourney({ highlights, topTheme, timeLabel, totalSongs }) {
  const journeyRef = useRef(null);
  const songMapRef = useRef(new Map());
  const { playSong, pause } = useScrollPlayback(highlights);
  const [activeId, setActiveId] = useState(null);

  const { scrollYProgress } = useScroll({ target: journeyRef, offset: ["start start", "end end"] });
  const heroY = useTransform(scrollYProgress, [0, 0.15], [0, -80]);
  const heroOpacity = useTransform(scrollYProgress, [0, 0.12], [1, 0]);

  const chapters = useMemo(() => {
    const groups = {};
    highlights.forEach((song) => {
      const vibe = song.theme || "unknown";
      if (!groups[vibe]) groups[vibe] = [];
      groups[vibe].push(song);
    });
    return Object.entries(groups)
      .sort((a, b) => b[1].length - a[1].length)
      .map(([vibe, songs]) => ({
        vibe,
        songs,
        tagline: getVibeTagline(vibe),
        visual: getEraVisual(vibe),
      }));
  }, [highlights]);

  const songMap = useMemo(() => {
    const map = new Map();
    highlights.forEach((s) => map.set(songKey(s), s));
    return map;
  }, [highlights]);

  useEffect(() => {
    songMapRef.current = songMap;
  }, [songMap]);

  const handleActive = useCallback(
    (slideId) => {
      setActiveId(slideId);
      const song = songMapRef.current.get(slideId);
      if (song) playSong(song);
    },
    [playSong]
  );

  useActiveSlideObserver(journeyRef, "[data-slide-id]", handleActive);

  useEffect(() => {
    const onVis = () => {
      if (document.hidden) pause();
    };
    document.addEventListener("visibilitychange", onVis);
    return () => document.removeEventListener("visibilitychange", onVis);
  }, [pause]);

  return (
    <div className="journey" ref={journeyRef}>
      <JourneyProgress chapters={chapters} activeId={activeId} songMap={songMap} />

      <motion.section
        className="journey-hero"
        data-slide-id="hero"
        style={{ y: heroY, opacity: heroOpacity }}
      >
        <div className="hero-glow" aria-hidden="true" />
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7 }}
          style={{ position: "relative", zIndex: 2 }}
        >
          <p className="journey-kicker">your emotional breakdown</p>
          <h1>{topTheme ? `mostly ${topTheme.theme}` : "your playlist"}</h1>
          {topTheme && (
            <p className="journey-tagline">{getVibeTagline(topTheme.theme)}</p>
          )}
          <p className="journey-sub">
            {totalSongs} tracks · {timeLabel}
          </p>
          <p className="scroll-cue">
            <span className="scroll-arrow">↓</span>
            scroll — music plays as you go
          </p>
        </motion.div>
      </motion.section>

      {chapters.map((chapter, ci) => (
        <div
          className="era-chapter"
          key={chapter.vibe}
          style={{
            "--era-gradient": chapter.visual.gradient,
            "--era-accent": chapter.visual.accent,
          }}
        >
          <div className="era-chapter-bg" aria-hidden="true" />
          <div className="era-chapter-content">
          <header
            className="era-intro"
            data-slide-id={`era-${chapter.vibe}`}
            style={{ "--era-accent": chapter.visual.accent }}
          >
            <div className="era-intro-bg" aria-hidden="true" />
            <span className="era-chapter-num">
              chapter {String(ci + 1).padStart(2, "0")}
            </span>
            <h2>
              your <em>{chapter.vibe}</em> era
            </h2>
            <p className="era-intro-tagline">{chapter.tagline}</p>
            <p className="era-intro-count">{chapter.songs.length} tracks</p>
          </header>

          {chapter.songs.length >= 4 && (
            <HorizontalBurst
              songs={chapter.songs.slice(0, 4)}
              eraVisual={chapter.visual}
              chapterIndex={ci}
            />
          )}

          {chapter.songs.map((song, si) => (
            <SongSlide
              key={songKey(song)}
              song={song}
              index={si}
              isActive={activeId === songKey(song)}
              hasPreview={Boolean(song.preview_url)}
              layout={getSlideLayout(ci, si)}
              eraVisual={chapter.visual}
              chapterIndex={ci}
            />
          ))}
          </div>
        </div>
      ))}

      <section className="journey-end">
        <p>that's your story.</p>
        <span className="scroll-arrow end">↑</span>
        <span className="journey-end-hint">keep scrolling for the full breakdown</span>
      </section>

      <JourneyPath containerRef={journeyRef} />
    </div>
  );
}

export default ScrollJourney;
