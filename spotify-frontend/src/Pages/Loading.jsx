import React, { useState, useEffect } from 'react';
import './Loading.scss';

function Loading() {
  const [dots, setDots] = useState('');

  useEffect(() => {
    const interval = setInterval(() => {
      setDots(prev => prev.length >= 3 ? '' : prev + '.');
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="loading-page">
      <div className="loading-content">
        <h1>analyzing your music{dots}</h1>
        <div className="progress-bar">
          <div className="progress-fill"></div>
        </div>
        <p className="status">fetching lyrics, running sentiment analysis</p>
        <p className="wait-time">the beta version will take longer than usual...</p>
      </div>
    </div>
  );
}

export default Loading;
