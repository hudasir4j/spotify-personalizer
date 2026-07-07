import React, { useMemo } from "react";
import { clearOAuthStorage } from "../utils/oauthStorage";
import "./Home.scss";

const TIME_RANGES = [
  { value: "short_term", label: "last 4 weeks" },
  { value: "medium_term", label: "last 6 months" },
  { value: "long_term", label: "all time" },
];

function Home() {
  const notes = useMemo(
    () =>
      Array.from({ length: 8 }, (_, i) => ({
        id: i,
        left: Math.random() * 100,
        delay: Math.random() * 5,
        duration: 10 + Math.random() * 6,
        symbol: i % 2 === 0 ? "♪" : "♫",
      })),
    []
  );

  const startLogin = () => {
    clearOAuthStorage();
    const timeRange =
      document.getElementById("time-range")?.value || "medium_term";
    const trackLimit = document.getElementById("track-limit")?.value || "50";
    sessionStorage.setItem("time_range", timeRange);
    sessionStorage.setItem("track_limit", trackLimit);
    window.location.href = `${process.env.REACT_APP_BACKEND_URL}/login`;
  };

  return (
    <div>
      <div className="gradient">
        {notes.map((note) => (
          <div
            key={note.id}
            className="music-note"
            style={{
              left: `${note.left}%`,
              animationDuration: `${note.duration}s`,
              animationDelay: `${note.delay}s`,
            }}
          >
            {note.symbol}
          </div>
        ))}
        <div className="hero-text">
          <h1 className="hero-title">
            your life's soundtrack, <span id="decoded">decoded</span>
          </h1>
          <h2>see what moves you</h2>

          <div className="options-panel">
            <label htmlFor="time-range">time range</label>
            <select id="time-range" defaultValue="medium_term">
              {TIME_RANGES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <label htmlFor="track-limit">tracks to analyze</label>
            <select id="track-limit" defaultValue="50">
              <option value="25">25 tracks</option>
              <option value="50">50 tracks</option>
            </select>
          </div>

          <button type="button" onClick={startLogin} className="button">
            <span>log into spotify</span>
          </button>
        </div>
      </div>
    </div>
  );
}

export default Home;
