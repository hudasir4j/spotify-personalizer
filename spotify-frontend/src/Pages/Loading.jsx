import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import "./Loading.scss";

function Loading({ progress, previews, statusText }) {
  const [dots, setDots] = useState("");
  const pct =
    progress?.total > 0
      ? Math.round((progress.done / progress.total) * 100)
      : 0;

  useEffect(() => {
    const interval = setInterval(() => {
      setDots((prev) => (prev.length >= 3 ? "" : prev + "."));
    }, 500);
    return () => clearInterval(interval);
  }, []);

  const visiblePreviews = previews?.slice(-3) || [];

  return (
    <div className="loading-page">
      <div className="loading-content">
        <motion.h1
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
        >
          analyzing your music{dots}
        </motion.h1>

        <div className="progress-bar">
          <motion.div
            className="progress-fill"
            initial={{ width: 0 }}
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>

        <motion.p
          className="status"
          key={progress?.done}
          initial={{ opacity: 0.5 }}
          animate={{ opacity: 1 }}
        >
          {statusText ||
            (progress?.total
              ? `${progress.done} of ${progress.total} tracks analyzed`
              : "starting analysis...")}
        </motion.p>
        <p className="wait-time">
          scoring vibes from lyrics, sentiment & genres
        </p>

        <div className="preview-list">
          <AnimatePresence mode="popLayout">
            {visiblePreviews.map((song, i) => (
              <motion.div
                key={`${song.song}-${song.line?.slice(0, 20)}`}
                className="preview-card"
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ duration: 0.35 }}
                layout
              >
                {song.album_art && (
                  <img src={song.album_art} alt="" className="preview-art" />
                )}
                <div className="preview-body">
                  <strong>{song.song}</strong>
                  <span>{song.artist}</span>
                  <p>"{song.line}"</p>
                  {song.theme && <em className="preview-vibe">{song.theme}</em>}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}

export default Loading;
