import React, { useState, useEffect } from "react";
import "./Results.scss";

function Results() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      try {
        const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/api/results`);
        if (!response.ok) {
          const errData = await response.json();
          setError(errData.error || "Failed to fetch results");
          setLoading(false);
          return;
        }
        const json = await response.json();
        if (!json.highlights || json.highlights.length === 0) {
          setError("No results available");
        } else {
          setData(json);
        }
      } catch {
        setError("Could not connect to backend");
      } finally {
        setLoading(false);
      }
    };

    fetchResults();
  }, []);

  if (loading) {
    return (
      <div className="loading-screen">
        <h2>processing your data...</h2>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error-screen">
        <h2>Error</h2>
        <p>{error}</p>
        <a href="/" className="back-button">← Back</a>
      </div>
    );
  }

  const maxThemeCount = Math.max(...data.themes.map(t => t.count));

  const floatingWords = data.top_words.map((wordObj, i) => ({
    word: wordObj.word,
    left: Math.random() * 100,
    delay: Math.random() * 5,
    duration: 15 + Math.random() * 10,
  }));

  return (
    <div className="results-page">
      {floatingWords.map((item, i) => (
        <div
          key={i}
          className="floating-word"
          style={{
            left: `${item.left}%`,
            animationDuration: `${item.duration}s`,
            animationDelay: `${item.delay}s`
          }}
        >
          {item.word}
        </div>
      ))}

      <div className="content">
        <header className="results-header">
          <h1>Your Emotional Breakdown</h1>
          <p className="subtitle">Analyzed {data.total_songs} tracks</p>
        </header>

        <section className="compact-section">
          <h2>Most Emotional Lines</h2>
          <div className="lyrics-list">
            {data.highlights.map((song, idx) => (
              <div key={idx} className="lyric-row">
                <div className="song-info">
                  <span className="song-title">{song.song}</span>
                  <span className="artist-name">{song.artist}</span>
                </div>
                <div className="lyric-text">"{song.line}"</div>
                <span className="theme-label">{song.theme}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="themes-section">
          <h2>Recurring Themes</h2>
          <div className="themes-container">
            {data.themes.map((theme, idx) => {
              const percentage = (theme.count / data.total_songs) * 100;
              return (
                <div key={idx} className="theme-bar">
                  <div className="theme-info">
                    <span className="theme-name">{theme.theme}</span>
                    <span className="theme-count">{theme.count}</span>
                  </div>
                  <div className="bar-container">
                    <div className="bar-fill" style={{ width: `${percentage}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="words-section">
          <h2>Most Common Words</h2>
          <div className="words-grid">
            {data.top_words.map((item, idx) => (
              <div key={idx} className="word-item">
                <span className="word">{item.word}</span>
                <span className="count">{item.count}</span>
              </div>
            ))}
          </div>
        </section>

        <div className="footer-nav">
          <a href="/" className="back-link">← Back</a>
        </div>
      </div>
    </div>
  );
}

export default Results;
