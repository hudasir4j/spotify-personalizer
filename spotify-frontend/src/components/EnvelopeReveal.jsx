import React, { useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import "./EnvelopeReveal.scss";

function EnvelopeReveal({ onReveal, teaser }) {
  const [phase, setPhase] = useState("closed");

  const open = useCallback(() => {
    if (phase !== "closed") return;
    setPhase("opening");
    setTimeout(() => {
      setPhase("done");
      onReveal();
    }, 1400);
  }, [phase, onReveal]);

  return (
    <div className="envelope-screen">
      <motion.p
        className="mail-greeting"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
      >
        oh, you've got mail!
      </motion.p>

      <div className="envelope-stage">
        <motion.div
          className={`envelope${phase !== "closed" ? " is-open" : ""}`}
          initial={{ opacity: 0, scale: 0.92 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.2, duration: 0.5 }}
          drag={phase === "closed" ? "y" : false}
          dragConstraints={{ top: -100, bottom: 0 }}
          dragElastic={0.1}
          onDragEnd={(_, info) => {
            if (info.offset.y < -50) open();
          }}
          onClick={open}
          onKeyDown={(e) => e.key === "Enter" && open()}
          role="button"
          tabIndex={0}
          aria-label="Open your results"
        >
          <div className="envelope-back" />
          <motion.div
            className="letter-peek"
            animate={
              phase === "opening"
                ? { y: -90, opacity: 1 }
                : { y: 0, opacity: phase === "closed" ? 0 : 1 }
            }
            transition={{ duration: 0.9, ease: [0.22, 1, 0.36, 1] }}
          >
            <span className="letter-line" />
            <span className="letter-line short" />
            {teaser && <em>{teaser}</em>}
          </motion.div>
          <motion.div
            className="envelope-flap"
            animate={
              phase === "opening"
                ? { rotateX: 180, y: -2 }
                : { rotateX: 0, y: 0 }
            }
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          />
          <div className="envelope-pocket" />
        </motion.div>
      </div>

      <AnimatePresence>
        {phase === "closed" && (
          <motion.div
            className="open-hint"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ delay: 0.8 }}
          >
            <motion.span
              className="swipe-cue"
              animate={{ y: [0, -8, 0] }}
              transition={{ repeat: Infinity, duration: 1.6, ease: "easeInOut" }}
            >
              ↑
            </motion.span>
            <p>tap or swipe up to open</p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default EnvelopeReveal;
