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
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get("code");

    if (!code) {
      setError("No authorization code found.");
      return;
    }

    const processCode = async () => {
      try {
        // Call backend to process user tracks
        const res = await fetch(`${import.meta.env.VITE_BACKEND_URL}/api/process?code=${code}`);
        const data = await res.json();

        if (res.ok && data.status === "complete") {
          navigate("/results");
        } else {
          setError(data.error || "Processing failed");
        }
      } catch (err) {
        setError("Could not connect to backend");
      }
    };

    processCode();
  }, [navigate]);

  if (error) {
    return (
      <div className="loading-page">
        <p>{error}</p>
        <a href="/">Go back</a>
      </div>
    );
  }

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
