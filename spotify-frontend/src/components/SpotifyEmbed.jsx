import React, { useEffect, useRef } from "react";

function SpotifyEmbed({ trackId, previewUrl }) {
  const audioRef = useRef(null);

  useEffect(() => {
    if (trackId || !previewUrl) return;
    const audio = audioRef.current;
    if (!audio) return;
    audio.load();
  }, [trackId, previewUrl]);

  if (trackId) {
    return (
      <div className="spotify-embed-wrap">
        <iframe
          title="Spotify preview"
          src={`https://open.spotify.com/embed/track/${trackId}?utm_source=generator&theme=0`}
          width="100%"
          height="152"
          frameBorder="0"
          allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture"
          loading="lazy"
        />
      </div>
    );
  }

  if (previewUrl) {
    return (
      <div className="spotify-embed-wrap">
        <audio ref={audioRef} controls src={previewUrl} className="preview-audio">
          Your browser does not support audio preview.
        </audio>
      </div>
    );
  }

  return null;
}

export default SpotifyEmbed;
