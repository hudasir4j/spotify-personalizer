import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Home from './Pages/Home';
import Loading from './Pages/Loading';
import Results from './Pages/Results';
import './App.css';

function LoadingWithRedirect() {
  const navigate = useNavigate();
  const [error, setError] = useState(null);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');

    if (!code) {
      setError('No authorization code');
      return;
    }

    const processAndNavigate = async () => {
      try {
        const response = await fetch(
          `${process.env.REACT_APP_BACKEND_URL}/api/process?code=${encodeURIComponent(code)}`
        );
        const data = await response.json();
        if (!response.ok) {
          setError(data.error || 'Failed to process data');
          return;
        }
        localStorage.setItem('resultsData', JSON.stringify(data));
        navigate('/results');
      } catch (err) {
        console.error(err);
        setError('Could not connect to server');
      }
    };

    processAndNavigate();
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
