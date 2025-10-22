import React, { useState, useEffect } from "react";
import "./Results.scss";

function Results() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchResults = async () => {
      const sessionId = sessionStorage.getItem("session_id");
      if (!sessionId) {
        setError("No session found — please log in again.");
        return;
      }
      try {
        const res = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/results?session_id=${sessionId}`
        );
        const json = await res.json();
        if (res.ok) setData(json);
        else setError(json.error);
      } catch {
        setError("Server unavailable");
      }
    };
    fetchResults();
  }, []);

  if (error)
    return (
      <div>
        <h2>Error</h2>
        <p>{error}</p>
        <a href="/">Go Back</a>
      </div>
    );

  if (!data) return <h2>Loading...</h2>;

  return (
    <div className="results">
      <h1>Your Emotional Breakdown</h1>
      <p>Analyzed {data.total_songs} tracks</p>
      {data.highlights.map((song, i) => (
        <div key={i}>
          <strong>{song.song}</strong> by {song.artist}: “{song.line}”
        </div>
      ))}
    </div>
  );
}

export default Results;
