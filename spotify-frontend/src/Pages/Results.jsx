import React, { useState, useEffect } from "react";
import EnvelopeReveal from "../components/EnvelopeReveal";
import ResultsContent from "../components/ResultsContent";
import { getVibeEnvelopeTeaser } from "../utils/vibeCopy";
import "./Results.scss";

function Results() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) {
      setError("No session found — please log in again.");
      return undefined;
    }

    let cancelled = false;
    let pollTimer = null;

    const fetchResults = async () => {
      try {
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 12000);
        const res = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/results?session_id=${sessionId}`,
          { signal: controller.signal }
        );
        clearTimeout(timeout);
        const json = await res.json();
        if (cancelled) return;
        if (res.ok) {
          setData(json);
          if (json.status !== "complete") {
            pollTimer = setTimeout(fetchResults, 2000);
          }
        } else {
          setError(json.error);
        }
      } catch {
        if (!cancelled) {
          setError("Server unavailable — try refreshing or log in again.");
        }
      }
    };

    fetchResults();
    return () => {
      cancelled = true;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, []);

  useEffect(() => {
    if (!data || data.previews_ready) return undefined;

    const sessionId = sessionStorage.getItem("session_id");
    if (!sessionId) return undefined;

    const timer = setInterval(async () => {
      try {
        const res = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/results?session_id=${sessionId}`
        );
        const json = await res.json();
        if (res.ok) {
          setData(json);
          if (json.previews_ready) clearInterval(timer);
        }
      } catch {
        /* keep polling briefly */
      }
    }, 2500);

    const stop = setTimeout(() => clearInterval(timer), 45000);
    return () => {
      clearInterval(timer);
      clearTimeout(stop);
    };
  }, [data?.previews_ready]);

  if (error) {
    return (
      <div className="results-status">
        <h2>something went wrong</h2>
        <p>{error}</p>
        <a href="/" className="status-btn">
          go back
        </a>
      </div>
    );
  }

  if (!data) {
    return (
      <div className="results-status">
        <h2>loading your breakdown...</h2>
      </div>
    );
  }

  if (!data.highlights?.length) {
    return (
      <div className="results-status">
        <h2>your emotional breakdown</h2>
        <p>no lyrics found for your top tracks</p>
        <p>
          Make sure GENIUS_TOKEN is set in your backend .env.local for fallback
          lyrics, then try again.
        </p>
        <a href="/" className="status-btn">
          ← analyze again
        </a>
      </div>
    );
  }

  const topTheme = [...(data.themes || [])].sort((a, b) => b.count - a.count)[0];

  if (!revealed) {
    return (
      <EnvelopeReveal
        onReveal={() => setRevealed(true)}
        teaser={
          topTheme ? getVibeEnvelopeTeaser(topTheme.theme) : undefined
        }
      />
    );
  }

  return <ResultsContent data={data} />;
}

export default Results;
