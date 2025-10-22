import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { useEffect, useState } from 'react';
import Home from './Pages/Home';
import Loading from './Pages/Loading';
import Results from './Pages/Results';
import './App.css'

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

    const processAndCheck = async () => {
      try {
        fetch(`${process.env.REACT_APP_BACKEND_URL}/api/process?code=${code}`);
        
        const checkResults = async () => {
          try {
            const response = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/results`);
            if (response.ok) {
              const data = await response.json();
              if (data.highlights && data.highlights.length > 0) {
                navigate('/results');
              } else {
                setTimeout(checkResults, 1000);
              }
            } else {
              setTimeout(checkResults, 1000);
            }
          } catch {
            setTimeout(checkResults, 1000);
          }
        };

        setTimeout(checkResults, 2000);
      } catch (err) {
        setError('Processing failed');
      }
    };

    processAndCheck();
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