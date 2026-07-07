import React, { useEffect } from "react";
import { motion } from "framer-motion";

function SongDetailModal({ song, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  if (!song) return null;

  return (
    <motion.div
      className="song-modal-backdrop"
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.2 }}
      onClick={onClose}
    >
      <motion.div
        className="song-modal"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 12 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="song-modal-title"
      >
        <button type="button" className="modal-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        {song.album_art && (
          <img src={song.album_art} alt="" className="modal-art" />
        )}
        <div className="modal-body">
          <p className="modal-vibe">{song.theme}</p>
          <blockquote>"{song.line}"</blockquote>
          <h3 id="song-modal-title">{song.song}</h3>
          <p className="modal-artist">{song.artist}</p>
          {song.genres?.length > 0 && (
            <p className="modal-genres">{song.genres.join(" · ")}</p>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}

export default SongDetailModal;
