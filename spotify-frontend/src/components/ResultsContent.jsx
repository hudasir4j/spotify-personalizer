import React, { useState, useMemo, useRef, useCallback } from "react";
import { motion } from "framer-motion";
import html2canvas from "html2canvas";
import ScrollJourney from "./ScrollJourney";
import VibeDonut from "./VibeDonut";
import "../Pages/Results.scss";

const TIME_RANGE_LABELS = {
  short_term: "last 4 weeks",
  medium_term: "last 6 months",
  long_term: "all time",
};

function ResultsContent({ data }) {
  const [activeTheme, setActiveTheme] = useState(null);
  const [activeWord, setActiveWord] = useState(null);
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

  const topTheme = useMemo(
    () => [...(data.themes || [])].sort((a, b) => b.count - a.count)[0],
    [data.themes]
  );

  const toggleTheme = useCallback((theme) => {
    setActiveWord(null);
    setActiveTheme((prev) => (prev === theme ? null : theme));
  }, []);

  const toggleWord = useCallback((word) => {
    setActiveTheme(null);
    setActiveWord((prev) => (prev === word ? null : word));
  }, []);

  const clearFilters = useCallback(() => {
    setActiveTheme(null);
    setActiveWord(null);
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
    <div className="results-page results-page--journey">
      <div className="film-grain" aria-hidden="true" />
      {(activeTheme || activeWord) && (
        <div className="filter-banner filter-banner--fixed">
          <span>
            filtered · {filteredHighlights.length} songs
            {activeTheme ? ` · ${activeTheme}` : ""}
            {activeWord ? ` · "${activeWord}"` : ""}
          </span>
          <button type="button" onClick={clearFilters}>
            clear
          </button>
        </div>
      )}

      <ScrollJourney
        highlights={filteredHighlights}
        topTheme={topTheme}
        timeLabel={timeLabel}
        totalSongs={data.total_songs}
      />

      <motion.div
        className="content journey-outro"
        ref={shareRef}
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.6 }}
      >
        {data.themes?.length > 0 && (
          <section className="themes-section">
            <h2>emotional themes</h2>
            <p className="section-hint">tap a slice to filter the journey above</p>
            <VibeDonut
              themes={data.themes}
              totalSongs={data.total_songs}
              activeTheme={activeTheme}
              onSelect={toggleTheme}
            />
          </section>
        )}

        {data.top_words?.length > 0 && (
          <section className="words-section">
            <h2>words that define you</h2>
            <p className="section-hint">tap a word to filter songs</p>
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
    </div>
  );
}

export default ResultsContent;
