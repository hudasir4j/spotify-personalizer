import { BrowserRouter, Routes, Route, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Home from "./Pages/Home";
import Loading from "./Pages/Loading";
import Results from "./Pages/Results";
import "./App.css";

function LoadingWithRedirect() {
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const code = new URLSearchParams(window.location.search).get("code");
    if (!code) {
      setError("No authorization code");
      return;
    }

    const processAndCheck = async () => {
      try {
        const processRes = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/process?code=${code}`
        );
        const processData = await processRes.json();
        if (processData.error) throw new Error(processData.error);

        const sessionId = processData.session_id;
        sessionStorage.setItem("session_id", sessionId);

        const pollResults = async () => {
          try {
            const resultsRes = await fetch(
              `${process.env.REACT_APP_BACKEND_URL}/api/results?session_id=${sessionId}`
            );
            if (resultsRes.ok) {
              const resData = await resultsRes.json();
              if (resData.highlights?.length) {
                navigate("/results");
                return;
              }
            }
            setTimeout(pollResults, 2000);
          } catch {
            setTimeout(pollResults, 2000);
          }
        };

        pollResults();
      } catch (err) {
        setError("Processing failed: " + err.message);
      }
    };
    processAndCheck();
  }, [navigate]);

  if (error)
    return (
      <div>
        <p>{error}</p>
        <a href="/">Go Back</a>
      </div>
    );

  return <Loading />;
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
