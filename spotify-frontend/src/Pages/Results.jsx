import React, { useState, useEffect } from 'react';
import './Results.scss';

function Results() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_BACKEND_URL}/api/results`);
      const json = await response.json();
      
      if (response.ok) {
        setData(json);
      } else {
        setError(json.error || 'Failed to load results');
      }
    } catch (err) {
      setError('Could not connect to server');
    } finally {
      setLoading(false);
    }
  };

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
        <h2>error</h2>
        <p>{error}</p>
        <a href="/" className="back-button">back</a>
      </div>
    );
  }

  if (!data) return null;

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
          <h1>your emotional breakdown</h1>
          <p className="subtitle">analyzed {data.total_songs} tracks</p>
        </header>

        <section className="compact-section">
          <h2>most emotional lines</h2>
          <div className="lyrics-list">
            {data.highlights.map((song, index) => (
              <div key={index} className="lyric-row">
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
          <h2>recurring themes</h2>
          <div className="themes-container">
            {data.themes.map((theme, index) => {
              const percentage = (theme.count / data.total_songs) * 100;
              return (
                <div key={index} className="theme-bar">
                  <div className="theme-info">
                    <span className="theme-name">{theme.theme}</span>
                    <span className="theme-count">{theme.count}</span>
                  </div>
                  <div className="bar-container">
                    <div 
                      className="bar-fill" 
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>

        <section className="words-section">
          <h2>most common words</h2>
          <div className="words-grid">
            {data.top_words.map((item, index) => (
              <div key={index} className="word-item">
                <span className="word">{item.word}</span>
                <span className="count">{item.count}</span>
              </div>
            ))}
          </div>
        </section>

        <div className="footer-nav">
          <a href="/" className="back-link">← back</a>
        </div>
      </div>
    </div>
  );
}

export default Results;