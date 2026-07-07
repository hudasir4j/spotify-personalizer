import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { clearOAuthStorage, OAUTH_CODE_KEY } from "./utils/oauthStorage";
import Home from "./Pages/Home";
import Loading from "./Pages/Loading";
import Results from "./Pages/Results";
import "./App.css";

function LoadingWithRedirect() {
  const navigate = useNavigate();
  const [error, setError] = useState(null);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const [previews, setPreviews] = useState([]);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlCode = params.get("code");
    let code = urlCode;

    if (urlCode) {
      clearOAuthStorage();
      sessionStorage.setItem(OAUTH_CODE_KEY, urlCode);
      window.history.replaceState({}, "", "/loading");
    } else {
      code = sessionStorage.getItem(OAUTH_CODE_KEY);
    }

    if (!code) {
      setError("No authorization code — please log in again.");
      return;
    }

    const timeRange = sessionStorage.getItem("time_range") || "medium_term";
    const trackLimit = sessionStorage.getItem("track_limit") || "50";
    const codeKey = `oauth_session_${code.slice(0, 16)}`;
    let cancelled = false;
    let pollTimer = null;

    const handleSessionLost = () => {
      clearOAuthStorage();
      setError("Session expired — please log in again from the home page.");
    };

    const pollResults = (sessionId) => {
      if (cancelled || !sessionId) return;
      fetch(
        `${process.env.REACT_APP_BACKEND_URL}/api/results?session_id=${sessionId}`
      )
        .then((res) => res.json().then((data) => ({ ok: res.ok, status: res.status, data })))
        .then(({ ok, status, data }) => {
          if (cancelled) return;
          if (status === 404) {
            handleSessionLost();
            return;
          }
          if (!ok) throw new Error(data.error || "Failed to fetch results");

          setProgress(data.progress || { done: 0, total: 0 });
          if (data.highlights?.length) {
            setPreviews(data.highlights);
          }

          if (data.status === "complete") {
            sessionStorage.removeItem(OAUTH_CODE_KEY);
            sessionStorage.setItem("time_range", data.time_range || timeRange);
            navigate("/results");
            return;
          }
          pollTimer = setTimeout(() => pollResults(sessionId), 1500);
        })
        .catch(() => {
          if (!cancelled) {
            pollTimer = setTimeout(() => pollResults(sessionId), 1500);
          }
        });
    };

    const startPolling = (sessionId) => {
      sessionStorage.setItem("session_id", sessionId);
      pollResults(sessionId);
    };

    const existingSession = sessionStorage.getItem(codeKey);
    if (existingSession) {
      startPolling(existingSession);
      return () => {
        cancelled = true;
        if (pollTimer) clearTimeout(pollTimer);
      };
    }

    fetch(
      `${process.env.REACT_APP_BACKEND_URL}/api/process?code=${encodeURIComponent(code)}&time_range=${timeRange}&limit=${trackLimit}`
    )
      .then((res) => res.json().then((data) => ({ ok: res.ok, data })))
      .then(({ ok, data }) => {
        if (!ok || data.error) {
          throw new Error(data.error || "Processing failed");
        }
        // Always save — React Strict Mode may unmount before poll starts
        sessionStorage.setItem(codeKey, data.session_id);
        sessionStorage.setItem("session_id", data.session_id);
        sessionStorage.setItem("time_range", data.time_range || timeRange);
        if (cancelled) return;
        setProgress({ done: 0, total: data.total || 0 });
        startPolling(data.session_id);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err.message);
        }
      });

    return () => {
      cancelled = true;
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [navigate]);

  if (error) {
    return (
      <div className="loading-page">
        <div className="loading-content">
          <p className="status">{error}</p>
          <a href="/" className="status" style={{ color: "#a8ff78" }}>
            ← log in again
          </a>
        </div>
      </div>
    );
  }

  return <Loading progress={progress} previews={previews} />;
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/loading" element={<LoadingWithRedirect />} />
        <Route path="/results" element={<Results />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
