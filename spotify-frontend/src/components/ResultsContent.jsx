import React, { useState, useMemo, useRef, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import html2canvas from "html2canvas";
import VibeDonut from "./VibeDonut";
import SongDetailModal from "./SongDetailModal";
import { getVibeTagline } from "../utils/vibeCopy";
import "../Pages/Results.scss";

const TIME_RANGE_LABELS = {
  short_term: "last 4 weeks",
  medium_term: "last 6 months",
  long_term: "all time",
};

const PAGE_SIZE = 18;

function truncate(text, max = 72) {
  if (!text || text.length <= max) return text;
  return `${text.slice(0, max).trim()}…`;
}

function SongTile({ song, selected, onSelect }) {
  return (
    <button
      type="button"
      className={`song-tile${selected ? " selected" : ""}`}
      onClick={() => onSelect(song)}
    >
      {song.album_art && (
        <img src={song.album_art} alt="" className="tile-art" loading="lazy" />
      )}
      <div className="tile-body">
        <div className="tile-top">
          <span className="tile-title">{song.song}</span>
          <span className="tile-vibe">{song.theme}</span>
        </div>
        <span className="tile-artist">{song.artist}</span>
        <p className="tile-line">"{truncate(song.line)}"</p>
      </div>
    </button>
  );
}

function ResultsContent({ data }) {
  const [activeTheme, setActiveTheme] = useState(null);
  const [activeWord, setActiveWord] = useState(null);
  const [selectedSong, setSelectedSong] = useState(null);
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);
  const [sharing, setSharing] = useState(false);
  const shareRef = useRef(null);

  const maxWordCount = useMemo(() => {
    if (!data?.top_words?.length) return 1;
    return Math.max(...data.top_words.map((w) => w[1]));
  }, [data]);

  const filteredHighlights = useMemo(() => {
    if (!data?.highlights) return [];
    return data.highlights.filter((song) => {
      if (activeTheme && song.theme !== activeTheme) return false;
      if (activeWord && !song.line.toLowerCase().includes(activeWord)) return false;
      return true;
    });
  }, [data, activeTheme, activeWord]);

  const visibleSongs = filteredHighlights.slice(0, visibleCount);
  const hasMore = visibleCount < filteredHighlights.length;

  const floatingWords = useMemo(() => {
    const words = data?.top_words || [];
    return words.slice(0, 10).map((item, i) => ({
      id: i,
      word: item[0],
      left: 8 + (i * 17) % 84,
      delay: i * 2,
      duration: 18 + (i % 4) * 3,
    }));
  }, [data]);

  const topTheme = useMemo(
    () => [...(data.themes || [])].sort((a, b) => b.count - a.count)[0],
    [data.themes]
  );

  const toggleTheme = useCallback((theme) => {
    setActiveWord(null);
    setSelectedSong(null);
    setVisibleCount(PAGE_SIZE);
    setActiveTheme((prev) => (prev === theme ? null : theme));
  }, []);

  const toggleWord = useCallback((word) => {
    setActiveTheme(null);
    setSelectedSong(null);
    setVisibleCount(PAGE_SIZE);
    setActiveWord((prev) => (prev === word ? null : word));
  }, []);

  const clearFilters = useCallback(() => {
    setActiveTheme(null);
    setActiveWord(null);
    setSelectedSong(null);
    setVisibleCount(PAGE_SIZE);
  }, []);

  const handleShare = async () => {
    if (!shareRef.current || sharing) return;
    setSharing(true);
    try {
      const canvas = await html2canvas(shareRef.current, {
        backgroundColor: "#1e0213",
        scale: 2,
        useCORS: true,
      });
      const link = document.createElement("a");
      link.download = "spotify-emotional-breakdown.png";
      link.href = canvas.toDataURL("image/png");
      link.click();
    } catch {
      alert("Could not generate share card — try again.");
    } finally {
      setSharing(false);
    }
  };

  const timeLabel =
    TIME_RANGE_LABELS[data.time_range] ||
    TIME_RANGE_LABELS[sessionStorage.getItem("time_range") || "medium_term"];

  return (
    <div className="results-page">
      {floatingWords.map((item) => (
        <span
          key={item.id}
          className="floating-word"
          style={{
            left: `${item.left}%`,
            animationDuration: `${item.duration}s`,
            animationDelay: `${item.delay}s`,
          }}
        >
          {item.word}
        </span>
      ))}

      <motion.div
        className="content"
        ref={shareRef}
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      >
        <header className="results-header">
          <h1>your emotional breakdown</h1>
          <p className="subtitle">
            {data.total_songs} tracks · {timeLabel}
          </p>
          {topTheme && (
            <p className="vibe-summary">{getVibeTagline(topTheme.theme)}</p>
          )}
        </header>

        {(activeTheme || activeWord) && (
          <div className="filter-banner">
            <span>
              showing {filteredHighlights.length} song
              {filteredHighlights.length !== 1 ? "s" : ""}
              {activeTheme ? ` · ${activeTheme}` : ""}
              {activeWord ? ` · "${activeWord}"` : ""}
            </span>
            <button type="button" onClick={clearFilters}>
              clear
            </button>
          </div>
        )}

        {data.themes?.length > 0 && (
          <section className="themes-section">
            <h2>emotional themes</h2>
            <p className="section-hint">tap a slice or label to filter songs</p>
            <VibeDonut
              themes={data.themes}
              totalSongs={data.total_songs}
              activeTheme={activeTheme}
              onSelect={toggleTheme}
            />
          </section>
        )}

        <section className="songs-section">
          <div className="songs-head">
            <h2>lyric highlights</h2>
            <span className="songs-count">
              {filteredHighlights.length} tracks
            </span>
          </div>
          <p className="section-hint">tap a card for the full lyric</p>

          <div className="song-grid">
            {visibleSongs.map((song) => (
              <SongTile
                key={song.track_id || `${song.song}-${song.artist}`}
                song={song}
                selected={
                  selectedSong &&
                  (selectedSong.track_id || selectedSong.song) ===
                    (song.track_id || song.song)
                }
                onSelect={setSelectedSong}
              />
            ))}
          </div>

          {hasMore && (
            <button
              type="button"
              className="load-more"
              onClick={() => setVisibleCount((n) => n + PAGE_SIZE)}
            >
              show more ({filteredHighlights.length - visibleCount} left)
            </button>
          )}
        </section>

        {data.top_words?.length > 0 && (
          <section className="words-section">
            <h2>words that define you</h2>
            <p className="section-hint">tap a word to see matching lyrics</p>
            <div className="word-cloud">
              {data.top_words.map(([word, count]) => {
                const size = 14 + (count / maxWordCount) * 22;
                return (
                  <button
                    key={word}
                    type="button"
                    className={`cloud-word${activeWord === word ? " active" : ""}`}
                    style={{ fontSize: `${size}px` }}
                    onClick={() => toggleWord(word)}
                  >
                    {word}
                    <span className="cloud-count">{count}</span>
                  </button>
                );
              })}
            </div>
          </section>
        )}

        <footer className="footer-nav">
          <button
            type="button"
            className="share-button"
            onClick={handleShare}
            disabled={sharing}
          >
            {sharing ? "generating..." : "download share card"}
          </button>
          <a href="/" className="back-link">
            ← analyze again
          </a>
        </footer>
      </motion.div>

      <AnimatePresence>
        {selectedSong && (
          <SongDetailModal
            song={selectedSong}
            onClose={() => setSelectedSong(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default ResultsContent;
